"""자막 트랙 선택·추출·검증.

자막도 영상과 똑같이 조각나 있고, 각 WebVTT 조각은 헤더에 X-TIMESTAMP-MAP
(90kHz MPEG-TS 클럭과 자막 로컬 시각의 대응표)을 달고 온다. 이 매핑을 잘못
적용하면 자막 전체가 일정량 밀리므로, 병합은 ffmpeg 에 위임하고 여기서는
'무엇을 받을지'와 '받은 결과가 영상과 맞는지'만 책임진다.

자막이 플레이리스트 밖 별도 파일로 놓인 경우(sidecar)는 트랙 목록에 나타나지
않아 위 경로로는 발견되지 않는다. 그쪽은 URL 을 조립해 직접 받되, 받은 뒤의
검증은 같은 함수(measure)를 쓴다 — 출처가 달라도 '영상과 맞는가'의 기준은 하나다.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import quote, urlparse, urlunparse

from .fetch import Fetcher
from .naming import name_variants
from .playlist import Media, is_playlist_uri
from .probe import input_args, require

# WebVTT(00:00:01.000) 와 SubRip(00:00:01,000) 의 큐 시각을 함께 받는다.
_CUE_RE = re.compile(
    r"(?:(\d+):)?(\d{2}):(\d{2})[.,](\d{3})\s*-->\s*(?:(\d+):)?(\d{2}):(\d{2})[.,](\d{3})"
)

_FORMAT_CODEC = {"vtt": "webvtt", "srt": "subrip"}
# 컨테이너에 자막을 넣을 때 쓰는 코덱. MP4 계열은 mov_text 외에는 사실상 안 된다.
_EMBED_CODEC = {".mkv": "srt", ".mp4": "mov_text", ".m4v": "mov_text"}


@dataclass
class SubtitleResult:
    track: Media
    path: Path | None = None
    ok: bool = False
    cues: int = 0
    first_cue: float = 0.0
    last_cue: float = 0.0
    duplicates: int = 0  # 세그먼트 경계 중복으로 제거된 큐 수
    header_leaks: int = 0  # 본문에 조각 헤더가 섞여 있어 정제한 큐 수
    offset: float = 0.0  # X-TIMESTAMP-MAP 으로 보정한 정렬 오프셋(초)
    sidecar: bool = False  # 플레이리스트 밖 별도 파일에서 받았는가
    tried: list[str] = field(default_factory=list)  # sidecar 조립 시 시도한 URL
    error: str = ""

    @property
    def span(self) -> float:
        return max(0.0, self.last_cue - self.first_cue)


@dataclass
class SubtitleReport:
    requested: str = ""
    results: list[SubtitleResult] = field(default_factory=list)
    # --sub-range 로 이웃 화수까지 함께 받은 것. 현재 영상과 짝이 아니므로
    # 타임라인 검사 대상이 아니다 — 수집 결과로만 기록한다.
    extra: list[SubtitleResult] = field(default_factory=list)
    embedded: list[str] = field(default_factory=list)  # 영상에 내장되어 별도 추출 불가한 트랙
    embed_tracks: list[Media] = field(default_factory=list)  # --sub-embed 로 컨테이너에 넣은 트랙
    embed_span: tuple[float, float] | None = None  # 내장 자막의 실제 시각 범위
    embed_offsets: dict[str, float] = field(default_factory=dict)

    @property
    def ok(self) -> list[SubtitleResult]:
        return [r for r in self.results if r.ok]


def select(tracks: list[Media], spec: str) -> list[Media]:
    """--subs 값에 따라 받을 자막을 고른다.

    all      전부
    default  DEFAULT=YES 또는 AUTOSELECT=YES 인 것만
    ko,en    해당 LANGUAGE 만 (접두 일치 — 'ko' 는 'ko-KR' 도 받는다)
    none     받지 않음
    """
    spec = (spec or "none").strip().lower()
    external = [t for t in tracks if not t.is_embedded]
    if spec == "none":
        return []
    if spec == "all":
        return external
    if spec == "default":
        return [t for t in external if t.default or t.autoselect]
    wanted = [s.strip() for s in spec.split(",") if s.strip()]
    return [
        t
        for t in external
        if any(t.language.lower().startswith(w) for w in wanted)
    ]


def _out_path(base: Path, track: Media, fmt: str) -> str:
    """out.mp4 + ko 트랙 → out.ko.vtt. 언어가 겹치면 순번을 붙인다.

    LANGUAGE 를 비워 내보내는 송출이 있다. 그때 자리를 채우려고 `track0` 같은
    표식을 넣으면 영상과 짝이 맞지 않는 이름(`영상.track0.srt`)이 되어 재생기가
    자막을 자동으로 붙이지 못한다. 근거 없는 이름을 지어내느니 언어 부분을 비운다.
    """
    lang = re.sub(r"[^A-Za-z0-9-]", "", track.language)
    parts = [p for p in (lang, "forced" if track.forced else "") if p]
    return str(base.with_suffix("")) + "".join(f".{p}" for p in parts) + f".{fmt}"


def extract(
    tracks: list[Media],
    out: Path,
    fmt: str,
    fetcher: Fetcher,
    offsets: dict[str, float] | None = None,
) -> list[SubtitleResult]:
    """자막 트랙을 각각 별도 파일(sidecar)로 뽑는다.

    트랙 URI 가 자막 플레이리스트면 조각을 이어붙여야 하므로 ffmpeg 에 맡긴다.
    완성된 자막 파일을 URI 로 그대로 선언하는 송출도 있는데(규격은 플레이리스트를
    요구하지만 실제로 그렇게 나간다), 그쪽은 받아서 저장하면 끝이다 — 이어붙일
    조각이 없는데 ffmpeg 를 태우면 원본 바이트를 잃기만 하고 얻는 것이 없다.
    받는 방법은 이미 `fetch_sidecar` 가 알고 있으므로 그리로 넘긴다.

    offsets 는 트랙 URI → 정렬 오프셋(초). ffmpeg 가 적용하지 않는
    X-TIMESTAMP-MAP 보정을 추출 후에 직접 반영한다. 완성 파일에는 그 매핑이
    없으므로 대상이 아니다.
    """
    codec = _FORMAT_CODEC[fmt]
    results: list[SubtitleResult] = []
    seen: dict[str, int] = {}

    for track in tracks:
        seen[track.language] = seen.get(track.language, 0) + 1
        dest = Path(_out_path(out, track, fmt))
        if seen[track.language] > 1:  # 같은 언어가 여럿이면 덮어쓰지 않는다
            dest = Path(f"{dest.with_suffix('')}.{seen[track.language]}.{fmt}")

        if not is_playlist_uri(track.uri or ""):
            results.append(fetch_sidecar([track.uri or ""], dest, fetcher, fmt, track))
            continue

        cmd = [require("ffmpeg"), "-hide_banner", "-loglevel", "error", "-y"]
        cmd += input_args(fetcher.headers, track.uri or "")
        cmd += [
            "-i", track.uri or "",
            "-map", "0:s:0",
            "-c:s", codec,
            str(dest),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        res = SubtitleResult(track=track, path=dest)
        if proc.returncode != 0:
            res.error = proc.stderr.strip()[-300:] or f"ffmpeg exit {proc.returncode}"
        elif not dest.exists() or dest.stat().st_size == 0:
            res.error = "빈 파일이 생성됐다 — 자막 조각에 큐가 없다"
        else:
            res.ok = True
            res.duplicates, res.header_leaks = dedupe(dest, fmt)
            res.offset = (offsets or {}).get(track.uri or "", 0.0)
            shift(dest, fmt, res.offset)
            res.cues, res.first_cue, res.last_cue = measure(dest)
            if res.cues == 0:
                res.ok, res.error = False, "큐가 하나도 없다"
        results.append(res)
    return results


# 조각마다 붙는 WebVTT 파일 헤더. 조각을 이어붙이면 앞 큐의 본문으로 흡수된다.
_SEG_HEADER_RE = re.compile(r"^[ \t]*(?:WEBVTT.*|X-TIMESTAMP-MAP=.*)$", re.MULTILINE)


def _clean_body(body: str) -> str:
    """큐 본문에 섞여 들어온 조각 헤더를 걷어낸다.

    ffmpeg 가 자막 조각을 이어붙일 때 각 조각 선두의 `WEBVTT` 와
    `X-TIMESTAMP-MAP=` 줄을 직전 큐의 본문으로 흡수한다. 그대로 두면 그 문자열이
    자막으로 화면에 표시되므로 제거한다.
    """
    return "\n".join(
        ln for ln in _SEG_HEADER_RE.sub("", body).split("\n") if ln.strip()
    ).strip()


_TSMAP_RE = re.compile(
    r"X-TIMESTAMP-MAP\s*=\s*(?=.*LOCAL:(?P<local>[\d:.]+))(?=.*MPEGTS:(?P<mpegts>-?\d+))",
    re.IGNORECASE,
)
MPEGTS_HZ = 90000  # MPEG-TS 시스템 클럭


def timestamp_offset(first_segment: bytes, video_pts0: float) -> float | None:
    """자막 조각의 X-TIMESTAMP-MAP 과 영상 첫 PTS 로 정렬 오프셋(초)을 구한다.

    X-TIMESTAMP-MAP=LOCAL:<자막 시각>,MPEGTS:<90kHz 클럭> 은 '자막의 이 시각이
    영상 타임라인의 이 클럭값에 해당한다'는 대응표다. ffmpeg 8.1.1 은 입력 구성과
    무관하게 이 매핑을 적용하지 않으므로(실측: 마스터 입력으로 열어도 MPEGTS 를 바꾼
    결과가 같다) 직접 계산해 보정한다. 0 이 아니면 자막이 그만큼 밀려 있다는 뜻이다.
    """
    head = first_segment[:2048].decode("utf-8", errors="replace")
    m = _TSMAP_RE.search(head)
    if not m:
        return None
    raw = m.group("mpegts")
    try:
        mpegts = int(raw)
    except ValueError:
        return None
    # 33비트 부호 없는 값이 규격이라 음수는 무효다 — 매핑 자체를 신뢰하지 않는다.
    if mpegts < 0:
        return None

    local = m.group("local")
    parts = [float(p) for p in local.split(":")]
    while len(parts) < 3:
        parts.insert(0, 0.0)
    local_sec = parts[0] * 3600 + parts[1] * 60 + parts[2]

    return (mpegts / MPEGTS_HZ) - video_pts0 - local_sec


def shift(path: Path, fmt: str, seconds: float) -> int:
    """자막 파일의 모든 큐 시각을 seconds 만큼 이동한다. 반환: 이동한 큐 수."""
    if abs(seconds) < 0.001:
        return 0

    def fmt_time(total: float) -> str:
        total = max(0.0, total)
        h, r = divmod(total, 3600)
        m, s = divmod(r, 60)
        sep = "." if fmt == "vtt" else ","
        return f"{int(h):02d}:{int(m):02d}:{int(s):02d}{sep}{int(round((s % 1) * 1000)):03d}"

    moved = 0

    def repl(m: re.Match[str]) -> str:
        nonlocal moved
        sh, sm, ss, sms, eh, em, es, ems = m.groups()
        start = int(sh or 0) * 3600 + int(sm) * 60 + int(ss) + int(sms) / 1000
        end = int(eh or 0) * 3600 + int(em) * 60 + int(es) + int(ems) / 1000
        moved += 1
        return f"{fmt_time(start + seconds)} --> {fmt_time(end + seconds)}"

    text = path.read_text(encoding="utf-8", errors="replace")
    path.write_text(_CUE_RE.sub(repl, text), encoding="utf-8")
    return moved


def _cue_bounds(line: str) -> tuple[float, float] | None:
    m = _CUE_RE.search(line)
    if not m:
        return None
    sh, sm, ss, sms, eh, em, es, ems = m.groups()
    return (
        int(sh or 0) * 3600 + int(sm) * 60 + int(ss) + int(sms) / 1000,
        int(eh or 0) * 3600 + int(em) * 60 + int(es) + int(ems) / 1000,
    )


def dedupe(path: Path, fmt: str) -> tuple[int, int]:
    """이어붙인 자막을 정리한다 — 조각 헤더 제거 + 경계 중복 큐 제거.

    HLS 규격은 구간에 걸치는 큐를 인접 세그먼트 양쪽에 넣는 것을 허용하고,
    실제 송출도 그렇게 나간다. ffmpeg 는 조각을 이어붙이기만 하므로 그대로 두면
    같은 자막이 두 번 실리고, 조각 헤더까지 본문에 섞인다.
    병합은 위임하되 이 후처리는 여기서 책임진다.

    반환: (제거한 중복 큐 수, 헤더가 섞여 있던 큐 수)
    """
    text = path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")
    blocks = [b for b in re.split(r"\n[ \t]*\n", text.strip("﻿").strip()) if b.strip()]

    header = ""
    if blocks and blocks[0].lstrip().upper().startswith("WEBVTT"):
        header = blocks.pop(0)

    seen: set[tuple[float, float, str]] = set()
    kept: list[tuple[float, float, str, str]] = []  # (start, end, 타이밍줄, 본문)
    preserved: list[str] = []  # NOTE·STYLE 등 큐가 아닌 블록
    removed = 0
    leaked = 0

    for block in blocks:
        lines = block.split("\n")
        # SubRip 은 블록 첫 줄이 일련번호다 — 재작성 때 새로 매기므로 버린다.
        if fmt == "srt" and lines and lines[0].strip().isdigit():
            lines = lines[1:]
        idx = next((i for i, ln in enumerate(lines) if "-->" in ln), None)
        if idx is None:
            preserved.append(block)
            continue
        bounds = _cue_bounds(lines[idx])
        if bounds is None:
            preserved.append(block)
            continue
        raw_body = "\n".join(lines[idx + 1 :]).strip()
        # 헤더 정제를 중복 판정보다 먼저 한다. 오염된 쪽과 깨끗한 쪽의 본문이
        # 달라 보이면 같은 큐인데도 중복으로 잡히지 않는다.
        body = _clean_body(raw_body)
        if body != raw_body:
            leaked += 1
        key = (round(bounds[0], 3), round(bounds[1], 3), body)
        if key in seen:
            removed += 1
            continue
        seen.add(key)
        kept.append((bounds[0], bounds[1], lines[idx].strip(), body))

    if not (removed or leaked):
        return 0, 0

    kept.sort(key=lambda c: (c[0], c[1]))
    out: list[str] = []
    if fmt == "vtt":
        out.append(header or "WEBVTT")
        out += preserved
        for _, _, timing, body in kept:
            out.append(f"{timing}\n{body}")
    else:
        for n, (_, _, timing, body) in enumerate(kept, 1):
            out.append(f"{n}\n{timing}\n{body}")
    path.write_text("\n\n".join(out) + "\n", encoding="utf-8")
    return removed, leaked


def measure(path: Path) -> tuple[int, float, float]:
    """자막 파일에서 큐 개수와 시작·종료 시각을 읽는다."""
    text = path.read_text(encoding="utf-8", errors="replace")
    starts: list[float] = []
    ends: list[float] = []
    for m in _CUE_RE.finditer(text):
        sh, sm, ss, sms, eh, em, es, ems = m.groups()
        starts.append(int(sh or 0) * 3600 + int(sm) * 60 + int(ss) + int(sms) / 1000)
        ends.append(int(eh or 0) * 3600 + int(em) * 60 + int(es) + int(ems) / 1000)
    if not starts:
        return 0, 0.0, 0.0
    return len(starts), min(starts), max(ends)


def embed_args(
    out: Path,
    tracks: list[Media],
    headers: dict[str, str] | None = None,
    offsets: dict[str, float] | None = None,
) -> tuple[list[str], list[str], str]:
    """자막을 영상 컨테이너에 함께 넣기 위한 ffmpeg 인자를 만든다.

    ffmpeg 의 입력 옵션은 해당 -i 바로 앞에 놓여야 하므로, 자막 입력에 필요한
    프로토콜 허용·헤더를 각 -i 앞에 직접 붙여서 돌려준다. 그래야 영상 입력이
    로컬 파일이든 원격 HLS 든 상관없이 같은 인자를 쓸 수 있다.

    반환: (입력 인자, 매핑·메타데이터 인자, 자막 코덱)
    """
    codec = _EMBED_CODEC.get(out.suffix.lower(), "")
    if not codec:
        raise ValueError(f"{out.suffix} 컨테이너에는 자막을 내장할 수 없다 — .mkv 를 쓸 것")

    inputs: list[str] = []
    maps: list[str] = ["-map", "0"]
    for i, track in enumerate(tracks, start=1):
        inputs += input_args(headers, track.uri or "")
        # ffmpeg 는 자막 입력의 X-TIMESTAMP-MAP 을 스스로 적용하지 않으므로,
        # 미리 계산한 정렬 오프셋을 입력 옵션으로 직접 준다.
        off = (offsets or {}).get(track.uri or "", 0.0)
        if abs(off) >= 0.001:
            inputs += ["-itsoffset", f"{off:.3f}"]
        inputs += ["-i", track.uri or ""]
        maps += ["-map", f"{i}:s:0"]
        if track.language:
            maps += [f"-metadata:s:s:{i - 1}", f"language={track.language}"]
        if track.name:
            maps += [f"-metadata:s:s:{i - 1}", f"title={track.name}"]
        if track.forced:
            maps += [f"-disposition:s:{i - 1}", "forced"]
    return inputs, maps, codec


# ─────────────────────────────────────────────────────────────────────────────
# 사이드카 자막 — 플레이리스트 밖 별도 파일
# ─────────────────────────────────────────────────────────────────────────────
#
# 자막을 #EXT-X-MEDIA 로 선언하지 않고 정적 파일로 따로 두는 송출이 있다. 이때
# 자막 URL 의 세 조각 중 둘은 영상 쪽에서 얻을 수 있고, 하나는 얻을 수 없다.
#
#   호스트   영상 응답의 Access-Control-Allow-Origin 이 플레이어 origin 을 알려준다.
#            자막도 같은 origin 에 놓이므로 그대로 쓴다 (cli._adopt_origin 이 이미
#            이 값을 Referer 로 채택해 두므로, 새로 요청하지 않고 재사용한다).
#   경로     사이트별 고정 규칙. 아래 SIDECAR_PATHS 에 실측한 것만 둔다.
#   이름     영상 URL 이 불투명 해시라면 어디에서도 유도되지 않는다. 다만 받는 쪽은
#            이미 그 영상의 이름을 알고 있다 — 출력 파일명이 곧 그 이름이다.
#            그래서 기본값을 -o 의 stem 으로 두고, 다르면 --sub-name 으로 덮는다.

# 앞에서부터 시도하고 첫 성공에서 멈춘다. 규칙이 확인된 사이트를 추가하는 지점 —
# 실측으로 200 을 받은 경로만 둔다. 짐작으로 넣은 경로는 실패할 때마다 헛요청이 된다.
SIDECAR_PATHS = ("/subtitles/old/{name}{ext}",)
SIDECAR_EXTS = (".srt", ".vtt")


def sidecar_urls(name: str, origin: str) -> list[str]:
    """이름과 origin 으로 자막 URL 후보를 조립한다 (경로 × 확장자 × 이름 표기)."""
    u = urlparse(origin.strip())
    if u.scheme not in ("http", "https") or not u.netloc:
        raise ValueError(f"자막 origin 이 URL 이 아니다: {origin!r}")
    base = urlunparse((u.scheme, u.netloc, "", "", "", ""))
    urls: list[str] = []
    for variant in name_variants(name):
        # 한글·공백이 든 이름이 그대로 경로에 들어가므로 인코딩한다. '/' 도 이름의
        # 일부일 수는 없으니 safe 를 비워 통째로 인코딩한다.
        encoded = quote(variant, safe="")
        for path in SIDECAR_PATHS:
            for ext in SIDECAR_EXTS:
                url = base + path.format(name=encoded, ext=ext)
                if url not in urls:
                    urls.append(url)
    return urls


def _sniff_format(body: bytes) -> str:
    """자막 본문의 형식을 선두 내용으로 판별한다. 자막이 아니면 빈 문자열.

    Content-Type 을 믿지 않는다 — 자막을 `application/octet-stream` 으로 주는
    서버가 있고, 반대로 200 으로 온 HTML 오류 페이지도 같은 헤더를 달고 온다.
    큐 타임코드가 하나라도 있는지가 유일하게 확실한 근거다.
    """
    head = body[:4096].decode("utf-8-sig", errors="replace")
    if not _CUE_RE.search(head) and not _CUE_RE.search(
        body.decode("utf-8-sig", errors="replace")
    ):
        return ""
    return "vtt" if head.lstrip().upper().startswith("WEBVTT") else "srt"


def _convert(src: Path, dest: Path, fmt: str) -> str:
    """자막 파일을 다른 형식으로 변환한다. 반환: 실패 사유 (성공이면 빈 문자열)."""
    cmd = [
        require("ffmpeg"), "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(src), "-c:s", _FORMAT_CODEC[fmt], str(dest),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        return proc.stderr.strip()[-300:] or f"ffmpeg exit {proc.returncode}"
    return ""


def fetch_sidecar(
    urls: list[str],
    out: Path,
    fetcher: Fetcher,
    fmt: str = "srt",
    track: Media | None = None,
) -> SubtitleResult:
    """자막 URL 후보를 앞에서부터 시도해 처음 성공한 것을 저장한다.

    받은 파일은 완성본이므로 dedupe/shift 를 걸지 않는다 — 그 둘은 조각을 이어붙인
    산물에서만 생기는 문제다. 원본 바이트를 그대로 두어야 같은 URL 을 손으로 받은
    결과와 대조할 수 있다. 요청 형식이 원본과 다를 때만 변환본을 따로 만든다.

    track 을 주면 그 트랙의 결과로 기록한다 — 플레이리스트가 선언한 트랙이 완성
    파일을 가리키는 경우다. 주지 않으면 URL 을 조립해 찾아낸 것으로 보고 `sidecar`
    로 표시한다. 이 구분이 리포트에서 "URL 조립으로 확보"의 근거가 된다.
    """
    res = SubtitleResult(
        track=track or Media(type="SUBTITLES", group_id="sidecar", name=out.stem),
        sidecar=track is None,
        tried=list(urls),
    )
    for url in urls:
        got = fetcher.get(url)
        if not got.ok:
            continue
        found = _sniff_format(got.body)
        if not found:
            # 200 이지만 자막이 아니다 — 오류 페이지를 자막으로 저장하지 않는다.
            continue
        res.track.uri = url
        dest = out.with_suffix(f".{found}")
        dest.write_bytes(got.body)
        if found != fmt:
            converted = out.with_suffix(f".{fmt}")
            err = _convert(dest, converted, fmt)
            if err:
                res.error = f"{found}→{fmt} 변환 실패: {err}"
                return res
            dest = converted
        res.path = dest
        res.cues, res.first_cue, res.last_cue = measure(dest)
        if res.cues == 0:
            res.error = "큐가 하나도 없다"
            return res
        res.ok = True
        return res

    res.error = f"후보 {len(urls)}개 모두 실패 — 이름 또는 경로 규칙이 다르다"
    return res
