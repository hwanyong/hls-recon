#!/usr/bin/env python3
"""교재 도식(SVG) 검사기.

대량으로 만든 SVG 에서 눈으로는 잘 놓치는 결함을 잡는다.

  1. XML 로 파싱되는가
  2. viewBox 가 있고 width/height 를 고정하지 않았는가 (반응형)
  3. 색을 요소에 직접 칠하지 않았는가 (테마 대응이 깨진다)
  4. 쓰인 클래스가 모두 <style> 에 정의돼 있는가
  5. 라이트에서 정의한 클래스가 다크에서도 재정의됐는가
  6. 색상 리터럴에 비ASCII 문자가 섞이지 않았는가
  7. <tspan> 을 쓰는 <text> 에 xml:space="preserve" 가 있는가
  8. rsvg-convert 로 실제 렌더되는가 (있을 때만)
  9. aria-label 이 있는가 (접근성)

사용: python3 tools/check_svg.py docs/images [--quiet]
"""

from __future__ import annotations

import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata

try:  # 외부 엔티티·엔티티 폭탄 방어. 없으면 아래 DTD 거부로 대신한다.
    from defusedxml import ElementTree as ET  # type: ignore
    _DEFUSED = True
except ImportError:
    import xml.etree.ElementTree as ET  # noqa: N817
    _DEFUSED = False

# 이 교재의 도식은 DTD·엔티티를 쓰지 않는다. 그런 선언이 있다면 우리가 만든
# 파일이 아니거나 손을 탄 것이므로, 파싱하기 전에 거부한다 — defusedxml 이
# 없는 환경에서 XXE·billion-laughs 로 들어가는 유일한 경로가 여기다.
DTD_DECL = re.compile(r"<!(?:DOCTYPE|ENTITY)\b", re.I)

# 의미 없는 색 이름은 허용한다 — 마커 등 구조적 용도.
ALLOW_DIRECT_FILL = {"none", "transparent"}

CLASS_USE = re.compile(r'class="([^"]+)"')
STYLE_BLOCK = re.compile(r"<style>(.*?)</style>", re.S)
CLASS_DEF = re.compile(r"\.([A-Za-z][\w-]*)\s*(?:,\s*\.[\w-]+\s*)*\{")
DARK_BLOCK = re.compile(r"@media\s*\(prefers-color-scheme:\s*dark\)\s*\{(.*)\}", re.S)
DIRECT_PAINT = re.compile(r'\b(?:fill|stroke)="(#[0-9A-Fa-f]{3,8}|[a-z]+)"')
COLOR_LITERAL = re.compile(r"#[^\s;\"'})]{2,10}")
TEXT_WITH_TSPAN = re.compile(r"<text\b([^>]*)>(?=[^<]*<tspan)")


def defined_classes(style: str) -> set[str]:
    return set(CLASS_DEF.findall(style))


def check(path: pathlib.Path, renderer: str | None) -> list[str]:
    raw = path.read_text(encoding="utf-8")
    errs: list[str] = []

    # 1. XML 파싱 — DTD/엔티티 선언은 파싱 전에 거부한다
    if (m := DTD_DECL.search(raw)):
        return [f"DTD·엔티티 선언이 있다 ({m.group(0)}) — 이 교재의 도식은 쓰지 않는다"]
    try:
        ET.fromstring(raw)
    except Exception as e:  # noqa: BLE001 — 파서 구현에 따라 예외형이 다르다
        return [f"XML 파싱 실패: {type(e).__name__}: {e}"]

    # 2. viewBox / 고정 크기
    head = raw[: raw.find(">") + 1]
    if "viewBox" not in head:
        errs.append("<svg> 에 viewBox 가 없다")
    if re.search(r'\bwidth="[\d.]+(px)?"', head) or re.search(r'\bheight="[\d.]+(px)?"', head):
        errs.append("<svg> 에 width/height 가 고정돼 있다 — viewBox 만 쓸 것")

    # 9. 접근성
    if "aria-label" not in head:
        errs.append("<svg> 에 aria-label 이 없다")

    style_m = STYLE_BLOCK.search(raw)
    if not style_m:
        errs.append("<style> 블록이 없다 — 색은 클래스로만 칠할 것")
        return errs
    style = style_m.group(1)

    # 3. 직접 칠하기
    for m in DIRECT_PAINT.finditer(raw):
        if m.group(1) not in ALLOW_DIRECT_FILL:
            line = raw[: m.start()].count("\n") + 1
            errs.append(f"{line}행: 색을 직접 칠했다 ({m.group(0)}) — 클래스를 쓸 것")

    # 4. 정의되지 않은 클래스
    defined = defined_classes(style)
    used: set[str] = set()
    for m in CLASS_USE.finditer(raw):
        used |= set(m.group(1).split())
    missing = sorted(used - defined)
    if missing:
        errs.append(f"<style> 에 없는 클래스: {', '.join(missing)}")

    # 5. 다크 대응
    dark_m = DARK_BLOCK.search(style)
    if not dark_m:
        errs.append("@media (prefers-color-scheme: dark) 블록이 없다")
    else:
        light = defined_classes(style[: dark_m.start()])
        dark = defined_classes(dark_m.group(1))
        # 실제로 쓰인 클래스만 따진다
        gap = sorted((light & used) - dark)
        if gap:
            errs.append(f"다크에서 재정의되지 않은 클래스: {', '.join(gap)}")

    # 6. 비ASCII 색상 리터럴
    for m in COLOR_LITERAL.finditer(raw):
        for ch in m.group(0):
            if not ch.isascii():
                errs.append(
                    f"색상 리터럴에 비ASCII 문자: {m.group(0)!r} "
                    f"({ch!r} U+{ord(ch):04X} {unicodedata.name(ch, '?')})"
                )
                break

    # 7. tspan + xml:space
    for m in TEXT_WITH_TSPAN.finditer(raw):
        if "xml:space" not in m.group(1):
            line = raw[: m.start()].count("\n") + 1
            errs.append(f'{line}행: <tspan> 을 쓰는 <text> 에 xml:space="preserve" 가 없다')

    # 8. 실제 렌더
    if renderer:
        with tempfile.NamedTemporaryFile(suffix=".png") as tmp:
            proc = subprocess.run(
                [renderer, "-w", "1000", str(path), "-o", tmp.name],
                capture_output=True, text=True,
            )
            if proc.returncode != 0:
                errs.append(f"렌더 실패: {proc.stderr.strip()[:160]}")

    return errs


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    root = pathlib.Path(sys.argv[1])
    quiet = "--quiet" in sys.argv
    renderer = shutil.which("rsvg-convert")

    files = sorted(root.glob("*.svg"))
    if not files:
        print(f"SVG 가 없다: {root}")
        return 1

    bad = 0
    for f in files:
        errs = check(f, renderer)
        if errs:
            bad += 1
            print(f"\n✗ {f.name}")
            for e in errs:
                print(f"    {e}")
        elif not quiet:
            print(f"✓ {f.name}")

    print(f"\n검사 {len(files)}개 / 결함 {bad}개"
          + ("" if renderer else "  (rsvg-convert 없음 — 렌더 검사 생략)"))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
