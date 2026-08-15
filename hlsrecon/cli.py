"""hls-recon — HLS 송출 데이터를 로컬 영상 파일로 재조립하고 무결성을 검증한다."""

from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
import time
from dataclasses import dataclass, field, replace
from pathlib import Path
from urllib.parse import urlparse

from . import assemble, inventory, library, naming, playlist, probe, report, series, subtitles
from .decrypt import KeyCache
from .fetch import Fetcher, FetchResult
from .tsanalyze import TSReport, analyze, sniff


@dataclass
class SegmentRun:
    """segments 모드 한 회 실행에서 나온 계측치 일체."""

    fetches: list[FetchResult] = field(default_factory=list)
    ts: TSReport = field(default_factory=TSReport)
    declared: float = 0.0
    bogus: list[tuple[int, str, str]] = field(default_factory=list)
    mux_cmd: list[str] = field(default_factory=list)


def _eprint(msg: str = "") -> None:
    print(msg, file=sys.stderr, flush=True)


def _is_url(s: str) -> bool:
    return urlparse(s).scheme in ("http", "https")


def _normalize_cookie(raw: str) -> str:
    """붙여넣은 쿠키 문자열을 Cookie 헤더 값으로 정규화한다.

    개발자도구에서 복사하면 헤더 이름(`Cookie:`)이 딸려오거나 줄바꿈이 섞여 들어온다.
    헤더 값에 개행이 남으면 요청 자체가 거부되므로 한 줄로 잇는다.

    쿠키 값 자체는 손대지 않는다 — 규격상 값에는 거의 모든 문자가 들어올 수 있어
    이름/값으로 쪼갠 뒤 다시 조립하면 원본이 훼손되는 쿠키가 생긴다. 통째로 넘긴다.
    """
    s = raw.strip().strip("\"'").strip()
    if s[:7].lower() == "cookie:":
        s = s[7:].lstrip()
    s = "; ".join(part.strip().rstrip(";") for part in s.splitlines() if part.strip())
    if "=" not in s:
        raise SystemExit(f"--cookie 형식이 잘못됐다 (name=value; name2=value2 필요): {raw[:60]}")
    return s


def _diagnose(res, url: str) -> str:
    """플레이리스트로 파싱되지 않은 응답이 실제로 무엇이었는지 설명한다.

    '#EXTM3U 헤더가 없다'만 던지면 사용자가 다음에 뭘 해야 할지 알 수 없다.
    무엇이 왔는지(상태·타입·선두 바이트)를 보여주고 흔한 원인을 짚어준다.
    """
    head = res.body[:64]
    printable = "".join(chr(b) if 32 <= b < 127 else "." for b in head)
    lines = [
        f"플레이리스트로 해석할 수 없는 응답이다: {url}",
        "",
        f"  HTTP 상태      : {res.status}",
        f"  Content-Type   : {res.content_type or '(없음)'}",
        f"  Content-Encoding: {res.encoding or '(없음)'}",
        f"  본문 크기      : {res.size:,} B",
        f"  선두 바이트    : {head[:16].hex()}",
        f"  선두 문자      : {printable[:48]}",
        "",
    ]

    lowered = res.body[:512].lstrip().lower()
    if lowered.startswith((b"<!doctype", b"<html", b"<?xml")):
        lines.append("  → 영상이 아니라 웹 페이지가 왔다. 서버가 오류 페이지를 200 으로 돌려주는 상황이다.")
    elif res.body[:2] == b"\x1f\x8b":
        lines.append("  → gzip 인데 Content-Encoding 이 선언되지 않았다. 서버 설정 문제다.")
    elif not res.body.strip():
        lines.append("  → 본문이 비어 있다.")
    elif res.size <= 200 and all(9 <= b < 127 for b in res.body):
        # 오류 페이지 대신 한 줄짜리 문자열만 돌려주는 방어(예: "security error")가 있다.
        # 본문이 곧 서버가 밝힌 거절 사유이므로 그대로 보여주는 편이 어떤 요약보다 정확하다.
        lines.append(f'  → 서버가 짧은 오류 문구를 200 으로 돌려줬다: "{res.body.decode().strip()}"')
        lines.append("     플레이리스트 URL 자체가 거절된 것이다 — 아래를 순서대로 확인할 것.")
    else:
        lines.append("  → M3U8 텍스트가 아니다.")

    lines += [
        "",
        "  흔한 원인:",
        "    · Referer/Origin 검증 — --referer 'https://원본페이지/' 를 붙일 것",
        "    · 쿠키·인증 필요 — 브라우저의 Cookie 헤더 값을 --cookie '...' 로 붙일 것",
        "    · 링크가 1회용이거나 수십 초 만에 만료 — 붙여넣기로는 늦는다.",
        "      브라우저에서 이 응답(m3u8 텍스트)을 파일로 저장해 그 파일을 넘길 것:",
        "        hls-recon ./list.m3u8 -o out.mp4",
        "      세그먼트가 절대 URL 로 적혀 있으면 그대로 내려받는다.",
    ]
    return "\n".join(lines)


def _adopt_origin(res: FetchResult, fetcher: Fetcher) -> bool:
    """응답이 알려준 허용 origin 을 Referer/Origin 으로 채택한다.

    핫링크 차단 CDN 은 플레이어 페이지의 origin 을 Access-Control-Allow-Origin 으로
    되돌려준다 — 차단당한 403 응답에도 붙어 온다. 사용자가 --referer 를 주지 않은
    경우에만, 서버가 스스로 알려준 이 값을 근거로 삼는다.

    `*` 는 아무 origin 이나 허용한다는 뜻이라 근거가 되지 못하므로 무시한다.
    ACAO 는 "브라우저 JS 가 읽어도 되는 origin"이지 "서버가 요구하는 Referer"가
    아니다 — 어디까지나 추정이고, 그래서 사용자 지정이 항상 우선한다.
    """
    if "Referer" in fetcher.headers:
        return False
    u = urlparse(res.allow_origin.strip())
    if u.scheme not in ("http", "https") or not u.netloc:
        return False
    fetcher.headers["Referer"] = f"{u.scheme}://{u.netloc}/"
    fetcher.headers.setdefault("Origin", f"{u.scheme}://{u.netloc}")
    _eprint(f"  Referer 자동 : {u.scheme}://{u.netloc}/ (서버가 알려준 허용 origin)")
    return True


