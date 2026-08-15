"""플레이리스트를 gzip 으로만 응답하는 테스트 서버.

Python 기본 http.server 는 압축을 전혀 하지 않아 이 경로를 재현하지 못한다.
실제 CDN 은 브라우저 User-Agent 를 보면 클라이언트가 무엇을 요청했든 압축해
돌려주는 경우가 있고, 그때 압축을 풀지 않으면 플레이리스트가 바이너리로 보여
'#EXTM3U 헤더가 없다'로 실패한다.

사용: python3 gzip_server.py <port> <root>
"""

import gzip
import http.server
import pathlib
import sys

ROOT = pathlib.Path(sys.argv[2] if len(sys.argv) > 2 else ".").resolve()
COMPRESSED_SUFFIXES = {".m3u8", ".vtt"}


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802 — BaseHTTPRequestHandler 규약
        target = (ROOT / self.path.lstrip("/").split("?")[0]).resolve()
        if not target.is_file() or ROOT not in target.parents and target != ROOT:
            self.send_error(404)
            return

        data = target.read_bytes()
        compress = target.suffix in COMPRESSED_SUFFIXES
        body = gzip.compress(data) if compress else data

        self.send_response(200)
        self.send_header("Content-Type", _content_type(target.suffix))
        if compress:
            # 클라이언트가 Accept-Encoding 으로 무엇을 보냈든 압축해 보낸다.
            self.send_header("Content-Encoding", "gzip")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args) -> None:
        pass


def _content_type(suffix: str) -> str:
    return {
        ".m3u8": "application/vnd.apple.mpegurl",
        ".ts": "video/mp2t",
        ".vtt": "text/vtt",
        ".mp4": "video/mp4",
        ".m4s": "video/iso.segment",
    }.get(suffix, "application/octet-stream")


if __name__ == "__main__":
    port = int(sys.argv[1])
    http.server.HTTPServer(("127.0.0.1", port), Handler).serve_forever()
