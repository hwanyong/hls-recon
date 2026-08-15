# 부록 C — 용어집

이 용어집은 본문 **39개 장**과 **부록 A·B·D** 가 `> **용어** —` 형식으로 **처음 정의한 낱말**을
한곳에 모은 것이다. 각 항목은 **표제어(원어) — 한 줄 정의 — 처음 정의된 장** 순으로 적었다.
같은 개념이 곳에 따라 다르게 **표기·정의**된 경우 그 사실을 밝히고 가장 정확한 정의를
실었으며(§C.1), 어느 장·부록에서도 정식 정의되지 않았으나 본문 전반에 쓰이는 핵심어는
**†**로 표시해 따로 추가했다.

**찾는 법.** 한글 표제어는 가나다순(§C.2), 영문·약어 표제어는 알파벳순(§C.3)으로 나눠 실었다.
표제어는 각 장이 **굵게 앞세운 낱말**을 그대로 따랐다 — `매직 넘버(magic number)` 는 §C.2 로,
`AEAD(Authenticated Encryption…)` 는 §C.3 으로 간다. 한 개념이 여러 장에 나오면 **처음 정의된
장**을 기준 링크로 삼고, 정의가 갈리는 지점은 아래 §C.1 표에 모았다.

---

## C.1 정합화가 필요한 표기

같은 개념이 장에 따라 다른 이름이나 다른 정밀도로 정의된 지점이다. 교재를 고쳐 쓸 때
표기를 하나로 모을 후보다. 본문 각 항목에는 이 사실을 다시 표시해 두었다.

| 개념 | 갈리는 지점 | 이 용어집의 채택 |
|---|---|---|
| bearer token | **소지자 증표**([제11장](11-signed-url.md)) vs **무기명 토큰**([제12장](12-ambient-credentials.md)) | 같은 개념으로 병기, 「소지자 증표」를 대표 표기로 |
| mutation testing | **변이 테스트**([제34장](34-oracle-problem.md)) vs **뮤테이션 테스팅**([제35장](35-fault-injection.md)) | 「변이 테스트」를 대표 표기로 |
| sidecar | **sidecar·곁파일**([제27장](27-affine-time-mapping.md)·[제32장](32-filename-interface.md)) vs **사이드카 자막**([제30장](30-delegation-boundary.md)) | 「곁파일(sidecar)」을 대표 표기로 |
| 위협 모델 | **3요소**([제24장](24-padding-oracle-inverse.md)) vs **4요소**([제25장](25-aes128-is-not-drm.md)) | 제25장의 4요소 정의를 채택 |
| Kerckhoffs 원리 | 약식([제13장](13-obfuscation-not-security.md)) vs **Shannon's maxim** 포함([제25장](25-aes128-is-not-drm.md)) | 제25장 정의를 채택 |
| 멱등(idempotent) | 함수 `f(f(x))=f(x)`([제7장](07-url-normalization.md)) · HTTP 메서드([제8장](08-parallel-retry-measure.md)) · 상태 변경 멱등성([제29장](29-at-least-once-idempotency.md)) | 한 개념의 세 국면으로 묶음 |
| SSOT / 단일 출처 | [제7장](07-url-normalization.md) 정의 · [제30장](30-delegation-boundary.md) 재정의 | 동일 개념, 제7장을 기준으로 |
| 오탐·미탐 | 위양성/위음성([제18장](18-cc-counter-limits.md)) · 1종/2종 오류([제22장](22-threshold-design.md)) · 자막 소실/중복([제29장](29-at-least-once-idempotency.md)) | 한 항목에 통합 |
| variant / 렌디션 | **정합화 완료** — 제2장이 `variant(변종·렌디션)` 으로 둘을 한 낱말처럼 쓰던 것을 RFC 8216 의 구분에 맞춰 갈랐다([제2장](02-abr-and-hls.md) · [부록 B](appendix-B-spec-crossref.md)) | variant 는 `EXT-X-STREAM-INF` 화질 후보(정식 명칭 Variant Stream), 렌디션은 `EXT-X-MEDIA` 대체 트랙 |
| 초기화 세그먼트 | **init segment · `EXT-X-MAP`**([제19장](19-self-synchronizing.md)) vs **Media Initialization Section**([부록 B](appendix-B-spec-crossref.md)) | 표제어는 「init segment」, RFC 8216 의 공식 명칭을 병기 |
| 동일 출처 정책 | **응답을 스크립트에 건넬지의 통제**([제10장](10-cors-leak.md)) vs **DOM·쿠키·저장소 접근 격리**([제16장](16-sniffing-two-faces.md)) | 같은 규칙의 두 국면으로 병기 |

---

## C.2 한글 표제어 (가나다순)

### ㄱ

- **가단성**(malleability) — 암호문을 조작해 평문에 **예측 가능한** 변화를 일으킬 수 있는 성질. 평문을 몰라도 특정 비트를 뒤집는 조작이 가능하다. 〔[제23장](23-aes-cbc-iv.md)〕
- **가치 명제**(value proposition) — 어떤 도구가 사용자에게 무엇을 제공하기에 쓸 만한가를 밝힌 진술. 〔[제36장](36-control-group.md)〕
- **간접 참조**(indirection) — 값을 그 자리에 두지 않고, 값을 찾을 수 있는 이름이나 주소를 대신 두는 것. 〔[제3장](03-two-tier-indirection.md)〕
- **개방 실패**(fail-open) / **폐쇄 실패**(fail-closed) — 판단할 수 없는 입력을 통과시키는 쪽으로 기울면 개방 실패, 막는 쪽으로 기울면 폐쇄 실패. 접근 통제는 폐쇄 실패가 원칙이다. 〔[제16장](16-sniffing-two-faces.md)〕
- **거부 목록**(denylist) / **허용 목록**(allowlist) — 금지할 것을 열거하고 나머지를 통과시키면 거부 목록, 허용할 것을 열거하고 나머지를 막으면 허용 목록(=기본 거부). 〔[제12장](12-ambient-credentials.md)〕
- **결함 주입**(fault injection) — 알려진 결함을 의도적으로 심어, 시스템이 그 결함을 실제로 검출·처리하는지 관측하는 기법. 넣은 쪽이 정답을 알므로 그 정답이 곧 오라클이다. 〔[제34장](34-oracle-problem.md) · [제35장](35-fault-injection.md)〕
- **결합**(coupling) — 한 모듈이 다른 모듈의 내부 구조를 알아야만 동작할 수 있는 상태. 결합이 강하면 한쪽 변경이 다른 쪽을 깨뜨린다. 〔[제26장](26-encryption-granularity.md)〕
- **경로 순회**(path traversal, directory traversal) — 입력에 `../` 등을 넣어 의도된 디렉터리 밖의 파일에 도달하는 공격(CWE-22). 〔[제7장](07-url-normalization.md) · [제32장](32-filename-interface.md)〕
- **경보 피로**(alert fatigue) — 오탐이 잦은 경보에 대응자가 둔감해져 진짜 경보까지 무시하거나 경보를 꺼 버리는 현상. 실패 원인은 탐지 능력이 아니라 임계값 설계다. 〔[제22장](22-threshold-design.md) · [제37장](37-bidirectional-fixing.md)〕
- **곁파일**(sidecar) → §C.3 「sidecar」 참조.
- **계획–적용 분리**(plan/apply) — 무엇을 할지 계산하는 단계와 실제 수행 단계를 분리하고, 그 사이에 사람의 확인을 두는 구조. 〔[제32장](32-filename-interface.md)〕
- **공유 책임 모델**(shared responsibility model) — 제공자와 이용자가 각각 어느 계층의 보안·가용성을 책임지는지 명시한 표. 〔[제30장](30-delegation-boundary.md)〕
- **관측 가능성**(observability) — 시스템의 외부 출력만으로 내부 상태를 얼마나 알아낼 수 있는가. 위임은 편의를 얻고 관측 가능성을 지불하는 거래다. 〔[제30장](30-delegation-boundary.md)〕
- **교락**(confounding, 交絡) — 둘 이상의 요인이 함께 변해, 관측된 효과를 어느 요인에 돌려야 할지 분리할 수 없는 상태. 〔[제35장](35-fault-injection.md)〕
- **교란 변수**(confounding variable) — 처치가 아닌데도 두 집단의 결과에 차이를 만들 수 있는 요인. 하나라도 통제되지 않으면 관측된 차이를 처치의 효과로 돌릴 수 없다. 〔[제36장](36-control-group.md)〕
- **글로브**(glob) — 셸이 `*` `?` `[]` 를 파일 이름 패턴으로 확장하는 것. 확장은 명령 실행 전에 셸이 하므로, 프로그램은 자기 인자가 원래 무엇이었는지 알 수 없다. 〔[제32장](32-filename-interface.md)〕
- **기수 표기**(radix notation, 진법 표기) — 정수를 밑수 `b` 의 거듭제곱 합으로 적는 표기. 10진법의 `0-9`, 16진법의 `0-9 a-f` 가 특수한 경우다. 〔[제13장](13-obfuscation-not-security.md)〕
- **기저율**(base rate) / **기저율 오류**(base rate fallacy) — 모집단에서 실제 양성이 차지하는 비율, 그리고 그 값을 무시한 채 재현율·오탐률만으로 판정의 신뢰도를 추정하는 오류. 〔[제37장](37-bidirectional-fixing.md)〕
- **기준선**(baseline) — 판정 규칙이 관측값과 견주는 대조값. "무엇에 비추어 이상하다고 말하는가"에 답한다. 〔[제38장](38-baseline-contamination.md)〕
- **기준선 오염**(baseline contamination) — 검사가 측정하려는 대상이 기준선의 값에 영향을 주어, 기준선이 관측값을 따라 움직이는 상태. 〔[제38장](38-baseline-contamination.md)〕
- **길이 선언 프레이밍**(length-prefixed framing) — 데이터 단위의 길이를 그 데이터 앞에 적어 경계를 표시하는 방식. 〔[제20장](20-isobmff-structural.md)〕
- **길이 확장 공격**(length extension attack) — `H(M)` 과 `len(M)` 만 알면 `M` 을 몰라도 `H(M‖pad‖M′)` 을 계산할 수 있는 성질을 이용하는 공격. Merkle–Damgård 해시에서 성립한다. 〔[제11장](11-signed-url.md)〕
- **꼬리 지연**(tail latency) — 지연 분포의 상위 백분위(p95·p99 등)에 해당하는 느린 응답들. 규모가 커질수록 실제 경험 지연은 여기로 수렴한다. 〔[제8장](08-parallel-retry-measure.md)〕

### ㄴ

- **내부 타당도**(internal validity) — 관측된 차이를 **정말 처치가 만들었는가** 하는 성질. 교란 변수를 통제할수록 높아진다. 〔[제36장](36-control-group.md)〕
- **널 바이트 주입**(null byte injection) — `\x00` 에서 끝나는 C 문자열과 길이를 따로 갖는 문자열이 만나는 경계에서 문자열이 **잘리는** 것을 노린 공격. 〔[제32장](32-filename-interface.md)〕
- **논리 시계**(logical clock) — 물리 시각 대신 사건의 **선후 관계**만 기록하는 카운터. Lamport 시계, 벡터 시계가 대표적이다. 〔[제27장](27-affine-time-mapping.md)〕
- **능력**(capability) — 권한을 지시하는 값 자체가 요청에 명시적으로 실려 있고, 그 값을 가진 자만이 권한을 행사하는 방식. 서명 URL 이 그 예다. 〔[제12장](12-ambient-credentials.md)〕
- **능력 기반 접근 통제**(capability-based access control) — 접근 권한을 "요청한 주체가 누구인가"가 아니라 "그 요청이 어떤 증표를 들고 왔는가"로 판정하는 방식. 증표는 대상 자원과 허용 조건을 스스로 서술한다. 〔[제11장](11-signed-url.md)〕

