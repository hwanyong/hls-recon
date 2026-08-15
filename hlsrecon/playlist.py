"""M3U8 플레이리스트 파서 (RFC 8216).

마스터 플레이리스트(화질 후보 목록)와 미디어 플레이리스트(세그먼트 목록)를
같은 진입점에서 파싱하고, 어느 쪽인지는 `Playlist.is_master`로 구분한다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlsplit

from .fetch import normalize_url

PLAYLIST_SUFFIXES = (".m3u8", ".m3u")


def is_playlist_uri(uri: str) -> bool:
    """주소가 플레이리스트를 가리키는가 — 경로 확장자로만 판단한다.

    자막 트랙 URI 에 자막 플레이리스트 대신 완성된 `.srt` 를 넣는 송출이 있어,
    받아보기 전에 갈라내야 하는 자리가 생긴다.
    """
    return urlsplit(uri).path.lower().endswith(PLAYLIST_SUFFIXES)

# 속성 리스트: KEY=VALUE 를 콤마로 구분하되, 따옴표 안의 콤마는 구분자가 아니다.
_ATTR_RE = re.compile(r'([A-Z0-9-]+)=("[^"]*"|[^,]*)')


def _absolute(base_url: str, uri: str | None) -> str | None:
    """플레이리스트에 적힌 URI 를 절대 주소로 만든다 — 여기가 URI 를 낳는 유일한 지점이다.

    절대화와 함께 퍼센트 인코딩까지 끝낸다. 이후 이 값은 요청에도, ffmpeg 입력에도
    그대로 쓰이므로 어느 한쪽에서만 정규화하면 다른 쪽이 열지 못한다.
    """
    if not uri:
        return uri
    return normalize_url(urljoin(base_url, uri) if base_url else uri)


def _parse_attrs(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for key, raw in _ATTR_RE.findall(text):
        out[key] = raw[1:-1] if raw.startswith('"') else raw
    return out


@dataclass
class Key:
    """#EXT-X-KEY — 이후 세그먼트에 적용되는 복호화 정보."""

    method: str  # NONE | AES-128 | SAMPLE-AES
    uri: str | None = None
    iv: bytes | None = None
    keyformat: str = "identity"

    @property
    def is_encrypted(self) -> bool:
        return self.method != "NONE"

    @property
    def is_supported(self) -> bool:
        # SAMPLE-AES 는 프레임 단위 부분 암호화라 세그먼트 통째 복호화가 불가능하다.
        return self.method in ("NONE", "AES-128") and self.keyformat == "identity"


@dataclass
class Media:
    """#EXT-X-MEDIA — 자막·다국어 오디오 등 부가 트랙 선언.

    GROUP-ID 로 묶이고, 화질 후보(#EXT-X-STREAM-INF)가 SUBTITLES/AUDIO 속성으로
    그 그룹을 참조한다. TYPE=CLOSED-CAPTIONS 만은 영상 스트림에 실려 오므로 URI 가 없다.
    """

    type: str  # AUDIO | SUBTITLES | CLOSED-CAPTIONS | VIDEO
    group_id: str
    name: str
    uri: str | None = None
    language: str = ""
    default: bool = False
    autoselect: bool = False
    forced: bool = False
    characteristics: str = ""
    instream_id: str = ""  # CLOSED-CAPTIONS 전용 (CC1~CC4, SERVICE1~)

    @property
    def is_embedded(self) -> bool:
        """영상 스트림에 실려 오는 트랙 — 따로 내려받을 대상이 아니다."""
        return self.uri is None

    def label(self) -> str:
        flags = [f for f, on in (("default", self.default), ("forced", self.forced)) if on]
        # 청각장애인용 자막(SDH)은 characteristics 로 표시된다.
        if "public.accessibility" in self.characteristics:
            flags.append("SDH")
        if self.is_embedded:
            flags.append(f"내장 {self.instream_id}" if self.instream_id else "내장")
        tag = f" [{', '.join(flags)}]" if flags else ""
        return f"{self.language or '?'} · {self.name or '이름없음'}{tag}"


