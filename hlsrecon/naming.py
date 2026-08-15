"""이름 규칙 — 화수 표기와 시리즈명의 단일 출처.

화수를 읽어야 하는 곳이 셋이다: 자막 파일명 후보(`name_variants`), 이웃 화수
수집(`episode_names`), 시리즈 폴더 배치(`series_of`). 규칙이 흩어지면 어디선가는
`그렌라간1` 과 `그렌라간01` 을 같은 작품으로 보고 어디선가는 다르게 보게 된다.
그래서 화수를 읽는 정규식과 범위 표기 해석은 이 모듈에만 둔다.
"""

from __future__ import annotations

import re
import unicodedata

# 이름 끝의 화수. 구분자(공백·밑줄·점·하이픈)와 단위(화·회)는 있을 수도 없을 수도 있다.
#
# `(?<!\d)` 가 핵심이다. 이것이 없으면 `Sky.Blue.2003` 이 줄기 `Sky.Blue.2` + 화수
# `003` 으로 갈린다 — 연도를 화수로 오인해 영화 한 편이 엉뚱한 시리즈명을 얻는다.
# 화수 앞이 또 숫자라면 그 숫자열은 통째로 하나의 수이지 화수가 아니다.
EPISODE_RE = re.compile(
    r"^(?P<stem>.*?)(?P<sep>[\s._-]*)(?<!\d)(?P<ep>\d{1,3})(?P<unit>\s*[화회])?$"
)

# 파일 이름에 쓸 수 없거나 쓰면 곤란한 문자.
# '/' 는 경로 구분자, ':' 는 Finder 가 '/' 로 되돌려 보여주고 일부 도구가 드라이브
# 구분자로 읽는다. 나머지는 Windows 예약 문자 — 외장 디스크가 exFAT 이면 걸린다.
_UNSAFE_RE = re.compile(r'[/\\:*?"<>|\x00-\x1f]')


def split_episode(name: str) -> tuple[str, str, str, str] | None:
    """이름을 (줄기, 구분자, 화수, 단위) 로 나눈다. 화수가 없으면 None.

    단위는 `1화`·`500회` 의 끝 글자다. 이름을 다시 조립할 때 그대로 붙여야
    `원피스 1화` 가 `원피스 1` 로 바뀌지 않는다.
    """
    m = EPISODE_RE.match(name)
    if not m:
        return None
    return m.group("stem"), m.group("sep"), m.group("ep"), m.group("unit") or ""


def series_of(name: str) -> str:
    """파일명에서 시리즈명을 얻는다 — 끝의 화수와 그 앞 구분자를 떼어낸다.

    `그렌라간01` → `그렌라간`. 화수가 없으면(영화 등) 이름을 그대로 돌려준다.
    줄기가 비면(파일명이 숫자뿐) 시리즈로 묶을 근거가 없으므로 원본을 쓴다.
    """
    parts = split_episode(name)
    if not parts:
        return name
    stem = parts[0].rstrip(" ._-")
    return stem or name


def episode_of(name: str) -> int | None:
    """파일명 끝의 화수를 정수로. 없으면 None."""
    parts = split_episode(name)
    return int(parts[2]) if parts else None


def name_variants(name: str) -> list[str]:
    """이름 후보. 원본을 먼저, 그다음 화수 표기를 정규화한 형태.

    영상 파일명과 자막 파일명은 같은 작품을 가리키면서도 화수 표기가 어긋나는 일이
    잦다 — `그렌라간1` 과 `그렌라간01`, `그렌라간 01` 과 `그렌라간01`. 어느 쪽이
    맞는지는 서버만 알고 있으므로 후보를 만들어 두고 존재하는 것을 채택한다.
    """
    out = [name]
    parts = split_episode(name)
    if not parts:
        return out
    stem, sep, ep, unit = parts

    cands = []
    if sep:  # 구분자를 뺀 표기
        cands.append(f"{stem}{ep}{unit}")
    # 자릿수 변형은 1~2자리에만 건다. 3자리는 화수가 아니라 연도('… 2026')일 수
    # 있고, 그것을 건드리면 원본과 무관한 이름이 만들어진다.
    if len(ep) == 1:
        cands.append(f"{stem}{sep}{ep.zfill(2)}{unit}")
    elif len(ep) == 2 and ep[0] == "0":
        cands.append(f"{stem}{sep}{ep[1]}{unit}")

    for c in cands:
        if c not in out:
            out.append(c)
    return out


def parse_range(spec: str, what: str) -> tuple[int, int]:
    """`01-27` 또는 `5` 를 (시작, 끝) 로 해석한다.

    what 은 형식이 틀렸을 때 사용자에게 되돌려줄 옵션 이름이다 — 어느 인자가
    잘못됐는지 모르면 고칠 수가 없다.
    """
    lo_s, sep, hi_s = spec.partition("-")
    if not sep:
        hi_s = lo_s
    try:
        lo, hi = int(lo_s), int(hi_s)
    except ValueError:
        raise ValueError(f"{what} 형식이 잘못됐다 (예: 01-27): {spec!r}") from None
    if lo > hi:
        raise ValueError(f"{what} 의 시작이 끝보다 크다: {spec!r}")
    return lo, hi


def episode_names(name: str, spec: str, what: str = "--sub-range") -> list[str]:
    """범위 표기를 이름에 적용해 화수별 이름 목록을 만든다.

    자릿수는 입력 이름의 화수 표기를 따른다 — `그렌라간01` 이면 2자리를 유지한다.
    """
    parts = split_episode(name)
    if not parts:
        raise ValueError(f"이름 끝에서 화수를 찾지 못했다: {name!r} (예: 그렌라간01)")
    stem, sep, ep, unit = parts
    lo, hi = parse_range(spec, what)
    return [f"{stem}{sep}{str(n).zfill(len(ep))}{unit}" for n in range(lo, hi + 1)]


def sanitize(name: str) -> str:
    """폴더·파일 이름으로 쓸 수 있게 다듬는다.

    macOS 파일 시스템은 한글을 자모 분리형(NFD)으로 저장하지만, 웹에서 받은 이름은
    완성형(NFC)이다. 섞이면 눈에 같아 보이는 두 폴더가 생기므로 NFC 로 고정한다.
    끝의 점·공백은 제거한다 — Windows 에서 열 수 없는 이름이 되고, 외장 디스크나
    네트워크 공유로 옮길 때 그대로 문제가 된다.
    """
    s = _UNSAFE_RE.sub("_", unicodedata.normalize("NFC", name)).strip()
    s = s.rstrip(". ")
    return s or "untitled"
