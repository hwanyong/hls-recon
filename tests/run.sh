#!/usr/bin/env bash
# hls-recon 회귀 테스트.
#
# 로컬에 HLS 스트림 4종을 만들어 정상 케이스가 PASS 로 나오는지 확인하고,
# 결함 3종을 주입해 실제로 FAIL 로 잡히는지 확인한다.
# 검증 도구가 PASS 만 낸다면 아무것도 검증하지 못하는 것과 같으므로,
# "결함을 잡는가"가 이 스크립트의 핵심이다.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RECON="$ROOT/hls-recon"
WORK="${TMPDIR:-/tmp}/hls-recon-tests"
PORT="${PORT:-8899}"
BASE="http://127.0.0.1:$PORT"

pass=0; fail=0
ok()   { printf '  \033[32m✓\033[0m %s\n' "$1"; pass=$((pass+1)); }
bad()  { printf '  \033[31m✗\033[0m %s\n' "$1"; fail=$((fail+1)); }
head_() { printf '\n\033[1m%s\033[0m\n' "$1"; }

for tool in ffmpeg ffprobe python3; do
  command -v "$tool" >/dev/null || { echo "필수 도구 없음: $tool"; exit 1; }
done

cleanup() {
  for pid in "${SERVER_PID:-}" "${GZIP_PID:-}"; do
    [[ -n "$pid" ]] && kill "$pid" 2>/dev/null || true
  done
}
trap cleanup EXIT

# ---------------------------------------------------------------- 자산 생성
head_ "[1/4] 테스트 스트림 생성"
rm -rf "$WORK"; mkdir -p "$WORK"/{plain,enc,fmp4,multi,out,subko,suben,subbad}
cd "$WORK"

ffmpeg -v error -y \
  -f lavfi -i "testsrc2=size=640x360:rate=30:duration=30" \
  -f lavfi -i "sine=frequency=440:duration=30" \
  -c:v libx264 -preset ultrafast -g 60 -keyint_min 60 -sc_threshold 0 -pix_fmt yuv420p \
  -c:a aac -b:a 128k source.mp4

ffmpeg -v error -y -i source.mp4 -c copy -f hls -hls_time 6 -hls_playlist_type vod \
  -hls_segment_filename "plain/seg%03d.ts" plain/index.m3u8

head -c 16 /dev/urandom > enc/enc.key
printf '%s/enc/enc.key\n%s/enc/enc.key\n' "$BASE" "$WORK" > enc/keyinfo
ffmpeg -v error -y -i source.mp4 -c copy -f hls -hls_time 6 -hls_playlist_type vod \
  -hls_key_info_file enc/keyinfo -hls_segment_filename "enc/seg%03d.ts" enc/index.m3u8

ffmpeg -v error -y -i source.mp4 -c copy -f hls -hls_time 6 -hls_playlist_type vod \
  -hls_segment_type fmp4 -hls_fmp4_init_filename "init.mp4" \
  -hls_segment_filename "fmp4/seg%03d.m4s" fmp4/index.m3u8

ffmpeg -v error -y -i source.mp4 -filter_complex "[0:v]scale=320:180[v0]" \
  -map "[v0]" -map 0:a -c:v libx264 -preset ultrafast -b:v 400k -c:a aac -b:a 64k \
  -f hls -hls_time 6 -hls_playlist_type vod -hls_segment_filename "multi/low%03d.ts" multi/low.m3u8
