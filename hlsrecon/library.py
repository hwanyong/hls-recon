"""보관 구조 — 받은 파일을 시리즈 폴더에 놓고, 흩어진 파일을 되모은다.

한 편씩 받다 보면 회차 파일이 받은 순서대로 한 폴더에 쌓인다. 서로 다른 작품이
섞이면 이름순 정렬로도 갈라지지 않아 재생기가 다음 화를 이어 틀지 못한다.
그래서 저장 위치를 정하는 규칙을 여기 한 곳에 둔다 — 새로 받는 것(`place`)과
이미 흩어진 것(`plan_tidy`)이 같은 기준을 쓴다.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .naming import sanitize, series_of, split_episode

# 시리즈 폴더로 묶을 대상. 자막 등 곁딸린 파일은 영상을 따라 움직인다.
MEDIA_EXTS = frozenset({".mp4", ".mkv", ".ts", ".m4v", ".mov", ".webm", ".avi"})
SIDECAR_EXTS = frozenset({".srt", ".vtt", ".ass", ".ssa", ".smi", ".sub", ".idx", ".json"})


def series_folder(base: Path, series: str) -> Path:
    """시리즈 폴더의 자리. 폴더 이름을 정하는 유일한 지점이다."""
    return base / sanitize(series)


def place(base: Path, name: str, ext: str, series: str = "") -> Path:
    """`base/<시리즈>/<이름><확장자>` 를 만든다 (디렉터리는 만들지 않는다).

    series 를 주면 그것을 폴더 이름으로 쓴다 — 사이트가 알려준 작품명이 파일명에서
    유도한 것보다 정확하다(`천원돌파 그렌라간` vs `그렌라간`). 주지 않으면 파일명
    끝의 화수를 떼어 시리즈를 가른다.
    """
    return series_folder(base, series or series_of(name)) / (sanitize(name) + ext)


@dataclass
class Move:
    src: Path
    dest: Path
    skip: str = ""  # 비어 있지 않으면 옮기지 않는다 — 그 사유


def sidecars(media: Path, files: list[Path]) -> list[Path]:
    """영상과 짝인 곁파일. `영상01.srt`, `영상01.ko.srt` 처럼 이름이 이어진다.

    점까지 포함해 견준다 — 그러지 않으면 `영상01` 의 곁파일을 찾을 때 `영상010`
    의 것까지 끌려온다.
    """
    prefix = media.stem + "."
    return [
        f
        for f in files
        if f != media and f.suffix.lower() in SIDECAR_EXTS and f.name.startswith(prefix)
    ]


def plan_tidy(root: Path) -> list[Move]:
    """폴더 바로 아래 흩어진 회차 파일을 시리즈 폴더로 모으는 계획을 세운다.

    옮기는 것은 **같은 시리즈로 묶이는 회차가 둘 이상**인 영상뿐이다. 화수가 없는
    파일(영화 한 편)이나 혼자뿐인 회차까지 폴더에 넣으면 파일 하나짜리 폴더만
    늘어 오히려 찾기 어려워진다. 하위 폴더는 이미 정리된 것으로 보고 건드리지 않는다.
    """
    files = sorted(p for p in root.iterdir() if p.is_file() and not p.name.startswith("."))
    media = [f for f in files if f.suffix.lower() in MEDIA_EXTS]

    groups: dict[str, list[Path]] = {}
    for f in media:
        if split_episode(f.stem) is None:
            continue  # 화수가 없다 — 시리즈의 한 회차라고 볼 근거가 없다
        groups.setdefault(series_of(f.stem), []).append(f)

    moves: list[Move] = []
    for series, members in sorted(groups.items()):
        if len(members) < 2:
            continue
        folder = root / sanitize(series)
        for m in members:
            for src in [m, *sidecars(m, files)]:
                dest = folder / src.name
                skip = ""
                if dest.exists():
                    skip = "같은 이름이 이미 있다"
                elif folder.exists() and not folder.is_dir():
                    skip = "같은 이름의 파일이 폴더 자리를 차지하고 있다"
                moves.append(Move(src=src, dest=dest, skip=skip))
    return moves


def apply_tidy(moves: list[Move]) -> tuple[int, int]:
    """계획대로 옮긴다. 반환: (옮긴 수, 건너뛴 수).

    건너뛴 항목은 그대로 둔다 — 덮어쓰면 되돌릴 수 없고, 이름이 겹친다는 것은
    같은 회차를 두 번 받았다는 뜻이라 사람이 확인할 일이다.
    """
    done = skipped = 0
    for mv in moves:
        if mv.skip or not mv.src.exists():
            skipped += 1
            continue
        mv.dest.parent.mkdir(parents=True, exist_ok=True)
        mv.src.rename(mv.dest)
        done += 1
    return done, skipped
