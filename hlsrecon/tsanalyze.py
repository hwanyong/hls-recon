"""세그먼트 페이로드 분석 — 컨테이너 판별과 MPEG-TS 전송 무결성.

ffmpeg 는 디코딩 관점의 오류만 보고한다. 송출 검증에서 정작 필요한 것은
"전송 도중 패킷이 빠졌는가"이고, 그 답은 TS 패킷 헤더의 4비트
continuity counter 에 있다 — PID 별로 0~15 를 순환하므로 값이 건너뛰면 유실이다.
"""

from __future__ import annotations

from dataclasses import dataclass, field

PACKET_SIZE = 188
SYNC_BYTE = 0x47
NULL_PID = 0x1FFF

# ISO base media file format 의 최상위 box 타입 — fMP4 세그먼트의 선두에 온다.
_MP4_BOXES = {b"ftyp", b"styp", b"moof", b"moov", b"sidx", b"emsg", b"free", b"skip"}


def sniff(data: bytes) -> str:
    """세그먼트 바이트의 컨테이너 종류를 판별한다: mpegts | fmp4 | unknown.

    HTTP 200 으로 응답했다고 미디어가 온 것은 아니다. 토큰이 만료된 CDN 이
    404 대신 HTML 오류 페이지를 200 으로 돌려주는 사례가 흔한데, 이때
    '수신 성공'으로 집계되면 검증 자체가 무의미해진다. 상태 코드가 아니라
    선두 바이트로 판정한다.
    """
    if len(data) < 8:
        return "unknown"
    # TS 는 188바이트 주기로 sync byte 가 반복되므로 두 번째 패킷까지 확인한다.
    if data[0] == SYNC_BYTE and (
        len(data) < PACKET_SIZE + 1 or data[PACKET_SIZE] == SYNC_BYTE
    ):
        return "mpegts"
    if data[4:8] in _MP4_BOXES:
        return "fmp4"
    return "unknown"


@dataclass
class TSReport:
    packets: int = 0
    parsed: bool = False  # TS 로 해석되었는가 (fMP4 면 False)
    sync_errors: int = 0  # sync byte 0x47 불일치 = 스트림 정렬 깨짐
    transport_errors: int = 0  # TEI 플래그 = 전송 계층이 표시한 오류
    cc_discontinuities: int = 0  # continuity counter 점프 = 패킷 유실
    scrambled_packets: int = 0  # scrambling control ≠ 0 = 복호화되지 않음
    pids: set[int] = field(default_factory=set)
    cc_detail: list[tuple[int, int, int]] = field(default_factory=list)  # (pid, 기대, 실제)

    @property
    def clean(self) -> bool:
        return (
            self.sync_errors == 0
            and self.transport_errors == 0
            and self.cc_discontinuities == 0
            and self.scrambled_packets == 0
        )

    def merge(self, other: "TSReport") -> None:
        self.packets += other.packets
        self.parsed = self.parsed or other.parsed
        self.sync_errors += other.sync_errors
        self.transport_errors += other.transport_errors
        self.cc_discontinuities += other.cc_discontinuities
        self.scrambled_packets += other.scrambled_packets
        self.pids |= other.pids
        self.cc_detail.extend(other.cc_detail[: max(0, 20 - len(self.cc_detail))])


def analyze(data: bytes, state: dict[int, int] | None = None) -> TSReport:
    """세그먼트 바이트열을 TS 로 해석해 검사한다.

    state 는 PID→직전 CC 매핑으로, 세그먼트 경계를 넘어 연속성을 이어보기 위해
    호출자가 같은 dict 를 계속 넘겨준다. None 이면 세그먼트 내부만 검사한다.
    """
    rep = TSReport()
    if len(data) < PACKET_SIZE or data[0] != SYNC_BYTE:
        # fMP4(ftyp/moof 시작) 등 TS 가 아닌 컨테이너 — 분석 대상 아님
        return rep

    rep.parsed = True
    last_cc = state if state is not None else {}

    for off in range(0, len(data) - PACKET_SIZE + 1, PACKET_SIZE):
        pkt = data[off : off + PACKET_SIZE]
        rep.packets += 1

        if pkt[0] != SYNC_BYTE:
            rep.sync_errors += 1
            continue

        if pkt[1] & 0x80:
            rep.transport_errors += 1

        pid = ((pkt[1] & 0x1F) << 8) | pkt[2]
        if pid == NULL_PID:
            continue
        rep.pids.add(pid)

        if (pkt[3] >> 6) & 0x03:
            rep.scrambled_packets += 1

        has_payload = bool(pkt[3] & 0x10)
        cc = pkt[3] & 0x0F

        # CC 는 payload 를 실은 패킷에서만 증가한다. adaptation-only 패킷은 유지.
        if not has_payload:
            last_cc[pid] = cc
            continue

        prev = last_cc.get(pid)
        if prev is not None:
            expected = (prev + 1) & 0x0F
            if cc != expected and cc != prev:  # cc == prev 는 규격상 허용된 중복 패킷
                rep.cc_discontinuities += 1
                if len(rep.cc_detail) < 20:
                    rep.cc_detail.append((pid, expected, cc))
        last_cc[pid] = cc

    return rep
