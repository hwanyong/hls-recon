"""검증 리포트 — 수집한 계측치를 판정으로 환산하고 사람이 읽는 형태로 낸다."""

from __future__ import annotations

import json
import unicodedata
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .fetch import FetchResult
from .probe import GapScan, MediaInfo
from .subtitles import SubtitleReport
from .tsanalyze import TSReport

PASS, WARN, FAIL = "PASS", "WARN", "FAIL"


def _tag(r) -> str:
    """자막 결과를 가리키는 짧은 이름. HLS 트랙은 언어, 사이드카는 파일 이름이 낫다."""
    return r.track.language or r.track.name or "?"


def _pct(part: float, whole: float) -> float:
    return (part / whole * 100) if whole else 0.0


def _pad(text: str, width: int) -> str:
    """한글은 terminal 에서 2칸을 차지하므로 문자 수가 아니라 표시 폭으로 채운다."""
    shown = sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in text)
    return text + " " * max(1, width - shown)


SENSITIVE_HEADERS = frozenset({"cookie", "authorization", "proxy-authorization", "x-api-key"})


def _redact_headers(cmd: list[str]) -> list[str]:
    """ffmpeg 명령의 -headers 블록에서 자격증명을 가린 사본을 만든다.

    리포트 JSON 은 CI 아티팩트로 남거나 그대로 첨부돼 오간다. 세션 쿠키가 평문으로
    실리면 파일 하나가 곧 계정 접근권이 된다.
    """
    out = list(cmd)
    for i, tok in enumerate(out):
        if tok == "-headers" and i + 1 < len(out):
            out[i + 1] = "\r\n".join(_redact_line(h) for h in out[i + 1].split("\r\n"))
    return out


def _redact_line(line: str) -> str:
    name, sep, _ = line.partition(":")
    if sep and name.strip().lower() in SENSITIVE_HEADERS:
        return f"{name}: ***"
    return line


def _quantile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    idx = min(len(s) - 1, int(round(q * (len(s) - 1))))
    return s[idx]


@dataclass
class Check:
    name: str
    verdict: str
    detail: str

    def line(self) -> str:
        mark = {PASS: "✓", WARN: "!", FAIL: "✗"}[self.verdict]
        return f"  {mark} {_pad(self.name, 18)} {self.detail}"


@dataclass
class Report:
    source: str = ""
    mode: str = ""
    output: str = ""
    variant: str = ""
    checks: list[Check] = field(default_factory=list)
    stats: dict = field(default_factory=dict)

    @property
    def verdict(self) -> str:
        if any(c.verdict == FAIL for c in self.checks):
            return FAIL
        if any(c.verdict == WARN for c in self.checks):
            return WARN
        return PASS

    def add(self, name: str, verdict: str, detail: str) -> None:
        self.checks.append(Check(name, verdict, detail))

    def to_json(self) -> str:
        return json.dumps(
            {
                "source": self.source,
                "mode": self.mode,
                "output": self.output,
                "variant": self.variant,
                "verdict": self.verdict,
                "checks": [asdict(c) for c in self.checks],
                "stats": self.stats,
            },
            ensure_ascii=False,
            indent=2,
        )

    def render(self) -> str:
        head = {PASS: "PASS — 송출 데이터 정상", WARN: "WARN — 확인 필요", FAIL: "FAIL — 결함 검출"}
        out = ["", "=" * 66, f"  검증 결과: {head[self.verdict]}", "=" * 66]
        if self.variant:
            out.append(f"  variant : {self.variant}")
        if self.output:
            out.append(f"  output  : {self.output}")
        out.append("")
        out += [c.line() for c in self.checks]
        out.append("")
        return "\n".join(out)


