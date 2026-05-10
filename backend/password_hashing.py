import hashlib

import bcrypt

_BCRYPT_MAX_BYTES = 72


def _password_bytes_for_bcrypt(plain: str) -> bytes:
    raw = plain.encode("utf-8")
    if len(raw) <= _BCRYPT_MAX_BYTES:
        return raw
    return hashlib.sha256(raw).hexdigest().encode("ascii")


def hash_password(plain: str) -> str:
    secret = _password_bytes_for_bcrypt(plain)
    return bcrypt.hashpw(secret, bcrypt.gensalt()).decode("ascii")


def verify_password(plain: str, hashed_password: str) -> bool:
    secret = _password_bytes_for_bcrypt(plain)
    try:
        return bcrypt.checkpw(secret, hashed_password.encode("ascii"))
    except ValueError:
        return False
