# 스트림에서 파일로

**HLS 재조립·검증 코드로 배우는 컴퓨터 과학과 웹 보안**

이 교재는 `hls-recon` 저장소의 실제 코드(15개 모듈 4,173 LOC + 회귀 테스트 525 LOC)를
교재 삼아, **웹 스트리밍을 로컬 파일로 되돌리는 과정에 필요한 컴퓨터 과학 지식과
그 과정에 내재한 보안 한계**를 다룬다.

출발점은 한 문장이다.

> **총 길이가 맞는데 중간이 비어 있다.**

`ffmpeg -i master.m3u8 -c copy out.mp4` 는 중간 세그먼트가 HTTP 404 로 빠져도 조용히
건너뛰고 종료 코드 0 으로 끝난다. 출력의 총 재생 길이조차 정상과 같다. 왜 이런 일이
가능한지 답하려면 MPEG-TS 의 표시 시각이 절대 시각이라는 사실을 알아야 하고, 그것을
알면 "총 길이 비교"라는 검증이 왜 무력한지가 따라 나온다. 이 교재는 그 연쇄를 따라간다.

---

## 읽는 방법

| 목적 | 경로 |
|---|---|
| **처음부터 제대로** | [제0장 커리큘럼](00-curriculum.md) → 제1부부터 순서대로 |
| **보안만** | 제3부(9~16장) → 제5부(23~26장) → 제8부(34~39장) |
| **비트 수준 지식만** | 제4부(17~22장) |
| **검증 방법론만** | 제8부(34~39장). 도구를 만드는 사람에게 |
| **손부터 움직이기** | [부록 A 실습 환경 구축](appendix-A-lab-setup.md) |

각 장은 **문제 → 원리 → 코드 → 일반화 → 보안** 다섯 단으로 구성된다. 모든 주장에는
`file.py:line` 형식의 코드 앵커가 붙어 있고, 그 앵커는 기계적으로 검증된다.

---

## 목차

### 제0장 — 설계

- [제0장 커리큘럼 — 지식 추출 매트릭스와 전체 설계](00-curriculum.md)

### 제1부 — 문제의 성립

- [제1장 스트림과 파일 — 두 존재론](01-stream-vs-file.md)
- [제2장 HTTP 위에서 스트리밍을 흉내내기 — ABR 과 HLS 의 발명](02-abr-and-hls.md)
- [제3장 RFC 8216 의 2계층 간접 참조](03-two-tier-indirection.md)

### 제2부 — 전송: HTTP 의 태생적 한계

- [제4장 무상태성과 무결성 보증의 부재](04-statelessness.md)
- [제5장 상태 코드의 의미론적 붕괴 — 200 은 성공이 아니다](05-status-code-collapse.md)
- [제6장 콘텐츠 협상의 부작용 — 압축, 범위, 그리고 충돌](06-content-negotiation.md)
- [제7장 URL 정규화와 멱등성 — `%20` 과 `%2520`](07-url-normalization.md)
- [제8장 병렬성·재시도·계측 — 관측하는 다운로더](08-parallel-retry-measure.md)

### 제3부 — 접근 통제와 그 한계

- [제9장 핫링크 차단의 해부 — Referer 라는 자기 신고](09-hotlink-referer.md)
- [제10장 CORS 헤더가 흘리는 것 — ACAO 의 오독과 정보 누출](10-cors-leak.md)
- [제11장 서명 URL — 시간 제한 능력의 설계](11-signed-url.md)
- [제12장 자격증명의 앰비언트 권한 — 쿠키, 프로세스 목록, 아티팩트](12-ambient-credentials.md)
- [제13장 난독화는 보안이 아니다 — packed JS 와 신뢰 경계](13-obfuscation-not-security.md)
- [제14장 세그먼트 확장자 위장 — 이름·선언·내용이 갈라질 때](14-segment-masquerading.md)
- [제15장 회피가 방어를 끄게 만들 때 — CVE-2023-6602 와 `allowed_extensions ALL`, 그리고 측정되지 않은 개선](15-evasion-disables-defense.md)
- [제16장 콘텐츠 스니핑의 양면 — 언제 미덕이고 언제 취약점인가](16-sniffing-two-faces.md)

### 제4부 — 비트 수준: 컨테이너와 무결성

- [제17장 MPEG-TS 패킷 해부 — 188바이트의 구조](17-mpegts-packet.md)
- [제18장 4비트 순환 카운터의 한계 — 검사기의 미탐률](18-cc-counter-limits.md)
- [제19장 자기동기 포맷과 연결의 대수](19-self-synchronizing.md)
- [제20장 ISO-BMFF: 재귀 TLV 구조와 구조적 완결성 검사](20-isobmff-structural.md)
- [제21장 PTS 와 90kHz — 왜 총 길이로는 결손을 못 잡는가](21-pts-and-90khz.md)
- [제22장 임계값 설계 — 중앙값의 3배, 그리고 오탐](22-threshold-design.md)