@dataclass
class Variant:
    """#EXT-X-STREAM-INF — 마스터 플레이리스트의 화질 후보 하나."""

    uri: str
    bandwidth: int = 0
    resolution: str = ""
    codecs: str = ""
    frame_rate: float = 0.0
    name: str = ""
    subtitles_group: str = ""  # SUBTITLES="..." — 이 후보에 딸린 자막 그룹
    audio_group: str = ""  # AUDIO="..."

    @property
    def height(self) -> int:
        if "x" in self.resolution:
            try:
                return int(self.resolution.split("x")[1])
            except ValueError:
                return 0
        return 0

    def label(self) -> str:
        parts = [self.name or (self.resolution or "unknown")]
        if self.bandwidth:
            parts.append(f"{self.bandwidth / 1_000_000:.2f}Mbps")
        if self.frame_rate:
            parts.append(f"{self.frame_rate:g}fps")
        if self.codecs:
            parts.append(self.codecs)
        return " / ".join(parts)


@dataclass
class Segment:
    """미디어 플레이리스트의 세그먼트 한 조각."""

    uri: str
    duration: float
    seq: int  # media sequence number — AES-128 기본 IV 산출에 쓰인다
    index: int  # 플레이리스트 내 0-기반 순번
    key: Key | None = None
    byterange: tuple[int, int] | None = None  # (length, offset)
    discontinuity: bool = False
    title: str = ""


@dataclass
class Playlist:
    version: int = 0
    is_master: bool = False
    variants: list[Variant] = field(default_factory=list)
    media: list[Media] = field(default_factory=list)
    segments: list[Segment] = field(default_factory=list)
    target_duration: float = 0.0
    media_sequence: int = 0
    playlist_type: str = ""  # VOD | EVENT | ""
    has_endlist: bool = False
    init_map: tuple[str, tuple[int, int] | None] | None = None  # #EXT-X-MAP (fMP4)
    base_url: str = ""

    @property
    def is_live(self) -> bool:
        """ENDLIST 가 없으면 진행 중인 라이브 송출이다."""
        return not self.is_master and not self.has_endlist

    @property
    def is_fmp4(self) -> bool:
        return self.init_map is not None

    @property
    def declared_duration(self) -> float:
        """EXTINF 선언값의 합계 — 실측 duration 과 대조할 기준선."""
        return sum(s.duration for s in self.segments)

    def tracks(self, kind: str, group: str = "") -> list[Media]:
        """부가 트랙 조회. group 을 주면 해당 그룹으로 한정한다."""
        return [
            m
            for m in self.media
            if m.type == kind and (not group or m.group_id == group)
        ]

    def pick_variant(
        self, height: int | None = None, max_bandwidth: int | None = None
    ) -> Variant:
        """화질 후보 선택. 지정이 없으면 대역폭 최댓값."""
        if not self.variants:
            raise ValueError("마스터 플레이리스트에 variant 가 없다")
        pool = self.variants
        if height is not None:
            matched = [v for v in pool if v.height == height]
            if not matched:
                avail = sorted({v.height for v in pool if v.height}, reverse=True)
                raise ValueError(
                    f"{height}p 후보가 없다. 사용 가능: {avail or '해상도 미표기'}"
                )
            pool = matched
        if max_bandwidth is not None:
            under = [v for v in pool if v.bandwidth <= max_bandwidth]
            if under:
                pool = under
        return max(pool, key=lambda v: v.bandwidth)


