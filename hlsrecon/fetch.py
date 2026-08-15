"""계측형 HTTP 페처.

일반 다운로더와 다른 점은 매 요청의 지연·크기·재시도 횟수를 기록한다는 것이다.
송출 검증에서 "받아졌다"보다 "언제·얼마나 걸려 받아졌다"가 중요하기 때문이다.
"""

from __future__ import annotations

import gzip
import hashlib
import time
import urllib.error
import urllib.request
import zlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Callable, Sequence
from urllib.parse import quote, urlencode, urlsplit, urlunsplit

DEFAULT_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
# 브라우저 UA 로 요청하면 서버가 압축 응답을 돌려주는 경우가 흔하다. 요청해두고
# 직접 해제한다 — 텍스트인 플레이리스트에서 전송량이 크게 준다.
# brotli(br)는 표준 라이브러리로 풀 수 없으므로 요청하지 않는다.
ACCEPT_ENCODING = "gzip, deflate"


# URL 각 부분에서 그대로 두어도 되는 문자. `%` 를 남기는 것이 핵심이다 — 이미
# 인코딩된 주소를 다시 인코딩하면 `%20` 이 `%2520` 이 되어 다른 주소가 된다.
_PATH_SAFE = "/%:@!$&'()*+,;=~"
_QUERY_SAFE = _PATH_SAFE + "?"


def normalize_url(url: str) -> str:
    """요청에도 ffmpeg 에도 그대로 넘길 수 있는 형태로 URL 을 정규화한다.

    경로에 한글이 퍼센트 인코딩 없이 박힌 주소를 그대로 내보내는 송출이 있다
    (`…/subtitles/그렌라간01.srt`). URL 은 규격상 ASCII 이므로 그런 주소는
    urllib 이 요청 줄을 쓰는 순간 UnicodeEncodeError 로 죽고, ffmpeg 도 입력을
    열지 못한다. 받는 쪽마다 따로 손보면 한 곳은 반드시 빠지므로 여기서 한 번에
    맞춘다.
    """
    u = urlsplit(url)
    return urlunsplit(
        (
            u.scheme,
            u.netloc,
            quote(u.path, safe=_PATH_SAFE),
            quote(u.query, safe=_QUERY_SAFE),
            quote(u.fragment, safe=_QUERY_SAFE),
        )
    )


def _decompress(body: bytes, encoding: str) -> bytes:
    """Content-Encoding 에 따라 본문을 해제한다."""
    enc = encoding.lower().strip()
    if not body or enc in ("", "identity"):
        return body
    if enc in ("gzip", "x-gzip"):
        return gzip.decompress(body)
    if enc == "deflate":
        # zlib 래퍼를 붙이는 서버와 raw deflate 를 보내는 서버가 섞여 있다.
        try:
            return zlib.decompress(body)
        except zlib.error:
            return zlib.decompress(body, -zlib.MAX_WBITS)
    raise ValueError(f"해제할 수 없는 Content-Encoding: {encoding}")


@dataclass
class FetchResult:
    """요청 한 건의 결과와 계측치."""

    url: str
    ok: bool
    status: int = 0
    body: bytes = b""  # 압축을 푼 뒤의 본문
    size: int = 0  # 해제 후 크기
    wire_size: int = 0  # 실제로 회선을 지나간 바이트 (압축된 상태)
    encoding: str = ""  # Content-Encoding 원문
    ttfb_ms: float = 0.0  # time to first byte — 서버 응답 개시까지
    total_ms: float = 0.0  # 본문 수신 완료까지
    attempts: int = 1
    error: str = ""
    content_type: str = ""
    sha256: str = ""
    # 핫링크 차단 CDN 은 플레이어 페이지의 origin 을 이 헤더로 되돌려준다.
    # 성공 응답에도, 403 에도 붙어 오므로 Referer 추론의 근거가 된다.
    allow_origin: str = ""

    @property
    def compressed(self) -> bool:
        return bool(self.encoding) and self.encoding.lower().strip() != "identity"

    @property
    def throughput_mbps(self) -> float:
        """회선 성능이므로 해제 후 크기가 아니라 실제 전송 바이트로 계산한다."""
        wire = self.wire_size or self.size
        if self.total_ms <= 0 or not wire:
            return 0.0
        return (wire * 8) / (self.total_ms / 1000) / 1_000_000


