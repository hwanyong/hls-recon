#!/usr/bin/env python3
"""교재 문서 검사기.

39개 장 규모에서 사람 눈으로는 반드시 새는 결함을 기계적으로 잡는다.

  1. 코드 앵커  `fetch.py:36-54` 가 실제 파일·줄 범위를 가리키는가.
                뒤에 붙은 식별자(`gap_scan`)가 그 범위 안이나 그것을 감싸는
                정의에 실제로 있는가 — 코드가 밀려 다른 함수를 가리키게 된
                앵커는 범위 검사만으로는 잡히지 않는다
  2. 이미지     참조한 SVG 가 존재하는가 / 만들어 놓고 안 쓰는 SVG 는 없는가
  3. 그림 캡션  참조마다 캡션이 붙어 있는가, 번호가 순서대로인가
  4. 상호 참조  "제N장" 이 실제 존재하는 장인가
  5. 도식 금지  ASCII·ANSI 아트 블록이 남아 있지 않은가
  6. 표         행마다 열 수가 같은가
  7. 강조       ** 가 짝이 맞는가
  8. 문자       깨진 문자·반복 조사 등 기계적으로 잡히는 오류
  9. 구조       제N장 파일에 N.0 과 요약 절이 있는가

사용: python3 tools/check_docs.py docs [--quiet]
"""

from __future__ import annotations

import pathlib
import re
import sys
import unicodedata

ROOT = pathlib.Path(__file__).resolve().parent.parent

# `fetch.py:36-54` · `tests/run.sh:129` · `README.md:15-34`
ANCHOR = re.compile(r"`([A-Za-z0-9_./-]+\.(?:py|sh|md|toml)):(\d+)(?:-(\d+))?`")
# 앵커 바로 뒤에 오는 백틱 식별자 — `probe.py:191-233` `gap_scan`
SYMBOL_AFTER = re.compile(r"\s*(?:의\s*)?`([A-Za-z_][A-Za-z0-9_.]*)`")
IMG = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
# 캡션은 여러 줄에 걸칠 수 있으므로 시작만 본다.
CAPTION = re.compile(r"^\*그림 ([\w-]+)-(\d+) — ", re.M)
CHAPTER_REF = re.compile(r"제(\d{1,2})장")
FENCE = re.compile(r"^```")
ART = set("─│┌┐└┘├┤┬┴┼━┃╔╗╚╝║═╭╮╯╰")
ARROWS = set("↓↑←→⟶▲▼◀▶")

# 코드가 있을 수 있는 곳
SEARCH_DIRS = ["", "hlsrecon/", "tests/", "docs/", "tools/"]


def resolve(name: str) -> pathlib.Path | None:
    for d in SEARCH_DIRS:
        p = ROOT / (d + name)
        if p.is_file():
            return p
    p = ROOT / name
    return p if p.is_file() else None


def strip_fences(text: str) -> str:
    """코드블록 안을 지운 사본. 표·강조 검사가 코드에 걸리지 않게 한다."""
    out, inside = [], False
    for ln in text.split("\n"):
        if FENCE.match(ln):
            inside = not inside
            out.append("")
            continue
        out.append("" if inside else ln)
    return "\n".join(out)


def art_blocks(text: str) -> list[int]:
    """ASCII 아트로 보이는 언어 미지정 코드블록의 시작 줄."""
    lines = text.split("\n")
    hits, i = [], 0
    while i < len(lines):
        if not FENCE.match(lines[i]):
            i += 1
            continue
        lang = lines[i][3:].strip()
        j = i + 1
        while j < len(lines) and not lines[j].startswith("```"):
            j += 1
        if not lang:
            body = lines[i + 1 : j]
            n = sum(1 for ln in body if any(c in ART for c in ln))
            if n >= 2:
                hits.append(i + 1)
        i = j + 1
    return hits


def enclosing(lines: list[str], lineno: int) -> set[str]:
    """`lineno`(1-기준)를 감싸는 def·class 이름들.

    본문은 함수 안의 한 줄을 짚으면서 그 함수 이름을 붙이는 일이 흔하다
    (``library.py:33`` `place`). 그것을 오류로 보면 안 되므로 감싸는 정의를
    거슬러 올라가 모은다.
    """
    names: set[str] = set()
    depth = None
    for i in range(min(lineno, len(lines)) - 1, -1, -1):
        ln = lines[i]
        if not ln.strip():
            continue
        ind = len(ln) - len(ln.lstrip())
        if depth is not None and ind >= depth:
            continue
        m = re.match(r"\s*(?:async\s+)?(?:def|class)\s+([A-Za-z_]\w*)", ln)
        if m:
            names.add(m.group(1))
            depth = ind
            if ind == 0:
                break
    return names


