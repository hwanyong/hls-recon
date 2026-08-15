"""ffprobe / ffmpeg 계측 래퍼.

플레이리스트가 선언한 값(EXTINF)과 실제 미디어의 값을 대조하기 위한 실측 계층이다.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass, field

from . import playlist


class ToolMissing(RuntimeError):
    pass


def require(tool: str) -> str:
    path = shutil.which(tool)
    if not path:
        raise ToolMissing(f"{tool} 를 찾을 수 없다. `brew install ffmpeg` 로 설치할 것")
    return path


# HLS 세그먼트로 열어도 되는 확장자 — 이 도구가 다루는 것의 단일 출처.
#
#   ts m4s mp4 m4v mov      영상 세그먼트와 fMP4 초기화 세그먼트(EXT-X-MAP)
#   m4a aac mp3 ac3 ec3     오디오 전용 송출
#   vtt webvtt              자막 세그먼트
#   m3u8 m3u                자막·variant 플레이리스트를 다시 가리키는 경우
#   html                    확장자 차단을 피하려는 위장 송출 — 실측한 것만 둔다.
#                           선두 바이트가 MPEG-TS 인 정상 세그먼트이며, 판별은
#                           확장자가 아니라 tsanalyze.sniff() 가 따로 한다.
#
# 예전에는 `ALL` 을 넘겼다. 열거로 바꾼 것은 이 옵션이 원래 **보안 방어**이기
# 때문이다 — HLS 플레이리스트의 세그먼트 URI 는 규격상 자유라, 그대로 열면 미디어와
# 무관한 demuxer 가 강제로 열린다(CVE-2023-6602: Force TTY Demuxer, XBIN DoS
# Amplification). ffmpeg 은 그 공격면을 확장자 allowlist 로 좁혔고 `ALL` 은 그것을
# 끄는 값이다.
#
# 다만 정직하게 적어 둔다. **ffmpeg 8.1.1 에서 실측한 결과 `ALL` 과 이 열거의 동작은
# 완전히 같았다.** 뒤에 놓인 포맷–확장자 일치 검사가 먼저 걸러내기 때문이다
# (내용이 MPEG-TS 인데 확장자가 `.avi` 면 어느 쪽이든 거부된다). 즉 이 변경의 현재
# 이득은 측정되지 않는다. 그럼에도 열거를 택한 이유는 둘이다.
#
#   · 이 도구는 ffmpeg 버전을 고정하지 않는다. 뒤쪽 검사가 없는 빌드에서는 이
#     옵션이 유일한 관문이 되므로, 그때는 `ALL` 과 열거의 차이가 그대로 드러난다.
#   · `ALL` 은 "무엇이든 연다"는 선언이고 그것은 이 도구의 실제 필요와 다르다.
#     목록 자체가 "이 도구가 무엇을 다루는가"의 기록이 된다.
ALLOWED_SEGMENT_EXTS = "ts,m4s,mp4,m4v,mov,m4a,aac,mp3,ac3,ec3,vtt,webvtt,m3u8,m3u,html"


def input_args(headers: dict[str, str] | None = None, target: str = "") -> list[str]:
    """ffmpeg/ffprobe 입력(`-i`) 앞에 붙일 공통 인자.

    세 도구(재조립·실측·자막 추출)가 같은 조건으로 원본에 접근해야 한다. 한 곳만
    빠지면 "받아지는데 실측만 실패" 같은 갈라진 증상이 난다.

    - headers      : UA·Referer·Cookie 를 세그먼트 요청까지 그대로 이어간다.
    - whitelist    : 로컬 .m3u8 이 원격 세그먼트를 참조하는 구조를 허용한다.
                     모든 demuxer 가 받는 옵션이라 입력을 가리지 않는다.
    - extensions   : 세그먼트를 `.html` 등으로 위장해 확장자 차단을 피하는 CDN 이
                     있다. ffmpeg 은 확장자를 두 층에서 검사하는데, 이 옵션이
                     관장하는 층은 **로컬 경로 세그먼트**에 걸린다(원격 세그먼트는
                     `allowed_segment_extensions` 라는 별도 옵션이 관장하며 그쪽
                     기본값에는 `html` 이 이미 들어 있다). 받아둔 세그먼트를 로컬
                     플레이리스트로 다시 검증할 때 이 옵션이 필요하다.
                     **HLS demuxer 에만 있는 옵션**이라 플레이리스트가 아닌 입력에
                     붙이면 `Option allowed_extensions not found` 로 열기 자체가
                     실패한다 — 자막 트랙에 완성 `.srt` 를 넣는 송출에서 실제로
                     걸린다. 그래서 target 을 받아 플레이리스트일 때만 붙인다.
    """
    args: list[str] = []
    if headers:
        args += ["-headers", "".join(f"{k}: {v}\r\n" for k, v in headers.items())]
    args += ["-protocol_whitelist", "file,http,https,tcp,tls,crypto"]
    if playlist.is_playlist_uri(target):
        args += ["-allowed_extensions", ALLOWED_SEGMENT_EXTS]
    return args


@dataclass
class StreamInfo:
    index: int
    kind: str  # video | audio | subtitle
    codec: str
    profile: str = ""
    width: int = 0
    height: int = 0
    fps: str = ""
    channels: int = 0
    sample_rate: str = ""
    bit_rate: int = 0

    def describe(self) -> str:
        rate = f" {self.bit_rate / 1000:.0f}kbps" if self.bit_rate else ""
        if self.kind == "video":
            geo = f"{self.width}x{self.height}" if self.width else "?"
            return f"{self.codec} {self.profile} {geo} @{self.fps or '?'}fps{rate}".strip()
        if self.kind == "audio":
            return f"{self.codec} {self.channels}ch {self.sample_rate or '?'}Hz{rate}".strip()
        return f"{self.codec}{rate}".strip()


@dataclass
class MediaInfo:
    ok: bool = False
    duration: float = 0.0
    size: int = 0
    bit_rate: int = 0
    format_name: str = ""
    streams: list[StreamInfo] = field(default_factory=list)
    error: str = ""

    def video(self) -> StreamInfo | None:
        return next((s for s in self.streams if s.kind == "video"), None)

    def audio(self) -> StreamInfo | None:
        return next((s for s in self.streams if s.kind == "audio"), None)


def probe(target: str, headers: dict[str, str] | None = None) -> MediaInfo:
    """로컬 파일 또는 URL 의 컨테이너·스트림 정보를 실측한다."""
    cmd = [require("ffprobe"), "-v", "error", "-hide_banner"]
    cmd += input_args(headers, target)
    cmd += ["-show_format", "-show_streams", "-of", "json", target]

    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        return MediaInfo(ok=False, error=proc.stderr.strip()[:500])

    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        return MediaInfo(ok=False, error=f"ffprobe 출력 파싱 실패: {e}")

    fmt = data.get("format", {})
    info = MediaInfo(
        ok=True,
        duration=float(fmt.get("duration", 0) or 0),
        size=int(fmt.get("size", 0) or 0),
        bit_rate=int(fmt.get("bit_rate", 0) or 0),
        format_name=fmt.get("format_name", ""),
    )
    for s in data.get("streams", []):
        info.streams.append(
            StreamInfo(
                index=s.get("index", 0),
                kind=s.get("codec_type", "?"),
                codec=s.get("codec_name", "?"),
                profile=s.get("profile", "") or "",
                width=int(s.get("width", 0) or 0),
                height=int(s.get("height", 0) or 0),
                fps=_ratio(s.get("avg_frame_rate", "")),
                channels=int(s.get("channels", 0) or 0),
                sample_rate=s.get("sample_rate", "") or "",
                bit_rate=int(s.get("bit_rate", 0) or 0),
            )
        )
    return info


@dataclass
class Gap:
    """재생 타임라인에서 프레임이 존재하지 않는 구간."""

    start: float
    end: float

    @property
    def length(self) -> float:
        return self.end - self.start


@dataclass
class GapScan:
    ok: bool = False
    gaps: list[Gap] = field(default_factory=list)
    frames: int = 0
    frame_interval: float = 0.0  # 프레임 간격 중앙값
    threshold: float = 0.0
    error: str = ""

    @property
    def lost(self) -> float:
        return sum(g.length for g in self.gaps)


def gap_scan(path: str, factor: float = 3.0, floor: float = 0.4) -> GapScan:
    """영상 트랙의 표시 시각을 훑어 결손 구간을 찾는다.

    총 길이 비교로는 중간 세그먼트 유실을 잡을 수 없다. MPEG-TS 세그먼트는
    절대 PTS(표시 시각)를 담고 있어서, 한 조각이 빠져도 뒤 조각의 시각이
    원래대로 유지되어 총 길이가 그대로이기 때문이다. 결손은 총량이 아니라
    타임라인의 구멍으로 나타나므로 인접 프레임 간격을 직접 본다.
    """
    proc = subprocess.run(
        [
            require("ffprobe"), "-v", "error", "-hide_banner",
            "-select_streams", "v:0",
            "-show_entries", "packet=pts_time",
            "-of", "csv=p=0",
            path,
        ],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return GapScan(ok=False, error=proc.stderr.strip()[:300])

    times: list[float] = []
    for tok in proc.stdout.replace(",", "\n").split():
        try:
            times.append(float(tok))
        except ValueError:
            continue  # N/A 등 시각 없는 패킷
    if len(times) < 3:
        return GapScan(ok=False, error="표시 시각을 가진 영상 패킷이 부족하다")

    # B-프레임이 있으면 패킷 순서가 표시 순서와 다르므로 시각 기준으로 정렬한다.
    times.sort()
    deltas = [b - a for a, b in zip(times, times[1:])]
    ordered = sorted(deltas)
    median = ordered[len(ordered) // 2]
    threshold = max(floor, median * factor)

    scan = GapScan(ok=True, frames=len(times), frame_interval=median, threshold=threshold)
    for (a, b), d in zip(zip(times, times[1:]), deltas):
        if d > threshold:
            scan.gaps.append(Gap(start=a, end=b))
    return scan


def first_pts(target: str, headers: dict[str, str] | None = None) -> float | None:
    """영상 트랙의 첫 표시 시각(초). 자막 정렬 기준선으로 쓴다."""
    cmd = [require("ffprobe"), "-v", "error", "-hide_banner"]
    cmd += input_args(headers, target)
    cmd += [
        "-select_streams", "v:0",
        "-show_entries", "packet=pts_time",
        "-read_intervals", "%+#1",
        "-of", "csv=p=0",
        target,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        return None
    for tok in proc.stdout.replace(",", "\n").split():
        try:
            return float(tok)
        except ValueError:
            continue
    return None


def subtitle_span(path: str, index: int = 0) -> tuple[float, float] | None:
    """컨테이너에 들어 있는 자막 트랙의 첫 큐 시작·마지막 큐 종료 시각(초).

    자막을 내장한 경우 sidecar 파일이 없으므로, 정렬이 맞는지 확인하려면
    산출물 안의 자막 패킷을 직접 봐야 한다.
    """
    proc = subprocess.run(
        [
            require("ffprobe"), "-v", "error", "-hide_banner",
            "-select_streams", f"s:{index}",
            "-show_entries", "packet=pts_time,duration_time",
            "-of", "csv=p=0",
            path,
        ],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return None

    starts: list[float] = []
    ends: list[float] = []
    for line in proc.stdout.splitlines():
        cols = [c for c in line.strip().split(",") if c not in ("", "N/A")]
        if not cols:
            continue
        try:
            start = float(cols[0])
        except ValueError:
            continue
        starts.append(start)
        try:
            ends.append(start + float(cols[1]))
        except (IndexError, ValueError):
            ends.append(start)
    if not starts:
        return None
    return min(starts), max(ends)


def decode_check(path: str) -> tuple[int, list[str]]:
    """전체 디코드를 돌려 오류 줄을 수집한다. 출력은 버린다(-f null).

    파일이 '열린다'와 '끝까지 디코드된다'는 다른 문제라, 재조립 검증에서는 후자가 기준이다.
    """
    proc = subprocess.run(
        [require("ffmpeg"), "-v", "error", "-hide_banner", "-xerror", "-i", path, "-f", "null", "-"],
        capture_output=True,
        text=True,
    )
    lines = [ln for ln in proc.stderr.splitlines() if ln.strip()]
    return len(lines), lines[:20]


def _ratio(value: str) -> str:
    """ffprobe 의 '30000/1001' 형태를 소수로 바꾼다."""
    if not value or "/" not in value:
        return value or ""
    num, _, den = value.partition("/")
    try:
        n, d = float(num), float(den)
    except ValueError:
        return value
    return "" if d == 0 else f"{n / d:.3f}".rstrip("0").rstrip(".")


