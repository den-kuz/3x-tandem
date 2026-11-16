from __future__ import annotations

import base64
import secrets
import uuid

from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)


def random_hex(hex_length: int = 16) -> str:
    nbytes = (hex_length + 1) // 2
    return secrets.token_hex(nbytes)[:hex_length]


def uuid4() -> str:
    return str(uuid.uuid4())


def reality_short_id(nbytes: int = 8) -> str:
    return secrets.token_hex(nbytes)


def _encode_key(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _decode_key(value: str) -> bytes:
    pad = "=" * ((4 - len(value) % 4) % 4)
    return base64.urlsafe_b64decode(value + pad)


def _decode_std_b64(value: str) -> bytes:
    pad = "=" * ((4 - len(value) % 4) % 4)
    return base64.b64decode(value + pad)


def _x25519_raw_from_private() -> tuple[bytes, bytes]:
    private_key = X25519PrivateKey.generate()
    private_bytes = private_key.private_bytes(
        encoding=Encoding.Raw,
        format=PrivateFormat.Raw,
        encryption_algorithm=NoEncryption(),
    )
    public_bytes = private_key.public_key().public_bytes(
        encoding=Encoding.Raw,
        format=PublicFormat.Raw,
    )
    return private_bytes, public_bytes


def reality_keypair() -> dict[str, str]:
    private_bytes, public_bytes = _x25519_raw_from_private()
    return {
        "private_key": _encode_key(private_bytes),
        "public_key": _encode_key(public_bytes),
    }


def reality_keypair_valid(private_b64: str, public_b64: str) -> bool:
    try:
        private_key = X25519PrivateKey.from_private_bytes(_decode_key(private_b64))
        derived = private_key.public_key().public_bytes(
            encoding=Encoding.Raw,
            format=PublicFormat.Raw,
        )
        return derived == _decode_key(public_b64)
    except (ValueError, TypeError):
        return False


def wireguard_keypair() -> dict[str, str]:
    """WireGuard-compatible keys (standard base64, as from wg genkey/pubkey)."""
    private_bytes, public_bytes = _x25519_raw_from_private()
    return {
        "private_key": base64.b64encode(private_bytes).decode("ascii"),
        "public_key": base64.b64encode(public_bytes).decode("ascii"),
    }


def wireguard_keypair_valid(private_b64: str, public_b64: str) -> bool:
    try:
        private_key = X25519PrivateKey.from_private_bytes(_decode_std_b64(private_b64))
        derived = private_key.public_key().public_bytes(
            encoding=Encoding.Raw,
            format=PublicFormat.Raw,
        )
        return derived == _decode_std_b64(public_b64)
    except (ValueError, TypeError):
        return False


_METHODS = {
    "random_hex": lambda p: random_hex(int(p.get("length", 16))),
    "uuid4": lambda _p: uuid4(),
    "reality_short_id": lambda p: reality_short_id(int(p.get("length", 8))),
}


def gen_secret(method: str, params: dict | None = None) -> str:
    try:
        return _METHODS[method](params or {})
    except KeyError as exc:
        raise ValueError(f"Неизвестный способ генерации: {method}") from exc