"""
Демо-дані: одна основна школа з 1000 учнями (паралелі А1–А11 та Б1–Б11),
директор, два завучі (паралель А та Б), директор бачить усю школу в аналітиці.
Запуск з кореня репозиторію: py -3 scripts/seed_demo_1000.py

Потрібні пакети Python (один раз), якщо скрипт не з контейнера API:
  py -3 -m pip install bcrypt sqlalchemy psycopg2-binary "psycopg[binary]"
або з кореня:
  py -3 -m pip install -r backend/requirements.txt
або повний набір:
  py -3 -m pip install -r backend/requirements.txt

PostgreSQL має бути доступний (локально або docker compose з портом 5432).

Якщо на ПК немає pip / bcrypt, після перезбірки образу:
  docker compose build api
  docker compose run --rm api python /seed_demo_1000.py
(у контейнері DATABASE_URL вже вказує на сервіс db.)
"""
import os
import sys
import uuid
from pathlib import Path

NS = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")

QUESTION_CODES = [
    "S1", "S2", "S3", "S4", "S5",
    "M1", "M2", "M3", "M4", "M5",
    "E1", "E2", "E3", "E4", "E5",
    "T1", "T2", "T3", "T4", "T5",
    "C1", "C2", "C3", "C4", "C5",
]


def uid(*parts: str) -> str:
    return str(uuid.uuid5(NS, "|".join(parts)))


def _backend_dir() -> Path:
    """Репозиторій: scripts/ → ../backend; Docker: скрипт у /, код API в /app."""
    here = Path(__file__).resolve()
    cand = here.parent.parent / "backend"
    if (cand / "main.py").exists():
        return cand
    docker_app = Path("/app")
    if (docker_app / "main.py").exists():
        return docker_app
    return cand


def score_val(student_n: int, qi: int, semester: int) -> int:
    r = (student_n * 1009 + qi * 31 + semester * 17) % 49
    v = 1 + r // 7
    if semester == 2:
        v = min(7, v + (r % 3))
    return v


