#!/usr/bin/env python3
"""마크다운 안의 ASCII 도식 블록을 SVG 참조로 바꾼다.

이 교재는 ANSI·ASCII 아트 도식을 쓰지 않는다. 명령·출력·코드 인용 블록은
그대로 두고, **괘선과 화살표로 그린 그림 블록만** 골라 이미지 참조로 교체한다.

  --list        교체 대상 블록을 번호와 함께 보여준다 (바꾸지 않는다)
  --map F:N=SVG|캡션   F 파일의 N번째 도식 블록을 SVG 로 교체

사용:
  python3 tools/swap_ascii_diagrams.py docs --list
  python3 tools/swap_ascii_diagrams.py docs \
      --map 14-segment-masquerading.md:1=14-three-names.svg|세 층위의 이름
"""

from __future__ import annotations

import pathlib
import re
import sys

# 괘선·화살표·블록문자. 이것이 2줄 이상 나오면 그림으로 본다.
ART = set("─│┌┐└┘├┤┬┴┼━┃╔╗╚╝║═╭╮╯╰↓↑←→⟶▲▼◀▶")
FENCE = re.compile(r"^```[a-zA-Z0-9]*\s*$")


def blocks(text: str):
    """(시작줄, 끝줄, 본문) 목록. 언어 지정 없는 펜스만 후보로 본다."""
    lines = text.split("\n")
    out = []
    i = 0
    while i < len(lines):
        m = FENCE.match(lines[i])
        if not m:
            i += 1
            continue
        lang = lines[i][3:].strip()
        j = i + 1
        while j < len(lines) and not lines[j].startswith("```"):
            j += 1
        if j >= len(lines):
            break
        body = lines[i + 1 : j]
        if not lang:
            art_lines = sum(1 for ln in body if any(c in ART for c in ln))
            if art_lines >= 2:
                out.append((i, j, body))
        i = j + 1
    return out


def show(root: pathlib.Path) -> None:
    for f in sorted(root.glob("*.md")):
        bs = blocks(f.read_text(encoding="utf-8"))
        if not bs:
            continue
        print(f"\n{f.name}")
        for n, (s, e, body) in enumerate(bs, 1):
            head = next((ln.strip() for ln in body if ln.strip()), "")
            print(f"  [{n}] {s + 1}~{e + 1}행 ({len(body)}줄)  {head[:56]}")


def swap(root: pathlib.Path, specs: list[str]) -> int:
    # 파일별로 모아 뒤에서부터 치환한다 — 앞을 먼저 바꾸면 줄 번호가 밀린다.
    by_file: dict[str, list[tuple[int, str, str]]] = {}
    for spec in specs:
        target, _, rest = spec.partition("=")
        fname, _, num = target.partition(":")
        svg, _, caption = rest.partition("|")
        by_file.setdefault(fname, []).append((int(num), svg, caption))

    changed = 0
    for fname, items in by_file.items():
        path = root / fname
        text = path.read_text(encoding="utf-8")
        lines = text.split("\n")
        bs = blocks(text)
        for num, svg, caption in sorted(items, key=lambda x: -x[0]):
            if num > len(bs):
                print(f"  ! {fname}: {num}번 블록이 없다 (총 {len(bs)}개)")
                continue
            s, e, _ = bs[num - 1]
            fig = f"{fname.split('-')[0]}-{num}"
            repl = [f"![{caption}](images/{svg})", "", f"*그림 {fig} — {caption}*"]
            lines[s : e + 1] = repl
            changed += 1
            print(f"  ✓ {fname} [{num}] → {svg}")
        path.write_text("\n".join(lines), encoding="utf-8")
    return changed


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    root = pathlib.Path(sys.argv[1])
    if "--list" in sys.argv:
        show(root)
        return 0
    specs = [sys.argv[i + 1] for i, a in enumerate(sys.argv) if a == "--map"]
    if not specs:
        print("--map 이 필요하다")
        return 2
    n = swap(root, specs)
    print(f"\n{n}개 블록 교체")
    return 0


if __name__ == "__main__":
    sys.exit(main())
