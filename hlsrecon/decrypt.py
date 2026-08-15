"""HLS AES-128 세그먼트 복호화 (RFC 8216 §4.3.2.4).

규격상 AES-128-CBC + PKCS7 패딩이고, IV 는 EXT-X-KEY 의 IV 속성을 쓰되
없으면 해당 세그먼트의 media sequence number 를 128비트 big-endian 으로 채운다.
키 자체는 평문 16바이트로 URI 에서 내려받는다 — DRM 이 아니라 링크 보호 수준이다.
"""

from __future__ import annotations

from .fetch import Fetcher
from .playlist import Key


class KeyCache:
    """같은 키 URI 를 세그먼트마다 다시 받지 않도록 캐시한다."""

    def __init__(self, fetcher: Fetcher) -> None:
        self._fetcher = fetcher
        self._cache: dict[str, bytes] = {}

    def material(self, key: Key) -> bytes:
        if not key.uri:
            raise ValueError("EXT-X-KEY 에 URI 가 없다")
        if key.uri not in self._cache:
            r = self._fetcher.get(key.uri)
            if not r.ok:
                raise RuntimeError(f"키 요청 실패: {key.uri}\n  {r.error}")
            if len(r.body) != 16:
                raise ValueError(f"AES-128 키 길이가 16바이트가 아니다: {len(r.body)}")
            self._cache[key.uri] = r.body
        return self._cache[key.uri]

    def decrypt(self, data: bytes, key: Key, seq: int) -> bytes:
        if not key.is_encrypted:
            return data
        if not key.is_supported:
            raise NotImplementedError(
                f"METHOD={key.method} KEYFORMAT={key.keyformat} 는 세그먼트 단위 "
                "복호화가 불가능하다 — --mode remux 로 ffmpeg 에 위임할 것"
            )

        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

        iv = key.iv if key.iv is not None else seq.to_bytes(16, "big")
        dec = Cipher(algorithms.AES(self.material(key)), modes.CBC(iv)).decryptor()
        plain = dec.update(data) + dec.finalize()
        return _unpad_pkcs7(plain)


def _unpad_pkcs7(data: bytes) -> bytes:
    if not data:
        return data
    n = data[-1]
    # 패딩이 깨졌으면(잘린 세그먼트 등) 자르지 않고 원본을 넘긴다.
    # 여기서 예외를 던지면 손상 검출이 복호화 단계에 묻혀버린다.
    if 1 <= n <= 16 and data[-n:] == bytes([n]) * n:
        return data[:-n]
    return data