### ㄷ

- **단사**(injective) — 서로 다른 입력이 언제나 서로 다른 출력을 갖는 성질(`x ≠ y ⟹ f(x) ≠ f(y)`). 〔[제7장](07-url-normalization.md)〕
- **단언**(assertion) — 테스트가 "이 조건이 참이어야 한다"고 명시하는 문장. 이 저장소에서는 콘솔 출력에 대한 `grep -q` 한 줄이 단언 하나다. 〔[제35장](35-fault-injection.md)〕
- **단일 출처**(SSOT, Single Source of Truth) — 어떤 값이 시스템 안에서 단 한 곳에서만 생산되고 나머지는 모두 그 값을 참조하기만 하는 설계. 여러 곳에서 만들어지면 같은 이름의 다른 값이 돌아다니게 된다. 〔[제7장](07-url-normalization.md) · 재정의 [제30장](30-delegation-boundary.md)〕
- **대소문자 접기**(case folding) — 대소문자 구별을 없앤 **비교 전용** 표기를 만드는 연산. `str.lower()`(소문자화)와 목적이 다르다 — 접기는 "같으면 같게 나오는 키"를 만든다. 〔[제31장](31-unicode-normalization.md)〕
- **대조군**(control group) — 실험에서 처치를 가하지 않고 나머지 조건은 처치군과 같게 유지한 비교 집단. 관측된 변화가 처치 때문인지 가르는 기준선이 된다. 〔[제36장](36-control-group.md)〕
- **대체 데이터 스트림**(ADS, Alternate Data Stream) — NTFS 가 한 파일에 여러 데이터 흐름을 붙이게 한 기능(`이름:스트림명`). 파일 이름 안의 `:` 가 Windows 에서 위험한 이유다. 〔[제32장](32-filename-interface.md)〕
- **델타 플레이리스트**(Delta Playlist) — 긴 라이브 플레이리스트에서 앞부분을 생략하고 변한 뒷부분만 실어 보내는 축약본. 생략된 구간은 `EXT-X-SKIP` 이 개수로만 표시한다. RFC 8216 에는 없고 `draft-pantos-hls-rfc8216bis` 에서 들어왔다. 〔[부록 B](appendix-B-spec-crossref.md)〕
- **동기 바이트**(sync byte) — MPEG-TS 의 188바이트 패킷마다 선두에 오는 고정값 `0x47`. 이 저장소에서는 상수로 못박혀 있다(`PACKET_SIZE = 188`, `SYNC_BYTE = 0x47`). 〔[제19장](19-self-synchronizing.md)〕
- **동등 변이체**(equivalent mutant) — 코드를 변형했는데도 관측 가능한 동작이 전혀 달라지지 않아 어떤 테스트로도 잡을 수 없는 변형. 뮤테이션 점수 분모에서 빼야 하며, 자동 판별이 일반적으로 불가능하다. 〔[제35장](35-fault-injection.md)〕
- **동일 출처 정책**(same-origin policy, SOP) — 어떤 출처에서 온 문서·스크립트가 다른 출처의 응답 내용을 읽지 못하게 하는 **브라우저 내부의 규칙**. 요청 자체가 아니라 응답을 스크립트에게 건넬지를 정한다. 제16장은 같은 규칙을 **스킴·호스트·포트가 같은 문서끼리만 서로의 DOM·쿠키·저장소에 접근할 수 있게 하는 격리**로 정의한다 — 한 규칙의 두 국면이다(§C.1). 〔[제10장](10-cors-leak.md) · [제16장](16-sniffing-two-faces.md)〕
- **동치류**(equivalence class) / **대표원**(representative) — 어떤 관계로 "같다"고 묶이는 값들의 집합, 그리고 그 집합에서 대표로 고른 하나의 값. 〔[제7장](07-url-normalization.md)〕
- **동형 문자**(homoglyph) — 서로 다른 문자인데 글꼴에서 거의 같게 보이는 문자(라틴 `a` U+0061 vs 키릴 `а` U+0430). 유니코드는 이 관계를 **혼동 가능(confusable)** 이라 부른다(UTS #39). 〔[제31장](31-unicode-normalization.md)〕
- **두 장군 문제**(Two Generals' Problem) — 신뢰할 수 없는 채널로만 소통하는 두 참여자가 어떤 사실에 대한 **공통 지식**에 도달할 수 없다는 불가능성 결과. 확인 응답의 사슬이 끝나지 않는다. 〔[제29장](29-at-least-once-idempotency.md)〕

### ㄹ

- **라이선스**(license) — 콘텐츠 키와 사용 규칙(기간·동시 재생 수·해상도 상한 등)을 함께 담아 **특정 기기만** 열 수 있도록 암호화한 메시지. 〔[제25장](25-aes128-is-not-drm.md)〕
- **래더**(ladder) / **variant**(변종) — 한 콘텐츠에 준비된 품질 후보의 집합이 래더, 후보 하나하나가 variant. 마스터 플레이리스트의 `#EXT-X-STREAM-INF` 한 줄이 variant 하나를 선언한다. RFC 8216 의 정식 명칭은 **Variant Stream** 이며, `EXT-X-MEDIA` 로 선언하는 렌디션과는 별개다. 〔[제2장](02-abr-and-hls.md)〕
- **렌디션**(rendition) — 같은 프로그램의 대체 표현. 한국어 자막과 영어 자막, 원어 오디오와 더빙 오디오가 각각 두 렌디션이다. `EXT-X-MEDIA` 로 선언되어 `GROUP-ID` 로 묶이고, `EXT-X-STREAM-INF` 의 `AUDIO`·`SUBTITLES` 속성이 그 그룹을 참조한다. 화질만 다른 720p·1080p 는 렌디션이 아니라 variant 다. 〔[부록 B](appendix-B-spec-crossref.md) · variant 와의 구분은 §C.1〕
- **리먹싱**(remuxing) — 오디오·비디오 스트림을 **재인코딩하지 않고** 컨테이너만 바꿔 다시 쓰는 작업(`-c copy`). 이 저장소는 어느 경로에서도 재인코딩하지 않는다. 〔[제30장](30-delegation-boundary.md)〕
- **링크 보호**(link protection) — 전송 경로에 놓인 자원의 **주소만** 획득한 제3자가 그 자원을 사용하지 못하게 하는 보호. 정당한 수신자는 배제 대상이 아니다. 〔[제25장](25-aes128-is-not-drm.md)〕

### ㅁ

- **마스터 플레이리스트**(Master Playlist) — 같은 콘텐츠의 여러 화질 후보와 부가 트랙의 **주소 목록**을 담은 M3U8 문서. 세그먼트를 직접 담지 않는다. 〔[제3장](03-two-tier-indirection.md)〕
- **마찰**(friction) — 공격 비용을 올리지만 적대자 집합 전체를 배제하지는 못하는 조치. 일부만 걸러 낸다. 〔[제25장](25-aes128-is-not-drm.md)〕
- **매니페스트**(manifest) / **플레이리스트**(playlist) — 세그먼트의 주소·재생 길이·부가 정보를 담은 목록 문서. HLS 에서는 `.m3u8` 확장자의 UTF-8 텍스트이며 태그 줄과 URI 줄이 번갈아 나온다. 〔[제2장](02-abr-and-hls.md)〕
- **매직 넘버**(magic number) — 파일 형식을 식별하기 위해 선두(고정 위치)에 놓이는 고정 바이트열. MPEG-TS 는 `0x47` 이 188바이트 주기로 반복되고, ISO-BMFF 는 오프셋 4~8 에 박스 타입이 온다 — TS 처럼 **주기 구조**로 판별하는 포맷도 있다. 〔[제14장](14-segment-masquerading.md) · [제16장](16-sniffing-two-faces.md)〕
- **먹싱**(muxing, 다중화) — 따로 부호화된 영상·음성·자막 스트림을 하나의 컨테이너 파일로 엮어 넣는 작업. 이 저장소에서는 `ffmpeg -c copy` 가 담당한다. 〔[제20장](20-isobmff-structural.md)〕
- **메시지 프레이밍**(message framing) — 바이트 스트림 위에서 "이 메시지의 본문은 여기서 시작해 여기서 끝난다"를 정하는 규칙. 스트림 프로토콜 TCP 위에 메시지 경계를 다시 세우는 일이다. 〔[제4장](04-statelessness.md)〕
- **멱등**(idempotent) — 함수 `f` 에 대해 `f(f(x)) = f(x)` 가 성립하는 성질. 분산 시스템에서는 같은 요청을 두 번 보내도 상태가 한 번 보낸 것과 같다는 뜻으로 쓴다. HTTP 는 `GET`·`HEAD`·`PUT`·`DELETE` 를 멱등으로 정의한다. 〔함수 관점 [제7장](07-url-normalization.md) · HTTP 메서드 [제8장](08-parallel-retry-measure.md) · §C.1〕
- **멱등성**(idempotency) — 같은 연산을 두 번 이상 수행해도 결과가 한 번 수행한 것과 같은 성질. `f(f(x)) = f(x)` 를 상태 변경에 적용한 것이다. 〔[제29장](29-at-least-once-idempotency.md)〕
- **멱등성 키**(idempotency key) — 같은 작업의 재시도를 하나로 묶기 위해 요청에 붙이는 식별자. 수신자는 같은 키를 이미 처리했으면 앞선 결과를 돌려준다. 〔[제29장](29-at-least-once-idempotency.md)〕
- **모노이드**(monoid) — 집합과 이항연산이 (1) 결합법칙과 (2) 단위원 `e`(여기서는 빈 바이트열)을 만족하는 대수 구조. 세그먼트의 바이트 연결이 이 구조를 이룬다. 〔[제19장](19-self-synchronizing.md)〕
- **무결성**(integrity) — 데이터가 만들어진 뒤 의도하지 않은 변경(잡음·결손·위조)을 겪지 않았음. 기밀성(내용을 못 보게 함)·가용성(받을 수 있음)과 다르다. 〔[제4장](04-statelessness.md)〕
- **무기명 토큰**(bearer token) — 그 값을 제시하는 자가 곧 권한자로 취급되는 자격증명. 소지 자체가 자격이며 신원을 따로 확인하지 않는다. [제11장](11-signed-url.md)의 「소지자 증표」와 같은 개념(§C.1). 〔[제12장](12-ambient-credentials.md)〕
- **무상태**(stateless) / **무상태성**(statelessness) — 서버가 요청 사이에 클라이언트별 상태를 유지하지 않는 성질(RFC 9110). 각 요청은 자기 자신만으로 해석되며, 그 대가로 필요한 문맥을 스스로 실어 날라야 한다. 〔[제2장](02-abr-and-hls.md) · [제4장](04-statelessness.md)〕
- **미디어 세그먼트**(media segment) — HLS 에서 재생 시간의 한 구간에 대응하는 독립된 자원. 이 저장소가 다루는 것은 MPEG-TS(`.ts`)와 fMP4(`.m4s`) 두 컨테이너다. 〔[제1장](01-stream-vs-file.md) · [제2장](02-abr-and-hls.md)〕
- **미디어 플레이리스트**(Media Playlist) — 실제 미디어 세그먼트의 주소를 재생 순서대로 나열한 M3U8 문서. RFC 8216 은 한 문서가 마스터·미디어 둘 다이면 **무효**라고 규정한다. 〔[제3장](03-two-tier-indirection.md)〕
- **미지원**(unsupported) — [부록 B](appendix-B-spec-crossref.md) 의 표기 규약. "파서가 그 줄을 인식하지 않고 그냥 지나친다"는 뜻으로, 오류도 경고도 남기지 않는다. 파서가 예외를 던지며 물리치는 경우는 「거부」로 따로 적는다. 〔[부록 B](appendix-B-spec-crossref.md)〕
- **미탐**(false negative) → 「오탐·미탐」(ㅇ) 참조.

### ㅂ

- **박스**(box) — ISO-BMFF 의 유일한 구조 단위. 크기와 종류를 선언하는 머리와 그 뒤의 본문으로 이루어지며, 본문 안에 다시 박스가 들어갈 수 있다. QuickTime 계열은 **atom** 이라 부른다. 〔[제20장](20-isobmff-structural.md)〕
- **반개구간**(half-open interval) — 한쪽 끝만 포함하는 구간 `[lo, hi)`. 경계 시각이 정확히 한 조각에만 속하게 하는 표준적 방법이며, 닫힌 구간으로 잡으면 경계 큐가 양쪽에 들어가 중복이 는다. 〔[제29장](29-at-least-once-idempotency.md)〕
- **범위 검사** → §C.3 「bounds check」 참조.
- **변이 테스트**(mutation testing, 뮤테이션 테스팅) — 프로그램에 인위적 결함(변이, mutant)을 심고 테스트 스위트가 그 변이를 잡아내는지 측정하는 기법. 잡히지 않은 변이는 스위트의 사각지대를 가리킨다. 〔[제34장](34-oracle-problem.md) · 「뮤테이션 테스팅」 [제35장](35-fault-injection.md) · §C.1〕
- **별도 출처 격리**(sandbox domain / user-content origin) — 사용자가 올린 자원을 주 서비스와 **다른 호스트**에서 서비스해, 실행되더라도 동일 출처 정책에 의해 주 서비스의 자격증명·DOM 에 닿지 못하게 하는 배치. 〔[제16장](16-sniffing-two-faces.md)〕
- **부분 암호화**(partial encryption) — 데이터의 일부만 암호화하고 나머지는 평문으로 남기는 방식. 남기는 부분은 대개 구조를 읽는 데 필요한 정보다. 〔[제26장](26-encryption-granularity.md)〕
- **부정 후방탐색**(negative lookbehind) — `(?<!X)` 형식의 **폭 0 어서션**. 현재 위치 바로 앞이 `X` 와 일치하면 그 자리 매치를 거부하되 문자를 소비하지 않는다. `(?<!\d)` 하나가 `Sky.Blue.2003` 의 연도 오분해를 막는다. 〔[제33장](33-regex-accuracy.md)〕
- **부채널**(side channel) — 프로토콜이 의도적으로 전달하는 값이 아니라 실행 시간·전력 소모·캐시 상태·응답 크기처럼 **구현이 부수적으로 흘리는 관측량**으로 비밀이 새는 경로. 〔[제24장](24-padding-oracle-inverse.md)〕
- **부호 혼동**(signed/unsigned confusion) — 부호 없는 값을 부호 있는 정수형으로 읽거나 그 반대로 다루어, 큰 양수가 음수로(또는 음수가 거대한 양수로) 해석되는 결함. 길이 검사 앞에서 일어나면 `if (len > max)` 가 그대로 통과한다. 〔[제28장](28-33bit-wrap.md)〕
- **분류기**(classifier) — 입력을 미리 정한 범주 중 하나로 배정하는 절차. `EPISODE_RE` 는 파일 이름을 "화수가 있는/없는"으로 가르는 이진 분류기다. 〔[제33장](33-regex-accuracy.md)〕
- **분리도**(separability) — 정상 집단과 이상 집단의 지표 분포가 겹치지 않는 정도. 겹치는 구간에서는 어떤 임계값도 두 오류를 동시에 0 으로 만들지 못한다((오탐률, 정탐률) 궤적이 **ROC 곡선**). 〔[제22장](22-threshold-design.md)〕
- **블록 암호**(block cipher) — 고정 길이 블록 하나를 키로 치환하는 함수. AES 의 블록 길이는 언제나 128비트(16바이트)이며, `AES-128` 의 128 은 **키 길이**이지 블록 길이가 아니다. 〔[제23장](23-aes-cbc-iv.md) · [제24장](24-padding-oracle-inverse.md)〕
- **비예약 문자**(unreserved characters) — 어떤 문맥에서도 데이터로만 쓰이는 문자(`ALPHA / DIGIT / - . _ ~`, RFC 3986 §2.3). 퍼센트 인코딩을 풀어도 안전한 유일한 부류다. 〔[제7장](07-url-normalization.md)〕
- **비인증 암호화**(unauthenticated encryption) — 기밀성만 제공하고 무결성·출처 인증은 제공하지 않는 암호화. HLS 의 AES-128-CBC 가 여기 해당해, 암호문이 변조돼도 복호화는 그냥 "다른 평문"을 내놓는다. 〔[제2장](02-abr-and-hls.md)〕
- **빅엔디언**(big-endian, 네트워크 바이트 순서) — 여러 바이트로 된 수를 최상위 바이트부터 저장하는 방식. ISO-BMFF 의 모든 다중 바이트 필드가 이 순서이며, 명시하지 않으면 리틀엔디언 기계에서 오독한다. 〔[제20장](20-isobmff-structural.md)〕

### ㅅ

- **사이드카 자막**(sidecar subtitle) → §C.3 「sidecar」 참조.
- **사전 압축**(dictionary compression) — 입력에서 반복되는 조각을 사전에 한 번만 저장하고, 본문에서는 그 사전의 위치(색인)를 가리켜 전체 길이를 줄이는 방식(LZ78 계열). 〔[제13장](13-obfuscation-not-security.md)〕
- **사전 요청**(preflight request) — 규격이 정한 "단순 요청" 범위를 벗어나는 요청 앞에 브라우저가 먼저 보내는 `OPTIONS` 요청. HLS 의 매니페스트·세그먼트 `GET` 은 여기 해당하지 않는다. 〔[제10장](10-cors-leak.md)〕
- **삼값 논리**(three-valued logic) — 참·거짓에 더해 **미결정(unknown)** 을 셋째 값으로 두는 논리 체계. SQL 의 `NULL` 비교가 대표적이다(`NULL = NULL` 은 `UNKNOWN`). 〔[제38장](38-baseline-contamination.md)〕
- **상태 코드**(status code) — HTTP 응답의 첫 줄에 오는 3자리 정수. 서버가 요청 처리 결과를 값 하나로 요약해 신고하는 필드다. 〔[제5장](05-status-code-collapse.md)〕
- **상호정보량**(mutual information) — 두 확률변수 중 하나를 관측했을 때 다른 하나에 대한 불확실성이 줄어드는 양. 0 이면 관측이 아무것도 알려주지 않는다. 〔[제34장](34-oracle-problem.md)〕
- **샘플**(sample) — 미디어 컨테이너에서 시각 하나에 대응하는 데이터 단위. 영상이면 화면 한 장(프레임), 오디오면 오디오 프레임 하나다. 〔[제26장](26-encryption-granularity.md)〕
- **생성 후 검사**(generate and test) — 정답을 직접 계산할 수 없을 때 후보를 열거하고 각각을 판정자에게 물어 맞는 것을 채택하는 전략. 여기서 판정자는 **서버**다. 〔[제33장](33-regex-accuracy.md)〕
- **서명 대상**(signed payload) / **정규 문자열**(canonical string) — 서명을 계산할 때 해시 입력으로 들어가는 바이트열. 발급자와 검증자가 같은 규칙으로 같은 문자열을 만들어야 서명이 맞는다. 〔[제11장](11-signed-url.md)〕
- **서비스 거부**(denial of service) — 정상 이용자가 서비스를 이용하지 못하게 되는 상태. **공격 의도는 정의에 포함되지 않는다** — 부하로 가용성이 무너지면 원인이 무엇이든 서비스 거부다. 〔[제8장](08-parallel-retry-measure.md)〕
- **선택 평문 공격**(chosen-plaintext attack, CPA) — 공격자가 임의의 평문을 골라 **같은 키로** 암호화시키고 그 암호문을 관찰할 수 있다고 가정하는 공격 모형. 현대 암호의 기본 안전성 기준(IND-CPA)이 상정한다. 〔[제23장](23-aes-cbc-iv.md)〕
- **소지자 증표**(bearer token) — 소지 사실 외에 아무 자격도 요구하지 않는 증표. 훔친 사람과 원래 소지자를 서버가 구별하지 못한다. 서명 URL 은 URL 문자열 전체가 소지자 증표다. [제12장](12-ambient-credentials.md)의 「무기명 토큰」과 같은 개념(§C.1). 〔[제11장](11-signed-url.md)〕
- **소프트웨어 공급망**(software supply chain) — 최종 산출물에 들어가는 모든 의존성과 그 의존성이 만들어지고 배포되는 경로 전체. 〔[제30장](30-delegation-boundary.md)〕
- **스플라이싱**(splicing) — 스트림 중간에 다른 스트림(광고 등)을 끼워 넣기 위해 경계를 잘라 잇는 작업. 〔[제26장](26-encryption-granularity.md)〕
- **신뢰 경계**(trust boundary) — 서로 다른 신뢰 수준의 두 영역이 맞닿는 지점. 경계를 넘어오는 데이터는 검증 대상이며, 경계를 어디에 긋느냐가 곧 "무엇을 검증해야 하는가"를 정한다. 〔[제13장](13-obfuscation-not-security.md) · [제30장](30-delegation-boundary.md)〕
- **신뢰 실행 환경**(TEE, Trusted Execution Environment) — 주 운영체제와 분리된 실행 영역으로, 그 안의 메모리와 코드에 운영체제 권한으로도 접근할 수 없도록 하드웨어가 강제한다. 〔[제25장](25-aes128-is-not-drm.md)〕

### ㅇ

- **아핀 변환**(affine transformation) — 선형 변환(스케일 `a`)에 평행이동(`b`)을 더한 변환. 직선을 직선으로, 등간격을 등간격으로 보낸다. 1차원 시간축에서 `a` 는 클럭 속도의 비, `b` 는 원점의 차이다. 〔[제27장](27-affine-time-mapping.md)〕
- **암호화 입자**(encryption granularity, 암호화 입도) — 암호 변환을 적용하는 최소 단위. "무엇 하나를 통째로 암호화하는가"의 그 **무엇**이다 — 파일·블록·프레임 하나일 수 있다. 〔[제26장](26-encryption-granularity.md)〕
- **압축 폭탄**(decompression bomb / zip bomb) — 압축된 상태에서는 작지만 해제하면 방어자의 메모리·디스크를 고갈시키도록 만들어진 데이터. 자원 소진(DoS) 공격의 한 형태다. 〔[제6장](06-content-negotiation.md)〕
- **앰비언트 권한**(ambient authority) — 요청하는 주체가 명시적으로 지정하지 않아도 **실행 환경이 자동으로 부여하는 권한**. 요청은 "무엇을 하겠다"만 말하고 "어떤 자격으로"는 환경이 채운다. 〔[제12장](12-ambient-credentials.md)〕
- **양성 클래스**(positive class) — 혼동 행렬에서 "검출 대상"으로 지정한 쪽. 정탐·오탐·미탐은 전부 이 지정에 상대적이라, 양성을 어디로 잡느냐에 따라 같은 오류가 오탐도 미탐도 된다. 〔[제37장](37-bidirectional-fixing.md)〕
- **역직렬화 취약점**(deserialization vulnerability) — 직렬화된 데이터를 객체로 복원할 때, 데이터가 지정한 타입의 생성자·마법 메서드가 호출되어 공격자가 고른 코드 경로가 실행되는 문제. `pickle`·자바 직렬화가 대표적이다. 〔[제13장](13-obfuscation-not-security.md)〕
- **예약 문자**(reserved characters) — 구분자로 쓰일 수 있는 문자(`reserved = gen-delims / sub-delims`, RFC 3986 §2.2). gen-delims 는 URI 대분류 성분을, sub-delims 는 성분 안 하위 구분자를 가른다. 〔[제7장](07-url-normalization.md)〕
- **오라클**(oracle) — 공격자가 임의로 질의할 수 있고, 그 응답이 비밀에 관한 정보를 조금씩(또는 통째로) 흘리는 인터페이스. 응답이 흘리는 정보량이 필요한 질의 횟수를 결정한다. 〔[제10장](10-cors-leak.md) · [제23장](23-aes-cbc-iv.md)〕
- **오탐**(false positive, 위양성) · **미탐**(false negative, 위음성) — 결함이 없는데 있다고 판정하면 오탐, 있는데 없다고 판정하면 미탐. 검사기의 성능은 이 두 오류율의 쌍으로만 서술된다(제22장은 1종/2종 오류로 부른다). 자막 문맥(제29장)에서는 위양성=자막 소실, 위음성=자막 중복이다. 〔[제18장](18-cc-counter-limits.md) · [제22장](22-threshold-design.md) · [제33장](33-regex-accuracy.md)〕
- **옥텟**(octet) — 8비트 바이트. 규격은 "문자"가 아니라 옥텟을 인코딩 대상으로 말한다 — 문자를 어떤 인코딩으로 바이트열로 바꿀지는 별개 결정(오늘날 웹은 UTF-8)이다. 〔[제7장](07-url-normalization.md)〕
- **요청 줄**(request line) — HTTP 요청 메시지의 첫 줄. `<메서드> SP <요청 대상> SP <버전>` 형태다. 〔[제7장](07-url-normalization.md)〕
- **운용 모드**(mode of operation) — 고정 길이 블록 암호를 임의 길이 메시지에 적용하는 규칙. 쪼개는 법·섞는 법·마지막 블록 채우는 법을 정한다. 블록 암호 자체는 모드를 알지 못한다. 〔[제23장](23-aes-cbc-iv.md)〕
- **위임**(delegation) — 어떤 책임을 자기가 구현하지 않고 다른 구성 요소에 넘기는 설계 결정. 넘기는 쪽이 위임자, 넘겨받는 쪽이 수임자다. 함수 호출·라이브러리·외부 프로세스·SaaS 가 모두 같은 형태다. 〔[제30장](30-delegation-boundary.md)〕
- **위협 모델**(threat model) — 어떤 보호가 **무엇을**(자산) **누구로부터**(적대자) **어떤 능력의 공격에 대해**(능력) **무엇을 신뢰한다는 가정 아래**(신뢰 가정) 지키는지를 명시한 서술. 네 항목이 채워져야 "보호된다"가 참·거짓을 가릴 주장이 된다. 〔[제24장](24-padding-oracle-inverse.md)의 3요소를 [제25장](25-aes128-is-not-drm.md)이 4요소로 확장 · §C.1〕
- **유니코드 정규화 공격**(Unicode normalization attack) — 검증을 통과하는 표기로 입력을 넣은 뒤, 검증 **이후**의 정규화가 그것을 금지된 값으로 바꾸게 하는 공격. 넓게는 정준화 공격의 한 종류(CWE-180). 〔[제31장](31-unicode-normalization.md)〕
- **유사난수함수**(PRF, pseudorandom function) — 키를 모르는 관찰자에게는 완전한 무작위 함수와 구별되지 않는 함수. 〔[제11장](11-signed-url.md)〕
- **의미론적 붕괴**(semantic collapse) — 서로 다른 계층의 두 명제가 하나의 신호로 표현되면서, 소비자가 아래 계층의 참을 위 계층의 참으로 읽게 되는 현상. 신호가 담을 수 있는 것보다 많은 것을 읽어 낸 것이다. 〔[제5장](05-status-code-collapse.md)〕
- **이중 인코딩 우회**(double encoding bypass) — 금지된 문자열을 두 번 퍼센트 인코딩해 검증기를 통과시킨 뒤, 검증 이후 계층의 디코딩이 그것을 금지된 문자열로 되돌리게 하는 기법(CWE-174, 정준화 공격의 한 종류). 〔[제7장](07-url-normalization.md)〕
- **임계 회피**(threshold evasion) — 탐지 규칙의 임계값을 아는 주체가 각 행위를 임계 미만으로 잘게 나누어 탐지를 피하는 기법. 속도 제한 아래로 기어가는 스캐닝이 같은 형태다. 〔[제22장](22-threshold-design.md)〕

### ㅈ

- **자격증명 포함 요청**(credentialed request) — 쿠키·HTTP 인증·클라이언트 인증서를 실어 보내는 교차 출처 요청. 응답은 `ACAO` 에 정확한 출처를 명시하고 `Access-Control-Allow-Credentials: true` 를 함께 보내야 한다. 〔[제10장](10-cors-leak.md)〕
- **자기동기 포맷**(self-synchronizing format) — 스트림의 임의 지점에서 읽기를 시작해 경계를 잃은 수신자가 **유한한 바이트만 소비하면 올바른 경계를 스스로 회복**하는 포맷. 경계 정보가 스트림 곳곳에 국소적으로 박혀 있어야 성립한다. 〔[제19장](19-self-synchronizing.md)〕
- **자족적 세그먼트**(self-contained segment) — 앞선 세그먼트를 받지 않아도 단독으로 복호·표시할 수 있는 조각. 영상에서는 각 세그먼트를 키프레임으로 시작하게 하는 것이 이 성질이다. 〔[제29장](29-at-least-once-idempotency.md)〕
- **재생 공격**(replay attack) — 정당하게 만들어진 요청이나 증표를 가로채 **그대로 다시 보내는** 공격. 내용을 위조하지 않으므로 서명 검증을 그대로 통과한다 — 방어는 "전에 본 적 있는가"의 판정에 의존한다. 〔[제11장](11-signed-url.md) · [제29장](29-at-least-once-idempotency.md)〕
- **재현율**(recall) → 「정탐률」 참조.
- **저장형 XSS**(stored cross-site scripting) — 공격자가 심어 둔 스크립트가 서버에 저장되었다가, 다른 사용자가 그 자원을 열 때 **피해자의 브라우저에서 그 사이트의 출처 권한으로** 실행되는 취약점. 〔[제16장](16-sniffing-two-faces.md)〕
- **적응형 기준선**(adaptive baseline) — 최근 관측치로 정상 범위를 계속 갱신하는 방식. 계절성·추세를 자동 흡수하는 대신, 갱신 창에 들어온 이상치가 기준선 자체를 움직인다. 〔[제38장](38-baseline-contamination.md)〕
- **전송 코딩**(transfer coding) — 한 홉(hop) 구간에서만 적용되는 인코딩(`Transfer-Encoding: chunked`). 다음 홉으로 넘어갈 때 벗겨질 수 있다. 〔[제6장](06-content-negotiation.md)〕
- **절단 공격**(truncation attack) — 경로상의 공격자가 통신을 정상 종료처럼 보이게 중간에서 끊어, 수신 측이 **부분 데이터를 완전한 것으로 받아들이게** 만드는 공격. 〔[제4장](04-statelessness.md)〕
- **정규 언어**(regular language) — 유한 오토마타로 인식되는 문자열 집합. 중첩·재귀 구조(괄호 짝, HTML 트리)는 정규 언어가 아니므로 정규식으로 인식할 수 없다. 〔[제33장](33-regex-accuracy.md)〕
- **정규식**(regular expression, 정규 표현식) — 문자열의 집합을 유한한 문법으로 기술하는 표기. 한 문자열이 그 집합에 드는지를 판정한다. 〔[제33장](33-regex-accuracy.md)〕
- **정규화**(normalization) — 동치인 여러 표현 중 하나를 대표로 정해 문자열을 그 대표형으로 바꾸는 연산. 규정은 UAX #15. 〔[제31장](31-unicode-normalization.md)〕
- **정규화 보존**(normalization-preserving) / **정규화 불변**(normalization-insensitive) — 만들 때 준 표기를 그대로 저장·반환하면 보존, 정규화 형식이 달라도 같은 이름으로 찾아주면 불변. 둘은 독립된 성질이다. 〔[제31장](31-unicode-normalization.md)〕
- **정밀도**(precision) — 도구가 양성으로 판정한 것 중 실제로 결함이었던 비율 `TP / (TP + FP)`. 재현율과 달리 **분모가 도구의 출력**이라는 점이 핵심이다. 〔[제37장](37-bidirectional-fixing.md)〕
- **정수 오버플로**(integer overflow) — 고정 폭 정수형의 표현 범위를 넘는 연산 결과가 그 폭 안으로 되돌아 감기는 현상. 부호 없는 정수에서는 모듈러 연산으로 **경고 없이 조용히** 일어난다. 〔[제20장](20-isobmff-structural.md)〕
- **정준 동치**(canonical equivalence) — 두 문자열이 **같은 문자**를 나타내며 어떤 문맥에서도 바꿔 써도 의미가 바뀌지 않는 관계(`Å` U+00C5 vs `A`+결합 고리). 〔[제31장](31-unicode-normalization.md)〕
- **정준 순서**(canonical ordering) — 결합 문자가 여럿 붙을 때 **정준 결합 클래스** 값 순으로 정렬하는 규칙. 분해 단계에서 이 정렬이 이루어진다. 〔[제31장](31-unicode-normalization.md)〕
- **정준 특이 분해**(canonical singleton decomposition) — 한 코드포인트가 결합 문자 없이 **다른 코드포인트 하나**로 정준 분해되는 경우. 역사적 중복 부호화를 정리하는 장치다. 〔[제31장](31-unicode-normalization.md)〕
- **정준화**(canonicalization) — 같은 것을 뜻하는 여러 표기를 하나의 표준 표기로 모으는 연산. `normalize_url` 이 URI 에 대한 정준화다. 〔[제7장](07-url-normalization.md)〕
- **정탐률**(true positive rate, 재현율 recall · 민감도 sensitivity) — 실제로 결함이 있는 입력 중 도구가 결함이라고 판정한 비율 `TP / (TP + FN)`. 〔[제34장](34-oracle-problem.md) · [제37장](37-bidirectional-fixing.md)〕
- **종단 간 논증**(end-to-end argument) — 어떤 기능이 응용의 관점에서 완전히 옳게 수행되려면 양 끝에서 확인해야 하며, 하위 계층이 같은 일을 해도 그것은 **성능 최적화**일 뿐 정확성의 근거가 못 된다(Saltzer·Reed·Clark, 1984). 〔[제4장](04-statelessness.md) · [제5장](05-status-code-collapse.md)〕
- **종료 코드**(exit status) — 프로세스가 종료하며 부모에게 남기는 정수. POSIX 관례상 `0` 이 성공이며, 셸의 `&&` 와 CI 파이프라인의 단계 진행이 이 값 하나로 갈린다. 〔[제1장](01-stream-vs-file.md)〕
- **죽은 코드**(dead code) — 어떤 실행 경로에서도 결과에 영향을 주지 않는 코드. 함수가 호출되지만 언제나 같은 값을 돌려주어 상수로 바꿔도 동작이 안 달라지는 상태를 포함한다. 〔[제37장](37-bidirectional-fixing.md)〕
- **중앙값**(median) / **붕괴점**(breakdown point) — 정렬한 표본의 가운데 값, 그리고 통계량이 임의로 망가지려면 오염돼야 하는 표본의 최소 비율. 중앙값의 붕괴점은 50%, 평균은 0%다(표본 하나로 평균이 무한대). 〔[제22장](22-threshold-design.md)〕
- **지수 백오프**(exponential backoff) — 재시도 간격을 시도 횟수에 대해 지수적으로 늘리는 방식. 이 코드는 `backoff × 2^(n−1)` 로, 기본값에서 0.8초 → 1.6초가 된다. 〔[제8장](08-parallel-retry-measure.md)〕
- **진행 보장**(progress guarantee) — 반복문이 매 회 상태를 반드시 앞으로 진전시킨다는 성질. 커서 파서에서는 "커서가 매 회 최소 1 증가"이며, 이것이 없으면 정지성(termination)을 증명할 수 없다. 〔[제20장](20-isobmff-structural.md)〕

### ㅊ

- **처치군**(treatment group) — 검증하려는 처치(개입)를 실제로 가한 집단. 〔[제36장](36-control-group.md)〕
- **최근접 순위**(nearest-rank) / **선형 보간**(linear interpolation) — 정렬 표본에서 실제 관측치 하나를 골라 분위수로 삼으면 최근접 순위, 두 이웃을 비례로 나눠 계산하면 선형 보간(반환값이 관측치가 아닐 수 있음). 〔[제8장](08-parallel-retry-measure.md)〕
- **최대 만족 원칙**(maximal munch) — 어휘 분석에서 한 토큰은 가능한 한 길게 잡는다는 규칙. 연속한 숫자열은 통째로 하나의 수이지 쪼갤 수 있는 두 수가 아니다. 〔[제33장](33-regex-accuracy.md)〕
- **출력 보호**(output protection) — 복호화된 신호가 기기 밖으로 나가는 경로에 대한 통제. 디스플레이 연결 규격 수준에서 이루어진다. 〔[제25장](25-aes128-is-not-drm.md)〕
- **출처**(origin) — 스킴·호스트·포트의 세 값으로 이루어진 조합. 직렬화 표기는 `https://site.example` 이며 **경로도 끝 슬래시도 없다**. 〔[제9장](09-hotlink-referer.md) · [제10장](10-cors-leak.md)〕
- **출처 반사**(origin reflection) — 요청의 `Origin` 헤더 값을 그대로 `ACAO` 에 되돌려 쓰는 구성(`ACAO: <요청이 보낸 Origin>`). 〔[제10장](10-cors-leak.md)〕
- **충돌 저항성**(collision resistance) — 같은 해시값을 갖는 서로 다른 두 입력을 찾기 어려운 성질. MD5 에서는 2004년 이후 실용적으로 깨져 있다. 〔[제11장](11-signed-url.md)〕
- **침묵 실패**(silent failure) — 작업의 일부가 실패했는데도 상위 계층에는 성공으로 보고되어, 실패가 관측 지점에 도달하지 못하는 상태. 〔[제1장](01-stream-vs-file.md)〕

### ㅋ

- **카오스 엔지니어링**(chaos engineering) — 운영 중인 분산 시스템에 의도적으로 장애(인스턴스 종료·네트워크 지연·패킷 손실)를 주입해 시스템이 견디는지 관측하는 실천. 〔[제35장](35-fault-injection.md)〕
- **캐시 키**(cache key) — CDN 이 캐시된 응답을 찾을 때 쓰는 식별자. 기본값은 대개 "호스트 + 경로 + 쿼리 스트링"이다. 〔[제11장](11-signed-url.md)〕
- **코드 커버리지**(code coverage) / **결함 커버리지**(fault coverage) — 테스트 실행이 지나간 코드 줄·분기의 비율, 그리고 상정한 결함 목록 중 테스트가 실제로 검출한 결함의 비율. 〔[제35장](35-fault-injection.md)〕
- **코드포인트**(code point) — 유니코드가 문자 하나에 부여한 번호(`U+AC00`). **바이트 수**(UTF-8 결과)와도, **화면에 보이는 글자 수**(자소 클러스터)와도 다르다. 〔[제31장](31-unicode-normalization.md)〕
- **콘텐츠 스니핑**(content sniffing) / **MIME 스니핑**(MIME sniffing) — 자원의 미디어 타입을 선언된 값(`Content-Type`·확장자)이 아니라 **본문 바이트를 검사해** 결정하는 절차. 이 교재는 둘을 같은 뜻으로 쓴다. 〔[제16장](16-sniffing-two-faces.md)〕
- **콘텐츠 코딩**(content coding) — 표현의 바이트열에 적용된 변환(주로 압축). `Content-Encoding` 이 선언하며, **표현의 일부**이자 종단 간이다. 〔[제6장](06-content-negotiation.md)〕
- **콘텐츠 협상**(content negotiation) — 같은 URI 가 여러 표현을 가질 때, 그중 어떤 표현을 보낼지 클라이언트의 선호와 서버의 판단으로 정하는 절차. 〔[제6장](06-content-negotiation.md)〕
- **클록 스큐**(clock skew) — 서로 다른 기계의 시계가 어긋난 양. 〔[제11장](11-signed-url.md)〕

### ㅌ

- **타이밍 공격**(timing attack) — 연산에 걸린 시간의 차이에서 비밀을 복원하는 부채널 공격. 〔[제11장](11-signed-url.md)〕
- **테스트 오라클**(test oracle) — 어떤 실행 결과가 옳은지 그른지 판정해 주는 독립적 근거. 오라클이 없으면 "테스트를 돌렸다"가 "검증했다"를 뜻하지 않는다. 명세·참조 구현·사람의 판단·자명한 불변식이 오라클 노릇을 한다. 〔[제1장](01-stream-vs-file.md) · [제34장](34-oracle-problem.md) · [제35장](35-fault-injection.md)〕
- **테스트 오라클 문제**(test oracle problem) — 실제 대상에 대해 그런 독립적 근거를 얻는 일이 일반적으로 어려운 문제. 테스트 입력은 만들기 쉬운데 **그 입력의 정답을 아는 일이 어렵다**는 비대칭에서 나온다. 〔[제34장](34-oracle-problem.md)〕
- **트릭 플레이**(trick play) — 배속 재생·되감기·구간 탐색처럼 순차 재생이 아닌 재생 동작. 대개 I-프레임만 골라 낸다. 〔[제26장](26-encryption-granularity.md)〕

### ㅍ

- **파국적 백트래킹**(catastrophic backtracking) — 같은 문자열을 나누는 경우의 수가 입력 길이에 대해 지수적으로 늘어나 매칭 시간이 폭증하는 현상. 〔[제33장](33-regex-accuracy.md)〕
- **파일명**(filename) — 디렉터리 항목에서 아이노드를 가리키는 문자열 키. **경로의 한 성분**이며 그 자체에 경로 구분자가 들어갈 수 없다. 〔[제32장](32-filename-interface.md)〕
- **판정**(verdict) — 관측치에 대해 검사기가 내리는 등급. 이 코드에서는 `PASS`·`WARN`·`FAIL` 세 값의 문자열 상수다. 〔[제39장](39-verdict-synthesis.md)〕
- **패딩 오라클**(padding oracle) — 제출된 암호문을 복호화한 뒤 **패딩이 규격에 맞는지 여부**를 외부에서 구별 가능하게 알려 주는 인터페이스. 알려 주는 정보는 1비트지만, 반복해 얻으면 키 없이 평문을 복원할 수 있다. 〔[제24장](24-padding-oracle-inverse.md)〕
- **패킷**(transport stream packet) — MPEG-TS 의 유일한 단위. 길이는 **언제나 188바이트**이고, 앞 4바이트가 헤더, 나머지 184바이트가 몸통이다. 〔[제17장](17-mpegts-packet.md)〕
- **패턴 암호화**(pattern encryption) — 암호화 블록과 평문 블록을 정해진 비율로 번갈아 배치하는 부분 암호화 방식. 복호화 비용을 줄이면서 내용을 쓸 수 없게 한다. 〔[제26장](26-encryption-granularity.md)〕
- **퍼센트 인코딩**(percent-encoding) — 옥텟 하나를 `%` 와 16진수 두 자리(`%HH`)로 표기하는 방법(RFC 3986 §2.1). 이미 인코딩된 `%20` 을 다시 인코딩하면 `%2520` 이 되어 다른 자원을 가리킨다. 〔[제7장](07-url-normalization.md)〕
- **폴리글롯 파일**(polyglot file) — 서로 다른 두 개 이상의 형식으로 **동시에 유효하게** 파싱되는 하나의 파일(GIF 이면서 JAR, PDF 이면서 ZIP 등). 콘텐츠 검사기가 "영상이다"라 판정한 그 바이트가 다른 파서에겐 전혀 다를 수 있다. 〔[제16장](16-sniffing-two-faces.md) · [제19장](19-self-synchronizing.md)〕
- **표본 실행** — 대상 전체가 아니라 그 일부만 처리하는 실행. 여기서는 플레이리스트 앞 N개 세그먼트만 받는 `--limit` 실행을 가리킨다. 〔[제38장](38-baseline-contamination.md)〕
- **표현**(representation) — 어떤 자원의 특정 시점·특정 형식의 바이트열과 그 메타데이터. 한 자원(resource)에 여러 표현이 있을 수 있다 — 한국어판과 영어판, gzip 판과 무압축판이 그렇다. 〔[제6장](06-content-negotiation.md)〕
- **품질 게이트**(quality gate) — 파이프라인의 한 단계에서 정해진 조건을 만족하지 못하면 다음 단계로 진행하지 못하게 막는 관문. CI 에서는 대개 종료 코드가 0 이 아니면 작업을 멈추는 형태다. 〔[제39장](39-verdict-synthesis.md)〕

### ㅎ

- **핫링크**(hotlinking, 인라인 링크) / **핫링크 차단**(hotlink protection) — 남의 서버 자원을 자기 페이지에서 직접 참조해 대역폭 비용은 원본이 지고 수익은 참조 측이 가져가는 것, 그리고 요청의 `Referer`·`Origin` 이 허용 목록에 없으면 자원을 안 내주는 서버 규칙. 값이 자기 신고이므로 위조를 막지 못한다. 〔[제9장](09-hotlink-referer.md) · [제10장](10-cors-leak.md)〕
- **항등원**(identity element) / **흡수원**(absorbing element) — 무엇과 결합해도 상대를 그대로 두는 원소(덧셈의 `0`, 여기서는 `PASS`), 그리고 무엇과 결합해도 자기 자신이 되는 원소(곱셈의 `0`, 여기서는 `FAIL`). 〔[제39장](39-verdict-synthesis.md)〕
- **허수아비 비교**(straw-man comparison) — 비교 대상을 실제보다 약한 형태로 세워 이긴 뒤, 강한 형태에도 이겼다고 말하는 오류. 대조군을 일부러 불리하게 구성하면 측정은 그대로여도 결론이 무의미해진다. 〔[제36장](36-control-group.md)〕
- **호환 동치**(compatibility equivalence) — 두 문자열이 **다른 문자**이지만 같은 추상 문자에서 파생된 관계(`ﬁ` 합자 vs `fi`, 전각 `Ａ` vs `A`). **바꿔 쓰면 정보가 사라진다.** 〔[제31장](31-unicode-normalization.md)〕
- **혼동 행렬**(confusion matrix) — 실제 상태(결함 있음/없음)와 판정(FAIL/PASS)의 조합을 네 칸으로 표시한 표. 정탐·오탐·미탐·정상통과의 개수가 들어간다. 〔[제34장](34-oracle-problem.md)〕

---

## C.3 영문·약어 표제어 (알파벳순)

각 장이 영문 낱말이나 약어를 앞세워 정의한 항목이다. 원어 표기를 표제어로 두고 우리말 뜻을 병기했다.

### 숫자

- **90kHz 클럭** — MPEG-2 시스템 클럭 27MHz 를 300 으로 나눈 눈금. PTS(표시 시각)가 이 눈금의 33비트 부호 없는 정수로 실린다. 〔[제27장](27-affine-time-mapping.md)〕

### A

- **ABR**(adaptive bitrate streaming, 적응 비트레이트 스트리밍) — 같은 콘텐츠를 여러 비트레이트로 인코딩해 두고, 클라이언트가 측정한 네트워크 상황에 따라 세그먼트 단위로 품질을 바꿔 가며 받는 방식. 〔[제2장](02-abr-and-hls.md)〕
- **ACAO**(`Access-Control-Allow-Origin`) — CORS 의 핵심 응답 헤더. "이 응답을 읽어도 되는 출처"를 하나 지정하거나 `*` 로 전부 허용한다. 〔[제10장](10-cors-leak.md)〕
- **adaptation field**(적응 필드) — payload 대신 TS 패킷 몸통에 들어갈 수 있는 제어 영역. 길이 바이트로 시작하며 PCR(기준 클럭)·불연속 표시·스터핑을 담는다. 헤더의 `adaptation_field_control` 2비트가 유무를 정한다. 〔[제17장](17-mpegts-packet.md) · [제18장](18-cc-counter-limits.md)〕
- **adaptation field control**(AFC, 적응 필드 제어) — 2비트. 몸통에 adaptation field 가 있는지, payload 가 있는지를 각각 한 비트로 알린다. 〔[제17장](17-mpegts-packet.md)〕
- **AEAD**(Authenticated Encryption with Associated Data, 연관 데이터를 갖는 인증 암호) — 기밀성과 무결성·인증을 **한 연산으로** 처리하는 방식(AES-GCM·ChaCha20-Poly1305). 복호화 시 인증 태그가 맞지 않으면 평문을 한 바이트도 내주지 않고 실패한다. 〔[제4장](04-statelessness.md) · [제23장](23-aes-cbc-iv.md) · [제24장](24-padding-oracle-inverse.md)〕
- **`as_completed`** — `concurrent.futures` 의 함수. 넘긴 Future 들을 **완료된 순서대로** 하나씩 내주는 이터레이터를 만든다. 제출 순서와는 무관하다. 〔[제8장](08-parallel-retry-measure.md)〕
- **at-most-once / at-least-once / exactly-once 전달** — 메시지 전달 보증. **최대 1회**는 유실 가능·중복 없음, **최소 1회**는 유실 없음·중복 가능(ack 미도착 시 재전송), **정확히 1회**는 유실도 중복도 없음. 〔[제29장](29-at-least-once-idempotency.md)〕

### B

- **B-프레임**(bidirectionally predicted frame, 양방향 예측 프레임) — 앞뒤 두 방향의 프레임을 참조해 부호화되는 프레임. 뒤 프레임을 참조하므로 디코드 순서가 표시 순서보다 앞서야 하고, 그 결과 컨테이너의 패킷 순서(DTS 순)와 화면 순서(PTS 순)가 달라진다. 〔[제22장](22-threshold-design.md)〕
- **bounds check**(범위 검사) — 값이 허용된 범위 안에 있는지 계산 이전에 확인하는 것. 형식을 보는 파싱·타입을 보는 타입 검사와 다르다(`-1` 은 `int` 이지만 33비트 부호 없는 값의 범위 밖). 〔[제28장](28-33bit-wrap.md)〕

### C

- **CBC**(Cipher Block Chaining, 암호 블록 연쇄) 모드 — 각 평문 블록을 직전 암호문 블록과 XOR 한 뒤 암호화하는 운용 모드. 복호화는 `P_i = D_K(C_i) XOR C_(i-1)` 이고 첫 블록의 `C_0` 자리에는 IV 가 들어간다. 〔[제24장](24-padding-oracle-inverse.md)〕
- **CEA-608/708** — 영상 기본 스트림(elementary stream) 안에 실려 전송되는 캡션 규격. 별도 자원이 아니므로 `EXT-X-MEDIA` 선언에 `URI` 속성이 없다. 〔[부록 D](appendix-D-known-limits.md)〕
- **CENC**(Common Encryption, ISO/IEC 23001-7) — ISO-BMFF 계열의 표준 부분 암호화 규격. 샘플 안 평문·암호문 구간의 길이 쌍을 별도 메타데이터로 기록해 두고 그 표를 보고 복호화한다. 〔[제26장](26-encryption-granularity.md)〕
- **CFR**(constant frame rate, 고정 프레임률) / **VFR**(variable frame rate, 가변 프레임률) — 모든 프레임이 같은 간격이면 CFR, 프레임마다 간격이 다를 수 있으면 VFR. 컨테이너는 각 프레임의 PTS 를 개별로 담으므로 **컨테이너 수준에서 둘은 구별되지 않는다.** 〔[제22장](22-threshold-design.md)〕
- **`Content-Disposition: attachment`** — 응답을 문서로 렌더하지 말고 파일로 내려받으라고 지시하는 HTTP 응답 헤더. 〔[제16장](16-sniffing-two-faces.md)〕
- **continuity counter**(연속성 카운터, CC) — MPEG-TS 패킷 헤더 마지막 바이트의 하위 4비트 필드. PID 별로 독립이며 **페이로드를 실은 패킷마다** 0~15 를 순환하며 1씩 증가한다. 값이 건너뛰면 그 사이 패킷이 유실된 것이고, 4비트뿐이라 정확히 16의 배수만큼 유실되면 검출되지 않는다. 〔[제1장](01-stream-vs-file.md) · [제18장](18-cc-counter-limits.md) · [제19장](19-self-synchronizing.md)〕
- **CORS**(Cross-Origin Resource Sharing, 교차 출처 자원 공유) — 서버가 응답 헤더로 SOP 를 **완화**해 특정 출처의 스크립트에게 응답 읽기를 허용하는 규격. 접근을 제한하는 규격이 아니라 제한을 푸는 규격이다. 〔[제10장](10-cors-leak.md)〕
- **CRIME(2012) · BREACH(2013)** — 압축된 데이터의 **크기**를 관찰해 그 안에 든 비밀(세션 토큰 등)을 한 글자씩 알아내는 공격. 추측 문자열이 비밀과 일치할수록 압축 결과가 짧아진다. 〔[제6장](06-content-negotiation.md)〕
- **CSP**(Content Security Policy, 콘텐츠 보안 정책) — 페이지가 어떤 출처의 스크립트·스타일·이미지를 실행·적재할 수 있는지 서버가 응답 헤더로 선언하는 브라우저 강제 정책. XSS 의 영향을 줄이는 실제 통제다. 〔[제13장](13-obfuscation-not-security.md)〕
- **CSRF**(Cross-Site Request Forgery, 교차 사이트 요청 위조) — 사용자가 로그인해 둔 사이트 A 에 대해 다른 사이트 B 가 사용자의 브라우저를 통해 요청을 보내게 만드는 공격. 브라우저가 A 의 쿠키를 자동으로 실어 A 는 정당한 요청과 구별하지 못한다. 〔[제12장](12-ambient-credentials.md)〕
- **CWE-180**(Incorrect Behavior Order: Validate Before Canonicalize) — 정준화보다 먼저 검증을 수행하는 잘못된 순서. 검증이 통과시킨 값이 정준화를 거쳐 금지된 값이 되는 부류의 결함을 가리킨다. 〔[제7장](07-url-normalization.md) · [제29장](29-at-least-once-idempotency.md)〕

### D

- **demuxer**(디멀티플렉서) — 컨테이너 파일에서 오디오·비디오·자막 등 개별 스트림을 분리해 내는 구성 요소. FFmpeg 은 수백 종을 내장하며, 상당수는 영상과 무관한 오래된 포맷이다. 〔[제15장](15-evasion-disables-defense.md)〕
- **DPI**(Deep Packet Inspection, 심층 패킷 검사) — 패킷의 헤더뿐 아니라 페이로드까지 들여다보아 트래픽 종류를 분류하는 기법. 〔[제14장](14-segment-masquerading.md)〕
- **DTS**(Decoding Time Stamp, 복호 시각) — 접근 단위를 언제 디코더에 넣어야 하는지를 나타내는 값. PTS 와 함께 90kHz 눈금의 33비트 부호 없는 정수이며, B-프레임이 있으면 두 값이 달라진다. 〔[제21장](21-pts-and-90khz.md)〕

### E

- **encrypt-then-MAC** — 평문을 암호화한 뒤 **암호문에 대해** MAC 을 계산해 붙이는 합성 방식. 수신 측은 복호화 **전에** MAC 을 검증하고, 실패하면 복호화를 아예 수행하지 않는다. 〔[제24장](24-padding-oracle-inverse.md)〕
- **exFAT**(Extended File Allocation Table) — 마이크로소프트가 만든 파일 시스템. USB 외장 디스크·SD 카드의 사실상 기본 포맷이며, 파일명 규칙은 Windows 의 것을 그대로 따른다. 〔[제32장](32-filename-interface.md)〕
- **`EXT-X-DISCONTINUITY`** — HLS 플레이리스트 태그. 다음 세그먼트에서 **타임스탬프의 연속성이 끊긴다**고 미리 선언한다(광고 삽입·소스 이어붙임·인코더 재시작). RFC 8216 이 정의한 정상 상태이지 오류가 아니다. 〔[제21장](21-pts-and-90khz.md)〕
- **`EXT-X-MAP`** → 「init segment」 참조.
- **EXT-X-TARGETDURATION** — 미디어 플레이리스트가 선언하는 세그먼트 최대 재생 길이(초, 정수). RFC 8216 이 미디어 플레이리스트에 필수로 요구한다. 〔[제22장](22-threshold-design.md)〕

### F

- **faststart** — `moov` 박스를 `mdat` 앞으로 옮겨 두는 MP4 배치. 재생기가 파일 전체를 받기 전에 메타데이터를 얻어 HTTP 점진 재생이 가능해진다. `-movflags +faststart` 는 먹싱 후 파일을 한 번 더 통과하며 재배치한다. 〔[제20장](20-isobmff-structural.md)〕
- **fetch metadata**(페치 메타데이터) — 브라우저가 요청마다 자동으로 붙이는 `Sec-Fetch-*` 헤더 묶음. 같은 사이트에서 왔는지(`Site`)·어떤 방식인지(`Mode`)·무엇을 위한 것인지(`Dest`)를 알린다. `Sec-` 접두어가 곧 금지 헤더 표시다. 〔[제9장](09-hotlink-referer.md)〕
- **fMP4**(fragmented MP4) — ISO-BMFF 를 조각으로 나눈 형태. 각 미디어 세그먼트는 `moof`(movie fragment)와 `mdat`(media data) 박스로 이루어진다. 이 저장소는 확장자 `.m4s` 로 다룬다. 〔[제19장](19-self-synchronizing.md)〕
- **forbidden header name**(금지 헤더 이름) — Fetch 규격이 스크립트로는 설정하지 못하도록 지정한 요청 헤더 이름 목록(`Referer`·`Origin`·`Host`·`Cookie`·`Sec-` 등). 지정하면 요청은 실패하지 않고 **그 지정만 조용히 무시된다.** 〔[제9장](09-hotlink-referer.md)〕
- **`ftyp` · `moov` · `mdat`** — `ftyp`(File Type Box)는 파일이 어떤 규격의 파생인지 선언하고, `moov`(Movie Box)는 스트림 구성·타임스케일·샘플 위치표 등 **메타데이터 전체**를, `mdat`(Media Data Box)는 부호화된 **본문 바이트열**만 담는다. `moov` 없이는 `mdat` 를 해석할 방법이 없다. 〔[제20장](20-isobmff-structural.md)〕

### G

- **`genpts`**(generate PTS) — ffmpeg 의 입력 플래그. "DTS 가 있으면 없는 PTS 를 생성한다" — 표시 시각이 비어 있고 디코딩 시각만 있을 때 프레임 간격으로부터 PTS 를 합성해 채운다. 〔[제19장](19-self-synchronizing.md)〕
- **GOP**(Group of Pictures, 영상 그룹) — 하나의 키프레임(독립 복호화 가능한 프레임)과 그에 이어지는 예측 프레임들의 묶음. HLS 세그먼트 경계는 키프레임에서 끊어야 각 세그먼트가 독립 재생되므로, GOP 길이가 세그먼트 분할의 전제가 된다. [제2장](02-abr-and-hls.md)의 IDR 프레임 정의 안에 이름만 먼저 나오고, 정식 정의는 부록 A 에 있다. 〔[부록 A](appendix-A-lab-setup.md)〕

### H

- **HLS**(HTTP Live Streaming) — 영상을 수 초 단위 조각으로 나누어 평범한 HTTP GET 으로 내려보내고, 그 조각들의 목록을 텍스트 파일(M3U8 플레이리스트)로 가리키는 전송 방식. RFC 8216 이 규정한다. 〔[제1장](01-stream-vs-file.md)〕
- **HTTP 요청 분할**(HTTP request splitting) — 요청 헤더 값에 CRLF(`\r\n`)를 밀어 넣어 하나의 요청을 수신 측이 **두 개로 읽게** 만드는 공격. 헤더 하나만 얹히면 헤더 주입, 요청 줄까지 새로 만들어지면 요청 분할이다. 〔[제12장](12-ambient-credentials.md)〕
- **Hyrum의 법칙**(Hyrum's Law) — 어떤 API 든 이용자가 충분히 많으면 명세와 무관하게 **관측 가능한 모든 동작**에 누군가 의존하게 된다. 여기서는 "ffmpeg 이 매핑을 적용하지 **않는다**"는 관측 동작에 보정 코드가 의존한다. 〔[제30장](30-delegation-boundary.md)〕

### I

- **IDR 프레임**(Instantaneous Decoder Refresh) — 그 프레임부터 디코딩을 시작해도 되는 H.264/H.265 의 독립 프레임. 앞 프레임을 참조하지 않으므로 조각을 자를 수 있는 유일한 지점이다. IDR 사이의 묶음을 GOP 라 한다. 〔[제2장](02-abr-and-hls.md)〕
- **init segment**(초기화 세그먼트) / **`EXT-X-MAP`** — fMP4 스트림의 디코딩 문맥(`ftyp`+`moov`)을 담은 세그먼트. 미디어 데이터는 없고 코덱·트랙 설정만 있으며, 모든 세그먼트 앞에 한 번 붙어야 재생이 성립한다. HLS 는 `#EXT-X-MAP:URI="init.mp4"` 태그로 가리킨다. RFC 8216 의 공식 명칭은 **Media Initialization Section** 이고 [부록 B](appendix-B-spec-crossref.md) 가 그 이름으로 정의한다(§C.1). 〔[제19장](19-self-synchronizing.md) · [부록 B](appendix-B-spec-crossref.md)〕
- **IRI**(Internationalized Resource Identifier, 국제화 자원 식별자) — 비-ASCII 문자를 허용하는 식별자 규격(RFC 3987). IRI → URI 변환은 비-ASCII 문자를 UTF-8 옥텟열로 바꾼 뒤 각 옥텟을 `%HH` 로 치환하는 것이다. 〔[제7장](07-url-normalization.md)〕
- **ISO-BMFF**(ISO base media file format) — ISO/IEC 14496-12 가 정의하는 미디어 컨테이너 형식. MP4(`.mp4`·`.m4v`)·fMP4 세그먼트(`.m4s`)·HEIF 가 이 형식의 파생이고, **QuickTime(`.mov`)은 파생이 아니라 이 형식이 유래한 원형**이다. 파일 전체가 **박스**라는 단일 단위의 나열로 이루어진다. 〔[제20장](20-isobmff-structural.md)〕
- **`-itsoffset`** — ffmpeg 의 **입력** 옵션. 바로 뒤에 오는 `-i` 입력의 모든 타임스탬프를 지정한 초만큼 이동시킨다. 출력 옵션이 아니라 입력 옵션이므로 `-i` 앞에 놓여야 한다. 〔[제27장](27-affine-time-mapping.md)〕
- **IV**(Initialization Vector, 초기화 벡터) — 운용 모드가 첫 블록을 처리할 때 필요한 초기값. CBC 에서는 `C₀` 자리에 들어가며 블록 길이와 같은 16바이트다. **비밀이 아니다** — 복호화 측이 알아야 하므로 대개 평문으로 전달된다. 〔[제23장](23-aes-cbc-iv.md)〕

### K

- **Kerckhoffs 원리**(Kerckhoffs's principle) — 암호 시스템의 안전성은 알고리즘의 비밀이 아니라 **오직 키의 비밀에만** 의존해야 한다는 설계 원칙(1883). 클로드 섀넌은 같은 요구를 "적이 시스템을 안다고 가정하라"(**Shannon's maxim**)로 다시 적었다. 〔[제25장](25-aes128-is-not-drm.md) · 약식 [제13장](13-obfuscation-not-security.md) · §C.1〕

### M

- **MAC**(Message Authentication Code, 메시지 인증 코드) — 비밀 키를 아는 쪽만 만들 수 있고 같은 키를 아는 쪽이 검증할 수 있는 짧은 태그. 메시지의 **무결성**과 **출처**를 함께 보증한다. 서명 URL 의 `md5=` 자리에 들어가야 하는 것이 이것이다. 〔[제11장](11-signed-url.md)〕
- **media sequence number**(미디어 시퀀스 번호) — 미디어 플레이리스트 안에서 세그먼트마다 부여되는 정수 일련번호. 첫 번호는 `EXT-X-MEDIA-SEQUENCE`(없으면 0)이고 이후 1씩 증가한다. 라이브에서 창이 밀려도 같은 세그먼트의 번호는 변하지 않는다. 〔[제2장](02-abr-and-hls.md) · [제23장](23-aes-cbc-iv.md)〕
- **Merkle–Damgård 구성** — 메시지를 고정 크기 블록으로 나눠 압축 함수를 되풀이 적용하고 **마지막 내부 상태를 그대로 출력**하는 해시 구성(MD5·SHA-1·SHA-2). 출력이 곧 내부 상태이므로 **이어서 계산할 수 있다.** 〔[제11장](11-signed-url.md)〕
- **MPEG-TS**(MPEG-2 Transport Stream) — ISO/IEC 13818-1 이 정의한 다중화 컨테이너. 오류가 잦고 되감을 수 없는 전송로를 전제로 설계되었으며, 스트림 전체가 **고정 길이 패킷의 나열** 하나로만 이루어진다. 〔[제17장](17-mpegts-packet.md)〕

### N

- **NAL 유닛**(Network Abstraction Layer unit) — H.264/H.265 비트스트림의 전송 단위. 종류 헤더와 페이로드로 이루어지고, 슬라이스 하나가 대개 NAL 유닛 하나에 담긴다. 〔[제26장](26-encryption-granularity.md)〕
- **nonce**(number used once, 논스) — 같은 키 아래에서 **두 번 쓰이지 않아야 하는** 값. IV 와 혼용되지만 요구가 다르다 — CBC 의 IV 는 예측 불가능해야 하고, CTR·GCM 의 nonce 는 예측 가능해도 되나 재사용은 안 된다. 재생 공격 방어에서는 수신자가 본 nonce 를 기억해 재사용을 거부한다. 〔[제23장](23-aes-cbc-iv.md) · [제29장](29-at-least-once-idempotency.md)〕
- **NTP**(Network Time Protocol, 네트워크 시각 프로토콜) — 네트워크 너머의 기준 시계에 로컬 시계를 맞추는 프로토콜. 왕복 측정으로 시계 차이를 추정한다. 〔[제27장](27-affine-time-mapping.md)〕
- **null packet**(널 패킷) — PID 가 `0x1FFF` 인 패킷. 내용에 의미가 없고 비트레이트를 일정하게 맞추기 위한 **패딩**으로만 존재하며, 중계 장비가 자유롭게 넣고 뺀다. 〔[제17장](17-mpegts-packet.md)〕

### O

- **OCSP**(Online Certificate Status Protocol, 온라인 인증서 상태 프로토콜) — 제시된 TLS 인증서가 폐기되었는지를 발급 기관에 실시간으로 묻는 프로토콜. 응답은 `good`·`revoked`·`unknown` 셋이다. 〔[제38장](38-baseline-contamination.md)〕
- **origin**(오리진) → 「출처」(§C.2) 참조.

### P

- **packed JS** — 자바스크립트 소스를 낱말 사전 + 색인으로 치환해 크기를 줄인 뒤, 복원 함수와 함께 한 줄로 묶어 `eval` 에 넘기는 형식. 가장 널리 쓰인 구현이 Dean Edwards Packer(`p,a,c,k,e,d` 패커)다. 〔[제13장](13-obfuscation-not-security.md)〕
- **pchar**(path character) — 경로 한 조각에 그대로 놓일 수 있는 문자. 비예약 문자, 퍼센트 인코딩된 삼중자, sub-delims 전체, 그리고 `:` 와 `@`. 〔[제7장](07-url-normalization.md)〕
- **PCR**(Program Clock Reference, 프로그램 클럭 기준) — 송신기의 STC 현재값을 수신기에 알려 주는 필드. TS 패킷의 adaptation field 에 실리며, 수신기는 이 값으로 자기 클럭을 끌어당긴다. 〔[제21장](21-pts-and-90khz.md)〕
- **PES**(Packetized Elementary Stream, 패킷화 기본 스트림) — 압축된 영상·음성 스트림을 시각 정보와 함께 감싼 계층. TS 188바이트 패킷이 실어 나르는 내용물이 PES 패킷이고, PTS·DTS 는 PES 의 선택 헤더에 들어간다. 〔[제21장](21-pts-and-90khz.md)〕
- **PID**(Packet Identifier, 패킷 식별자) — 13비트 정수. 그 패킷이 어느 기본 스트림(영상·오디오·자막·제어 테이블)에 속하는지를 가리키는 **번호표**이지 주소가 아니다. 의미 배정은 스트림 안의 제어 테이블(PAT·PMT)이 정한다. 〔[제17장](17-mpegts-packet.md)〕
- **PKCS#7 패딩**(PKCS#7 padding) — 블록 길이를 채우기 위해 부족한 `n` 바이트를 **전부 값 `n`** 으로 채우는 규칙(RFC 5652 §6.3). HLS 의 AES-128 은 RFC 8216 §4.3.2.4 에서 이 패딩을 쓴다고 규정한다. 〔[제24장](24-padding-oracle-inverse.md)〕
- **PTS**(Presentation Time Stamp, 표시 시각) — 프레임을 언제 화면에 내보낼지 지정하는 값. MPEG-TS 에서는 **90kHz 클럭 기준의 33비트 부호 없는 정수**로 실리며, 직전 프레임과의 간격이 아니라 **타임라인 위의 절대 좌표**다. 〔[제1장](01-stream-vs-file.md) · [제21장](21-pts-and-90khz.md)〕

### R

- **ReDoS**(Regular expression Denial of Service, 정규식 서비스 거부) — 백트래킹 기반 정규식 엔진에서 특정 입력이 비정상적으로 긴 매칭 시간을 유발해 CPU 를 고갈시키는 공격. 〔[제33장](33-regex-accuracy.md)〕
- **Referer**(리퍼러) — 이 요청을 유발한 문서의 주소를 담는 HTTP 요청 헤더(RFC 9110 §10.1.3). 철자가 틀린 것은 RFC 1945(1996)의 오타가 굳은 것이다. 〔[제9장](09-hotlink-referer.md)〕
- **Referrer-Policy**(리퍼러 정책) — 문서가 유발한 요청에 Referer 를 얼마나 실을지 정하는 응답 헤더 겸 문서 메타데이터(`no-referrer`·`origin`·`strict-origin-when-cross-origin` 등). 〔[제9장](09-hotlink-referer.md)〕
- **RTMP**(Real-Time Messaging Protocol, 실시간 메시징 프로토콜) — Macromedia(이후 Adobe)가 만든 스트리밍 프로토콜. 기본 TCP 포트 **1935** 로 지속 연결을 열고 그 위로 오디오·비디오 메시지를 흘려보낸다. 〔[제2장](02-abr-and-hls.md)〕
- **RTSP**(Real Time Streaming Protocol, 실시간 스트리밍 프로토콜) — RFC 2326(1998)의 **제어** 프로토콜. TCP 554 로 `PLAY`·`PAUSE` 같은 명령만 주고받고 미디어는 별도로 RTP 가 나른다 — 제어 채널과 데이터 채널이 분리돼 있다. 〔[제2장](02-abr-and-hls.md)〕

### S

- **same-origin policy** → 「동일 출처 정책」(§C.2) 참조.
- **SAST**(Static Application Security Testing, 정적 애플리케이션 보안 시험) — 프로그램을 실행하지 않고 소스 코드를 분석해 취약점 후보를 찾는 도구 부류. 찾은 것마다 심각도를 매기고, 어느 등급부터 빌드를 세울지는 이용자가 정한다. 〔[제39장](39-verdict-synthesis.md)〕
- **security through obscurity**(모호성에 의한 보안) — 설계·구현·데이터 형식을 상대가 모른다는 가정 위에 안전성을 세우는 방식. 〔[제13장](13-obfuscation-not-security.md)〕
- **sidecar**(곁파일 · 사이드카) — 영상 컨테이너 안이 아니라 **별도 파일**로 본체 옆에 같은 이름으로 놓인 자막·리포트(`영상.ko.srt`·`.json` 등). 재생기가 파일명 규칙으로 짝을 찾는다. 제30장은 「사이드카 자막」으로 부른다(§C.1). 〔[제27장](27-affine-time-mapping.md) · [제30장](30-delegation-boundary.md) · [제32장](32-filename-interface.md)〕
- **soft-fail**(연성 실패) — 폐기 상태를 확인하지 못했을 때 연결을 막지 않고 그대로 진행하는 정책. 반대는 hard-fail 이다. 〔[제38장](38-baseline-contamination.md)〕
- **SSOT**(Single Source of Truth) → 「단일 출처」(§C.2) 참조.
- **start code prefix**(시작 코드 접두) — MPEG 계열 스트림에서 패킷 경계를 찾기 위한 고정 바이트열 `00 00 01`. 파서는 이 패턴을 만나면 거기서부터 새 구조가 시작한다고 판단한다. 〔[제21장](21-pts-and-90khz.md)〕
- **STC**(System Time Clock, 시스템 시각 클럭) — MPEG-2 시스템 규격이 정한 기준 클럭. 공칭 주파수 **27MHz** 이며, 송신기와 수신기가 이 클럭을 맞추는 것이 동기 재생의 전제다. 〔[제21장](21-pts-and-90khz.md)〕
- **`stts`**(Decoding Time to Sample Box) — ISO-BMFF 의 박스 중 하나로, 샘플마다 **다음 샘플까지의 지속(sample_delta)** 을 적는다. 절대 좌표가 아니라 상대 지속의 나열이다. 〔[제21장](21-pts-and-90khz.md)〕

### T

- **telescoping sum**(망원 합) — 이웃한 항이 서로 상쇄되어 양 끝만 남는 합. `Σ(tᵢ₊₁ − tᵢ) = tₙ − t₀`. 〔[제21장](21-pts-and-90khz.md)〕
- **tick**(틱) — 클럭의 한 눈금. MPEG-TS 의 표시 시각은 초가 아니라 90kHz 클럭의 눈금 수로 실린다. 1 tick = 1/90,000초 ≈ 11.1 µs. 〔[제21장](21-pts-and-90khz.md)〕
- **TLV**(Type-Length-Value) — 데이터를 «종류·길이·값» 세 칸으로 감싸는 부호화 규약. 값 안에 다시 TLV 가 들어가면 **재귀 TLV**. ISO-BMFF 는 순서가 «길이·종류·값» 인 TLV 변형이다. 〔[제20장](20-isobmff-structural.md)〕
- **TOCTOU**(Time-Of-Check to Time-Of-Use, 검사 시점과 사용 시점의 불일치) — 검사한 시점의 상태와 사용하는 시점의 상태가 다를 수 있는 구조. 두 시점 사이에 대상이 바뀌면 검사 결과가 무효가 된다. 〔[제3장](03-two-tier-indirection.md) · [제32장](32-filename-interface.md)〕
- **transport scrambling control**(TSC, 전송 스크램블 제어) — 헤더의 2비트. `00` 은 스크램블 없음, 그 외 값은 **payload 가 스크램블되어 있음**을 뜻한다. 헤더와 adaptation field 는 이 값과 무관하게 언제나 평문이다. 〔[제17장](17-mpegts-packet.md)〕
- **TTFB**(Time To First Byte, 최초 바이트 도달 시간) — 요청을 보낸 뒤 응답의 첫 바이트가 도착하기까지의 시간. 서버의 처리 지연을 전송량과 분리해 본다. 본문 수신 완료 시간은 여기에 **본문 크기 ÷ 대역폭**이 더해진 값이다. 〔[제4장](04-statelessness.md) · [제22장](22-threshold-design.md)〕

### U

- **Unix 시각**(Unix time) — 1970-01-01 00:00:00 UTC 로부터 흐른 초를 정수로 센 값. 시간대 표기가 없어 서로 다른 기계가 같은 순간을 같은 수로 부른다. 서명 URL 의 `expires=` 뒤에 오는 정수가 이것이다. 〔[제11장](11-signed-url.md)〕
- **URI**(Uniform Resource Identifier, 통합 자원 식별자) — 자원을 가리키는 문자열의 일반 규격(RFC 3986). URL 은 그중 **위치로 가리키는** 부분집합의 통칭이다. 〔[제7장](07-url-normalization.md)〕

### V

- **`Vary` 응답 헤더** — 이 응답이 어떤 **요청 헤더**에 따라 달라지는지를 캐시에게 알리는 헤더. 캐시는 그 헤더를 캐시 키에 포함해야 한다. 〔[제10장](10-cors-leak.md)〕

### W

- **WAF**(Web Application Firewall, 웹 애플리케이션 방화벽) — HTTP 요청을 규칙과 대조해 악성 패턴을 차단하는 중간 장치. 규칙은 대개 문자열·정규식 매칭이다. 〔[제7장](07-url-normalization.md)〕
- **WebVTT**(Web Video Text Tracks) — 자막·캡션을 담는 텍스트 형식. 파일이 `WEBVTT` 로 시작하고, 그 뒤에 **큐(cue)** — 시작 시각·종료 시각·본문 — 가 이어진다. 〔[제27장](27-affine-time-mapping.md)〕
- **wraparound / wrap-around**(래핑, 되감김) — 카운터가 표현 범위의 끝에서 0 으로 되돌아가는 것. 33비트 90kHz PTS 는 약 **26.5시간마다** 래핑하며, [제18장](18-cc-counter-limits.md)의 4비트 연속성 카운터(0~15 순환)와 폭만 다른 같은 현상이다. 〔[제21장](21-pts-and-90khz.md) · [제28장](28-33bit-wrap.md)〕

### X

- **X-TIMESTAMP-MAP** — HLS 가 WebVTT 파일 헤더에 두는 대응표. `X-TIMESTAMP-MAP=LOCAL:<자막 시각>,MPEGTS:<90kHz 클럭값>` 형식으로, 자막의 `LOCAL` 시각이 영상 타임라인의 `MPEGTS` 클럭값에 해당한다는 한 쌍의 대응을 선언한다. 〔[제27장](27-affine-time-mapping.md) · [제38장](38-baseline-contamination.md)〕

---

## C.4 본문에 정의 없이 쓰인 핵심어 (추가 †)

어느 장·부록도 `> **용어** —` 로 정식 정의하지 않았으나, 다른 정의 안에서 이름만 등장하며 이해에 필요한 낱말이다. **†** 는 이 용어집이 보충한 항목임을 뜻한다.

- **† HMAC**(Hash-based Message Authentication Code, 해시 기반 메시지 인증 코드) — 해시 함수와 비밀 키로 MAC 을 만드는 표준 구성(RFC 2104). 안쪽 해시의 출력을 다시 키와 함께 해시하므로 [제11장](11-signed-url.md)의 길이 확장 공격이 성립하지 않는다. 제11장이 다루는 서명 URL 의 `md5=` 가 원래 있어야 할 자리다.
- **† PAT · PMT**(Program Association Table · Program Map Table) — MPEG-TS 안에 실려 다니는 제어 테이블. PAT 는 스트림에 어떤 프로그램이 있는지를, PMT 는 그 프로그램의 영상·오디오·자막이 각각 어느 PID 에 실리는지를 정한다. [제17장](17-mpegts-packet.md)의 PID 정의가 "의미 배정은 PAT·PMT 가 정한다"고 참조한다.
