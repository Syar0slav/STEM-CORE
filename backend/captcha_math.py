"""Математична капча для реєстрації (JWT з очікуваною відповіддю)."""

import random
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from fastapi import HTTPException

from config import settings

_CAPTCHA_TTL_MIN = 10


def create_math_captcha() -> tuple[str, str]:
    a, b = random.randint(1, 12), random.randint(1, 12)
    total = a + b
    exp = datetime.now(timezone.utc) + timedelta(minutes=_CAPTCHA_TTL_MIN)
    token = jwt.encode(
        {"cap": total, "exp": int(exp.timestamp())},
        settings.secret_key,
        algorithm=settings.algorithm,
    )
    return token, f"{a} + {b} = ?"


def verify_math_captcha(token: str, answer_raw: str) -> None:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        expected = int(payload["cap"])
        answer = int(str(answer_raw).strip())
    except (JWTError, ValueError, KeyError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid or expired captcha")
    if answer != expected:
        raise HTTPException(status_code=400, detail="Invalid captcha")