def _load(src: str, fetcher: Fetcher) -> tuple[playlist.Playlist, str]:
    """소스(URL 또는 로컬 .m3u8)를 파싱한다. 반환의 두 번째 값은 base URL."""
    if _is_url(src):
        res = fetcher.get(src)
        # 첫 응답에서 Referer 를 얻었다면, 그 때문에 막혔던 요청은 다시 해볼 값이 있다.
        if _adopt_origin(res, fetcher) and not res.ok:
            res = fetcher.get(src)
        if not res.ok:
            raise SystemExit(f"플레이리스트 요청 실패: {src}\n  {res.error}")
        text = res.body.decode("utf-8", errors="replace")
        try:
            return playlist.parse(text, base_url=src), src
        except ValueError:
            raise SystemExit(_diagnose(res, src)) from None
    p = Path(src).expanduser().resolve()
    if not p.is_file():
        raise SystemExit(f"파일이 없다: {p}")
    try:
        return playlist.parse(p.read_text(encoding="utf-8"), base_url=p.as_uri()), p.as_uri()
    except ValueError as e:
        raise SystemExit(f"{p}\n  {e}") from None


@dataclass
class Source:
    """소스 해석 결과. 자막·다국어 오디오 선언은 마스터에만 있으므로 함께 들고 다닌다."""

    media: playlist.Playlist
    media_url: str
    master: playlist.Playlist | None = None
    variant: playlist.Variant | None = None
    label: str = ""

    def subtitle_tracks(self) -> list[playlist.Media]:
        """선택된 화질 후보에 딸린 자막 그룹. 그룹 참조가 없으면 전체를 본다."""
        if not self.master:
            return []
        group = self.variant.subtitles_group if self.variant else ""
        return self.master.tracks("SUBTITLES", group)

    def closed_captions(self) -> list[playlist.Media]:
        """영상 스트림에 실려 오는 캡션(CEA-608/708). 별도 내려받을 수 없어 안내만 한다."""
        return self.master.tracks("CLOSED-CAPTIONS") if self.master else []


def _resolve_media(
    pl: playlist.Playlist, src: str, fetcher: Fetcher, args: argparse.Namespace
) -> Source:
    """마스터면 variant 를 골라 미디어 플레이리스트까지 내려간다."""
    if not pl.is_master:
        return Source(media=pl, media_url=src)

    _eprint(f"  마스터 플레이리스트 — 화질 후보 {len(pl.variants)}개")
    for v in sorted(pl.variants, key=lambda x: -x.bandwidth):
        _eprint(f"    · {v.label()}")

    chosen = pl.pick_variant(height=args.height, max_bandwidth=args.max_bandwidth)
    _eprint(f"  선택: {chosen.label()}")
    res = fetcher.get(chosen.uri)
    if not res.ok:
        raise SystemExit(f"variant 플레이리스트 요청 실패: {chosen.uri}\n  {res.error}")
    try:
        media = playlist.parse(res.body.decode("utf-8", errors="replace"), base_url=chosen.uri)
    except ValueError:
        raise SystemExit(_diagnose(res, chosen.uri)) from None
    if media.is_master:
        raise SystemExit("variant URL 이 또 마스터 플레이리스트다 — 중첩 구조는 지원하지 않는다")
    return Source(
        media=media, media_url=chosen.uri, master=pl, variant=chosen, label=chosen.label()
    )


def _print_structure(pl: playlist.Playlist, label: str) -> None:
    enc = {s.key.method for s in pl.segments if s.key and s.key.is_encrypted}
    _eprint()
    _eprint(f"  미디어 플레이리스트{f' [{label}]' if label else ''}")
    _eprint(f"    세그먼트      : {len(pl.segments)}개")
    _eprint(f"    선언 길이     : {pl.declared_duration:.2f}s ({pl.declared_duration / 60:.1f}분)")
    _eprint(f"    TARGETDURATION: {pl.target_duration:g}s")
    _eprint(f"    컨테이너      : {'fMP4 (EXT-X-MAP)' if pl.is_fmp4 else 'MPEG-TS'}")
    _eprint(f"    암호화        : {', '.join(enc) if enc else '없음'}")
    _eprint(f"    유형          : {'LIVE (ENDLIST 없음)' if pl.is_live else pl.playlist_type or 'VOD'}")
    disc = sum(1 for s in pl.segments if s.discontinuity)
    if disc:
        _eprint(f"    불연속 지점   : {disc}개 (EXT-X-DISCONTINUITY)")


def _print_tracks(src: Source) -> None:
    """마스터에 선언된 부가 트랙(자막·다국어 오디오·내장 캡션)을 보여준다."""
    if not src.master:
        return
    subs, cc = src.subtitle_tracks(), src.closed_captions()
    audio = src.master.tracks("AUDIO", src.variant.audio_group if src.variant else "")
    if not (subs or cc or audio):
        return
    _eprint()
    if audio:
        _eprint(f"    오디오 트랙   : {len(audio)}개")
        for m in audio:
            _eprint(f"      · {m.label()}")
    if subs:
        _eprint(f"    자막 트랙     : {len(subs)}개")
        for m in subs:
            _eprint(f"      · {m.label()}")
    if cc:
        _eprint(f"    내장 캡션     : {len(cc)}개 (영상에 실려 옴 — 별도 추출 불가)")
        for m in cc:
            _eprint(f"      · {m.label()}")


def _subtitle_offsets(
    tracks: list[playlist.Media],
    media: playlist.Playlist,
    fetcher: Fetcher,
    headers: dict[str, str],
) -> dict[str, float]:
    """트랙별 자막 정렬 오프셋(초)을 구한다.

    영상의 첫 표시 시각을 기준으로, 각 자막 트랙 첫 조각의 X-TIMESTAMP-MAP 이
    가리키는 위치와의 차이를 계산한다. ffmpeg 는 자막만 단독으로 열 때 이 매핑을
    적용하지 않으므로, 여기서 구한 값을 추출 후에 반영해야 자막이 제자리에 놓인다.
    """
    if not media.segments:
        return {}

    # 자막 트랙 URI 에 자막 플레이리스트 대신 완성된 파일(.srt)을 넣는 송출이 있다.
    # 그런 파일에는 X-TIMESTAMP-MAP 이 없어 오프셋을 계산할 근거 자체가 없으므로
    # 보정 대상에서 뺀다 — 적힌 시각을 그대로 믿는다(sidecar 자막과 같은 취급).
    segmented: list[playlist.Media] = []
    for track in tracks:
        if not track.uri:
            continue
        if playlist.is_playlist_uri(track.uri):
            segmented.append(track)
        else:
            _eprint(f"    · {track.label()} 완성 자막 파일이라 정렬 기준이 없다 — 보정 없이 쓴다")
    if not segmented:
        return {}

    pts0 = probe.first_pts(media.segments[0].uri, headers)
    if pts0 is None:
        _eprint("    · 영상 첫 표시 시각을 읽지 못해 자막 정렬 보정을 건너뛴다")
        return {}

    offsets: dict[str, float] = {}
    for track in segmented:
        try:
            sub_pl = playlist.parse(fetcher.get_text(track.uri), base_url=track.uri)
        except (RuntimeError, ValueError) as e:
            _eprint(f"    · {track.label()} 플레이리스트를 읽지 못했다: {e}")
            continue
        if not sub_pl.segments:
            continue
        first = fetcher.get(sub_pl.segments[0].uri, sub_pl.segments[0].byterange)
        if not first.ok:
            continue
        off = subtitles.timestamp_offset(first.body, pts0)
        if off is None:
            continue
        offsets[track.uri] = off
        if abs(off) >= 0.5:
            _eprint(f"    · {track.label()} X-TIMESTAMP-MAP 기준 {off:+.2f}s 보정")
    return offsets


