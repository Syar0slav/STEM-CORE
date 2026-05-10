"""Вимоги до складності пароля при реєстрації."""

import re

from fastapi import HTTPException

_UPPER = re.compile(r"[A-ZА-ЯІЇЄҐЁ]")
_LOWER = re.compile(r"[a-zа-яіїєґё]")
_DIGIT = re.compile(r"\d")
_SPECIAL = re.compile(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?`~]")


def assert_password_strength(password: str) -> None:
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Password too short")
    if len(password) > 128:
        raise HTTPException(status_code=400, detail="Password too long")
    if not _UPPER.search(password):
        raise HTTPException(status_code=400, detail="Password needs uppercase")
    if not _LOWER.search(password):
        raise HTTPException(status_code=400, detail="Password needs lowercase")
    if not _DIGIT.search(password):
        raise HTTPException(status_code=400, detail="Password needs digit")
    if not _SPECIAL.search(password):
        raise HTTPException(status_code=400, detail="Password needs special character")
