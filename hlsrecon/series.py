"""시리즈 페이지 해석 — 회차 목록 발견과 회차별 재생 소스 해석.

한 편짜리 다운로드는 재생 소스(m3u8)를 사람이 개발자도구에서 떠와 넘기면 된다.
시리즈 전체는 그 방식이 성립하지 않는다. 회차마다 CDN 경로가 불투명 해시라
1화 주소에서 2화를 유도할 수 없고, 발급된 링크에는 만료 시각이 박혀 있다.

    …/cdn/hls/<회차별 해시>/master.m3u8?md5=<서명>&expires=<unix>

그래서 27화를 미리 모아두고 순서대로 받는 방식은 뒤쪽 회차에서 반드시 깨진다.
이 모듈은 **회차 목록만 먼저 확보하고, 재생 소스는 그 회차를 받기 직전에**
해석한다(late resolution). `resolve()` 가 매번 새 링크를 받아오는 이유다.

실측한 경로는 다음 넷이며, 사이트가 구조를 바꾸면 여기만 고치면 된다.

    /c/<제목>              시리즈 페이지 — li.list-item 에 회차 번호와 링크
    /e/<제목> N화          회차 페이지  — <iframe> 이 플레이어를 가리킨다
    <플레이어>/video/<해시> 플레이어    — packed JS 안에 정식 파일 이름
    <플레이어>/player/index.php?data=<해시>&do=getVideo  → 서명된 m3u8
"""

from __future__ import annotations

import html
import json
import re
import string
from dataclasses import dataclass
from urllib.parse import unquote, urljoin, urlparse

from . import playlist
from .fetch import Fetcher, normalize_url
from .naming import sanitize

# ─────────────────────────────────────────────────────────────────────────────
# 시리즈 페이지 — 회차 목록
# ─────────────────────────────────────────────────────────────────────────────

# 회차 한 줄. 번호(.wr-num)와 제목 링크(a.item-subject)가 같은 li 안에 들어 있다.
_ITEM_RE = re.compile(r'<li\b[^>]*class="[^"]*\blist-item\b[^"]*"[^>]*>(.*?)</li>', re.S | re.I)
# 목록 머리글에도 같은 class 가 붙어 있으므로(내용은 '에피소드') 숫자만 받는다.
_NUM_RE = re.compile(r'class="[^"]*\bwr-num\b[^"]*"[^>]*>\s*(\d+)\s*<', re.I)
# href 와 class 의 순서는 보장되지 않는다 — 태그 속성을 통째로 잡고 안에서 찾는다.
_SUBJECT_RE = re.compile(
    r'<a\b(?P<attrs>[^>]*\bclass="[^"]*\bitem-subject\b[^"]*"[^>]*)>(?P<text>.*?)</a>',
    re.S | re.I,
)
_HREF_RE = re.compile(r'\bhref="([^"]*)"', re.I)
# 회차 페이지에서 시리즈 페이지로 돌아가는 빵부스러기 링크.
_BREADCRUMB_RE = re.compile(
    r'<a\b(?P<attrs>[^>]*\bclass="[^"]*\bbreadcrumb-title\b[^"]*"[^>]*)>', re.I
)
_TAG_RE = re.compile(r"<[^>]+>")
# 제목 끝의 회차 표기 — `… 3화`, `… 27화(完)`.
_EP_SUFFIX_RE = re.compile(r"\s*\d{1,4}\s*화\s*(?:\(.*?\))?\s*$")

SERIES_PATH = "/c/"
EPISODE_PATH = "/e/"


@dataclass
class Episode:
    """시리즈 목록에 실린 회차 하나. 아직 재생 소스는 모른다."""

    number: int
    title: str
    page_url: str


@dataclass
class Series:
    title: str
    url: str
    episodes: list[Episode]

    @property
    def width(self) -> int:
        """화수 자릿수 — 27화까지면 2자리로 맞춰 파일이 이름순으로 정렬되게 한다."""
        return max(2, len(str(max((e.number for e in self.episodes), default=0))))


@dataclass
class Play:
    """회차 하나의 재생 정보. 서명 링크는 만료되므로 받기 직전에 만든다."""

    playlist_url: str
    name: str  # 확장자를 뗀 파일 이름 — 사이트가 정한 정식 이름
    referer: str


def _text(fragment: str) -> str:
    """태그를 걷어내고 엔티티를 푼 뒤 공백을 하나로 줄인다."""
    return re.sub(r"\s+", " ", html.unescape(_TAG_RE.sub("", fragment))).strip()


def _origin(url: str) -> str:
    return "{u.scheme}://{u.netloc}".format(u=urlparse(url))