def _sidecar_origin(args: argparse.Namespace, fetcher: Fetcher) -> str:
    """사이드카 자막을 찾을 호스트를 정한다.

    사용자 지정이 우선이고, 없으면 영상 요청에서 이미 확보한 origin 을 쓴다 —
    `_adopt_origin` 이 서버가 알려준 허용 origin 을 Referer 에 넣어 두었다면
    자막도 같은 곳에 있다. 그래서 호스트를 알아내려고 따로 요청하지 않는다.
    """
    if args.sub_origin:
        return args.sub_origin
    return fetcher.headers.get("Referer", "")


def _run_sidecar(
    args: argparse.Namespace, out: Path, fetcher: Fetcher
) -> tuple[subtitles.SubtitleResult | None, list[subtitles.SubtitleResult]]:
    """플레이리스트 밖 자막을 URL 조립(또는 직접 지정)으로 받는다.

    반환: (현재 영상에 해당하는 결과, --sub-range 로 함께 받은 이웃 화수 결과)
    """
    name = args.sub_name or out.stem
    fmt = args.sub_format

    if args.sub_url:
        urls = list(args.sub_url)
        _eprint(f"\n  자막 직접 지정 — 후보 {len(urls)}개")
    else:
        origin = _sidecar_origin(args, fetcher)
        if not origin:
            _eprint("\n  · 자막 origin 을 알 수 없다 — 서버가 허용 origin 을 알려주지 않았다. "
                    "--sub-origin 또는 --referer 로 지정할 것")
            return None, []
        try:
            urls = subtitles.sidecar_urls(name, origin)
        except ValueError as e:
            raise SystemExit(str(e)) from None
        _eprint(f"\n  자막 조립 — 이름 '{name}', origin {urlparse(origin).netloc}")

    res = subtitles.fetch_sidecar(urls, out, fetcher, fmt)
    if res.ok:
        _eprint(f"    ✓ {res.track.uri}")
        _eprint(f"      → {Path(res.path).name} ({res.cues}큐, "
                f"{res.first_cue:.1f}~{res.last_cue:.1f}s)")
    else:
        _eprint(f"    ✗ {res.error}")
        for u in res.tried[:6]:
            _eprint(f"      시도: {u}")

    extra: list[subtitles.SubtitleResult] = []
    if args.sub_range:
        origin = _sidecar_origin(args, fetcher)
        if not origin:
            _eprint("    · --sub-range 는 origin 이 있어야 한다 — 건너뛴다")
            return res, extra
        try:
            names = naming.episode_names(name, args.sub_range)
        except ValueError as e:
            raise SystemExit(str(e)) from None
        _eprint(f"    이웃 화수 {len(names)}개 수집 ({args.sub_range})")
        for nm in names:
            if nm == name:
                continue  # 위에서 이미 받았다
            dest = out.parent / (nm + out.suffix)
            got = subtitles.fetch_sidecar(
                subtitles.sidecar_urls(nm, origin), dest, fetcher, fmt
            )
            extra.append(got)
            mark = "✓" if got.ok else "✗"
            detail = f"{got.cues}큐" if got.ok else "없음"
            _eprint(f"      {mark} {nm} — {detail}")

    return res, extra


def _extract_subs(
    chosen: list[playlist.Media],
    media: playlist.Playlist,
    out: Path,
    args: argparse.Namespace,
    fetcher: Fetcher,
    headers: dict[str, str],
) -> list[subtitles.SubtitleResult]:
    """고른 자막 트랙을 영상 옆에 별도 파일로 뽑는다.

    받으면서 뽑는 경로(`_run_one`)와 자막만 메우는 경로(`--refill-subs`)가 이것을
    함께 쓴다. 정렬 보정과 파일 이름 규칙이 두 경로에서 갈라지면, 나중에 메운
    자막만 미묘하게 어긋나 있는데 원인을 짚기 어렵다.
    """
    _eprint(f"\n  자막 추출 — {len(chosen)}개 ({args.sub_format})")
    offsets = _subtitle_offsets(chosen, media, fetcher, headers)
    results = subtitles.extract(chosen, out, args.sub_format, fetcher, offsets)
    for r in results:
        if r.ok:
            _eprint(f"    ✓ {r.track.label()} → {Path(r.path).name} "
                    f"({r.cues}큐, {r.first_cue:.1f}~{r.last_cue:.1f}s)")
        else:
            _eprint(f"    ✗ {r.track.label()} — {r.error.splitlines()[-1][:100]}")
    return results


def _decide_mode(args: argparse.Namespace, pl: playlist.Playlist) -> str:
    """auto 모드 결정 — 세그먼트 단위 계측이 불가능한 조건이면 ffmpeg 위임으로 내린다."""
    if args.mode != "auto":
        return args.mode
    unsupported = [s for s in pl.segments if s.key and s.key.is_encrypted and not s.key.is_supported]
    if unsupported:
        _eprint("  · SAMPLE-AES 등 세그먼트 단위 복호화 불가 → remux 모드로 전환")
        return "remux"
    if pl.is_live:
        _eprint("  · LIVE 플레이리스트 → remux 모드로 전환 (스냅샷 계측 불가)")
        return "remux"
    return "segments"