### 제5부 — 암호: 보호와 보호처럼 보이는 것

- [제23장 AES-128-CBC 와 IV 유도 규칙](23-aes-cbc-iv.md)
- [제24장 패딩 오라클의 반대편 — 왜 여기서는 예외를 던지지 않는가](24-padding-oracle-inverse.md)
- [제25장 AES-128 은 DRM 이 아니다 — 위협 모델과 Kerckhoffs 원리](25-aes128-is-not-drm.md)
- [제26장 암호화 입자가 구조를 결정한다 — SAMPLE-AES 가 거부되는 이유](26-encryption-granularity.md)

### 제6부 — 시간과 분산

- [제27장 두 시간축의 아핀 대응 — X-TIMESTAMP-MAP](27-affine-time-mapping.md)
- [제28장 33비트 래핑과 신뢰할 수 없는 입력](28-33bit-wrap.md)
- [제29장 at-least-once 와 멱등성 — 경계 중복 큐](29-at-least-once-idempotency.md)
- [제30장 위임의 경계 — 라이브러리가 하지 않는 일을 아는 것](30-delegation-boundary.md)

### 제7부 — 표현과 이식성

- [제31장 유니코드 정규화 — NFC/NFD 와 정규화 공격](31-unicode-normalization.md)
- [제32장 파일명이라는 인터페이스 — 예약 문자와 이식성](32-filename-interface.md)
- [제33장 정규식의 정확도가 곧 오분류율](33-regex-accuracy.md)

### 제8부 — 검증 방법론

- [제34장 테스트 오라클 문제 — 검증기를 검증하기](34-oracle-problem.md)
- [제35장 결함 주입 설계 — 8종의 대응표](35-fault-injection.md)
- [제36장 대조군 — "ffmpeg 은 놓친다"를 테스트로 고정하기](36-control-group.md)
- [제37장 양방향 고정 — 오탐과 미탐을 함께 테스트한다](37-bidirectional-fixing.md)
- [제38장 기준선 오염과 판정 보류](38-baseline-contamination.md)
- [제39장 판정의 종합 — 임계값에서 종료 코드까지](39-verdict-synthesis.md)

### 부록

- [부록 A — 실습 환경 구축](appendix-A-lab-setup.md)
- [부록 B — 규격 원문 대조표](appendix-B-spec-crossref.md)
- [부록 C — 용어집](appendix-C-glossary.md)
- [부록 D — 이 코드의 알려진 한계](appendix-D-known-limits.md)

### 선행 조사

- [조사 01 — 세그먼트 확장자·MIME 위장](research-01-segment-masquerading.md)
  제14·15장이 여기서 도출됐다. 조사 → 커리큘럼 반영의 실제 기록이다.

---

## 이 교재가 다루지 않는 것

- **DRM 우회.** 이 저장소는 `KEYFORMAT=identity` 인 AES-128 만 처리하고 Widevine ·
  FairPlay · PlayReady · SAMPLE-AES 를 코드 레벨에서 거부한다. 교재는 "AES-128 이 왜
  DRM 이 아닌가"를 **위협 모델의 문제로** 설명하되, 상용 보호 시스템의 키 추출 기법은
  다루지 않는다.
- **영상 코덱 내부.** 이 코드는 재인코딩을 하지 않는다(`-c copy`). 코덱은 불투명한
  바이트열로 다룬다.
- **권한 없는 콘텐츠 취득의 정당화.** 접근 통제 메커니즘을 해부하는 목적은 그것이
  어디까지 보증하고 어디부터 보증하지 못하는지를 아는 것이다. 방어자·감사자 관점에서
  읽어야 의미가 있다.

---

## 도식과 검사

모든 개념 도식은 **SVG 파일**이다(`images/`). ASCII·ANSI 아트 도식은 쓰지 않는다.
제작 규약은 [`images/_style.md`](images/_style.md) 에 있다.

이 교재는 두 개의 검사기로 스스로를 검증한다.

```bash
python3 tools/check_svg.py docs/images   # 도식: 렌더·테마 대응·접근성
python3 tools/check_docs.py docs         # 본문: 코드 앵커·상호 참조·구조·표기
```

`check_docs.py` 는 본문에 인용된 모든 `file.py:line` 앵커가 **실제 파일의 실제 줄
범위를 가리키는지** 검사한다. 코드가 바뀌면 교재가 먼저 깨지고, 그것이 드러난다.
