#!/usr/bin/env python3
"""교재 문서의 장·절 번호 표기를 통일한다.

파일 이름은 정렬을 위해 두 자리를 쓰지만(`01-stream-vs-file.md`), 본문의 장 번호와
절 번호는 한 자리로 쓴다 — `제1장`, `## 1.2`, `*그림 1-1*`. 병렬로 집필하면 이
표기가 갈리므로 한 번에 맞춘다.

이미지 경로(`images/01-….svg`)와 코드 앵커는 건드리지 않는다.

사용:
  python3 tools/normalize_docs.py docs           # 미리보기
  python3 tools/normalize_docs.py docs --apply
"""

from __future__ import annotations

import pathlib
import re
import sys


def normalize(text: str) -> tuple[str, list[str]]:
    notes: list[str] = []

    def log(what: str, before: str, after: str) -> None:
        notes.append(f"{what}: {before!r} → {after!r}")

    # 1. 제목줄 — `# 제01장` → `# 제1장`
    def h1(m: re.Match[str]) -> str:
        new = f"# 제{int(m.group(1))}장"
        if new != m.group(0):
            log("제목", m.group(0), new)
        return new

    text = re.sub(r"^# 제(\d{1,2})장", h1, text, flags=re.M)

    # 2. 절 헤딩 — `## 01.2` → `## 1.2` (헤딩 줄에서만)
    def head(m: re.Match[str]) -> str:
        hashes, num, rest = m.group(1), m.group(2), m.group(3)
        parts = [str(int(p)) for p in num.split(".")]
        new = f"{hashes} {'.'.join(parts)}{rest}"
        if new != m.group(0):
            log("절 번호", m.group(0)[:28], new[:28])
        return new

    text = re.sub(r"^(#{2,4}) (\d{1,2}(?:\.\d{1,2})+)( )", head, text, flags=re.M)

    # 3. 그림 캡션 — `*그림 01-1 —` → `*그림 1-1 —`
    def fig(m: re.Match[str]) -> str:
        new = f"*그림 {int(m.group(1))}-{int(m.group(2))} —"
        if new != m.group(0):
            log("그림 번호", m.group(0), new)
        return new

    text = re.sub(r"\*그림 (\d{1,2})-(\d{1,2}) —", fig, text)

    # 4. 본문 상호 참조 — `제01장` → `제1장`, `§01.2` → `§1.2`
    text = re.sub(r"제(\d{2})장", lambda m: f"제{int(m.group(1))}장", text)
    text = re.sub(
        r"§(\d{1,2}(?:\.\d{1,2})+)",
        lambda m: "§" + ".".join(str(int(p)) for p in m.group(1).split(".")),
        text,
    )

    return text, notes


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    root = pathlib.Path(sys.argv[1])
    apply = "--apply" in sys.argv

    touched = 0
    for f in sorted(root.glob("*.md")):
        old = f.read_text(encoding="utf-8")
        new, notes = normalize(old)
        if new == old:
            continue
        touched += 1
        print(f"\n{f.name}  ({len(notes)}건)")
        for n in notes[:6]:
            print(f"    {n}")
        if len(notes) > 6:
            print(f"    … 외 {len(notes) - 6}건")
        if apply:
            f.write_text(new, encoding="utf-8")

    print(f"\n{touched}개 파일" + ("  — 적용됨" if apply else "  — 미리보기 (적용하려면 --apply)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