def _run_segments(
    pl: playlist.Playlist,
    out: Path,
    args: argparse.Namespace,
    fetcher: Fetcher,
    embed: tuple[list[str], list[str], str] | None = None,
    headers: dict[str, str] | None = None,
) -> SegmentRun:
    """세그먼트를 개별 수신하며 계측한 뒤 로컬에서 재조립한다."""
    segs = pl.segments[: args.limit] if args.limit else pl.segments
    declared = sum(s.duration for s in segs)

    work = Path(args.keep_segments).expanduser().resolve() if args.keep_segments else Path(
        tempfile.mkdtemp(prefix="hls-recon-")
    )
    work.mkdir(parents=True, exist_ok=True)
    _eprint(f"\n  [1/3] 세그먼트 수신 — {len(segs)}개, 동시 {args.jobs}건 → {work}")

    items = [(s.uri, s.byterange) for s in segs]
    t0 = time.perf_counter()

    def tick(done: int, _res) -> None:
        if done % 10 == 0 or done == len(items):
            pct = done / len(items) * 100
            print(f"\r        {done}/{len(items)} ({pct:5.1f}%)", end="", file=sys.stderr, flush=True)

    results = fetcher.get_many(items, jobs=args.jobs, on_done=tick)
    _eprint(f"   — {time.perf_counter() - t0:.1f}s")

    # 복호화 + TS 무결성 분석 + 디스크 기록
    _eprint(f"  [2/3] 복호화 · 전송 무결성 분석")
    keys = KeyCache(fetcher)
    ts_total = TSReport()
    cc_state: dict[int, int] = {}
    paths: list[Path] = []

    if pl.init_map:
        init_uri, init_range = pl.init_map
        init = fetcher.get(init_uri, init_range)
        if not init.ok:
            raise SystemExit(f"초기화 세그먼트(EXT-X-MAP) 수신 실패: {init.error}")
        ipath = work / "init.mp4"
        ipath.write_bytes(init.body)
        paths.append(ipath)

    ext = ".m4s" if pl.is_fmp4 else ".ts"
    bogus: list[tuple[int, str, str]] = []  # (세그먼트 번호, Content-Type, 선두 바이트 판정)
    for seg, res in zip(segs, results):
        if not res.ok:
            _eprint(f"    ✗ seg#{seg.index} 수신 실패: {res.error}")
            continue
        data = res.body
        if seg.key and seg.key.is_encrypted:
            data = keys.decrypt(data, seg.key, seg.seq)
        kind = sniff(data)
        if kind == "unknown":
            # 200 을 받았지만 미디어가 아니다 — 오류 페이지가 실려 온 경우다.
            bogus.append((seg.index, res.content_type, data[:16].hex()))
            _eprint(f"    ✗ seg#{seg.index} 미디어가 아님 (Content-Type: {res.content_type or '없음'})")
            continue
        ts_total.merge(analyze(data, cc_state))
        p = work / f"seg{seg.index:06d}{ext}"
        p.write_bytes(data)
        paths.append(p)

    if not paths:
        raise SystemExit("수신된 세그먼트가 없다 — 토큰 만료 또는 Referer 검증 실패 가능성")

    _eprint(f"  [3/3] 재조립 → {out}")
    raw = work / f"joined{ext}"
    assemble.concat_segments(paths, raw)
    mux_cmd = assemble.remux_local(raw, out, subs=embed)

    if not args.keep_segments:
        shutil.rmtree(work, ignore_errors=True)
    else:
        _eprint(f"        세그먼트 보존: {work}")

    return SegmentRun(
        fetches=results, ts=ts_total, declared=declared, bogus=bogus, mux_cmd=mux_cmd
    )


def _given_headers(args: argparse.Namespace) -> dict[str, str]:
    """사용자가 지정한 요청 헤더를 모은다. 자동 추론보다 언제나 우선한다."""
    given: dict[str, str] = {}
    for h in args.header:
        k, sep, v = h.partition(":")
        if not sep:
            raise SystemExit(f"--header 형식이 잘못됐다 (K:V 필요): {h}")
        given[k.strip()] = v.strip()
    if args.referer:
        given["Referer"] = args.referer
        given.setdefault("Origin", "{u.scheme}://{u.netloc}".format(u=urlparse(args.referer)))
    if args.cookie:
        given["Cookie"] = _normalize_cookie(args.cookie)
    return given


def _check_container(suffix: str) -> str:
    if suffix.lower() not in assemble.supported_containers():
        raise SystemExit(
            f"지원하지 않는 컨테이너: {suffix or '(확장자 없음)'} "
            f"— {'/'.join(assemble.supported_containers())} 중에서 고를 것"
        )
    return suffix