class Fetcher:
    def __init__(
        self,
        headers: dict[str, str] | None = None,
        timeout: float = 30.0,
        retries: int = 3,
        backoff: float = 0.8,
    ) -> None:
        self.headers = {"User-Agent": DEFAULT_UA, **(headers or {})}
        self.timeout = timeout
        self.retries = retries
        self.backoff = backoff

    def get(
        self,
        url: str,
        byterange: tuple[int, int] | None = None,
        extra: dict[str, str] | None = None,
    ) -> FetchResult:
        """단건 GET. byterange 는 (length, offset) — HLS EXT-X-BYTERANGE 표기 순서."""
        return self._send(url, byterange=byterange, extra=extra)

    def post(
        self, url: str, fields: dict[str, str], extra: dict[str, str] | None = None
    ) -> FetchResult:
        """폼 POST. 재생 소스를 XHR 로만 알려주는 플레이어를 위해 있다.

        계측·재시도·헤더는 GET 과 같은 경로를 쓴다 — 요청 방식이 다르다고 별도
        코드를 두면 자동 채택한 Referer 나 사용자 헤더가 한쪽에만 반영된다.
        """
        return self._send(url, data=urlencode(fields).encode(), extra=extra)

    def _send(
        self,
        url: str,
        byterange: tuple[int, int] | None = None,
        data: bytes | None = None,
        extra: dict[str, str] | None = None,
    ) -> FetchResult:
        # extra 는 이 요청에만 얹는 헤더다. 페이지를 타고 들어가는 동안 Referer 가
        # 단계마다 달라지는데(부모 페이지 → iframe → XHR), 그걸 인스턴스 헤더에
        # 써 버리면 다음 요청까지 오염된다. 사용자 지정 헤더는 그대로 이긴다.
        headers = {**self.headers, **{k: v for k, v in (extra or {}).items()
                                      if k not in self.headers}}
        url = normalize_url(url)
        if data is not None:
            headers.setdefault("Content-Type", "application/x-www-form-urlencoded")
            headers.setdefault("X-Requested-With", "XMLHttpRequest")
        if byterange:
            length, offset = byterange
            headers["Range"] = f"bytes={offset}-{offset + length - 1}"
            # 부분 요청에 압축이 걸리면 바이트 범위의 의미가 깨진다.
            headers.setdefault("Accept-Encoding", "identity")
        else:
            headers.setdefault("Accept-Encoding", ACCEPT_ENCODING)

        last_err = ""
        last_status = 0
        last_origin = ""
        for attempt in range(1, self.retries + 1):
            req = urllib.request.Request(url, data=data, headers=headers)
            t0 = time.perf_counter()
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    ttfb = (time.perf_counter() - t0) * 1000
                    raw = resp.read()
                    total = (time.perf_counter() - t0) * 1000
                    encoding = resp.headers.get("Content-Encoding", "") or ""
                    try:
                        body = _decompress(raw, encoding)
                    except Exception as e:  # noqa: BLE001 — 해제 실패는 응답 손상으로 다룬다
                        last_err = f"Content-Encoding={encoding} 해제 실패: {e}"
                        last_status = resp.status
                        break
                    return FetchResult(
                        url=url,
                        ok=True,
                        status=resp.status,
                        body=body,
                        size=len(body),
                        wire_size=len(raw),
                        encoding=encoding,
                        ttfb_ms=ttfb,
                        total_ms=total,
                        attempts=attempt,
                        content_type=resp.headers.get("Content-Type", ""),
                        sha256=hashlib.sha256(body).hexdigest(),
                        allow_origin=resp.headers.get("Access-Control-Allow-Origin", "") or "",
                    )
            except urllib.error.HTTPError as e:
                last_status, last_err = e.code, f"HTTP {e.code} {e.reason}"
                last_origin = (e.headers or {}).get("Access-Control-Allow-Origin", "") or ""
                # 4xx 는 재시도해도 결과가 같다 (401/403/404 = 토큰 만료·핫링크 차단)
                if 400 <= e.code < 500 and e.code not in (408, 429):
                    break
            except Exception as e:  # noqa: BLE001 — 네트워크 예외 전종을 계측 대상으로 삼는다
                last_err = f"{type(e).__name__}: {e}"

            if attempt < self.retries:
                time.sleep(self.backoff * (2 ** (attempt - 1)))

        return FetchResult(
            url=url,
            ok=False,
            status=last_status,
            attempts=self.retries,
            error=last_err,
            allow_origin=last_origin,
        )

    def get_text(self, url: str, extra: dict[str, str] | None = None) -> str:
        r = self.get(url, extra=extra)
        if not r.ok:
            raise RuntimeError(f"요청 실패: {url}\n  {r.error}")
        return r.body.decode("utf-8", errors="replace")

    def get_many(
        self,
        items: Sequence[tuple[str, tuple[int, int] | None]],
        jobs: int = 8,
        on_done: Callable[[int, FetchResult], None] | None = None,
    ) -> list[FetchResult]:
        """병렬 GET. 반환 순서는 입력 순서를 유지한다."""
        results: list[FetchResult | None] = [None] * len(items)
        with ThreadPoolExecutor(max_workers=jobs) as pool:
            futures = {
                pool.submit(self.get, url, rng): i for i, (url, rng) in enumerate(items)
            }
            done = 0
            for fut in as_completed(futures):
                i = futures[fut]
                res = fut.result()
                results[i] = res
                done += 1
                if on_done:
                    on_done(done, res)
        return [r for r in results if r is not None]
