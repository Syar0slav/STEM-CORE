"""
Створює в БД двох користувачів з відомими обліковими даними (для ручного тесту).

  • Директор: role=user, staff_scope=school
  • Вчитель: role=user, без staff_scope, прив’язаний до одного класу (teacher_id)

Потрібна та сама база, що й API. Паролі відповідають password_policy (8+ символів, велика/мала літери, цифра, спецсимвол).

Запуск з кореня репозиторію:
  py -3 scripts/insert_manual_demo_director_teacher.py

Або з DATABASE_URL:
  $env:DATABASE_URL="postgresql://postgres:postgres@localhost:5432/stem_diagnostic"
"""
from __future__ import annotations

import os
import re
import sys
import uuid
from pathlib import Path

# --- згенеровані облікові дані (можна змінити перед запуском) ---
DIRECTOR_EMAIL = "director.demo@example.com"
TEACHER_EMAIL = "teacher.demo@example.com"
DIRECTOR_PASSWORD = "Director.Stem2026!"
TEACHER_PASSWORD = "Teacher.Stem2026!"

NS = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")


def uid(*parts: str) -> str:
    return str(uuid.uuid5(NS, "|".join(parts)))


def _check_password_policy(p: str) -> None:
    if len(p) < 8:
        raise ValueError("Password too short")
    if len(p) > 128:
        raise ValueError("Password too long")
    if not re.search(r"[A-ZА-ЯІЇЄҐЁ]", p):
        raise ValueError("Password needs uppercase")
    if not re.search(r"[a-zа-яіїєґё]", p):
        raise ValueError("Password needs lowercase")
    if not re.search(r"\d", p):
        raise ValueError("Password needs digit")
    if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?`~]", p):
        raise ValueError("Password needs special character")


def main() -> None:
    for label, pw in (
        ("Директор", DIRECTOR_PASSWORD),
        ("Вчитель", TEACHER_PASSWORD),
    ):
        _check_password_policy(pw)
        print(f"OK політика пароля ({label}): складність відповідає вимогам API")

    backend = Path(__file__).resolve().parent.parent / "backend"
    sys.path.insert(0, str(backend))
    os.chdir(backend)

    from password_hashing import hash_password
    from sqlalchemy import create_engine, text

    url = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/stem_diagnostic")
    env_path = backend / ".env"
    if env_path.exists() and "DATABASE_URL" not in os.environ:
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("DATABASE_URL="):
                url = line.split("=", 1)[1].strip().strip('"').strip("'")
                break

    sch1 = uid("school", "1")
    dir_id = uid("manual", "director", "demo", DIRECTOR_EMAIL)
    tea_id = uid("manual", "teacher", "demo", TEACHER_EMAIL)

    engine = create_engine(url)
    pwd_dir = hash_password(DIRECTOR_PASSWORD)
    pwd_tea = hash_password(TEACHER_PASSWORD)

    ins = text(
        """
        INSERT INTO users (id, email, password_hash, full_name, role, school_id, staff_scope, email_verified)
        VALUES (CAST(:id AS uuid), :email, :hash, :name, 'user', CAST(:sid AS uuid), :scope, TRUE)
        ON CONFLICT (email) DO UPDATE SET
            password_hash = EXCLUDED.password_hash,
            full_name = EXCLUDED.full_name,
            role = EXCLUDED.role,
            school_id = EXCLUDED.school_id,
            staff_scope = EXCLUDED.staff_scope,
            email_verified = TRUE
        """
    )

    with engine.begin() as conn:
        r = conn.execute(text("SELECT id::text FROM schools WHERE id = CAST(:sid AS uuid)"), {"sid": sch1})
        if not r.fetchone():
            print("Помилка: немає школи з id з демо-сиду. Спочатку виконайте: py -3 scripts/seed_demo_1000.py")
            sys.exit(1)

        conn.execute(
            ins,
            {
                "id": dir_id,
                "email": DIRECTOR_EMAIL,
                "hash": pwd_dir,
                "name": "Директор (ручний демо)",
                "sid": sch1,
                "scope": "school",
            },
        )
        conn.execute(
            ins,
            {
                "id": tea_id,
                "email": TEACHER_EMAIL,
                "hash": pwd_tea,
                "name": "Вчитель (ручний демо)",
                "sid": sch1,
                "scope": None,
            },
        )

        cr = conn.execute(
            text(
                """
                SELECT id::text FROM classes
                WHERE school_id = CAST(:sid AS uuid)
                ORDER BY name
                LIMIT 1
                """
            ),
            {"sid": sch1},
        )
        row = cr.fetchone()
        if not row:
            print("Помилка: немає класів у школі 1. Запустіть seed_demo_1000.py")
            sys.exit(1)
        cid = row[0]
        conn.execute(
            text("UPDATE classes SET teacher_id = CAST(:tid AS uuid) WHERE id = CAST(:cid AS uuid)"),
            {"tid": tea_id, "cid": cid},
        )
        print(f"Вчителя прив’язано до класу id={cid}")

    out = Path(__file__).resolve().parent / "MANUAL_DEMO_CREDENTIALS.txt"
    out.write_text(
        "Ручні демо-облікові записи (згенеровано insert_manual_demo_director_teacher.py)\n\n"
        f"Директор (аналітика школи, staff_scope=school):\n"
        f"  Email:    {DIRECTOR_EMAIL}\n"
        f"  Пароль:   {DIRECTOR_PASSWORD}\n\n"
        f"Вчитель (модель класу для прив’язаного класу):\n"
        f"  Email:    {TEACHER_EMAIL}\n"
        f"  Пароль:   {TEACHER_PASSWORD}\n\n"
        "Вхід: login.html або POST /api/auth/login\n",
        encoding="utf-8",
    )
    print("Записано:", out)
    print("Готово.")


if __name__ == "__main__":
    main()
