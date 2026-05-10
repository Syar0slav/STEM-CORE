"""
Локальна перевірка з'єднання та колонок таблиці users (без запуску uvicorn).

Приклад (PowerShell):
  cd backend
  $env:DATABASE_URL="postgresql://postgres:postgres@127.0.0.1:5432/stem_diagnostic"
  py check_schema.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text

from config import settings


def main() -> int:
    url = os.environ.get("DATABASE_URL", settings.database_url)
    print("DATABASE_URL:", url.split("@")[-1] if "@" in url else "(hidden)")
    eng = create_engine(url)
    try:
        with eng.connect() as c:
            c.execute(text("SELECT 1"))
            print("SELECT 1: OK")
            r = c.execute(
                text(
                    """
                SELECT column_name FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = 'users'
                ORDER BY column_name
                """
                )
            )
            cols = [row[0] for row in r]
            print("users columns:", ", ".join(cols) if cols else "(empty / no table)")
            need = {"email_verified", "email_verification_token"}
            ok = need.issubset(set(cols))
            print("required for registration:", need)
            print("schema_ok:", ok)
            if not ok:
                print("FIX: alembic upgrade head")
                return 1
    except OSError as e:
        print("CONNECTION FAILED:", e)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
