# 도식 제작 규약

이 교재의 모든 도식은 **SVG 파일**로 만들어 마크다운에서 참조한다.
ASCII·ANSI 아트 도식은 쓰지 않는다.

```markdown
![세 층위의 이름](images/14-three-names.svg)
```

## 파일 이름

`<장번호>-<슬러그>.svg` — 예: `14-three-names.svg`, `15-defense-layers.svg`
부록·조사 문서는 `a-`, `r01-` 접두어를 쓴다.

## 캔버스

- `viewBox` 필수, `width`/`height` 속성은 쓰지 않는다 — 마크다운에서 폭에 맞춰 늘어난다.
- 기본 폭 `880`. 높이는 내용에 맞춘다.
- 여백은 상하좌우 최소 `20`.

## 테마 대응

라이트·다크 양쪽에서 읽혀야 한다. SVG 안에 `<style>` 을 넣고 클래스로만 칠한다.
`fill="#..."` 을 요소에 직접 쓰지 않는다.

```svg
<style>
  .bg    { fill:#ffffff; stroke:#d8dee6 }
  .panel { fill:#f6f8fa; stroke:#d8dee6 }
  .ink   { fill:#1f2328 }
  .muted { fill:#656d76 }
  .rule  { stroke:#d8dee6 }
  .acc   { fill:#0969da }   /* 강조 */
  .warn  { fill:#9a6700 }   /* 주의 */
  .bad   { fill:#cf222e }   /* 실패·위험 */
  .good  { fill:#1a7f37 }   /* 정상·안전 */
  @media (prefers-color-scheme: dark) {
    .bg    { fill:#0d1117; stroke:#30363d }
    .panel { fill:#161b22; stroke:#30363d }
    .ink   { fill:#e6edf3 }
    .muted { fill:#8b949e }
    .rule  { stroke:#30363d }
    .acc   { fill:#4493f8 }
    .warn  { fill:#d29922 }
    .bad   { fill:#f85149 }
    .good  { fill:#3fb950 }
  }
</style>
```

## 글꼴

```
본문  font-family="-apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', 'Noto Sans KR', 'Malgun Gothic', sans-serif"
코드  font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"
```

크기: 제목 16 · 본문 14 · 보조 12 · 코드 13.
한글은 자간이 넓으므로 글자당 폭을 **본문 14px 기준 약 15px** 로 잡고 배치한다.

## 텍스트 — 반드시 지킬 둘

**1. 한 문장을 여러 `<text>` 로 쪼개지 않는다.** 조각마다 `x` 를 고정하면 글꼴에 따라
간격이 어긋난다. 강조가 섞인 문장은 하나의 `<text>` 안에서 `<tspan>` 으로 잇는다.

```svg
<!-- 나쁨 — 조각마다 x 고정 -->
<text x="44" y="308">위장 송출은 </text>
<text class="bad" x="128" y="308">①과 ②만</text>

<!-- 좋음 -->
<text x="44" y="308" xml:space="preserve"><tspan>위장 송출은 </tspan><tspan class="bad">①과 ②만</tspan><tspan> 바꾼다</tspan></text>
```

**2. `<tspan>` 을 쓰는 `<text>` 에는 `xml:space="preserve"` 를 반드시 붙인다.**
없으면 tspan 경계의 공백이 사라져 `위장 송출은①과 ②만바꾼다` 로 렌더된다.
그 경우 `<text>` 는 **한 줄로** 써야 한다 — 줄바꿈과 들여쓰기까지 보존되기 때문이다.

## 검증

새 도식을 만들면 반드시 돌린다. 렌더 실패·클래스 누락·다크 대응 누락을 잡는다.

```bash
python3 tools/check_svg.py docs/images
```

## 원칙

1. **도식은 본문이 말하지 못하는 것만 말한다.** 표로 충분하면 표를 쓴다.
2. 색은 **의미**에만 쓴다. 장식으로 칠하지 않는다.
3. 화살표에는 항상 라벨을 붙인다. 방향만으로는 관계를 알 수 없다.
4. 도식 하나에 개념 하나. 두 개면 두 장으로 나눈다.
5. 모든 도식에는 마크다운 캡션(`*그림 14-1 — …*`)을 붙인다.

## 화살표 마커

```svg
<defs>
  <marker id="a" viewBox="0 0 10 10" refX="9" refY="5"
          markerWidth="7" markerHeight="7" orient="auto-start-reverse">
    <path d="M0,0 L10,5 L0,10 z" class="mk"/>
  </marker>
</defs>
```
`.mk { fill:#656d76 }` / 다크 `#8b949e`. 강조 화살표는 `.mk-acc` 를 따로 둔다.