def _run_one(
    args: argparse.Namespace,
    source: str,
    out: Path | None,
    given: dict[str, str],
    report_path: Path | None = None,
) -> report.Report | None:
    """플레이리스트 하나를 받아 검증한다. --probe-only 면 조사만 하고 None 을 준다.

    시리즈 모드는 회차마다 이 함수를 부른다 — 한 편을 받는 방법은 하나뿐이어야
    회차별로 검증 기준이 갈라지지 않는다.
    """
    fetcher = Fetcher(headers=dict(given), timeout=args.timeout, retries=args.retries)
    # 이후 요청 헤더의 단일 출처는 fetcher.headers 다. 기본 User-Agent 와 자동 채택한
    # Referer 가 그 안에만 반영되므로, ffmpeg/ffprobe 에도 같은 dict 를 그대로 넘긴다.
    # 따로 만든 사본을 넘기면 세그먼트 수신과 재조립이 서로 다른 헤더로 요청하게 된다.
    headers = fetcher.headers

    _eprint(f"\n  source: {source}")
    pl, src_url = _load(source, fetcher)
    src = _resolve_media(pl, src_url, fetcher, args)
    media, media_url, label = src.media, src.media_url, src.label
    _print_structure(media, label)
    _print_tracks(src)

    if args.probe_only:
        info = probe.probe(media_url, headers)
        if info.ok:
            _eprint(f"    실측 길이     : {info.duration:.2f}s")
            for s in info.streams:
                _eprint(f"    스트림 #{s.index}    : {s.describe()}")
        else:
            _eprint(f"    실측 실패     : {info.error[:200]}")
        return None

    assert out is not None  # probe-only 가 아니면 호출자가 반드시 정해 준다
    out.parent.mkdir(parents=True, exist_ok=True)

    # 받을 자막을 먼저 정한다 — 내장 방식이면 재조립 명령 자체가 달라지기 때문이다.
    all_subs = src.subtitle_tracks()
    chosen_subs = subtitles.select(all_subs, args.subs)
    subrep = subtitles.SubtitleReport(
        requested=args.subs, embedded=[m.label() for m in src.closed_captions()]
    )
    if args.subs != "none" and all_subs and not chosen_subs:
        _eprint(f"  · --subs {args.subs} 에 해당하는 자막이 없다 "
                f"(가용: {', '.join(m.language or '?' for m in all_subs)})")

    # 플레이리스트 밖 자막은 여기서 먼저 받는다 — 내장하려면 재조립 전에 파일이 있어야 한다.
    sidecar: subtitles.SubtitleResult | None = None
    if args.sub_url or args.sub_guess:
        sidecar, subrep.extra = _run_sidecar(args, out, fetcher)
        if sidecar and sidecar.ok:
            subrep.results.append(sidecar)

    embed = None
    embed_tracks = list(chosen_subs)
    if sidecar and sidecar.ok:
        # 받아둔 로컬 파일을 그대로 내장 입력으로 쓴다 — 다시 받지 않는다.
        embed_tracks.append(replace(sidecar.track, uri=str(sidecar.path)))
    if embed_tracks and args.sub_embed:
        # 오프셋은 HLS 트랙에만 해당한다. 사이드카는 완성 파일이라 X-TIMESTAMP-MAP 이 없다.
        offsets = _subtitle_offsets(chosen_subs, media, fetcher, headers)
        try:
            embed = subtitles.embed_args(out, embed_tracks, headers, offsets)
        except ValueError as e:
            raise SystemExit(str(e))
        subrep.embed_tracks = embed_tracks
        subrep.embed_offsets = offsets

    mode = _decide_mode(args, media)
    run = SegmentRun(declared=media.declared_duration)

    if mode == "segments":
        run = _run_segments(media, out, args, fetcher, embed, headers)
    else:
        if args.limit:
            _eprint("  · --limit 은 segments 모드에서만 적용된다 — 전체를 재조립한다")
        _eprint(f"\n  ffmpeg 위임 재조립 → {out}"
                + (f" (자막 {len(chosen_subs)}개 내장)" if embed else ""))
        total = run.declared
        t0 = time.perf_counter()
        run.mux_cmd = assemble.remux_from_url(
            media_url,
            out,
            headers,
            on_progress=lambda sec: print(
                f"\r        {sec:.1f}s / {total:.1f}s ({sec / total * 100 if total else 0:5.1f}%)",
                end="",
                file=sys.stderr,
                flush=True,
            ),
            subs=embed,
        )
        _eprint(f"   — {time.perf_counter() - t0:.1f}s")

    # 내장하지 않는 경우에만 별도 파일로 뽑는다.
    if chosen_subs and not args.sub_embed:
        subrep.results = _extract_subs(chosen_subs, media, out, args, fetcher, headers)

    info = probe.probe(str(out))
    if subrep.embed_tracks:
        subrep.embed_span = probe.subtitle_span(str(out))
    gaps = None if args.no_gap_scan else probe.gap_scan(str(out))
    decode = None if args.no_decode_check else probe.decode_check(str(out))

    rep = report.build(
        source=source,
        mode=mode,
        output=out,
        variant=label,
        declared_duration=run.declared,
        target_duration=media.target_duration,
        segment_count=len(
            media.segments[: args.limit] if args.limit and mode == "segments" else media.segments
        ),
        encrypted=any(s.key and s.key.is_encrypted for s in media.segments),
        fetches=run.fetches or None,
        bogus=run.bogus,
        ts=run.ts if mode == "segments" else None,
        media=info,
        gaps=gaps,
        discontinuities=sum(1 for s in media.segments if s.discontinuity),
        decode_errors=decode,
        mux_cmd=run.mux_cmd,
        subs=subrep,
        sampled=bool(args.limit and mode == "segments"),
    )
    print(rep.render())

    if report_path:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(rep.to_json(), encoding="utf-8")
        _eprint(f"  리포트 저장: {report_path}\n")

    return rep


def _exit_code(verdict: str) -> int:
    return {report.PASS: 0, report.WARN: 0, report.FAIL: 2}[verdict]


def _place_single(args: argparse.Namespace, out: Path) -> Path:
    """-o 로 받은 파일 경로를 시리즈 폴더 안으로 옮겨 놓는다.

    파일명 끝에 화수가 있을 때만 폴더를 만든다. 영화 한 편처럼 화수가 없는 이름까지
    폴더로 감싸면 파일 하나짜리 폴더만 늘어난다. 파일 이름 자체는 손대지 않는다 —
    사용자가 직접 적어 넣은 값이다.
    """
    out = out.expanduser().resolve()
    if args.flat or naming.split_episode(out.stem) is None:
        return out
    placed = library.series_folder(out.parent, naming.series_of(out.stem)) / out.name
    if placed != out:
        _eprint(f"  시리즈 폴더 : {placed.parent}  (해제하려면 --flat)")
    return placed


def _run_single(args: argparse.Namespace, given: dict[str, str]) -> int:
    out: Path | None = None
    if not args.probe_only:
        if not args.output:
            raise SystemExit("-o/--output 이 필요하다 (--probe-only 로 조사만 할 수도 있다)")
        out = _place_single(args, Path(args.output))
        _check_container(out.suffix)
    rep = _run_one(
        args,
        args.source,
        out,
        given,
        Path(args.report).expanduser().resolve() if args.report else None,
    )
    return 0 if rep is None else _exit_code(rep.verdict)


def _discard(out: Path) -> None:
    """중간까지 만들어진 출력 파일을 지운다.

    남겨두면 다음 실행이 '이미 받았다'고 보고 건너뛴다 — 깨진 파일이 완성본 행세를
    하게 되므로, 실패한 자리는 비워두는 편이 안전하다.
    """
    if out.exists():
        out.unlink(missing_ok=True)
        _eprint(f"  · 미완성 파일 제거: {out.name}")


