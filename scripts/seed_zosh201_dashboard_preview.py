"""
Демо-дані для школи з database/seed.sql (ЗЗСО №201): кілька класів 5–9 та 10–12,
учні з повними відповідями на два опитування (для порівняння півріч),
чотири STEM-предметники (S/T/E/M) із призначеннями до класів за циклом через teacher_class_assignments,
обліковий запис директора з повним доступом до аналітики.

Запуск після schema.sql + seed.sql (або Alembic):
  DATABASE_URL=... python scripts/seed_zosh201_dashboard_preview.py

З Windows (PowerShell):
  cd backend
  $env:DATABASE_URL="postgresql://postgres:postgres@localhost:5432/stem_diagnostic"
  python ..\\scripts\\seed_zosh201_dashboard_preview.py

Або всередині контейнера API (після перезборки образу з COPY скрипта):
  docker compose run --rm api python /seed_zosh201_dashboard_preview.py

Вхід після сіду (подив. вивід скрипта):
  EMAIL: director.zzso201@preview.stem
  ПАРОЛЬ: Preview.Stem2026!

Повторний запуск: видаляє когорти *@zzso201.preview.stem і (застарілу) *@zosh201.preview.stem
разом із відповідями, потім заповнює знову (ідемпотентно для демонстрацій).
"""

from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

_NS = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")
SCHOOL_ID = uuid.UUID("a0000000-0000-0000-0000-000000000001")
SURVEY_A = uuid.UUID("b0000000-0000-0000-0000-000000000001")
SURVEY_B = uuid.UUID("b0000000-0000-0000-0000-000000000002")
DIRECTOR_ID = uuid.UUID("d0000000-0000-0000-0000-000000000201")
# З database/seed.sql — той самий рядок «5-А», щоб не порушити UNIQUE (school_id, name)
CLASS_5A_ID = uuid.UUID("c0000000-0000-0000-0000-000000000001")

# Раніше: @zosh201.preview.stem — cleanup лишився для безболісного переходу при повторному сиді.
OLD_PREVIEW_DOMAIN_SUFFIX = "@zosh201.preview.stem"
DOMAIN = "@zzso201.preview.stem"
DIRECTOR_EMAIL = "director.zzso201@preview.stem"

QUESTION_CODES = [
    "S1",
    "S2",
    "S3",
    "S4",
    "S5",
    "M1",
    "M2",
    "M3",
    "M4",
    "M5",
    "E1",
    "E2",
    "E3",
    "E4",
    "E5",
    "T1",
    "T2",
    "T3",
    "T4",
    "T5",
    "C1",
    "C2",
    "C3",
    "C4",
    "C5",
]

# Назви класів як у школі — різні «профілі» STEM для помітних стовпчиків у Chart.js.
CLASS_ROWS: list[tuple[str, int, str]] = [
    ("5-А", 5, "a"),
    ("6-Б", 6, "b"),
    ("7-А", 7, "c"),
    ("8-А", 8, "d"),
    ("9-Б", 9, "e"),
    ("10-А", 10, "f"),
    ("11-Б", 11, "g"),
    ("12-А", 12, "h"),
]


def uid(*parts: str) -> uuid.UUID:
    # Префікс «zosh201» лишаємо для стабільних UUID існуючих рядків у БД.
    return uuid.uuid5(_NS, "|".join(("zosh201", *parts)))


def class_id_for(name: str, ck: str) -> uuid.UUID:
    if name == "5-А":
        return CLASS_5A_ID
    return uid("class", name, ck)


def _backend_dir() -> Path:
    here = Path(__file__).resolve()
    cand = here.parent.parent / "backend"
    if (cand / "main.py").exists():
        return cand
    if (Path("/app") / "main.py").exists():
        return Path("/app")
    return cand


def score_val(student_n: int, qi: int, semester: int, grade: int) -> int:
    r = (student_n * 1009 + qi * 31 + semester * 17) % 49
    v = 1 + r // 7
    if semester == 2:
        v = min(7, v + (r % 3))
    # За методичними висновками: середній інтерес помітніший у нижчих паралелях порівняно зі старшими.
    drift = max(0, grade - 5) // 2 + max(0, grade - 9)
    v -= min(5, drift)
    return max(1, min(7, v))