def build(
    *,
    source: str,
    mode: str,
    output: Path | None,
    variant: str,
    declared_duration: float,
    target_duration: float,
    segment_count: int,
    encrypted: bool,
    fetches: list[FetchResult] | None,
    bogus: list[tuple[int, str, str]],
    ts: TSReport | None,
    media: MediaInfo | None,
    gaps: GapScan | None,
    discontinuities: int,
    decode_errors: tuple[int, list[str]] | None,
    mux_cmd: list[str],
    subs: SubtitleReport | None,
    sampled: bool = False,
) -> Report:
    """계측치를 판정 규칙에 통과시켜 Report 를 만든다."""
    rep = Report(source=source, mode=mode, output=str(output) if output else "", variant=variant)
    # 리포트만 보고 같은 산출물을 다시 만들 수 있도록 실제 실행된 먹싱 명령을 남긴다.
    # 단 쿠키·인증 헤더는 가린다 — 재현성보다 자격증명 유출 방지가 앞선다.
    if mux_cmd:
        rep.stats["mux_command"] = _redact_headers(mux_cmd)

    # 1) 플레이리스트 구조
    rep.add(
        "플레이리스트",
        PASS,
        f"세그먼트 {segment_count}개, 선언 길이 {declared_duration:.2f}s, "
        f"TARGETDURATION {target_duration:g}s, 암호화 {'AES-128' if encrypted else '없음'}",
    )

    # 2) 전송 계층 — segments 모드에서만 수집된다
    if fetches:
        failed = [f for f in fetches if not f.ok]
        retried = [f for f in fetches if f.ok and f.attempts > 1]
        ttfb = [f.ttfb_ms for f in fetches if f.ok]
        tput = [f.throughput_mbps for f in fetches if f.ok and f.throughput_mbps]
        total_bytes = sum(f.size for f in fetches)

        if failed:
            codes = sorted({f.status or 0 for f in failed})
            rep.add(
                "세그먼트 수신",
                FAIL,
                f"{len(failed)}/{len(fetches)}개 실패 (HTTP {codes}) — 재조립본에 결손 구간 발생",
            )
        elif retried:
            rep.add(
                "세그먼트 수신",
                WARN,
                f"{len(fetches)}개 전량 수신, 단 {len(retried)}개가 재시도 후 성공 — 송출 측 불안정",
            )
        else:
            rep.add("세그먼트 수신", PASS, f"{len(fetches)}개 전량 1회 수신, {total_bytes / 1e6:.1f} MB")

        compressed = [f for f in fetches if f.ok and f.compressed]
        wire_bytes = sum(f.wire_size or f.size for f in fetches if f.ok)
        rep.add(
            "응답 지연",
            WARN if _quantile(ttfb, 0.95) > 3000 else PASS,
            f"TTFB p50 {_quantile(ttfb, 0.5):.0f}ms / p95 {_quantile(ttfb, 0.95):.0f}ms, "
            f"처리량 중앙값 {_quantile(tput, 0.5):.1f} Mbps"
            + (
                f", {len(compressed)}개 압축 전송 "
                f"({wire_bytes / 1e6:.1f}→{total_bytes / 1e6:.1f}MB)"
                if compressed
                else ""
            ),
        )

        # HTTP 200 이어도 내용이 미디어가 아닐 수 있다 (만료 토큰에 대한 오류 페이지 등).
        if bogus:
            types = sorted({ct or "Content-Type 없음" for _, ct, _ in bogus})
            rep.add(
                "페이로드 유효성",
                FAIL,
                f"{len(bogus)}개가 200 응답이나 미디어가 아님 ({', '.join(types)}) "
                f"— seg#{bogus[0][0]} 선두 {bogus[0][2][:16]}",
            )
            rep.stats["bogus_payloads"] = [
                {"segment": i, "content_type": ct, "head_hex": h} for i, ct, h in bogus
            ]
        else:
            rep.add("페이로드 유효성", PASS, "전량 미디어 컨테이너로 확인 (선두 바이트 검사)")

        dup = len({f.sha256 for f in fetches if f.ok}) != len([f for f in fetches if f.ok])
        rep.add(
            "세그먼트 고유성",
            WARN if dup else PASS,
            "중복 해시 존재 — 동일 세그먼트가 반복 송출됨" if dup else "SHA-256 전량 상이",
        )

        rep.stats["transport"] = {
            "segments": len(fetches),
            "failed": len(failed),
            "retried": len(retried),
            "bytes": total_bytes,
            "wire_bytes": wire_bytes,
            "compressed_responses": len(compressed),
            "ttfb_ms_p50": round(_quantile(ttfb, 0.5), 1),
            "ttfb_ms_p95": round(_quantile(ttfb, 0.95), 1),
            "throughput_mbps_p50": round(_quantile(tput, 0.5), 2),
        }

    # 3) TS 전송 무결성
    if ts and ts.parsed:
        problems = []
        if ts.cc_discontinuities:
            problems.append(f"CC 불연속 {ts.cc_discontinuities}건(패킷 유실)")
        if ts.transport_errors:
            problems.append(f"TEI {ts.transport_errors}건")
        if ts.sync_errors:
            problems.append(f"동기 이탈 {ts.sync_errors}건")
        if ts.scrambled_packets:
            problems.append(f"미복호 패킷 {ts.scrambled_packets}건")
        rep.add(
            "TS 무결성",
            FAIL if (ts.sync_errors or ts.scrambled_packets) else (WARN if problems else PASS),
            ", ".join(problems)
            if problems
            else f"{ts.packets:,} 패킷 / PID {len(ts.pids)}종, 손실 0",
        )
        rep.stats["mpegts"] = {
            "packets": ts.packets,
            "pids": sorted(ts.pids),
            "cc_discontinuities": ts.cc_discontinuities,
            "transport_errors": ts.transport_errors,
            "sync_errors": ts.sync_errors,
            "scrambled_packets": ts.scrambled_packets,
            "cc_detail": [
                {"pid": p, "expected": e, "actual": a} for p, e, a in ts.cc_detail
            ],
        }

    # 4) 재조립 결과 — 선언 길이 대비 실측 길이 드리프트
    if media and media.ok:
        drift = media.duration - declared_duration
        drift_pct = abs(_pct(drift, declared_duration))
        # 한 세그먼트 이상 어긋났으면 구간 결손으로 본다.
        if target_duration and abs(drift) >= target_duration:
            verdict = FAIL
        elif drift_pct > 0.5:
            verdict = WARN
        else:
            verdict = PASS
        rep.add(
            "길이 정합",
            verdict,
            f"실측 {media.duration:.2f}s vs 선언 {declared_duration:.2f}s "
            f"(드리프트 {drift:+.2f}s / {drift_pct:.2f}%)",
        )

        v, a = media.video(), media.audio()
        subtitle_streams = [s for s in media.streams if s.kind == "subtitle"]
        parts = [v.describe() if v else "", a.describe() if a else ""]
        if subtitle_streams:
            parts.append(
                f"자막 {len(subtitle_streams)}트랙 ({subtitle_streams[0].codec})"
            )
        rep.add(
            "스트림 구성",
            PASS if v else WARN,
            " + ".join(filter(None, parts)) or "영상 트랙 없음",
        )
        rep.stats["output"] = {
            "duration": round(media.duration, 3),
            "declared_duration": round(declared_duration, 3),
            "drift_sec": round(drift, 3),
            "drift_pct": round(drift_pct, 4),
            "size": media.size,
            "bit_rate": media.bit_rate,
            "format": media.format_name,
            "streams": [s.describe() for s in media.streams],
        }

    # 5) 타임라인 연속성 — 총 길이가 맞아도 중간이 비어 있을 수 있다
    if gaps is not None and gaps.ok:
        if gaps.gaps:
            worst = max(gaps.gaps, key=lambda g: g.length)
            where = ", ".join(f"{g.start:.2f}~{g.end:.2f}s" for g in gaps.gaps[:3])
            more = f" 외 {len(gaps.gaps) - 3}건" if len(gaps.gaps) > 3 else ""
            # 플레이리스트가 EXT-X-DISCONTINUITY 로 예고한 불연속이면 의도된 이음매일 수 있다.
            intended = discontinuities >= len(gaps.gaps)
            rep.add(
                "타임라인 연속성",
                WARN if intended else FAIL,
                f"결손 {len(gaps.gaps)}건 / 합계 {gaps.lost:.2f}s (최대 {worst.length:.2f}s) "
                f"@ {where}{more}"
                + (" — EXT-X-DISCONTINUITY 선언 구간과 수가 일치(의도된 이음매 가능)" if intended else ""),
            )
        else:
            rep.add(
                "타임라인 연속성",
                PASS,
                f"영상 프레임 {gaps.frames:,}개 연속, 결손 0 "
                f"(간격 중앙값 {gaps.frame_interval * 1000:.1f}ms, 임계 {gaps.threshold * 1000:.0f}ms)",
            )
        rep.stats["timeline"] = {
            "frames": gaps.frames,
            "frame_interval_sec": round(gaps.frame_interval, 6),
            "threshold_sec": round(gaps.threshold, 4),
            "gap_count": len(gaps.gaps),
            "gap_total_sec": round(gaps.lost, 3),
            "gaps": [
                {"start": round(g.start, 3), "end": round(g.end, 3), "length": round(g.length, 3)}
                for g in gaps.gaps[:50]
            ],
        }

    # 6) 자막 — 추출 성공 여부와 영상 타임라인과의 정합
    #
    # 기준선은 실측 duration 이 아니라 플레이리스트 선언 길이다. 자막을 컨테이너에
    # 내장하면 자막 끝까지 전체 duration 이 늘어나므로, 실측을 기준으로 삼으면
    # 밀린 자막이 스스로 기준을 끌고 가 검사가 항상 통과해 버린다.
    video_len = declared_duration or (media.duration if media and media.ok else 0.0)
    if subs and (subs.results or subs.embedded or subs.embed_tracks or subs.extra):
        # 컨테이너에 넣은 경우, 실제로 자막 스트림이 들어갔는지 산출물에서 확인한다.
        if subs.embed_tracks:
            actual = [s for s in media.streams if s.kind == "subtitle"] if media and media.ok else []
            want = len(subs.embed_tracks)
            shifted = {k: v for k, v in subs.embed_offsets.items() if abs(v) >= 0.5}
            rep.add(
                "자막 내장",
                PASS if len(actual) == want else FAIL,
                f"{len(actual)}/{want}개 트랙 내장 ("
                + ", ".join(m.language or "?" for m in subs.embed_tracks)
                + f"), 코덱 {actual[0].codec if actual else '없음'}"
                + (f", X-TIMESTAMP-MAP 정렬 {len(shifted)}트랙 보정" if shifted else ""),
            )
            # 넣었다고 맞는 것은 아니다 — 산출물 안 자막의 실제 시각을 영상과 대조한다.
            if subs.embed_span and video_len > 0:
                lo, hi = subs.embed_span
                strayed = hi > video_len + 5.0 or lo < -0.5
                rep.add(
                    "자막 타임라인",
                    FAIL if strayed else PASS,
                    f"내장 자막 {lo:.1f}~{hi:.1f}s vs 영상 {video_len:.1f}s"
                    + (" — 영상 범위를 벗어남, X-TIMESTAMP-MAP 정렬 실패 의심" if strayed else ""),
                )
            rep.stats["subtitles"] = {
                "requested": subs.requested,
                "mode": "embedded",
                "tracks": [
                    {
                        "language": m.language,
                        "name": m.name,
                        "forced": m.forced,
                        "timestamp_offset_sec": round(subs.embed_offsets.get(m.uri or "", 0.0), 3),
                    }
                    for m in subs.embed_tracks
                ],
                "streams_in_output": len(actual),
                "span": list(subs.embed_span) if subs.embed_span else None,
            }

        if subs.embedded:
            rep.add(
                "내장 캡션",
                PASS,
                f"{len(subs.embedded)}개 선언 ({', '.join(subs.embedded)}) — 영상에 실려 있어 별도 파일 없음",
            )
        if subs.results:
            failed = [r for r in subs.results if not r.ok]
            good = subs.ok
            if failed:
                rep.add(
                    "자막 추출",
                    FAIL,
                    f"{len(failed)}/{len(subs.results)}개 실패 — "
                    + "; ".join(f"{r.track.label()}: {r.error.splitlines()[-1][:60]}" for r in failed[:2]),
                )
            else:
                fixes = []
                if (dups := sum(r.duplicates for r in good)):
                    fixes.append(f"경계 중복 {dups}큐 제거")
                if (leaks := sum(r.header_leaks for r in good)):
                    fixes.append(f"본문에 섞인 조각 헤더 {leaks}건 정제")
                if (shifted := [r for r in good if abs(r.offset) >= 0.5]):
                    fixes.append(
                        "X-TIMESTAMP-MAP 정렬 "
                        + ", ".join(f"{_tag(r)} {r.offset:+.2f}s" for r in shifted)
                    )
                if (side := [r for r in good if r.sidecar]):
                    fixes.append(f"사이드카 {len(side)}개는 URL 조립으로 확보")
                rep.add(
                    "자막 추출",
                    PASS,
                    f"{len(good)}개 전량 추출 ("
                    + ", ".join(f"{_tag(r)} {r.cues}큐" for r in good)
                    + ")"
                    + (f" — {', '.join(fixes)}" if fixes else ""),
                )

            # 자막 시각이 영상 길이를 벗어나면 X-TIMESTAMP-MAP 정렬이 어긋난 것이다.
            # --limit 로 앞부분만 받은 실행은 예외다 — 영상만 잘리고 자막은 온전히
            # 오므로 반드시 벗어난다. 기준선이 성립하지 않는 검사는 하지 않는다.
            if good and sampled:
                rep.add(
                    "자막 타임라인",
                    PASS,
                    f"판정 보류 — 영상이 앞 {video_len:.1f}s 만 받아진 표본이라 "
                    f"자막 전체 길이({max(r.last_cue for r in good):.1f}s)와 견줄 기준선이 없다",
                )
            elif good and video_len > 0:
                strayed = [r for r in good if r.last_cue > video_len + 5.0 or r.first_cue < -0.5]
                if strayed:
                    # 원인이 출처마다 다르다. HLS 트랙은 정렬 매핑을 잘못 적용한 것이고,
                    # 사이드카는 애초에 다른 영상의 자막을 집어온 것이다.
                    cause = (
                        "이름이 다른 영상의 자막일 가능성 — --sub-name 확인"
                        if all(r.sidecar for r in strayed)
                        else "X-TIMESTAMP-MAP 정렬 실패 의심"
                    )
                    rep.add(
                        "자막 타임라인",
                        FAIL,
                        "영상 범위를 벗어난 트랙 "
                        + ", ".join(
                            f"{_tag(r)}({r.first_cue:.1f}~{r.last_cue:.1f}s "
                            f"vs 영상 {video_len:.1f}s)"
                            for r in strayed[:3]
                        )
                        + f" — {cause}",
                    )
                else:
                    worst = min(good, key=lambda r: r.span)
                    cover = _pct(worst.span, video_len)
                    rep.add(
                        "자막 타임라인",
                        WARN if cover < 20 else PASS,
                        f"전 트랙이 영상 범위 내 (최소 커버리지 {cover:.0f}% — "
                        f"{worst.track.language or '?'} {worst.first_cue:.1f}~{worst.last_cue:.1f}s)",
                    )

        if subs.extra:
            got = [r for r in subs.extra if r.ok]
            rep.add(
                "자막 일괄 수집",
                PASS if got else WARN,
                f"이웃 화수 {len(got)}/{len(subs.extra)}개 확보 "
                f"— 현재 영상과 짝이 아니라 타임라인 검사 대상이 아니다",
            )

        rep.stats["subtitles"] = {
            "requested": subs.requested,
            "embedded_captions": subs.embedded,
            "extra": [
                {"name": r.track.name, "url": r.track.uri or "",
                 "path": str(r.path) if r.path else "", "ok": r.ok, "cues": r.cues}
                for r in subs.extra
            ],
            "tracks": [
                {
                    "language": r.track.language,
                    "name": r.track.name,
                    "forced": r.track.forced,
                    "default": r.track.default,
                    "sidecar": r.sidecar,
                    "url": r.track.uri or "",
                    "path": str(r.path) if r.path else "",
                    "ok": r.ok,
                    "cues": r.cues,
                    "duplicates_removed": r.duplicates,
                    "header_leaks_cleaned": r.header_leaks,
                    "timestamp_offset_sec": round(r.offset, 3),
                    "first_cue": round(r.first_cue, 3),
                    "last_cue": round(r.last_cue, 3),
                    "error": r.error[:300],
                }
                for r in subs.results
            ],
        }

    # 7) 전체 디코드
    if decode_errors is not None:
        count, lines = decode_errors
        rep.add(
            "전체 디코드",
            FAIL if count else PASS,
            f"오류 {count}건 — {lines[0][:80]}" if count else "끝까지 오류 없이 디코드",
        )
        rep.stats["decode"] = {"errors": count, "sample": lines}

    return rep