cp plain/*.ts multi/; cp plain/index.m3u8 multi/high.m3u8
cat > multi/master.m3u8 <<'EOF'
#EXTM3U
#EXT-X-VERSION:3
#EXT-X-STREAM-INF:PROGRAM-ID=1,BANDWIDTH=1400000,RESOLUTION=640x360,NAME="360p",CODECS="avc1.42c01e,mp4a.40.2"
high.m3u8
#EXT-X-STREAM-INF:PROGRAM-ID=1,BANDWIDTH=480000,RESOLUTION=320x180,NAME="180p",CODECS="avc1.42c00f,mp4a.40.2"
low.m3u8
EOF
echo "  평문 TS / AES-128 / fMP4 / 멀티 variant 준비 완료"

# 자막 트랙. ffmpeg 의 HLS muxer 는 WebVTT 를 세그먼트화하지 못하므로,
# 실제 CDN 이 내보내는 형태 그대로 직접 만든다. 걸치는 큐를 양쪽 조각에 넣는
# 것까지 재현해야 경계 중복 제거가 실제로 검증된다.
python3 - <<'PY'
import pathlib, subprocess

raw = subprocess.run(
    ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "packet=pts_time",
     "-of", "csv=p=0", "plain/seg000.ts"], capture_output=True, text=True).stdout.split()[0]
base = int(round(float(raw.strip().rstrip(",")) * 90000))   # 영상 첫 PTS (90kHz)

def ts(sec):
    h, r = divmod(sec, 3600); m, s = divmod(r, 60)
    return f"{int(h):02d}:{int(m):02d}:{s:06.3f}"

CUES = {
    "subko":  [(i * 5, i * 5 + 4, f"한국어 자막 {i+1}번") for i in range(6)],
    "suben":  [(i * 5, i * 5 + 4, f"English subtitle line {i+1}") for i in range(6)],
    "subbad": [(i * 5, i * 5 + 4, f"어긋난 자막 {i+1}번") for i in range(6)],
}
# subbad 는 X-TIMESTAMP-MAP 기준을 60초 어긋나게 잡아 자막이 영상 범위를 벗어나게 만든다.
# 음수로 만들면 안 된다 — 33비트 부호 없는 PTS 에 음수는 무효라 timestamp_offset 이
# None 을 돌려주고(subtitles.py:208-210), 보정을 아예 걸지 않아 결함이 주입되지 않는다.
OFFSET = {"subko": 0, "suben": 0, "subbad": 60 * 90000}
SEG, COUNT = 6.0, 5

for name, cues in CUES.items():
    d = pathlib.Path(name); d.mkdir(exist_ok=True)
    pl = ["#EXTM3U", "#EXT-X-VERSION:3", f"#EXT-X-TARGETDURATION:{int(SEG)}",
          "#EXT-X-MEDIA-SEQUENCE:0", "#EXT-X-PLAYLIST-TYPE:VOD"]
    for i in range(COUNT):
        lo, hi = i * SEG, (i + 1) * SEG
        body = ["WEBVTT", f"X-TIMESTAMP-MAP=LOCAL:00:00:00.000,MPEGTS:{base + OFFSET[name]}", ""]
        for s, e, text in cues:
            if e > lo and s < hi:                      # 경계에 걸치면 양쪽에 넣는다
                body += [f"{ts(s)} --> {ts(e)}", text, ""]
        (d / f"seg{i:03d}.vtt").write_text("\n".join(body), encoding="utf-8")
        pl += [f"#EXTINF:{SEG:.5f},", f"seg{i:03d}.vtt"]
    pl.append("#EXT-X-ENDLIST")
    (d / "index.m3u8").write_text("\n".join(pl) + "\n", encoding="utf-8")

def master(path, tracks):
    out = ["#EXTM3U", "#EXT-X-VERSION:3"]
    for group, lang, nm, extra in tracks:
        out.append(
            f'#EXT-X-MEDIA:TYPE=SUBTITLES,GROUP-ID="subs",NAME="{nm}",LANGUAGE="{lang}",'
            f'AUTOSELECT=YES,{extra}URI="{group}/index.m3u8"'
        )
    out += ['#EXT-X-STREAM-INF:PROGRAM-ID=1,BANDWIDTH=1400000,RESOLUTION=640x360,'
            'SUBTITLES="subs",CODECS="avc1.42c01e,mp4a.40.2"', "plain/index.m3u8"]
    pathlib.Path(path).write_text("\n".join(out) + "\n", encoding="utf-8")

master("master-subs.m3u8", [
    ("subko", "ko", "한국어", "DEFAULT=YES,"),
    ("suben", "en", "English", 'CHARACTERISTICS="public.accessibility.transcribes-spoken-dialog",'),
])
master("master-badsub.m3u8", [("subbad", "xx", "어긋난자막", "DEFAULT=YES,")])
print("  자막 트랙: ko / en(SDH) / 타임스탬프 어긋난 트랙")
PY

# 결함 주입본
cp -R plain damaged
python3 - <<'PY'
import pathlib
d = pathlib.Path("damaged")
p = d / "seg002.ts"                       # 결함 1: TS 패킷 12개 제거 → CC 점프
raw = p.read_bytes()
cut = (len(raw) // 188 // 2) * 188
p.write_bytes(raw[:cut] + raw[cut + 188 * 12:])
# 결함 2: 중복 송출. 아래 결함들이 건드리지 않는 seg000 을 원본으로 삼는다.
(d / "seg004.ts").write_bytes((d / "seg000.ts").read_bytes())
(d / "seg001.ts").unlink()                                      # 결함 3: 세그먼트 404
# 결함 4: 만료 토큰에 오류 페이지를 200 으로 돌려주는 CDN 재현
(d / "seg003.ts").write_bytes(
    b"<!DOCTYPE html><html><body><h1>403 Forbidden</h1>"
    b"<p>Link expired</p></body></html>\n"
)
PY
echo "  결함 주입: 패킷 유실 / 세그먼트 중복 / 세그먼트 404 / 200-오류페이지"

python3 -m http.server "$PORT" --bind 127.0.0.1 >/dev/null 2>&1 &
SERVER_PID=$!
# 압축 응답 경로는 기본 http.server 로 재현되지 않아 전용 서버를 따로 띄운다.
GZIP_PORT=$((PORT + 1))
python3 "$ROOT/tests/gzip_server.py" "$GZIP_PORT" "$WORK" >/dev/null 2>&1 &
GZIP_PID=$!
sleep 1.5
curl -sf -o /dev/null "$BASE/plain/index.m3u8" || { echo "HTTP 서버 기동 실패"; exit 1; }
curl -sf -o /dev/null "http://127.0.0.1:$GZIP_PORT/plain/index.m3u8" \
  || { echo "gzip 서버 기동 실패"; exit 1; }

# ---------------------------------------------------------------- 정상 케이스
# 기대: 종료 코드 0 + 리포트에 FAIL 항목 없음
expect_pass() {
  local name="$1"; shift
  local log="$WORK/out/$name.log"
  if "$RECON" "$@" >"$log" 2>&1 && ! grep -q '✗' "$log"; then
    ok "$name"
  else
    bad "$name — $(grep -m1 '✗' "$log" || echo '종료 코드 비정상')"
  fi
}

head_ "[2/4] 정상 스트림 — PASS 여야 한다"
expect_pass "평문TS-segments"  "$BASE/plain/index.m3u8"  -o "$WORK/out/plain.mp4"
expect_pass "AES128-복호화"    "$BASE/enc/index.m3u8"    -o "$WORK/out/enc.mp4"
expect_pass "fMP4-CMAF"        "$BASE/fmp4/index.m3u8"   -o "$WORK/out/fmp4.mp4"
expect_pass "마스터-variant선택" "$BASE/multi/master.m3u8" -o "$WORK/out/multi.mkv" --height 180
expect_pass "remux-위임"       "$BASE/plain/index.m3u8"  -o "$WORK/out/remux.mp4" --mode remux
expect_pass "구조조사"          "$BASE/multi/master.m3u8" --probe-only

# 압축 응답. 풀지 않으면 플레이리스트가 바이너리로 보여 '#EXTM3U 없음'으로 죽는다.
GLOG="$WORK/out/gzip.log"
set +e
"$RECON" "http://127.0.0.1:$GZIP_PORT/plain/index.m3u8" -o "$WORK/out/gzip.mp4" \
  --no-decode-check >"$GLOG" 2>&1
gcode=$?
set -e
[[ $gcode -eq 0 ]] && ! grep -q '✗' "$GLOG" \
  && ok "gzip 플레이리스트 처리" || bad "gzip 처리 실패: $(grep -m1 -E '✗|Error|error' "$GLOG" || echo "exit $gcode")"
# 압축을 요청조차 하지 않으면 이 경로는 애초에 검증되지 않는다.
curl -s -H 'Accept-Encoding: identity' -o /dev/null -D - \
  "http://127.0.0.1:$GZIP_PORT/plain/index.m3u8" | grep -qi 'content-encoding: gzip' \
  && ok "테스트 서버가 실제로 압축 응답" || bad "테스트 서버가 압축하지 않음"

# 플레이리스트가 아닌 응답이 왔을 때. 스택 트레이스가 아니라 무엇이 왔는지 알려야 한다.
printf '<!DOCTYPE html><html><body><h1>403 Forbidden</h1></body></html>\n' > "$WORK/expired.m3u8"
: > "$WORK/emptypl.m3u8"
DIAG="$WORK/out/diag.log"
set +e
"$RECON" "$BASE/expired.m3u8" --probe-only >"$DIAG" 2>&1
dcode=$?
set -e
grep -q 'Traceback' "$DIAG" && bad "스택 트레이스가 노출됨" || ok "스택 트레이스 없이 종료"
grep -q '웹 페이지가 왔다' "$DIAG" && ok "HTML 응답 원인 진단" || bad "HTML 응답 진단 실패"
grep -q '선두 바이트' "$DIAG" && ok "수신 내용 제시" || bad "수신 내용 미제시"
grep -q 'Referer' "$DIAG" && ok "해결 방법 안내" || bad "해결 방법 미안내"
[[ $dcode -ne 0 ]] && ok "실패 시 0 이 아닌 종료 코드" || bad "실패인데 종료 코드 0"

set +e
"$RECON" "$BASE/emptypl.m3u8" --probe-only >"$WORK/out/diag2.log" 2>&1
set -e
grep -q '본문이 비어 있다' "$WORK/out/diag2.log" \
  && ok "빈 응답 원인 진단" || bad "빈 응답 진단 실패"

# ---------------------------------------------------------------- 자막
head_ "[2b/4] 자막 — 추출·중복정리·내장"
SLOG="$WORK/out/subs.log"
set +e
"$RECON" "$BASE/master-subs.m3u8" -o "$WORK/out/subs.mp4" --subs all \
  --no-decode-check >"$SLOG" 2>&1
set -e
grep -q 'ko · 한국어 \[default\]' "$SLOG" && ok "자막 트랙 인지 (언어·플래그)" || bad "자막 트랙 미인지"
grep -q 'SDH' "$SLOG" && ok "SDH 특성 인지" || bad "SDH 미인지"
[[ -s "$WORK/out/subs.ko.vtt" && -s "$WORK/out/subs.en.vtt" ]] \
  && ok "자막 파일 2개 생성" || bad "자막 파일 누락"
# 원본은 트랙당 6큐. 경계 중복이 남아 있으면 9큐가 된다.
kocues=$(grep -c -- '-->' "$WORK/out/subs.ko.vtt" || true)
[[ "$kocues" -eq 6 ]] && ok "경계 중복 제거 (6큐)" || bad "큐 수가 6이 아님: $kocues"
grep -q 'WEBVTT' <(tail -n +2 "$WORK/out/subs.ko.vtt") \
  && bad "본문에 조각 헤더가 남음" || ok "조각 헤더 정제"
grep -q '자막 타임라인.*영상 범위 내' "$SLOG" && ok "자막 타임라인 정합" || bad "타임라인 검사 실패"

# SubRip 변환과 컨테이너 내장
"$RECON" "$BASE/master-subs.m3u8" -o "$WORK/out/srt.mp4" --subs ko --sub-format srt \
  --no-decode-check --no-gap-scan >"$WORK/out/srt.log" 2>&1
[[ -s "$WORK/out/srt.ko.srt" ]] && grep -q '^1$' "$WORK/out/srt.ko.srt" \
  && ok "SubRip 변환 (번호 재부여)" || bad "SubRip 변환 실패"

"$RECON" "$BASE/master-subs.m3u8" -o "$WORK/out/embed.mkv" --subs all --sub-embed \
  --no-decode-check --no-gap-scan >"$WORK/out/embed.log" 2>&1
subcount=$(ffprobe -v error -select_streams s -show_entries stream=index -of csv=p=0 \
  "$WORK/out/embed.mkv" | grep -c . || true)
[[ "$subcount" -eq 2 ]] && ok "컨테이너 내장 (2트랙)" || bad "내장 트랙 수: $subcount"
ffprobe -v error -select_streams s:0 -show_entries stream_tags=language -of csv=p=0 \
  "$WORK/out/embed.mkv" | grep -q ko && ok "내장 언어 메타데이터" || bad "언어 메타데이터 누락"

# ------------------------------------------------------- 사이드카 자막 (URL 조립)
# 플레이리스트에 자막 선언이 없는 송출. 이름과 origin 으로 URL 을 만들어 받는다.
# 한글·화수 표기를 그대로 쓰는 것은 URL 인코딩과 이름 후보 생성까지 함께 고정하기
# 위해서다 — 실제로 마주친 경로가 그 형태였다.
head_ "[2c/4] 사이드카 자막 — 플레이리스트 밖 파일"
mkdir -p "$WORK/subtitles/old"
WORK="$WORK" python3 - <<'PY'
import os, pathlib
work = pathlib.Path(os.environ["WORK"]) / "subtitles" / "old"
cue = "1\n00:00:01,000 --> 00:00:03,000\n첫 줄\n\n2\n00:00:04,000 --> 00:00:06,000\n둘째 줄\n"
for name in ("에피소드01", "에피소드02"):
    (work / f"{name}.srt").write_text("﻿" + cue.replace("\n", "\r\n"), encoding="utf-8")
# 200 으로 오지만 자막이 아닌 응답. 이것을 자막으로 저장하면 안 된다.
(work / "함정01.srt").write_text("<!DOCTYPE html><html><body>404</body></html>\n", encoding="utf-8")
PY

CLOG="$WORK/out/sidecar.log"
set +e
"$RECON" "$BASE/plain/index.m3u8" -o "$WORK/out/에피소드01.mp4" \
  --sub-guess --sub-origin "$BASE" --sub-format srt --sub-range 01-02 \
  --no-decode-check --no-gap-scan --report "$WORK/out/sidecar.json" >"$CLOG" 2>&1
set -e
grep -q '자막 추출.*사이드카' "$CLOG" && ok "사이드카 URL 조립·수신" || bad "사이드카 수신 실패"
# 출력은 화수를 떼어낸 시리즈 폴더 아래에 놓인다.
[[ -f "$WORK/out/에피소드/에피소드01.mp4" ]] \
  && ok "시리즈 폴더 자동 배치" || bad "시리즈 폴더에 놓이지 않음"
# 받은 파일은 완성본이라 손대지 않는다 — 서버 원본과 바이트가 같아야 한다.
cmp -s "$WORK/out/에피소드/에피소드01.srt" "$WORK/subtitles/old/에피소드01.srt" \
  && ok "원본 바이트 보존 (BOM·CRLF 포함)" || bad "받은 자막이 원본과 다름"
grep -q '자막 일괄 수집.*1/1개' "$CLOG" && ok "이웃 화수 수집" || bad "화수 확장 실패"

# 이름 표기가 어긋나도 후보를 만들어 찾아낸다 (에피소드1 → 에피소드01).
set +e
"$RECON" "$BASE/plain/index.m3u8" -o "$WORK/out/에피소드1.mp4" \
  --sub-guess --sub-origin "$BASE" --sub-format srt \
  --no-decode-check --no-gap-scan >"$WORK/out/sidecar2.log" 2>&1
set -e
grep -q 'old/%EC%97%90%ED%94%BC%EC%86%8C%EB%93%9C01.srt' "$WORK/out/sidecar2.log" \
  && ok "화수 표기 차이 흡수 (1 → 01)" || bad "이름 후보 생성 실패"

# 200 이지만 HTML 인 응답. 헤더가 아니라 선두 내용으로 걸러야 한다.
set +e
"$RECON" "$BASE/plain/index.m3u8" -o "$WORK/out/함정01.mp4" \
  --sub-guess --sub-origin "$BASE" --sub-format srt \
  --no-decode-check --no-gap-scan >"$WORK/out/sidecar3.log" 2>&1
set -e
[[ ! -e "$WORK/out/함정/함정01.srt" ]] && ok "자막 아닌 200 응답 거부" || bad "HTML 을 자막으로 저장함"
grep -q '후보 .*개 모두 실패' "$WORK/out/sidecar3.log" \
  && ok "실패를 후보 목록과 함께 보고" || bad "실패 보고 누락"

# --limit 표본은 영상만 잘리므로 자막 타임라인 검사의 기준선이 성립하지 않는다.
set +e
"$RECON" "$BASE/plain/index.m3u8" -o "$WORK/out/표본01.mp4" --limit 1 \
  --sub-guess --sub-origin "$BASE" --sub-name 에피소드01 --sub-format srt \
  --no-decode-check --no-gap-scan >"$WORK/out/sidecar4.log" 2>&1
set -e
grep -q '자막 타임라인.*판정 보류' "$WORK/out/sidecar4.log" \
  && ok "표본 실행에서 타임라인 판정 보류" || bad "표본인데 타임라인을 판정함"

# ---------------------------------------------------------------- 보관 구조
# 기대: 회차물만 시리즈 폴더로 모이고, 영화 한 편은 제자리에 남는다.
head_ "[2d/4] 보관 구조 — 시리즈 폴더와 되모으기"

set +e
"$RECON" "$BASE/plain/index.m3u8" -o "$WORK/out/평면01.mp4" --flat \
  --no-decode-check --no-gap-scan >"$WORK/out/flat.log" 2>&1
set -e
[[ -f "$WORK/out/평면01.mp4" ]] && ok "--flat 은 폴더를 만들지 않는다" || bad "--flat 인데 폴더로 옮김"

TIDY="$WORK/tidy"
rm -rf "$TIDY"; mkdir -p "$TIDY/이미정리됨"
for n in 01 02; do : >"$TIDY/모아모아${n}.mp4"; : >"$TIDY/모아모아${n}.srt"; done
: >"$TIDY/외톨이01.mp4"                 # 혼자뿐인 회차 — 폴더로 감싸지 않는다
: >"$TIDY/Sky.Blue.2003.1080p.mkv"      # 끝이 연도·화질 — 화수가 아니다
: >"$TIDY/목록.m3u8"                    # 미디어가 아니다
: >"$TIDY/이미정리됨/모아모아09.mp4"

"$RECON" --tidy "$TIDY" >"$WORK/out/tidy1.log" 2>&1
[[ -f "$TIDY/모아모아01.mp4" && ! -d "$TIDY/모아모아" ]] \
  && ok "미리보기는 파일을 옮기지 않는다" || bad "--apply 없이 이동함"

"$RECON" --tidy "$TIDY" --apply >"$WORK/out/tidy2.log" 2>&1
[[ -f "$TIDY/모아모아/모아모아01.mp4" && -f "$TIDY/모아모아/모아모아02.srt" ]] \
  && ok "회차와 곁파일을 함께 모은다" || bad "시리즈 폴더로 모이지 않음"
[[ -f "$TIDY/외톨이01.mp4" && -f "$TIDY/Sky.Blue.2003.1080p.mkv" && -f "$TIDY/목록.m3u8" ]] \
  && ok "단독 회차·영화·비미디어는 건드리지 않는다" || bad "옮기지 말아야 할 것을 옮김"
[[ -f "$TIDY/이미정리됨/모아모아09.mp4" ]] \
  && ok "하위 폴더는 정리 대상이 아니다" || bad "하위 폴더를 건드림"

# 같은 이름이 이미 있으면 덮어쓰지 않는다 — 되돌릴 수 없는 손실이기 때문이다.
: >"$TIDY/모아모아01.mp4"; : >"$TIDY/모아모아02.mp4"
"$RECON" --tidy "$TIDY" --apply >"$WORK/out/tidy3.log" 2>&1
[[ -f "$TIDY/모아모아01.mp4" ]] && grep -q '같은 이름이 이미 있다' "$WORK/out/tidy3.log" \
  && ok "이름 충돌은 건너뛴다" || bad "충돌인데 덮어씀"

# ------------------------------------------------------------------- 재고 조사
# 두 번째 실행에서 '빠진 회차'만 가려내는 판단. 여기서 잘못 짚으면 증상이 정반대로
# 갈린다 — 너무 관대하면 깨진 파일이 완성본 행세를 해 회차가 영원히 빠지고,
# 너무 엄격하면 멀쩡한 27화를 매번 다시 받는다. 양쪽을 함께 고정한다.
head_ "[2e/4] 재고 조사 — 빠진 회차 가려내기"

STOCK="$WORK/stock/그렌라간"
rm -rf "$WORK/stock"; mkdir -p "$STOCK"
# 온전한 회차 둘 — 하나는 faststart(moov 앞), 하나는 기본(moov 뒤). 둘 다 정상이다.
ffmpeg -v error -y -i source.mp4 -t 5 -c copy -movflags +faststart "$STOCK/그렌라간01.mp4"
ffmpeg -v error -y -i source.mp4 -t 5 -c copy "$STOCK/그렌라간02.mp4"
# 화수 표기가 다른 회차(`3` vs `03`)와 컨테이너가 다른 회차(.mkv) — 같은 회차여야 한다.
ffmpeg -v error -y -i source.mp4 -t 5 -c copy "$STOCK/그렌라간3.mp4"
ffmpeg -v error -y -i source.mp4 -t 5 -c copy "$STOCK/그렌라간04.mkv"
# 먹싱 도중 끊긴 회차 — 있지만 온전하지 않다.
python3 - "$STOCK" <<'PY'
import sys, pathlib
d = pathlib.Path(sys.argv[1])
whole = (d / "그렌라간02.mp4").read_bytes()
(d / "그렌라간05.mp4").write_bytes(whole[: len(whole) * 6 // 10])
(d / "그렌라간06.mp4").write_bytes(b"")
PY
for n in 01 02 3 04; do : >"$STOCK/그렌라간${n}.ko.srt"; done

INV="$WORK/out/inventory.txt"
python3 - "$ROOT" "$STOCK" >"$INV" <<'PY'
import sys, pathlib
sys.path.insert(0, sys.argv[1])
from hlsrecon import inventory

folder = pathlib.Path(sys.argv[2])
groups = inventory.scan(folder)
stock, note = inventory.stock_for(groups, "천원돌파 그렌라간")
for n in sorted(stock):
    it = stock[n]
    print(f"EP {n} {it.video.name} ok={it.ok} subs={len(it.subs)} flaw={it.flaw}")
print(f"NOTE {note}")
print(f"GAPS {inventory.subtitle_gaps(stock)}")

# --flat 으로 여러 작품이 한 폴더에 섞인 경우. 작품명이 두 무리에 다 걸리면
# 번호만으로는 어느 쪽이 내 회차인지 알 수 없다 — 남의 회차를 근거로 건너뛰면
# 회차가 조용히 빠지므로, 가리지 못할 때는 건너뛰지 않는 편이 옳다.
mixed = folder.parent / "mixed"
mixed.mkdir(exist_ok=True)
whole = (folder / "그렌라간01.mp4").read_bytes()
for stem in ("다른작품", "또다른작품"):
    for n in ("01", "02"):
        (mixed / f"{stem}{n}.mp4").write_bytes(whole)
# 작품명이 어느 줄기와도 같지 않고 두 줄기 모두에 들어 있다 — 우열이 없다.
picked, why = inventory.stock_for(inventory.scan(mixed), "작품")
print(f"MIXED {len(picked)} {why}")

# 반대로 우열이 있으면 가려내야 한다. 모호할 때 포기하는 규칙이 '항상 포기한다'로
# 굳으면 --flat 에서는 재고 조사가 통째로 죽은 코드가 된다.
alone, _ = inventory.stock_for(inventory.scan(mixed), "또다른작품 시즌2")
print(f"ALONE {len(alone)}")
PY

grep -q 'EP 1 그렌라간01.mp4 ok=True' "$INV" \
  && ok "정상 회차를 온전하다고 본다 (faststart)" || bad "정상 파일을 손상으로 오인 (faststart)"
grep -q 'EP 2 그렌라간02.mp4 ok=True' "$INV" \
  && ok "정상 회차를 온전하다고 본다 (moov 뒤)" || bad "정상 파일을 손상으로 오인 (moov 뒤)"
grep -q 'EP 3 그렌라간3.mp4 ok=True' "$INV" \
  && ok "화수 표기 차이를 같은 회차로 (3 = 03)" || bad "화수 표기가 다르면 못 알아봄"
grep -q 'EP 4 그렌라간04.mkv ok=True' "$INV" \
  && ok "컨테이너가 달라도 같은 회차로 (.mkv)" || bad "확장자가 다르면 못 알아봄"
grep -q 'EP 5 .* ok=False' "$INV" \
  && ok "잘린 파일을 손상으로 검출" || bad "잘린 파일을 완성본으로 오인"
grep -q 'EP 6 .* ok=False' "$INV" \
  && ok "0바이트 파일을 손상으로 검출" || bad "0바이트를 완성본으로 오인"
grep -q "NOTE '그렌라간'" "$INV" \
  && ok "작품명이 달라도 파일 무리를 찾는다 (천원돌파 그렌라간 → 그렌라간)" \
  || bad "작품명과 파일 줄기를 잇지 못함"
grep -q 'MIXED 0' "$INV" \
  && ok "작품명이 여러 무리에 걸리면 번호로 건너뛰지 않는다" || bad "남의 회차를 근거로 건너뜀"
grep -q 'ALONE 2' "$INV" \
  && ok "한 무리에만 걸리면 가려낸다 (--flat 에서도 동작)" || bad "가릴 수 있는데도 포기함"

# --------------------------------------------------------------- 자막 메우기
# 영상은 멀쩡한데 자막만 없는 회차. 영상을 다시 받지 않고 자막만 받아 메운다.
# 실제 추출 경로(_extract_subs)를 그대로 타야 의미가 있으므로, 재생 소스 해석만
# 대역으로 바꿔 끼우고 나머지는 전부 진짜 코드로 돌린다.
head_ "[2f/4] 자막 메우기 — 영상 없이 자막만"

FILL="$WORK/fill/메움"
rm -rf "$WORK/fill"; mkdir -p "$FILL"
for n in 01 02 03; do
  ffmpeg -v error -y -i source.mp4 -t 5 -c copy "$FILL/메움${n}.mp4"
done
# 01·02 만 자막이 있다 → 03 이 '자막만 빠진' 회차다.
for n in 01 02; do printf 'WEBVTT\n\n00:00:01.000 --> 00:00:02.000\n기존\n' >"$FILL/메움${n}.ko.vtt"; done

REFILL="$WORK/out/refill.txt"
set +e
python3 - "$ROOT" "$FILL" "$BASE" >"$REFILL" 2>&1 <<'PY'
import pathlib, sys
sys.path.insert(0, sys.argv[1])
from hlsrecon import cli, inventory, series
from hlsrecon.fetch import Fetcher

folder, base = pathlib.Path(sys.argv[2]), sys.argv[3]

# 재생 소스 해석만 대역으로 바꾼다 — 사이트가 없어도 그 뒤 경로는 진짜로 돈다.
def fake_resolve(ep, fetcher, width=2):
    return series.Play(
        playlist_url=f"{base}/master-subs.m3u8", name=f"메움{ep.number:02d}", referer=f"{base}/"
    )

series.resolve = fake_resolve

args = cli.build_parser().parse_args(["--subs", "all", "--refill-subs", "--delay", "0"])
picked = [series.Episode(number=n, title=f"{n}화", page_url=f"{base}/e/{n}") for n in (1, 2, 3)]
stock, _ = inventory.stock_for(inventory.scan(folder), "메움")
print("GAPS", inventory.subtitle_gaps(stock))
filled, failed = cli._refill_subs(args, picked, stock, {}, Fetcher(), 2)
print(f"FILLED {filled} {failed}")
PY
set -e

grep -q 'FILLED 1 0' "$REFILL" \
  && ok "자막만 빠진 회차 1개를 메웠다" || bad "메우기 결과가 예상과 다름: $(tail -3 "$REFILL")"
[[ -s "$FILL/메움03.ko.vtt" ]] \
  && ok "자막이 영상 옆에 같은 이름으로 놓인다" || bad "메움03.ko.vtt 가 생기지 않음"
fillcues=$(grep -c -- '-->' "$FILL/메움03.ko.vtt" 2>/dev/null || true)
[[ "$fillcues" -eq 6 ]] \
  && ok "메운 자막도 경계 중복이 정리된다 (6큐)" || bad "메운 자막 큐 수가 6이 아님: $fillcues"
grep -q '기존' "$FILL/메움01.ko.vtt" \
  && ok "이미 자막이 있는 회차는 건드리지 않는다" || bad "기존 자막을 덮어씀"
[[ ! -f "$FILL/메움03.mp4.part" ]] && [[ $(wc -c <"$FILL/메움03.mp4") -eq $(wc -c <"$FILL/메움01.mp4") ]] \
  && ok "영상은 다시 받지 않는다" || bad "영상을 건드림"

# ---------------------------------------------------------------- 결함 검출
# 기대: 종료 코드 2 + 해당 검사 항목이 실제로 결함을 지목
head_ "[3/4] 결함 주입 스트림 — 검출해야 한다"
DLOG="$WORK/out/damaged.log"
set +e
"$RECON" "$BASE/damaged/index.m3u8" -o "$WORK/out/damaged.mp4" --report "$WORK/out/damaged.json" >"$DLOG" 2>&1
code=$?
set -e

[[ $code -eq 2 ]] && ok "종료 코드 2 (FAIL)" || bad "종료 코드가 2가 아님: $code"
grep -q '세그먼트 수신.*실패'   "$DLOG" && ok "세그먼트 404 검출"   || bad "세그먼트 404 미검출"
grep -q 'CC 불연속'            "$DLOG" && ok "패킷 유실 검출"       || bad "패킷 유실 미검출"
grep -q '중복 해시'            "$DLOG" && ok "중복 세그먼트 검출"   || bad "중복 세그먼트 미검출"
grep -q '타임라인 연속성.*결손' "$DLOG" && ok "타임라인 결손 검출"   || bad "타임라인 결손 미검출"
grep -q '페이로드 유효성.*미디어가 아님' "$DLOG" \
  && ok "200-오류페이지 검출" || bad "200-오류페이지 미검출"

# 자막 시각이 영상 범위를 벗어나는 결함 — X-TIMESTAMP-MAP 정렬 실패에 해당한다.
BLOG="$WORK/out/badsub.log"
set +e
"$RECON" "$BASE/master-badsub.m3u8" -o "$WORK/out/badsub.mp4" --subs all \
  --no-decode-check --no-gap-scan >"$BLOG" 2>&1
bcode=$?
set -e
grep -q '자막 타임라인.*영상 범위를 벗어난' "$BLOG" \
  && ok "자막 타임스탬프 어긋남 검출 (sidecar)" || bad "자막 타임스탬프 어긋남 미검출 (sidecar)"
[[ $bcode -eq 2 ]] && ok "자막 결함도 종료 코드 2" || bad "자막 결함 종료 코드: $bcode"

# 내장 모드에서도 같은 결함을 잡아야 한다. 자막을 컨테이너에 넣으면 전체 duration 이
# 자막 끝까지 늘어나므로, 기준선을 실측으로 잡으면 이 검사는 항상 통과해 버린다.
ELOG="$WORK/out/badembed.log"
set +e
"$RECON" "$BASE/master-badsub.m3u8" -o "$WORK/out/badembed.mkv" --subs all --sub-embed \
  --no-decode-check --no-gap-scan >"$ELOG" 2>&1
ecode=$?
set -e
grep -q '자막 타임라인.*영상 범위를 벗어남' "$ELOG" \
  && ok "자막 타임스탬프 어긋남 검출 (내장)" || bad "자막 타임스탬프 어긋남 미검출 (내장)"
[[ $ecode -eq 2 ]] && ok "내장 자막 결함 종료 코드 2" || bad "내장 자막 결함 종료 코드: $ecode"

# ffmpeg 단독으로는 같은 결손을 놓친다는 사실 자체를 고정한다.
head_ "[4/4] 대조군 — ffmpeg 단독은 결손을 놓친다"
set +e
ffmpeg -v error -y -i "$BASE/damaged/index.m3u8" -c copy "$WORK/out/naive.mp4" >/dev/null 2>&1
naive=$?
set -e
if [[ $naive -eq 0 ]]; then
  ok "ffmpeg 단독 exit 0 — 결손을 보고하지 않음 (도구가 필요한 이유)"
else
  printf '  \033[33m·\033[0m ffmpeg 가 exit %s 로 실패 — 환경에 따라 다를 수 있음\n' "$naive"
fi

head_ "결과: 통과 $pass / 실패 $fail"
[[ $fail -eq 0 ]] || exit 1