def _from(referer: str) -> dict[str, str]:
    """이 요청에만 얹을 Referer/Origin.

    사슬의 각 단계는 서로 다른 곳에서 열린다 — 회차 페이지는 사이트 안에서,
    플레이어는 회차 페이지 안의 iframe 으로, 재생 소스는 플레이어 안의 XHR 로.
    브라우저가 보내는 것과 같은 값을 보내야 한다. 하나라도 비면 서버가 404 로
    돌려보내는데, 없는 페이지처럼 보여서 원인을 짚기 어렵다.
    """
    # 헤더 값은 ASCII 로 쓰인다. 한글이 든 회차 주소를 그대로 Referer 에 넣으면
    # 요청이 만들어지는 순간 죽으므로, 주소와 같은 규칙으로 인코딩해서 싣는다.
    return {"Referer": normalize_url(referer), "Origin": _origin(referer)}


def looks_like_series(url: str) -> bool:
    return SERIES_PATH in urlparse(url).path


def looks_like_episode(url: str) -> bool:
    return EPISODE_PATH in urlparse(url).path


def is_page(url: str) -> bool:
    """플레이리스트가 아니라 사이트의 시리즈/회차 페이지인가.

    확장자가 먼저다 — 플레이리스트 주소가 어쩌다 `/c/` 를 지나갈 수는 있어도,
    `.m3u8` 로 끝나는 주소는 언제나 플레이리스트다.
    """
    if playlist.is_playlist_uri(url):
        return False
    return looks_like_series(url) or looks_like_episode(url)


def _series_url_of_episode(page: str, url: str) -> str:
    """회차 페이지에서 시리즈 페이지 주소를 얻는다.

    빵부스러기 링크의 제목에는 끝 공백이 붙어 있는 경우가 있다. 그 주소도 200 을
    돌려주지만 **목록이 비어서** 온다 — 오류로 보이지 않는 실패다. 그래서 받은
    주소를 그대로 쓰지 않고 제목 부분의 공백을 떼어 정규화한다.
    """
    m = _BREADCRUMB_RE.search(page)
    if not m:
        raise ValueError(
            f"회차 페이지에서 시리즈 목록 링크(a.breadcrumb-title)를 찾지 못했다: {url}"
        )
    href = _HREF_RE.search(m.group("attrs"))
    if not href:
        raise ValueError(f"시리즈 목록 링크에 href 가 없다: {url}")
    absolute = urljoin(url, href.group(1))
    u = urlparse(absolute)
    return u._replace(path=unquote(u.path).rstrip()).geturl()


def discover(url: str, fetcher: Fetcher) -> Series:
    """시리즈(또는 회차) 페이지 주소로 회차 목록을 만든다.

    회차 주소를 받으면 먼저 그 시리즈의 목록 페이지로 올라간다 — 사용자가 1화
    주소만 들고 있는 경우가 흔하기 때문이다.
    """
    page = fetcher.get_text(url, _from(_origin(url) + "/"))
    if looks_like_episode(url) and not looks_like_series(url):
        url = _series_url_of_episode(page, url)
        page = fetcher.get_text(url, _from(_origin(url) + "/"))

    episodes: list[Episode] = []
    seen: set[str] = set()
    for block in _ITEM_RE.findall(page):
        link = _SUBJECT_RE.search(block)
        if not link:
            continue
        href = _HREF_RE.search(link.group("attrs"))
        if not href:
            continue
        page_url = urljoin(url, href.group(1))
        if page_url in seen:
            continue
        seen.add(page_url)
        title = _text(link.group("text"))
        num = _NUM_RE.search(block)
        if num:
            number = int(num.group(1))
        else:
            # 번호 칸이 없으면 제목 끝의 `N화` 를 쓴다. 그것도 없으면 나온 순서.
            from_title = re.search(r"(\d{1,4})\s*화", title)
            number = int(from_title.group(1)) if from_title else len(episodes) + 1
        episodes.append(Episode(number=number, title=title, page_url=page_url))

    if not episodes:
        raise ValueError(
            f"회차 목록을 찾지 못했다: {url}\n"
            "  시리즈 페이지 주소가 맞는지 확인할 것 (예: https://…/c/작품제목).\n"
            "  주소 끝에 공백이 붙으면 빈 목록이 200 으로 돌아온다."
        )

    # 목록은 최신 화가 위에 오도록 역순으로 실린다. 받는 순서는 1화부터가 자연스럽다.
    episodes.sort(key=lambda e: e.number)
    series_title = sanitize(_EP_SUFFIX_RE.sub("", _series_title(page, url)))
    return Series(title=series_title, url=url, episodes=episodes)


_TITLE_TAG_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.S | re.I)


def _series_title(page: str, url: str) -> str:
    """시리즈 제목. 주소의 마지막 조각이 곧 제목이고, 없으면 <title> 로 물러선다."""
    tail = unquote(urlparse(url).path).rstrip("/").rsplit("/", 1)[-1].strip()
    if tail:
        return tail
    m = _TITLE_TAG_RE.search(page)
    # `<title>` 은 `작품 1화 - 사이트이름` 꼴이다 — 사이트 이름은 제목이 아니다.
    return _text(m.group(1)).split(" - ")[0] if m else "series"


# ─────────────────────────────────────────────────────────────────────────────
# 회차 → 재생 소스
# ─────────────────────────────────────────────────────────────────────────────