def _refill_subs(
    args: argparse.Namespace,
    picked: list[series.Episode],
    stock: dict[int, inventory.Item],
    given: dict[str, str],
    pages: Fetcher,
    width: int,
) -> tuple[int, int]:
    """영상은 멀쩡한데 자막만 없는 회차를 **영상을 다시 받지 않고** 메운다.

    자막 하나 때문에 수백 MB 를 다시 받는 것은 대가가 맞지 않는다. 자막은 영상과
    다른 트랙(또는 아예 다른 파일)이므로 따로 받을 수 있다 — 회차의 재생 소스만
    다시 발급받으면 자막 플레이리스트 주소를 알 수 있고, 세그먼트는 자막 것만
    받으면 된다.

    정렬 보정 때문에 영상 첫 세그먼트 하나는 받는다. X-TIMESTAMP-MAP 을 영상의
    첫 표시 시각과 대조해야 자막이 제자리에 놓이기 때문이다 — 그것을 건너뛰면
    받아지긴 해도 통째로 밀린 자막이 남는다.

    반환: (메운 회차 수, 실패한 회차 수)
    """
    gaps = inventory.subtitle_gaps(stock)
    wanted = {e.number for e in picked}
    todo = [(n, stock[n]) for n in gaps if n in wanted]
    if not todo:
        _eprint("\n  자막 메우기   : 메울 회차가 없다 "
                "(영상이 온전한 회차는 모두 자막을 갖고 있다)")
        return 0, 0

    _eprint("\n" + "═" * 72)
    _eprint(f"  자막 메우기 — {len(todo)}개 회차 (영상은 다시 받지 않는다)")

    # 이웃 화수 일괄 수집은 회차마다 되풀이하면 같은 일을 몇 번씩 한다. 메우기는
    # 이미 회차별로 돌므로 여기서는 끈다.
    sub_args = argparse.Namespace(**vars(args))
    sub_args.sub_range = None

    by_number = {e.number: e for e in picked}
    filled = failed = 0
    for i, (number, have) in enumerate(todo, 1):
        ep = by_number[number]
        _eprint("\n" + "─" * 72)
        _eprint(f"  [{i}/{len(todo)}] {ep.title}  →  {have.video.name}")
        try:
            play = series.resolve(ep, pages, width)
        except (ValueError, RuntimeError) as e:
            _eprint(f"  ✗ 재생 소스 해석 실패 — 건너뛴다\n    {e}")
            failed += 1
            continue

        headers = dict(given)
        headers.setdefault("Referer", play.referer)
        headers.setdefault("Origin", play.referer.rstrip("/"))
        fetcher = Fetcher(headers=headers, timeout=args.timeout, retries=args.retries)

        try:
            pl, src_url = _load(play.playlist_url, fetcher)
            src = _resolve_media(pl, src_url, fetcher, args)
        except SystemExit as e:
            _eprint(f"  ✗ {e}")
            failed += 1
            continue

        chosen = subtitles.select(src.subtitle_tracks(), args.subs)
        got: list[subtitles.SubtitleResult] = []
        if chosen:
            got = _extract_subs(
                chosen, src.media, have.video, sub_args, fetcher, fetcher.headers
            )
        elif args.sub_url or args.sub_guess:
            one, _ = _run_sidecar(sub_args, have.video, fetcher)
            got = [one] if one else []
        else:
            _eprint("  · 플레이리스트에 자막 선언이 없다 — 조립해 받으려면 --sub-guess")

        if any(r.ok for r in got):
            filled += 1
        else:
            failed += 1
        if args.delay > 0 and i < len(todo):
            time.sleep(args.delay)

    _eprint(f"\n  자막 메우기 완료 — {filled}개 메움, {failed}개 실패")
    return filled, failed


