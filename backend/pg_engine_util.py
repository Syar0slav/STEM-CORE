"""SQLAlchemy Engine для PostgreSQL без сирих DSN у psycopg2 (UnicodeDecodeError на Windows).

На Windows при невдалій автентифікації PostgreSQL часто повертає локалізоване повідомлення;
psycopg2 тоді падає з UnicodeDecodeError. За наявності psycopg (v3) використовуємо його.
"""
from __future__ import annotations

import os
import sys
from urllib.parse import unquote, urlparse


def _normalize_pg_host(host: str) -> str:
    if sys.platform == "win32" and host.lower() in ("localhost", "::1"):
        return "127.0.0.1"
    return host


def _want_psycopg_v3() -> bool:
    if sys.platform != "win32":
        return False
    try:
        import psycopg  # noqa: F401
    except ImportError:
        return False
    return True


def make_pg_engine(url: str, **engine_kwargs):
    from sqlalchemy import create_engine

    u = (url or "").strip()
    if u.startswith("\ufeff"):
        u = u.lstrip("\ufeff")
    u = u.replace("\r", "").strip()
    if u.startswith("postgresql+psycopg2://"):
        u = "postgresql://" + u[len("postgresql+psycopg2://") :]
    elif u.startswith("postgresql+asyncpg://"):
        u = "postgresql://" + u[len("postgresql+asyncpg://") :]

    p = urlparse(u)
    if p.scheme not in ("postgresql", "postgres") or not p.hostname:
        return create_engine(url, **engine_kwargs)

    user = unquote(p.username or "postgres")
    password = unquote(p.password or "")
    host = _normalize_pg_host(p.hostname)
    port = int(p.port or 5432)
    path = (p.path or "").lstrip("/")
    dbname = (path.split("?")[0] if path else "") or "stem_diagnostic"

    connect_args = {
        "user": user,
        "password": password,
        "host": host,
        "port": port,
        "dbname": dbname,
    }

    if _want_psycopg_v3():
        import psycopg

        def _creator():
            old_pw = os.environ.get("PGPASSWORD")
            try:
                if password:
                    os.environ["PGPASSWORD"] = password
                else:
                    os.environ.pop("PGPASSWORD", None)
                return psycopg.connect(
                    host=host,
                    port=port,
                    user=user,
                    dbname=dbname,
                )
            finally:
                if old_pw is None:
                    os.environ.pop("PGPASSWORD", None)
                else:
                    os.environ["PGPASSWORD"] = old_pw

        return create_engine("postgresql+psycopg://", creator=_creator, **engine_kwargs)

    return create_engine(
        "postgresql+psycopg2://",
        connect_args={**connect_args, "client_encoding": "utf8"},
        **engine_kwargs,
    )