_IFRAME_RE = re.compile(r'<iframe\b[^>]*\bsrc="([^"]+)"', re.I)
# 플레이어 주소는 `<호스트>/video/<해시>` 꼴이다. 광고·소셜 iframe 과 구분하는 근거.
_PLAYER_RE = re.compile(r"^https?://[^/]+/video/(?P<hash>[0-9A-Za-z]{8,})/?$")
_PACKED_RE = re.compile(r"}\('(?P<payload>.*?)',(?P<base>\d+),\d+,'(?P<words>.*?)'\.split\('\|'\)", re.S)
_JS_TITLE_RE = re.compile(r'"title"\s*:\s*"(?P<title>[^"]*)"')

_ALPHABET = string.digits + string.ascii_lowercase + string.ascii_uppercase


def unpack(text: str) -> str:
    """packed JS(`eval(function(p,a,c,k,e,d){…})`)를 원래 소스로 되돌린다.

    플레이어 설정은 이 압축 안에 들어 있다. 압축은 자주 쓰이는 낱말을 사전에 모으고
    본문에서는 사전 번호를 진법 표기로 참조하는 방식이라, 번호를 낱말로 되돌리면
    원본이 나온다. 진법이 36 을 넘으므로(대개 62) 파이썬 `int(x, base)` 는 쓸 수
    없고 자릿수 표를 직접 둔다.

    되돌리지 못하면 빈 문자열을 준다 — 실행하지 않고 읽기만 한다.
    """
    m = _PACKED_RE.search(text)
    if not m:
        return ""
    payload, base = m.group("payload"), int(m.group("base"))
    words = m.group("words").split("|")

    def decode(token: str) -> int | None:
        n = 0
        for ch in token:
            i = _ALPHABET.find(ch)
            if i < 0 or i >= base:
                return None
            n = n * base + i
        return n

    def swap(mo: re.Match[str]) -> str:
        i = decode(mo.group(0))
        return words[i] if i is not None and i < len(words) and words[i] else mo.group(0)

    # 사전 참조는 ASCII 낱말이다. 파이썬 기본 \w 는 한글도 포함하므로 ASCII 로 묶는다.
    out = re.sub(r"\b\w+\b", swap, payload, flags=re.ASCII)
    return out.replace("\\/", "/")


def _player_url(page: str, url: str) -> str:
    for src in _IFRAME_RE.findall(page):
        absolute = urljoin(url, src)
        if _PLAYER_RE.match(absolute):
            return absolute
    raise ValueError(f"회차 페이지에서 플레이어 iframe 을 찾지 못했다: {url}")


def resolve(episode: Episode, fetcher: Fetcher, fallback_width: int = 2) -> Play:
    """회차 하나의 재생 소스를 지금 시점에 해석한다.

    링크에 만료 시각이 박혀 있으므로 미리 모아두지 않는다 — 받기 직전에 부른다.
    """
    page_url = episode.page_url
    page = fetcher.get_text(page_url, _from(_origin(page_url) + "/"))
    player = _player_url(page, episode.page_url)
    origin = _origin(player)
    video_hash = _PLAYER_RE.match(player).group("hash")

    # 플레이어 HTML 은 설정만 들고 있다. 실제 재생 주소는 아래 XHR 이 발급한다.
    settings = unpack(fetcher.get_text(player, _from(page_url)))

    res = fetcher.post(
        f"{origin}/player/index.php?data={video_hash}&do=getVideo",
        {"hash": video_hash, "r": episode.page_url},
        _from(player),
    )
    if not res.ok:
        raise ValueError(f"재생 소스 요청 실패: {episode.title}\n  {res.error}")
    body = res.body.decode("utf-8", errors="replace")
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        # 실패하면 JSON 대신 사람이 읽을 문구를 그대로 돌려준다 — 그게 곧 거절 사유다.
        raise ValueError(
            f"재생 소스를 얻지 못했다: {episode.title}\n  서버 응답: {body.strip()[:200]}"
        ) from None

    link = data.get("securedLink") or data.get("videoSource") or ""
    if not link:
        raise ValueError(f"응답에 재생 주소가 없다: {episode.title}\n  {body[:200]}")

    return Play(playlist_url=link, name=_name_of(settings, episode, fallback_width), referer=origin + "/")


def _name_of(settings: str, episode: Episode, width: int) -> str:
    """저장할 파일 이름(확장자 없음).

    플레이어 설정의 `title` 이 사이트가 정한 정식 이름이다(`그렌라간01.mkv`).
    자막 파일도 같은 이름으로 놓이므로 이 이름을 따르는 편이 짝이 맞는다.
    설정을 읽지 못했을 때만 목록의 제목으로 물러선다.
    """
    m = _JS_TITLE_RE.search(settings)
    if m and m.group("title").strip():
        stem = re.sub(r"\.(mkv|mp4|ts|m4v|avi|webm|mov)$", "", m.group("title").strip(), flags=re.I)
        if stem:
            return sanitize(stem)
    base = _EP_SUFFIX_RE.sub("", episode.title).strip() or "episode"
    return sanitize(f"{base} {episode.number:0{width}d}")