def _run_series(args: argparse.Namespace, given: dict[str, str]) -> int:
    """시리즈 페이지 주소 하나로 전편을 받는다."""
    pages = Fetcher(headers=dict(given), timeout=args.timeout, retries=args.retries)
    _eprint(f"\n  시리즈 페이지: {args.source}")
    try:
        found = series.discover(args.source, pages)
    except (ValueError, RuntimeError) as e:
        raise SystemExit(str(e)) from None

    picked = found.episodes
    if args.episodes:
        try:
            lo, hi = naming.parse_range(args.episodes, "--episodes")
        except ValueError as e:
            raise SystemExit(str(e)) from None
        picked = [e for e in found.episodes if lo <= e.number <= hi]
        if not picked:
            raise SystemExit(
                f"--episodes {args.episodes} 에 해당하는 회차가 없다 "
                f"(가용: {found.episodes[0].number}-{found.episodes[-1].number})"
            )

    ext = _check_container(
        args.container if args.container.startswith(".") else "." + args.container
    )
    base = Path(args.output).expanduser().resolve() if args.output else Path.cwd()
    folder = base if args.flat else library.series_folder(base, found.title)

    _eprint(f"  작품          : {found.title}")
    _eprint(f"  회차          : 전체 {len(found.episodes)}개 중 {len(picked)}개 대상")
    _eprint(f"  보관 위치     : {folder}")

    # 재고를 **재생 소스 발급 전에** 훑는다. 회차 번호는 목록에서 이미 알고 있으므로
    # 여기서 가려내면 이미 받아둔 회차에는 요청이 한 건도 나가지 않는다.
    stock, note = inventory.stock_for(
        inventory.scan(folder, deep=args.verify_existing), found.title
    )
    broken = [it for it in stock.values() if not it.ok]
    if stock:
        # --overwrite 면 재고와 무관하게 전부 다시 받는다. 예고한 수와 실제가
        # 어긋나면 재고 표시가 오히려 오해를 만든다.
        target = (
            len(picked)
            if args.overwrite
            else sum(1 for e in picked if not (stock.get(e.number) and stock[e.number].ok))
        )
        _eprint(
            f"  재고          : {len(stock)}개 있음 {note}"
            + (f", 손상 {len(broken)}개" if broken else "")
            + f" — 받을 것 {target}개"
            + ("" if args.verify_existing else " (구조만 확인 — 실제로 열어보려면 --verify-existing)")
        )
        gaps = inventory.subtitle_gaps(stock)
        if gaps:
            _eprint(f"  자막만 빠짐   : {', '.join(str(n) for n in gaps)}화 "
                    + ("— 영상 없이 자막만 받는다 (--refill-subs)" if args.refill_subs
                       else "— 영상이 멀쩡하므로 다시 받지 않는다 (--refill-subs 로 메운다)"))
    elif note:
        _eprint(f"  재고          : 번호로 가릴 수 없다 — {note}")
        _eprint("                  파일명이 정확히 같을 때만 건너뛴다 (--flat 로 여러 작품이 섞인 경우)")

    if args.probe_only:
        # 시리즈에서는 회차마다 재생 소스를 따로 발급받아야 한다. 조사만 하겠다는
        # 요청에 27번의 발급 요청을 보내지 않는다 — 목록까지만 보여준다.
        _eprint("\n  회차 목록 (--probe-only — 내려받지 않는다)")
        for e in picked:
            have = stock.get(e.number)
            if have is None:
                mark = "받을 것"
            elif have.ok:
                mark = "있음   "
            else:
                mark = "손상   "
            _eprint(f"    {e.number:>3}. {mark}  {e.title}"
                    + (f"   ({have.flaw})" if have and not have.ok else ""))
        return 0

    refilled = refill_failed = 0
    if args.refill_subs:
        refilled, refill_failed = _refill_subs(args, picked, stock, given, pages, found.width)

    done: list[tuple[series.Episode, str]] = []
    failed = 0
    for i, ep in enumerate(picked, 1):
        _eprint("\n" + "─" * 72)
        _eprint(f"  [{i}/{len(picked)}] {ep.title}")

        # 재생 소스를 발급받기 전에 재고부터 본다 — 이미 온전히 받아둔 회차라면
        # 여기서 끝나고 요청이 한 건도 나가지 않는다.
        have = stock.get(ep.number)
        stale = bool(have and not have.ok)
        if have and have.ok and not args.overwrite:
            _eprint(f"  · 이미 있다 — 건너뛴다 ({have.video.name}). 다시 받으려면 --overwrite")
            done.append((ep, "건너뜀"))
            continue
        if stale and not args.overwrite:
            _eprint(f"  · 다시 받는다 — {have.flaw} ({have.video.name})")

        try:
            play = series.resolve(ep, pages, found.width)
        except (ValueError, RuntimeError) as e:
            _eprint(f"  ✗ 재생 소스 해석 실패 — 건너뛴다\n    {e}")
            done.append((ep, "해석실패"))
            failed += 1
            continue

        out = folder / (naming.sanitize(play.name) + ext)
        # 번호로 가리지 못한 경우(--flat 로 여러 작품이 섞인 폴더)를 위한 뒷받침.
        # 손상이라 다시 받기로 한 회차는 여기서 다시 걸러내면 안 된다.
        if out.exists() and not args.overwrite and not stale:
            _eprint(f"  · 이미 있다 — 건너뛴다 ({out.name}). 다시 받으려면 --overwrite")
            done.append((ep, "건너뜀"))
            continue

        # 회차마다 세그먼트 보존 위치를 갈라둔다 — 한 폴더를 돌려쓰면 앞 회차의
        # 세그먼트가 남아 다음 회차의 검증을 오염시킨다.
        ep_args = argparse.Namespace(**vars(args))
        if args.keep_segments:
            ep_args.keep_segments = str(Path(args.keep_segments) / play.name)

        # 플레이어가 알려준 origin 을 Referer 로 쓴다. 사용자 지정이 있으면 그대로 둔다.
        ep_headers = dict(given)
        ep_headers.setdefault("Referer", play.referer)
        ep_headers.setdefault("Origin", play.referer.rstrip("/"))

        report_path = (
            Path(args.report).expanduser().resolve() / (play.name + ".json")
            if args.report
            else None
        )
        try:
            rep = _run_one(ep_args, play.playlist_url, out, ep_headers, report_path)
        except SystemExit as e:
            _eprint(f"  ✗ {e}")
            _discard(out)
            done.append((ep, "실패"))
            failed += 1
            continue
        except KeyboardInterrupt:
            _discard(out)
            raise
        done.append((ep, rep.verdict if rep else "?"))
        if rep and rep.verdict == report.FAIL:
            failed += 1
        # 손상본을 대체해 받았는데 확장자가 달라 다른 자리에 놓인 경우. 지우지 않는다 —
        # 이 도구가 만든 조각이라는 보장이 없고, 지우면 되돌릴 수 없다.
        if stale and have.video != out and have.video.exists():
            _eprint(f"  · 손상본이 그대로 남아 있다: {have.video.name} (직접 지울 것)")
        if args.delay > 0 and i < len(picked):
            time.sleep(args.delay)

    _eprint("\n" + "═" * 72)
    _eprint(f"  시리즈 요약 — {found.title}  →  {folder}")
    for ep, verdict in done:
        _eprint(f"    {ep.number:>3}. {verdict:<8} {ep.title}")
    _eprint(f"  {len(done)}개 처리, 실패 {failed}개"
            + (f" · 자막 {refilled}개 메움" if refilled else "")
            + (f", 자막 메우기 실패 {refill_failed}개" if refill_failed else ""))
    return 2 if failed or refill_failed else 0


def _run_tidy(args: argparse.Namespace) -> int:
    """이미 흩어진 회차 파일을 시리즈 폴더로 되모은다."""
    root = Path(args.tidy).expanduser().resolve()
    if not root.is_dir():
        raise SystemExit(f"폴더가 아니다: {root}")

    moves = library.plan_tidy(root)
    if not moves:
        _eprint(f"\n  정리할 것이 없다: {root}")
        _eprint("  · 같은 시리즈로 묶이는 회차가 둘 이상인 영상만 폴더로 모은다.")
        return 0

    _eprint(f"\n  {root}")
    current = None
    for mv in moves:
        if mv.dest.parent != current:
            current = mv.dest.parent
            _eprint(f"\n  {current.name}/")
        mark = "·" if not mv.skip else "✗"
        note = f"   ({mv.skip})" if mv.skip else ""
        _eprint(f"    {mark} {mv.src.name}{note}")

    movable = sum(1 for m in moves if not m.skip)
    if not args.apply:
        _eprint(f"\n  미리보기 — {movable}개를 옮길 수 있다. 실행하려면 --apply 를 붙일 것")
        return 0

    moved, skipped = library.apply_tidy(moves)
    _eprint(f"\n  {moved}개 이동, {skipped}개 건너뜀")
    return 0


