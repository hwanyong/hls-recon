"""재고 조사 — 같은 폴더에 다시 받을 때 '빠진 회차'만 가려낸다.

두 번째 실행에서 이미 있는 회차를 건너뛰는 것은 파일이 있는지 보면 되는 일처럼
보인다. 실제로는 셋이 걸린다.

- **파일 이름을 미리 알 수 없다.** 저장 이름은 플레이어 설정의 `title` 에서 오고,
  그것을 읽으려면 회차마다 재생 소스를 발급받아야 한다(`series.resolve`). 이름을
  안 뒤에 건너뛰면 27화를 이미 다 받아둔 경우에도 발급 요청이 27번 그대로 나간다 —
  회차마다 페이지·플레이어·XHR 세 번이므로 80여 건이 헛되이 오간다. 그래서 이름
  대신 **회차 번호**로 견준다. 번호는 목록 페이지에서 이미 알고 있어 공짜다.
- **확장자가 지난번과 다를 수 있다.** `--container` 를 바꿔 실행하면 이름은 같고
  확장자만 다르다. 완전 일치로 보면 전부 없는 것이 되어 27화를 다시 받는다.
- **끊긴 파일이 완성본 행세를 한다.** `_discard` 는 SystemExit·Ctrl-C 경로만
  치운다. 강제 종료·전원 차단·디스크 가득 참으로 남은 조각은 다음 실행에서
  '이미 있다'로 읽혀 **영원히 복구되지 않는다.** 있는지뿐 아니라 온전한지까지 본다.

온전한지는 싸게 확인할 수 있는 것만 기본으로 본다. 27개를 매번 ffprobe 로 열면
재실행이 느려져 '빠진 것만 받는다'는 이득이 사라지기 때문이다. 실제로 열어보는
것은 `--verify-existing` 으로 따로 요청받는다.
"""

from __future__ import annotations

import re
import struct
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

from . import probe
from .library import MEDIA_EXTS, SIDECAR_EXTS, sidecars
from .naming import episode_of, series_of

# 이보다 작으면 영상일 수 없다. 먹싱이 시작하자마자 끊기면 헤더 몇 KB 만 남는다.
MIN_BYTES = 64 * 1024

# ISO-BMFF 상자 머리 = 크기 4바이트 + 종류 4바이트.
_BOX_HEADER = 8

_ISOBMFF_EXTS = frozenset({".mp4", ".m4v", ".mov"})
_EBML_EXTS = frozenset({".mkv", ".webm"})

_EBML_MAGIC = b"\x1a\x45\xdf\xa3"
_TS_SYNC = 0x47
_TS_PACKET = 188


@dataclass
class Item:
    """폴더에 이미 있는 회차 하나."""

    number: int
    video: Path
    subs: list[Path] = field(default_factory=list)
    flaw: str = ""  # 비어 있지 않으면 온전하다고 볼 수 없는 사유

    @property
    def ok(self) -> bool:
        return not self.flaw


# ─────────────────────────────────────────────────────────────────────────────
# 온전한가
# ─────────────────────────────────────────────────────────────────────────────


def _isobmff_flaw(path: Path, size: int) -> str:
    """MP4 계열이 끝까지 쓰였는지 최상위 상자만 훑어 확인한다.

    `-movflags +faststart` 로 만들므로 정상 파일은 `ftyp` 다음에 `moov` 가 온다.
    먹싱 도중 끊기면 `moov` 가 아예 없거나, 선언된 크기가 파일 끝을 넘어간다.
    본문(`mdat`)은 읽지 않고 건너뛰므로 파일이 아무리 커도 빠르다 — 상자 수만큼의
    seek 이 전부다.
    """
    seen: set[bytes] = set()
    with path.open("rb") as fh:
        offset = 0
        while offset < size:
            fh.seek(offset)
            head = fh.read(_BOX_HEADER)
            if len(head) < _BOX_HEADER:
                return "상자 머리가 잘렸다 — 먹싱이 끝나기 전에 끊겼다"
            box_size, kind = struct.unpack(">I4s", head)
            if box_size == 1:  # 64비트 largesize 가 뒤따른다
                ext = fh.read(8)
                if len(ext) < 8:
                    return "64비트 상자 크기가 잘렸다 — 먹싱이 끝나기 전에 끊겼다"
                box_size = struct.unpack(">Q", ext)[0]
            elif box_size == 0:  # 파일 끝까지가 이 상자다
                box_size = size - offset
            name = kind.decode("ascii", errors="replace")
            if box_size < _BOX_HEADER:
                return f"상자 크기가 비정상이다 ({name}: {box_size})"
            if offset + box_size > size:
                return f"{name} 상자가 파일 끝을 넘어간다 — 잘린 파일"
            seen.add(kind)
            offset += box_size
    if b"moov" not in seen:
        return "moov 상자가 없다 — 먹싱이 끝나기 전에 끊겼다"
    if b"mdat" not in seen:
        return "mdat 상자가 없다 — 내용이 비었다"
    return ""