def cleanup_preview_users(session, User, SurveyAnswer, SurveyResponse, ClassStudent) -> None:
    from sqlalchemy import or_, select

    rows = session.execute(
        select(User.id).where(
            or_(
                User.email.like(f"%{DOMAIN}"),
                User.email.like(f"%{OLD_PREVIEW_DOMAIN_SUFFIX}"),
            )
        )
    ).scalars().all()
    ids = list(rows)
    if not ids:
        return

    sid_list = SurveyResponse.__table__.c.student_id
    resp_tbl = SurveyResponse.__table__
    rsp_ids = session.execute(select(resp_tbl.c.id).where(sid_list.in_(ids))).scalars().all()
    if rsp_ids:
        session.query(SurveyAnswer).filter(SurveyAnswer.response_id.in_(rsp_ids)).delete(
            synchronize_session=False
        )
    session.query(SurveyResponse).filter(SurveyResponse.student_id.in_(ids)).delete(
        synchronize_session=False
    )
    session.query(ClassStudent).filter(ClassStudent.student_id.in_(ids)).delete(
        synchronize_session=False
    )
    session.query(User).filter(User.id.in_(ids)).delete(synchronize_session=False)
    session.commit()


def main() -> None:
    backend = _backend_dir()
    sys.path.insert(0, str(backend))
    os.chdir(backend)

    from password_hashing import hash_password
    from sqlalchemy.orm import Session

    from database import SessionLocal
    import models as M
    from services import upsert_class_model

    url = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/stem_diagnostic")
    env_path = backend / ".env"
    if env_path.exists() and "DATABASE_URL" not in os.environ:
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("DATABASE_URL="):
                url = line.split("=", 1)[1].strip().strip('"').strip("'")
                break
    os.environ["DATABASE_URL"] = url

    db: Session = SessionLocal()

    pwd_demo = hash_password("Preview.Stem2026!")
    try:
        cleanup_preview_users(db, M.User, M.SurveyAnswer, M.SurveyResponse, M.ClassStudent)
        db.expire_all()

        school = db.query(M.School).filter(M.School.id == SCHOOL_ID).first()
        if not school:
            db.add(M.School(id=SCHOOL_ID, name="ЗЗСО №201", city="Київ"))
        else:
            school.name = "ЗЗСО №201"
        db.commit()

        s_a = db.query(M.Survey).filter(M.Survey.id == SURVEY_A).first()
        if not s_a:
            db.add(
                M.Survey(
                    id=SURVEY_A,
                    name="STEM Semantics Survey 2024-2025 (І півріччя)",
                    school_year="2024-2025",
                )
            )
        s_b = db.query(M.Survey).filter(M.Survey.id == SURVEY_B).first()
        if not s_b:
            db.add(
                M.Survey(
                    id=SURVEY_B,
                    name="STEM Semantics Survey 2025-2026 (ІІ півріччя)",
                    school_year="2025-2026",
                )
            )

        dir_u = db.query(M.User).filter(M.User.id == DIRECTOR_ID).first()
        if not dir_u:
            dir_u = M.User(
                id=DIRECTOR_ID,
                email=DIRECTOR_EMAIL,
                password_hash=pwd_demo,
                full_name="Директор ЗЗСО №201 — демо",
                role="user",
                staff_scope="school",
                school_id=SCHOOL_ID,
                email_verified=True,
            )
            db.add(dir_u)
        else:
            dir_u.email = DIRECTOR_EMAIL
            dir_u.password_hash = pwd_demo
            dir_u.full_name = "Директор ЗЗСО №201 — демо"
            dir_u.staff_scope = "school"
            dir_u.school_id = SCHOOL_ID
            dir_u.email_verified = True

        classes: list[M.Class] = []
        for name, grade, ck in CLASS_ROWS:
            cid = class_id_for(name, ck)
            cl = db.query(M.Class).filter(M.Class.id == cid).first()
            if not cl:
                cl = M.Class(id=cid, school_id=SCHOOL_ID, name=name, grade=grade)
                db.add(cl)
            else:
                cl.grade = grade
                cl.school_id = SCHOOL_ID
            classes.append(cl)
        db.commit()

        db.query(M.TeacherClassAssignment).filter(
            M.TeacherClassAssignment.class_id.in_([c.id for c in classes])
        ).delete(synchronize_session=False)

        STEM_ROT = ["S", "T", "E", "M"]
        stem_ids_by_letter = {}
        stem_full_names = {
            "S": "STEM Наука (S), демо №201",
            "T": "STEM Технології (T), демо №201",
            "E": "STEM Інженерія (E), демо №201",
            "M": "STEM Математика (M), демо №201",
        }
        for letter in STEM_ROT:
            tid = uid("stem_teacher", letter)
            stem_ids_by_letter[letter] = tid
            email = f"stem-{letter.lower()}{DOMAIN}"
            u = db.query(M.User).filter(M.User.id == tid).first()
            if not u:
                db.add(
                    M.User(
                        id=tid,
                        email=email,
                        password_hash=pwd_demo,
                        full_name=stem_full_names[letter],
                        role="user",
                        staff_scope=None,
                        stem_specialty=letter,
                        school_id=SCHOOL_ID,
                        email_verified=True,
                    )
                )
            else:
                u.email = email
                u.password_hash = pwd_demo
                u.full_name = stem_full_names[letter]
                u.role = "user"
                u.staff_scope = None
                u.stem_specialty = letter
                u.school_id = SCHOOL_ID
                u.email_verified = True

        db.flush()

        for ci, cl in enumerate(classes):
            letter = STEM_ROT[ci % 4]
            tid = stem_ids_by_letter[letter]
            exists = (
                db.query(M.TeacherClassAssignment)
                .filter(
                    M.TeacherClassAssignment.user_id == tid,
                    M.TeacherClassAssignment.class_id == cl.id,
                )
                .first()
            )
            if not exists:
                db.add(M.TeacherClassAssignment(user_id=tid, class_id=cl.id))

        db.commit()

        STUDENTS_PER_CLASS = 22
        for cl in classes:
            for si in range(STUDENTS_PER_CLASS):
                st_id = uid("student", str(cl.id), str(si))
                email = f"st.{cl.name.replace('-', '').lower()}.{si + 1:02d}{DOMAIN}"
                u = db.query(M.User).filter(M.User.id == st_id).first()
                if not u:
                    u = M.User(
                        id=st_id,
                        email=email,
                        password_hash=pwd_demo,
                        full_name=f"Учень {cl.name} №{si + 1}",
                        role="user",
                        staff_scope=None,
                        school_id=SCHOOL_ID,
                        email_verified=True,
                    )
                    db.add(u)
                else:
                    u.email = email
                    u.password_hash = pwd_demo
                # FK class_students.student_id → users.id та survey_responses.student_id: рядок users
                # має існувати до INSERT у залежні таблиці (пакетний flush може змінювати порядок).
                db.flush()
                cs = (
                    db.query(M.ClassStudent)
                    .filter(
                        M.ClassStudent.class_id == cl.id,
                        M.ClassStudent.student_id == st_id,
                    )
                    .first()
                )
                if not cs:
                    db.add(M.ClassStudent(class_id=cl.id, student_id=st_id))

                student_n = hash(str(st_id)) % 100000 + si * 17 + len(QUESTION_CODES)
                for survey_id, semester in ((SURVEY_A, 1), (SURVEY_B, 2)):
                    existing = (
                        db.query(M.SurveyResponse)
                        .filter(
                            M.SurveyResponse.survey_id == survey_id,
                            M.SurveyResponse.student_id == st_id,
                        )
                        .first()
                    )
                    if existing:
                        db.query(M.SurveyAnswer).filter(
                            M.SurveyAnswer.response_id == existing.id
                        ).delete(synchronize_session=False)
                        db.delete(existing)
                        db.flush()
                    rsp = M.SurveyResponse(
                        survey_id=survey_id,
                        student_id=st_id,
                        class_id=cl.id,
                    )
                    db.add(rsp)
                    db.flush()
                    for qi, code in enumerate(QUESTION_CODES):
                        db.add(
                            M.SurveyAnswer(
                                response_id=rsp.id,
                                question_code=code,
                                value=score_val(student_n, qi, semester, cl.grade),
                            )
                        )
        db.commit()

        db.query(M.ClassModel).filter(
            M.ClassModel.survey_id.in_([SURVEY_A, SURVEY_B]),
            M.ClassModel.class_id.in_([c.id for c in classes]),
        ).delete(synchronize_session=False)
        db.commit()

        for cl in classes:
            upsert_class_model(db, cl.id, SURVEY_A)
            upsert_class_model(db, cl.id, SURVEY_B)

        db.commit()
        print("OK — сідування ЗЗСО №201 для панелі аналітики завершено.")
        print("")
        print("Вхід (директор, повний зріз школи та графіки):")
        print(f"  EMAIL:    {DIRECTOR_EMAIL}")
        print("  ПАРОЛЬ:   Preview.Stem2026!")
        print("")
        print("Опитування в інтерфейсі:")
        print(f"  A: {SURVEY_A} — І півріччя")
        print(f"  B: {SURVEY_B} — ІІ півріччя (для порівняння)")
        print("")
        print("Вчителі STEM (демо №201, пароль Preview.Stem2026!, призначення по класах за циклом S→T→E→M):")
        for letter in ("S", "T", "E", "M"):
            print(f"  stem-{letter.lower()}{DOMAIN}")
        print("")
        print("Далі: http://127.0.0.1:8000/ → Увійти → Панель → Аналітика школи.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