def parse(text: str, base_url: str = "") -> Playlist:
    """M3U8 텍스트를 Playlist 로 변환한다. 모든 uri 는 base_url 기준 절대 URL."""
    lines = [ln.strip() for ln in text.splitlines()]
    if not lines or not lines[0].startswith("#EXTM3U"):
        raise ValueError("#EXTM3U 헤더가 없다 — M3U8 플레이리스트가 아니다")

    pl = Playlist(base_url=base_url)

    cur_key: Key | None = None
    cur_inf: tuple[float, str] | None = None
    cur_range: tuple[int, int] | None = None
    pending_disc = False
    prev_range_end = 0
    seq = 0
    pending_variant: Variant | None = None

    for line in lines:
        if not line:
            continue

        if not line.startswith("#"):
            # 태그가 아닌 줄 = 직전 태그가 가리키는 URI
            uri = _absolute(base_url, line)
            if pending_variant is not None:
                pending_variant.uri = uri
                pl.variants.append(pending_variant)
                pending_variant = None
            elif cur_inf is not None:
                dur, title = cur_inf
                pl.segments.append(
                    Segment(
                        uri=uri,
                        duration=dur,
                        seq=seq,
                        index=len(pl.segments),
                        key=cur_key,
                        byterange=cur_range,
                        discontinuity=pending_disc,
                        title=title,
                    )
                )
                seq += 1
                cur_inf = None
                if cur_range:
                    prev_range_end = cur_range[1] + cur_range[0]
                cur_range = None
                pending_disc = False
            continue

        if line.startswith("#EXT-X-VERSION:"):
            pl.version = int(line.split(":", 1)[1])

        elif line.startswith("#EXT-X-STREAM-INF:"):
            a = _parse_attrs(line.split(":", 1)[1])
            pl.is_master = True
            pending_variant = Variant(
                uri="",
                bandwidth=int(a.get("BANDWIDTH", 0) or 0),
                resolution=a.get("RESOLUTION", ""),
                codecs=a.get("CODECS", ""),
                frame_rate=float(a.get("FRAME-RATE", 0) or 0),
                name=a.get("NAME", ""),
                subtitles_group=a.get("SUBTITLES", ""),
                audio_group=a.get("AUDIO", ""),
            )

        elif line.startswith("#EXT-X-MEDIA:"):
            a = _parse_attrs(line.split(":", 1)[1])
            pl.is_master = True
            uri = a.get("URI")
            pl.media.append(
                Media(
                    type=a.get("TYPE", ""),
                    group_id=a.get("GROUP-ID", ""),
                    name=a.get("NAME", ""),
                    uri=_absolute(base_url, uri),
                    language=a.get("LANGUAGE", ""),
                    default=a.get("DEFAULT", "NO") == "YES",
                    autoselect=a.get("AUTOSELECT", "NO") == "YES",
                    forced=a.get("FORCED", "NO") == "YES",
                    characteristics=a.get("CHARACTERISTICS", ""),
                    instream_id=a.get("INSTREAM-ID", ""),
                )
            )

        elif line.startswith("#EXTINF:"):
            body = line.split(":", 1)[1]
            dur_s, _, title = body.partition(",")
            cur_inf = (float(dur_s), title.strip())

        elif line.startswith("#EXT-X-TARGETDURATION:"):
            pl.target_duration = float(line.split(":", 1)[1])

        elif line.startswith("#EXT-X-MEDIA-SEQUENCE:"):
            pl.media_sequence = int(line.split(":", 1)[1])
            seq = pl.media_sequence

        elif line.startswith("#EXT-X-PLAYLIST-TYPE:"):
            pl.playlist_type = line.split(":", 1)[1].strip()

        elif line.startswith("#EXT-X-KEY:"):
            a = _parse_attrs(line.split(":", 1)[1])
            method = a.get("METHOD", "NONE")
            iv_hex = a.get("IV", "")
            cur_key = Key(
                method=method,
                uri=_absolute(base_url, a.get("URI")),
                iv=bytes.fromhex(iv_hex[2:]) if iv_hex.lower().startswith("0x") else None,
                keyformat=a.get("KEYFORMAT", "identity"),
            )

        elif line.startswith("#EXT-X-MAP:"):
            a = _parse_attrs(line.split(":", 1)[1])
            uri = a.get("URI", "")
            rng = None
            if "BYTERANGE" in a:
                n, _, o = a["BYTERANGE"].partition("@")
                rng = (int(n), int(o or 0))
            pl.init_map = (_absolute(base_url, uri), rng)

        elif line.startswith("#EXT-X-BYTERANGE:"):
            n, _, o = line.split(":", 1)[1].partition("@")
            cur_range = (int(n), int(o) if o else prev_range_end)

        elif line == "#EXT-X-DISCONTINUITY":
            pending_disc = True

        elif line == "#EXT-X-ENDLIST":
            pl.has_endlist = True

    return pl