def _head_flaw(path: Path, magic: bytes, what: str) -> str:
    """선두 몇 바이트가 그 컨테이너의 서명과 맞는지만 본다."""
    with path.open("rb") as fh:
        if fh.read(len(magic)) != magic:
            return f"{what} 서명이 없다 — 내용이 그 컨테이너가 아니다"
    return ""


def _ts_flaw(path: Path) -> str:
    """MPEG-TS 는 188바이트 주기로 동기 바이트(0x47)가 온다. 둘을 견준다."""
    with path.open("rb") as fh:
        head = fh.read(_TS_PACKET + 1)
    if len(head) < _TS_PACKET + 1:
        return "패킷 하나도 채우지 못했다"
    if head[0] != _TS_SYNC or head[_TS_PACKET] != _TS_SYNC:
        return "MPEG-TS 동기 바이트가 맞지 않는다"
    return ""


def flaw(path: Path, deep: bool = False) -> str:
    """파일이 온전하지 않다고 볼 사유. 온전하면 빈 문자열.

    기본은 컨테이너 구조만 본다 — 크기·서명·상자 경계. 이것만으로 '먹싱 도중
    끊긴 파일'이라는 현실적인 실패는 잡힌다. deep 은 그 위에 ffprobe 를 얹어
    실제로 열리는지까지 확인한다. 느린 대신 확실하다.
    """
    try:
        size = path.stat().st_size
    except OSError as e:
        return f"읽을 수 없다: {e}"
    if size < MIN_BYTES:
        return f"{size:,}B 뿐이다 — 영상이라고 보기 어렵다"

    ext = path.suffix.lower()
    try:
        if ext in _ISOBMFF_EXTS:
            why = _isobmff_flaw(path, size)
        elif ext in _EBML_EXTS:
            why = _head_flaw(path, _EBML_MAGIC, "EBML")
        elif ext == ".ts":
            why = _ts_flaw(path)
        else:
            why = ""
    except OSError as e:
        return f"읽는 중 실패: {e}"
    if why:
        return why

    if deep:
        info = probe.probe(str(path))
        if not info.ok:
            tail = info.error.strip().splitlines()[-1][:120] if info.error else ""
            return f"ffprobe 가 열지 못했다: {tail}"
        if info.duration <= 0:
            return "재생 길이가 0 이다"
    return ""


# ─────────────────────────────────────────────────────────────────────────────
# 폴더 훑기
# ─────────────────────────────────────────────────────────────────────────────


def scan(folder: Path, deep: bool = False) -> dict[str, dict[int, Item]]:
    """폴더의 영상 파일을 시리즈 줄기별 → 회차 번호별로 정리한다.

    줄기로 한 번 가르는 이유는 `--flat` 때문이다. 시리즈 폴더 안이라면 한 작품뿐이라
    번호만으로 충분하지만, 여러 작품을 한 폴더에 쌓아두면 `A 03` 이 있다고 해서
    `B 03` 을 받은 것이 아니다. 번호만 보고 건너뛰면 남의 회차를 근거로 내 회차를
    빠뜨린다.

    화수가 없는 파일(영화 한 편)은 시리즈의 회차로 볼 근거가 없어 제외한다.
    하위 폴더는 보지 않는다 — 받는 자리는 언제나 이 폴더 하나다.
    """
    if not folder.is_dir():
        return {}
    files = sorted(p for p in folder.iterdir() if p.is_file() and not p.name.startswith("."))

    groups: dict[str, dict[int, Item]] = {}
    for f in files:
        if f.suffix.lower() not in MEDIA_EXTS:
            continue
        number = episode_of(f.stem)
        if number is None:
            continue
        item = Item(
            number=number,
            video=f,
            subs=[s for s in sidecars(f, files) if s.suffix.lower() in SIDECAR_EXTS],
            flaw=flaw(f, deep),
        )
        slot = groups.setdefault(series_of(f.stem), {})
        prev = slot.get(number)
        # 같은 회차가 확장자만 달리 둘 있으면(.mp4 로 받았다가 .mkv 로 다시 받은 경우)
        # 온전한 쪽을 남긴다. 손상본을 근거로 '이미 있다'고 판단하지 않기 위해서다.
        if prev is None or (prev.flaw and not item.flaw):
            slot[number] = item
    return groups


