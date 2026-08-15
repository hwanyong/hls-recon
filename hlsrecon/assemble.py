"""재조립 계층 — 실제 컨테이너 작업은 전부 ffmpeg 에 위임한다.

세그먼트 병합·복호화·타임스탬프 정규화는 ffmpeg 의 hls/mpegts demuxer 가
이미 규격대로 구현하고 있으므로 여기서 다시 만들지 않는다. 이 모듈의 책임은
"어떤 인자로 위임할지"와 "진행 상황을 어떻게 계측할지" 뿐이다.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Callable, Iterable

from .probe import input_args, require

# 컨테이너별 추가 인자. 재인코딩은 어느 경우에도 하지 않는다(-c copy).
_CONTAINER_ARGS: dict[str, list[str]] = {
    # ADTS 헤더가 붙은 AAC 를 MP4 의 ASC 형식으로 바꾸는 비트스트림 필터.
    #
    # 정직하게 적어 둔다. **ffmpeg 8.1.1 에서 실측하면 mov 먹서가 이 필터를 스스로
    # 끼워 넣는다** — verbose 로그에 "Automatically inserted bitstream filter
    # 'aac_adtstoasc'" 가 찍히고, 명시한 출력과 명시하지 않은 출력의 오디오
    # 페이로드 md5 가 같다. 즉 이 인자의 현재 이득은 측정되지 않는다.
    #
    # 그래도 남겨 두는 이유는 probe.py 의 확장자 열거와 같다 — 이 도구는 ffmpeg
    # 버전을 고정하지 않으므로 먹서의 자동 삽입에 기대고 싶지 않다.
    ".mp4": ["-bsf:a", "aac_adtstoasc", "-movflags", "+faststart"],
    ".m4v": ["-bsf:a", "aac_adtstoasc", "-movflags", "+faststart"],
    ".mkv": [],
    ".ts": [],
}


def supported_containers() -> tuple[str, ...]:
    return tuple(_CONTAINER_ARGS)


def container_args(out: Path) -> list[str]:
    return _CONTAINER_ARGS.get(out.suffix.lower(), [])


def _run_with_progress(
    cmd: list[str], on_progress: Callable[[float], None] | None
) -> None:
    """-progress 파이프로 out_time_ms 를 읽어 진행 초를 콜백한다."""
    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1
    )
    assert proc.stdout is not None
    for line in proc.stdout:
        if on_progress and line.startswith("out_time_ms="):
            raw = line.strip().split("=", 1)[1]
            if raw.isdigit():
                on_progress(int(raw) / 1_000_000)
    proc.wait()
    if proc.returncode != 0:
        err = (proc.stderr.read() if proc.stderr else "").strip()
        raise RuntimeError(f"ffmpeg 실패 (exit {proc.returncode})\n{err[-2000:]}")


def _stream_args(subs: tuple[list[str], list[str], str] | None) -> list[str]:
    """자막 내장 여부에 따른 매핑·코덱 인자. subs 는 subtitles.embed_args() 의 반환."""
    if not subs:
        return ["-map", "0", "-c", "copy"]
    _, maps, codec = subs
    return [*maps, "-c", "copy", "-c:s", codec]


def remux_from_url(
    url: str,
    out: Path,
    headers: dict[str, str] | None = None,
    on_progress: Callable[[float], None] | None = None,
    subs: tuple[list[str], list[str], str] | None = None,
) -> list[str]:
    """플레이리스트 URL 을 ffmpeg 에 직접 물려 재조립한다 (기본 경로).

    AES-128 복호화, 토큰 URL, 리다이렉션, 세그먼트 재시도를 ffmpeg 가 처리한다.
    subs 가 주어지면 자막 플레이리스트를 추가 입력으로 붙여 한 파일로 먹싱한다.
    """
    cmd = [require("ffmpeg"), "-hide_banner", "-loglevel", "error", "-y"]
    cmd += input_args(headers, url)
    cmd += ["-i", url]
    if subs:
        cmd += subs[0]
    cmd += _stream_args(subs)
    cmd += container_args(out)
    cmd += ["-progress", "pipe:1", str(out)]
    _run_with_progress(cmd, on_progress)
    return cmd


def concat_segments(paths: Iterable[Path], raw_out: Path) -> int:
    """내려받은 세그먼트를 바이트 단위로 이어붙인다.

    MPEG-TS 는 자기동기(self-synchronizing) 포맷이라 단순 연결이 규격상 유효하고,
    fMP4 는 호출자가 init segment(EXT-X-MAP)를 목록 맨 앞에 넣어주면 동일하게 성립한다.
    """
    total = 0
    with raw_out.open("wb") as fh:
        for p in paths:
            data = p.read_bytes()
            fh.write(data)
            total += len(data)
    return total


def remux_local(
    raw: Path,
    out: Path,
    on_progress: Callable[[float], None] | None = None,
    subs: tuple[list[str], list[str], str] | None = None,
) -> list[str]:
    """이어붙인 원본을 최종 컨테이너로 무손실 먹싱한다.

    자막 입력은 subtitles.embed_args() 가 자기 입력 옵션까지 담아 돌려주므로
    여기서는 그대로 이어 붙이기만 한다.
    """
    cmd = [
        require("ffmpeg"), "-hide_banner", "-loglevel", "error", "-y",
        "-fflags", "+genpts",  # 세그먼트 연결부의 PTS 결손을 보정
        "-i", str(raw),
    ]
    if subs:
        cmd += subs[0]
    cmd += _stream_args(subs)
    cmd += container_args(out)
    cmd += ["-progress", "pipe:1", str(out)]
    _run_with_progress(cmd, on_progress)
    return cmd