def check(path: pathlib.Path, all_chapters: set[str], used_svgs: set[str]) -> list[str]:
    raw = path.read_text(encoding="utf-8")
    body = strip_fences(raw)
    errs: list[str] = []
    line_of = lambda pos: raw[:pos].count("\n") + 1  # noqa: E731

    # 1. 코드 앵커
    for m in ANCHOR.finditer(raw):
        name, a, b = m.group(1), int(m.group(2)), m.group(3)
        target = resolve(name)
        if target is None:
            errs.append(f"{line_of(m.start())}행: 앵커 대상 파일 없음 — {name}")
            continue
        total = len(target.read_text(encoding="utf-8", errors="replace").split("\n"))
        hi = int(b) if b else a
        if a < 1 or hi > total:
            errs.append(
                f"{line_of(m.start())}행: 앵커 범위가 파일을 벗어남 — "
                f"{m.group(0)} (실제 {total}행)"
            )
        elif b and int(b) < a:
            errs.append(f"{line_of(m.start())}행: 앵커 범위 역순 — {m.group(0)}")
        else:
            # 범위가 파일 안에 있는 것만으로는 부족하다. 앵커 바로 뒤에 백틱으로
            # 붙은 식별자(`probe.py:191-233` `gap_scan`)는 그 범위 안에 실제로
            # 있어야 한다. 코드가 밀리면 범위는 여전히 유효한데 가리키는 곳이
            # 달라지므로, 이 대조가 없으면 앵커 오류가 조용히 남는다.
            sym = SYMBOL_AFTER.match(raw, m.end())
            if sym and name.endswith(".py"):
                name_ = sym.group(1)
                seg = target.read_text(encoding="utf-8", errors="replace").split("\n")
                if not (
                    any(name_ in ln for ln in seg[a - 1 : hi])
                    or name_ in enclosing(seg, a)
                ):
                    errs.append(
                        f"{line_of(m.start())}행: 앵커가 가리키는 범위에도 "
                        f"그것을 감싸는 정의에도 `{name_}` 이(가) 없다 — {m.group(0)}"
                    )

    # 2. 이미지
    for m in IMG.finditer(raw):
        alt, src = m.group(1), m.group(2)
        if not alt.strip():
            errs.append(f"{line_of(m.start())}행: 이미지 대체 텍스트가 비었다 — {src}")
        p = (path.parent / src).resolve()
        if not p.is_file():
            errs.append(f"{line_of(m.start())}행: 이미지 파일 없음 — {src}")
        else:
            used_svgs.add(p.name)

    # 3. 그림 캡션 — 이미지 수와 캡션 수가 같아야 한다
    imgs = len(IMG.findall(raw))
    caps = CAPTION.findall(raw)
    if imgs != len(caps):
        errs.append(f"이미지 {imgs}개인데 그림 캡션은 {len(caps)}개 — 짝이 맞지 않는다")
    nums = [int(n) for _, n in caps]
    if nums != sorted(nums) or len(set(nums)) != len(nums):
        errs.append(f"그림 번호가 순서대로가 아니거나 중복 — {nums}")

    # 4. 상호 참조
    for m in CHAPTER_REF.finditer(body):
        n = m.group(1).zfill(2)
        if n not in all_chapters:
            errs.append(f"{line_of(m.start())}행: 없는 장을 참조 — 제{m.group(1)}장")

    # 5. ASCII 아트
    for ln in art_blocks(raw):
        errs.append(f"{ln}행: ASCII 도식 블록이 남아 있다 — SVG 로 교체할 것")

    # 6. 표 열 수 — 셀 안의 `\|` 는 이스케이프된 파이프이므로 열 구분자가 아니다.
    rows: list[tuple[int, int]] = []
    for i, ln in enumerate(body.split("\n"), 1):
        s = ln.strip()
        if s.startswith("|") and s.endswith("|"):
            rows.append((i, s.replace("\\|", "").count("|")))
        elif rows:
            widths = {w for _, w in rows}
            if len(widths) > 1:
                errs.append(f"{rows[0][0]}행: 표의 열 수가 행마다 다르다 — {sorted(widths)}")
            rows = []

    # 7. 강조 짝 — 마크다운에서 ** 는 줄바꿈을 넘나드는 것이 정상이므로
    #    줄이 아니라 문단(빈 줄로 구분) 단위로 센다.
    #    인라인 코드는 제외한다 — 제12장은 편집된 자격증명 `***` 를 코드 스팬으로
    #    인용하는데, 그 안의 `**` 는 강조가 아니라 리터럴이다.
    pos = 0
    for para in body.split("\n\n"):
        if re.sub(r"`[^`]*`", "``", para).count("**") % 2:
            head = next((ln.strip() for ln in para.split("\n") if ln.strip()), "")
            errs.append(
                f"{body[:pos].count(chr(10)) + 1}행 문단: ** 강조가 닫히지 않았다 "
                f"— {head[:50]}"
            )
        pos += len(para) + 2

    # 8. 문자 위생 — 인라인 코드(`…`) 안은 인용된 리터럴이므로 제외한다.
    #    제33장은 폭 0 공백을 코드 스팬으로 **인용해서** 설명한다. 그것까지 결함으로
    #    보면 그 설명 자체를 쓸 수 없다. 산문에 섞여 든 것만 잡는다.
    for i, ln in enumerate(re.sub(r"`[^`]*`", "``", body).split("\n"), 1):
        for ch in ln:
            if ch in ("\t", " ", "​", "﻿"):
                errs.append(
                    f"{i}행: 보이지 않는 문자 — U+{ord(ch):04X} "
                    f"{unicodedata.name(ch, '?')}"
                )
                break
    # 같은 줄 안에서 공백 하나를 사이에 둔 반복만 본다. 개행을 넘기면
    # 멀리 떨어진 같은 낱말이 걸려 오탐이 쏟아진다.
    #    16진 덤프(`00 00`, `0001 0001`)는 반복이 정상이므로 제외한다.
    for i, ln in enumerate(re.sub(r"`[^`]*`", "``", body).split("\n"), 1):
        for m in re.finditer(r"(?<![\w가-힣])([\w가-힣]{2,}) \1(?![\w가-힣])", ln):
            if re.fullmatch(r"[0-9a-fA-F]+", m.group(1)):
                continue
            errs.append(f"{i}행: 낱말 반복 — '{m.group(0)}'")

    # 9. 구조 (제N장 파일만) — 00 은 커리큘럼 설계 문서라 장 형식을 따르지 않는다.
    mnum = re.match(r"^(0[1-9]|[1-9]\d)-", path.name)
    if mnum:
        n = int(mnum.group(1))
        if not re.search(rf"^## {n}\.0 ", raw, re.M):
            errs.append(f"'## {n}.0 이 장에서 답할 것' 절이 없다")
        if not re.search(rf"^## {n}\.\d+ 요약", raw, re.M):
            errs.append(f"'## {n}.N 요약' 절이 없다")
        if not re.search(rf"^## {n}\.\d+ 한계", raw, re.M):
            errs.append(f"'## {n}.N 한계와 미해결' 절이 없다")
        if not raw.startswith(f"# 제{n}장"):
            errs.append(f"첫 줄이 '# 제{n}장 …' 이 아니다")

    return errs


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    docs = pathlib.Path(sys.argv[1])
    quiet = "--quiet" in sys.argv

    files = sorted(docs.glob("*.md"))
    chapters = {m.group(1) for f in files if (m := re.match(r"^(\d{2})-", f.name))}
    used: set[str] = set()

    total = 0
    for f in files:
        errs = check(f, chapters, used)
        total += len(errs)
        if errs:
            print(f"\n✗ {f.name}  ({len(errs)}건)")
            for e in errs[:25]:
                print(f"    {e}")
            if len(errs) > 25:
                print(f"    … 외 {len(errs) - 25}건")
        elif not quiet:
            print(f"✓ {f.name}")

    # 안 쓰는 도식
    have = {p.name for p in (docs / "images").glob("*.svg")}
    orphan = sorted(have - used)
    if orphan:
        print(f"\n! 참조되지 않는 도식 {len(orphan)}개: {', '.join(orphan)}")

    print(f"\n문서 {len(files)}개 / 장 {len(chapters)}개 / 결함 {total}건")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