def _key(s: str) -> str:
    """견주기용 표기 — NFC 로 맞추고 공백·구분자를 없앤다.

    macOS 파일 시스템은 한글을 자모 분리형(NFD)으로 돌려주고 사이트가 알려준
    작품명은 완성형(NFC)이다. 정규화하지 않으면 눈에 같은 두 문자열이 어긋난다.
    """
    return re.sub(r"[\s._-]+", "", unicodedata.normalize("NFC", s)).casefold()


def stock_for(groups: dict[str, dict[int, Item]], title: str) -> tuple[dict[int, Item], str]:
    """작품명에 해당하는 재고를 고른다. 반환: (회차 번호 → 항목, 사람에게 보일 사유)

    파일 이름의 줄기(`그렌라간`)와 사이트가 알려준 작품명(`천원돌파 그렌라간`)은
    자주 어긋난다 — 파일 이름은 플레이어가 정하고 작품명은 목록 페이지가 정하기
    때문이다. 그래서 완전 일치만 보지 않고 세 단계로 좁힌다.

        1. 완전 일치                     `작품`      ← `작품`
        2. 작품명이 줄기를 품는다        `그렌라간`   ← `천원돌파 그렌라간`
        3. 줄기가 작품명을 품는다        `천원돌파 그렌라간` ← `그렌라간`

    2단계에서 여럿이 걸리면 **가장 긴 줄기**를 택한다. `다른작품 시즌2` 에는
    `작품` 과 `다른작품` 이 모두 들어 있지만 더 많이 겹치는 쪽이 그 작품이다.
    길이가 같아 우열이 없으면 포기한다.

    가릴 수 없으면 **빈 재고를 준다.** 잘못 짚어 건너뛰면 회차가 조용히 빠지지만,
    빈 재고는 기존의 파일명 일치 검사로 되돌아갈 뿐이라 손해가 작다.
    """
    if not groups:
        return {}, ""
    if len(groups) == 1:
        stem, only = next(iter(groups.items()))
        return only, f"'{stem}'"

    want = _key(title)
    keys = {stem: _key(stem) for stem in groups}

    exact = [s for s, k in keys.items() if k and k == want]
    if len(exact) == 1:
        return groups[exact[0]], f"'{exact[0]}'"

    inside = sorted((s for s, k in keys.items() if k and k in want), key=lambda s: -len(keys[s]))
    if inside and (len(inside) == 1 or len(keys[inside[0]]) > len(keys[inside[1]])):
        return groups[inside[0]], f"'{inside[0]}'"

    outside = [s for s, k in keys.items() if want and want in k]
    if len(outside) == 1:
        return groups[outside[0]], f"'{outside[0]}'"

    tied = sorted(set(inside) | set(outside))
    if not tied:
        return {}, f"작품명과 맞는 파일 무리가 없다 (있는 무리: {', '.join(sorted(groups))})"
    return {}, f"작품명과 맞는 무리가 여럿이다 ({', '.join(tied)}) — 번호로 가릴 수 없다"


def subtitle_gaps(stock: dict[int, Item]) -> list[int]:
    """자막이 통례인 폴더에서 자막만 빠진 회차.

    영상이 멀쩡한데 자막만 없다고 영상을 통째로 다시 받는 것은 대가가 너무 크다.
    그래서 자동으로 다시 받지 않고 어느 회차인지만 알린다. 절반도 자막이 없으면
    원래 자막이 없는 작품이므로 빠진 것이 아니다.

    손상된 회차는 세지 않는다 — 그쪽은 어차피 영상부터 다시 받으므로 자막도 함께
    돌아온다. 여기서 알리면 이미 처리될 일을 두 번 말하는 셈이다.
    """
    sound = {n: it for n, it in stock.items() if it.ok}
    if not sound:
        return []
    withsub = sum(1 for it in sound.values() if it.subs)
    if withsub * 2 < len(sound):
        return []
    return sorted(n for n, it in sound.items() if not it.subs)