def main():
    backend = _backend_dir()
    sys.path.insert(0, str(backend))
    _scripts_dir = Path(__file__).resolve().parent
    sys.path.insert(0, str(_scripts_dir))
    from pg_engine_util import make_pg_engine

    os.chdir(backend)

    from password_hashing import hash_password
    from sqlalchemy import text
    from sqlalchemy.orm import Session

    pwd_hash = hash_password("Demo2026!")
    # Окремі паролі (політика API) — зручний вхід через @example.com без окремого скрипта
    pwd_dir_demo = hash_password("Director.Stem2026!")
    pwd_tea_demo = hash_password("Teacher.Stem2026!")
    manual_dir_id = uid("manual", "director", "demo", "director.demo@example.com")
    manual_tea_id = uid("manual", "teacher", "demo", "teacher.demo@example.com")

    env_path = backend / ".env"
    # Якщо задати DATABASE_URL у PowerShell — не перезаписувати з backend/.env (інакше зламаний рядок/кодування ламає psycopg2).
    url = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/stem_diagnostic")
    if env_path.exists() and "DATABASE_URL" not in os.environ:
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("DATABASE_URL="):
                url = line.split("=", 1)[1].strip().strip('"').strip("'")
                break

    engine = make_pg_engine(url)

    sch1 = uid("school", "1")
    sch2 = uid("school", "2")
    survey_h1 = uid("survey", "2025-2026-I")
    survey_h2 = uid("survey", "2025-2026-II")

    # 22 класи: 1-А … 11-А, 1-Б … 11-Б
    class_specs = []
    for gr in range(1, 12):
        class_specs.append((gr, "А"))
        class_specs.append((gr, "Б"))

    n_classes = len(class_specs)
    total_students_s1 = 1000
    base = total_students_s1 // n_classes
    extra = total_students_s1 % n_classes
    per_class_counts = [base + (1 if i < extra else 0) for i in range(n_classes)]

    ins_user = text(
        """
        INSERT INTO users (id, email, password_hash, full_name, role, school_id, staff_scope, email_verified)
        VALUES (CAST(:id AS uuid), :email, :hash, :name, :role, CAST(:sid AS uuid), :staff_scope, TRUE)
        ON CONFLICT (email) DO UPDATE SET
            password_hash = EXCLUDED.password_hash,
            full_name = EXCLUDED.full_name,
            role = EXCLUDED.role,
            school_id = EXCLUDED.school_id,
            staff_scope = EXCLUDED.staff_scope,
            email_verified = TRUE
        """
    )

    ins_class = text(
        """
        INSERT INTO classes (id, school_id, name, grade, teacher_id)
        VALUES (CAST(:id AS uuid), CAST(:sid AS uuid), :name, :grade, CAST(:tid AS uuid))
        ON CONFLICT (school_id, name) DO UPDATE SET
            grade = EXCLUDED.grade,
            teacher_id = EXCLUDED.teacher_id
        """
    )

    ins_link = text(
        """
        INSERT INTO class_students (class_id, student_id)
        VALUES (CAST(:cid AS uuid), CAST(:sid AS uuid))
        ON CONFLICT DO NOTHING
        """
    )

    ins_resp = text(
        """
        INSERT INTO survey_responses (id, survey_id, student_id, class_id)
        VALUES (CAST(:id AS uuid), CAST(:sv AS uuid), CAST(:st AS uuid), CAST(:cid AS uuid))
        ON CONFLICT (survey_id, student_id) DO UPDATE SET class_id = EXCLUDED.class_id
        """
    )

    ins_ans = text(
        """
        INSERT INTO survey_answers (id, response_id, question_code, value)
        VALUES (CAST(:id AS uuid), CAST(:rid AS uuid), :code, :val)
        """
    )

    with engine.begin() as conn:
        for row in (
            {"id": sch1, "name": "ЗОШ №1 «STEM-демо»", "city": "Київ"},
            {"id": sch2, "name": "ЗОШ №2 (тест мережі)", "city": "Львів"},
        ):
            conn.execute(
                text(
                    """
                    INSERT INTO schools (id, name, city) VALUES (CAST(:id AS uuid), :name, :city)
                    ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, city = EXCLUDED.city
                    """
                ),
                row,
            )

        conn.execute(
            text(
                """
                INSERT INTO surveys (id, name, school_year) VALUES (CAST(:id AS uuid), :name, :year)
                ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name
                """
            ),
            {"id": survey_h1, "name": "STEM Semantics Survey — І півріччя 2025-2026", "year": "2025-2026"},
        )
        conn.execute(
            text(
                """
                INSERT INTO surveys (id, name, school_year) VALUES (CAST(:id AS uuid), :name, :year)
                ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name
                """
            ),
            {"id": survey_h2, "name": "STEM Semantics Survey — ІІ півріччя 2025-2026", "year": "2025-2026"},
        )

        # --- Школа 1: директор, завуч А, завуч Б ---
        conn.execute(
            ins_user,
            {
                "id": uid("director", "1"),
                "email": "director.s1@demo.stem.local",
                "hash": pwd_hash,
                "name": "Директор (повна аналітика школи)",
                "role": "user",
                "sid": sch1,
                "staff_scope": "school",
            },
        )
        conn.execute(
            ins_user,
            {
                "id": uid("deputy", "1", "A"),
                "email": "deputy.parallel_a@demo.stem.local",
                "hash": pwd_hash,
                "name": "Завуч (паралель А, класи А1–А11)",
                "role": "user",
                "sid": sch1,
                "staff_scope": "parallel_a",
            },
        )
        conn.execute(
            ins_user,
            {
                "id": uid("deputy", "1", "B"),
                "email": "deputy.parallel_b@demo.stem.local",
                "hash": pwd_hash,
                "name": "Завуч (паралель Б, класи Б1–Б11)",
                "role": "user",
                "sid": sch1,
                "staff_scope": "parallel_b",
            },
        )
        # Додаткові директори школи 1 (тести порталу / прав)
        for alt in ("2", "3"):
            conn.execute(
                ins_user,
                {
                    "id": uid("director", "1", "alt", alt),
                    "email": f"director{alt}.s1@demo.stem.local",
                    "hash": pwd_hash,
                    "name": f"Директор (тестовий облік {alt})",
                    "role": "user",
                    "sid": sch1,
                    "staff_scope": "school",
                },
            )

        for ci, (gr, letter) in enumerate(class_specs, start=1):
            t_id = uid("teacher", "1", str(ci))
            c_id = uid("class", "1", str(gr), letter)
            cname = f"{gr}-{letter}"
            conn.execute(
                ins_user,
                {
                    "id": t_id,
                    "email": f"teacher.s1.{cname}@demo.stem.local",
                    "hash": pwd_hash,
                    "name": f"Класний керівник {cname}",
                    "role": "user",
                    "sid": sch1,
                    "staff_scope": None,
                },
            )
            conn.execute(
                ins_class,
                {
                    "id": c_id,
                    "sid": sch1,
                    "name": cname,
                    "grade": gr,
                    "tid": t_id,
                },
            )

        # Директор + вчитель з @example.com (для curl / PowerShell без .local)
        conn.execute(
            ins_user,
            {
                "id": manual_dir_id,
                "email": "director.demo@example.com",
                "hash": pwd_dir_demo,
                "name": "Директор (демо @example.com)",
                "role": "user",
                "sid": sch1,
                "staff_scope": "school",
            },
        )
        conn.execute(
            ins_user,
            {
                "id": manual_tea_id,
                "email": "teacher.demo@example.com",
                "hash": pwd_tea_demo,
                "name": "Вчитель (демо @example.com)",
                "role": "user",
                "sid": sch1,
                "staff_scope": None,
            },
        )
        class_1a = uid("class", "1", "1", "А")
        conn.execute(
            text(
                "UPDATE classes SET teacher_id = CAST(:tid AS uuid) WHERE id = CAST(:cid AS uuid)"
            ),
            {"tid": manual_tea_id, "cid": class_1a},
        )

        # Школа 2: лише директор для тестів мережі
        conn.execute(
            ins_user,
            {
                "id": uid("director", "2"),
                "email": "director.s2@demo.stem.local",
                "hash": pwd_hash,
                "name": "Директор школи 2",
                "role": "user",
                "sid": sch2,
                "staff_scope": "school",
            },
        )

        n = 0
        for class_idx, (gr, letter) in enumerate(class_specs):
            c_id = uid("class", "1", str(gr), letter)
            for _ in range(per_class_counts[class_idx]):
                n += 1
                st_id = uid("student", str(n))
                conn.execute(
                    ins_user,
                    {
                        "id": st_id,
                        "email": f"student.{n:04d}@demo.stem.local",
                        "hash": pwd_hash,
                        "name": f"Учень {n} ({gr}-{letter})",
                        "role": "user",
                        "sid": sch1,
                        "staff_scope": None,
                    },
                )
                conn.execute(ins_link, {"cid": c_id, "sid": st_id})

        conn.execute(
            text(
                """
                DELETE FROM survey_answers WHERE response_id IN (
                    SELECT id FROM survey_responses WHERE survey_id IN (
                        CAST(:h1 AS uuid), CAST(:h2 AS uuid)
                    )
                )
                """
            ),
            {"h1": survey_h1, "h2": survey_h2},
        )
        conn.execute(
            text(
                """
                DELETE FROM class_models WHERE survey_id IN (CAST(:h1 AS uuid), CAST(:h2 AS uuid))
                """
            ),
            {"h1": survey_h1, "h2": survey_h2},
        )
        conn.execute(
            text(
                """
                DELETE FROM survey_responses WHERE survey_id IN (CAST(:h1 AS uuid), CAST(:h2 AS uuid))
                """
            ),
            {"h1": survey_h1, "h2": survey_h2},
        )

        n = 0
        for class_idx, (gr, letter) in enumerate(class_specs):
            c_id = uid("class", "1", str(gr), letter)
            for _ in range(per_class_counts[class_idx]):
                n += 1
                st_id = uid("student", str(n))
                for semester, sv in ((1, survey_h1), (2, survey_h2)):
                    rid = uid("response", str(n), f"H{semester}")
                    conn.execute(
                        ins_resp,
                        {
                            "id": rid,
                            "sv": sv,
                            "st": st_id,
                            "cid": c_id,
                        },
                    )
                    for qi, code in enumerate(QUESTION_CODES):
                        val = score_val(n, qi, semester)
                        conn.execute(
                            ins_ans,
                            {
                                "id": uid("ans", str(n), f"H{semester}", code),
                                "rid": rid,
                                "code": code,
                                "val": val,
                            },
                        )

    os.environ["DATABASE_URL"] = url
    from database import SessionLocal
    from services import upsert_class_model

    db: Session = SessionLocal()
    try:
        for gr, letter in class_specs:
            cid = uuid.UUID(uid("class", "1", str(gr), letter))
            for sv in (survey_h1, survey_h2):
                upsert_class_model(db, cid, uuid.UUID(sv))
    finally:
        db.close()

    print("OK: школа 1 — 1000 учнів у класах А1–А11 та Б1–Б11; директор + 2 завучі; школа 2 — лише директор.")
    print("Опитування: І та ІІ півріччя — повні відповіді, моделі класів оновлено.")
    print("Пароль усіх демо-акаунтів: Demo2026!")
    print("  Окремо (@example.com, свої паролі): director.demo@example.com / Director.Stem2026!")
    print("                                    teacher.demo@example.com / Teacher.Stem2026!")
    print("  Директор школи 1: director.s1@demo.stem.local")
    print("  Ще директори (школа 1): director2.s1@demo.stem.local, director3.s1@demo.stem.local")
    print("  Завуч паралель А: deputy.parallel_a@demo.stem.local")
    print("  Завуч паралель Б: deputy.parallel_b@demo.stem.local")
    print("  Учні: student.0001@demo.stem.local … student.1000@demo.stem.local")
    print("Опитування id: І півріччя =", survey_h1)
    print("                ІІ півріччя =", survey_h2)


if __name__ == "__main__":
    main()