def build_parser() -> argparse.ArgumentParser:
    """인자 정의. main 에서 떼어 둔 것은 기본값 그대로의 args 를 테스트가 만들 수
    있어야 하기 때문이다 — 손으로 Namespace 를 조립하면 실제 기본값과 어긋난다."""
    ap = argparse.ArgumentParser(
        prog="hls-recon",
        description="HLS 송출 데이터를 로컬 영상 파일로 재조립하고 전송 무결성을 검증한다.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""예시:
  hls-recon https://cdn.example/master.m3u8 -o out.mp4
  hls-recon master.m3u8 --probe-only
  hls-recon https://cdn.example/master.m3u8 -o s.mp4 --limit 20 --referer https://site/
  hls-recon https://cdn.example/master.m3u8 -o out.mp4 --cookie 'sid=abc; token=xyz'
  hls-recon https://cdn.example/master.m3u8 -o out.mp4 --mode remux --height 1080

시리즈 — 목록 페이지 주소 하나로 전편을 받는다 (회차 주소를 줘도 목록으로 올라간다):
  hls-recon 'https://site.example/c/작품제목' -o ~/Movies
  hls-recon 'https://site.example/c/작품제목' -o ~/Movies --episodes 5-12 --container .mkv

다시 실행하면 없는 회차와 깨진 회차만 받는다 (--probe-only 로 뭐가 빠졌는지만 보기):
  hls-recon 'https://site.example/c/작품제목' -o ~/Movies --probe-only
  hls-recon 'https://site.example/c/작품제목' -o ~/Movies --verify-existing

이미 흩어진 파일을 시리즈 폴더로 되모은다 (기본은 미리보기):
  hls-recon --tidy ~/Movies/torrent
  hls-recon --tidy ~/Movies/torrent --apply
""",
    )
    ap.add_argument(
        "source",
        nargs="?",
        help="플레이리스트 URL·로컬 .m3u8 경로, 또는 시리즈/회차 페이지 URL",
    )
    ap.add_argument("-o", "--output", help="출력 파일 (.mp4/.mkv/.ts). 확장자로 컨테이너 결정")
    ap.add_argument(
        "--mode",
        choices=["auto", "remux", "segments"],
        default="auto",
        help="remux=ffmpeg 위임(빠름·견고) / segments=세그먼트 개별 계측(검증용) / auto=자동 선택",
    )
    ap.add_argument("--height", type=int, help="화질 선택 (예: 1080). 미지정 시 최대 대역폭")
    ap.add_argument("--max-bandwidth", type=int, help="이 대역폭(bps) 이하 후보 중 최대치 선택")
    ap.add_argument("--header", action="append", default=[], metavar="K:V", help="추가 요청 헤더 (반복 가능)")
    ap.add_argument("--referer", help="Referer 헤더 — 핫링크 차단된 CDN 에 필요")
    ap.add_argument(
        "--cookie",
        metavar="STR",
        help="쿠키 문자열 — 개발자도구 Network 탭의 Cookie 요청 헤더 값을 그대로 "
        "붙여넣는다 (예: 'sid=abc; token=xyz'). 'Cookie:' 접두어가 붙어 있어도 된다",
    )
    ap.add_argument(
        "--subs",
        default="default",
        metavar="SPEC",
        help="받을 자막: all | default | none | 언어코드 목록(ko,en). 기본 default",
    )
    ap.add_argument(
        "--sub-format", choices=["vtt", "srt"], default="vtt", help="자막 파일 형식 (기본 vtt)"
    )
    ap.add_argument(
        "--sub-embed",
        action="store_true",
        help="자막을 별도 파일 대신 영상 컨테이너에 내장 (.mkv 권장)",
    )
    ap.add_argument(
        "--sub-guess",
        action="store_true",
        help="플레이리스트에 자막 선언이 없을 때 URL 을 조립해 받는다 "
             "(호스트=서버가 알려준 origin, 이름=출력 파일명)",
    )
    ap.add_argument("--sub-name", metavar="NAME", help="조립에 쓸 자막 이름 (기본: 출력 파일명)")
    ap.add_argument("--sub-origin", metavar="URL", help="자막 호스트 (기본: 영상이 알려준 origin)")
    ap.add_argument(
        "--sub-url",
        action="append",
        default=[],
        metavar="URL",
        help="자막 URL 을 직접 지정 — 조립을 건너뛴다 (반복 가능)",
    )
    ap.add_argument(
        "--sub-range",
        metavar="A-B",
        help="이웃 화수 자막까지 함께 수집 (예: 01-27). --sub-guess 와 함께 쓴다",
    )
    ap.add_argument("--jobs", type=int, default=8, help="동시 다운로드 수 (기본 8)")
    ap.add_argument("--limit", type=int, help="앞 N개 세그먼트만 처리 — 빠른 샘플 검증")
    ap.add_argument("--keep-segments", metavar="DIR", help="세그먼트 원본을 이 디렉터리에 보존")
    ap.add_argument("--report", metavar="PATH", help="검증 결과를 JSON 으로 저장")
    ap.add_argument("--probe-only", action="store_true", help="다운로드 없이 구조만 조사")
    ap.add_argument("--no-decode-check", action="store_true", help="전체 디코드 검사 생략 (긴 영상에서 시간 절약)")
    ap.add_argument("--no-gap-scan", action="store_true", help="타임라인 결손 스캔 생략")
    ap.add_argument("--timeout", type=float, default=30.0, help="요청 타임아웃 초 (기본 30)")
    ap.add_argument("--retries", type=int, default=3, help="세그먼트 재시도 횟수 (기본 3)")

    grp = ap.add_argument_group("보관 구조")
    grp.add_argument(
        "--flat",
        action="store_true",
        help="시리즈 폴더를 만들지 않고 -o 가 가리킨 자리에 그대로 둔다",
    )
    grp.add_argument(
        "--tidy",
        metavar="DIR",
        help="이미 흩어진 회차 파일을 시리즈 폴더로 되모은다 (기본은 미리보기)",
    )
    grp.add_argument("--apply", action="store_true", help="--tidy 를 실제로 실행한다")

    grp = ap.add_argument_group("시리즈")
    grp.add_argument(
        "--episodes", metavar="A-B", help="받을 회차 범위 (예: 5-12). 기본 전체"
    )
    grp.add_argument(
        "--container",
        metavar="EXT",
        default=".mp4",
        help="시리즈 모드 출력 컨테이너 (기본 .mp4). 자막 내장은 .mkv 를 쓸 것",
    )
    grp.add_argument(
        "--overwrite", action="store_true", help="이미 받은 회차도 다시 받는다"
    )
    grp.add_argument(
        "--refill-subs",
        action="store_true",
        help="영상은 있는데 자막만 없는 회차를 영상을 다시 받지 않고 자막만 메운다",
    )
    grp.add_argument(
        "--verify-existing",
        action="store_true",
        help="이미 있는 파일을 ffprobe 로 실제로 열어보고 온전한지 확인한다 "
        "(기본은 컨테이너 구조만 — 빠른 대신 열리는지까지는 보지 않는다)",
    )
    grp.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="회차 사이 대기 초 (기본 1.0) — 연속 요청으로 차단되지 않게 한다",
    )
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.tidy:
        return _run_tidy(args)
    if not args.source:
        raise SystemExit("source 가 필요하다 — 플레이리스트/시리즈 주소 또는 --tidy DIR")

    given = _given_headers(args)
    if _is_url(args.source) and series.is_page(args.source):
        return _run_series(args, given)
    return _run_single(args, given)


if __name__ == "__main__":
    sys.exit(main())
