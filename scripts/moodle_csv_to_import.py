"""
Парсинг експорту Moodle (CSV) і опційно запис у БД STEM Diagnostic.

Колонки питань — moodle/question_mapping.json (S1…C5).
Користувач: email/username АБО збіг ПІБ у межах школи (--school-id).

Приклади:
  python scripts/moodle_csv_to_import.py export.csv --import-db --survey-id UUID \\
      --database-url postgresql://... --school-id UUID
  python scripts/moodle_csv_to_import.py export.csv --import-db --survey-id UUID \\
      --class-id UUID --email-column email
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

MAPPING_PATH = ROOT / "moodle" / "question_mapping.json"
with open(MAPPING_PATH, encoding="utf-8") as f:
    MAPPING = json.load(f)

CODES: list[str] = []
for b in MAPPING["blocks"]:
    CODES.extend(b["questions"])


def _cell(row: dict, code: str) -> str:
    v = row.get(code)
    if v is not None and str(v).strip() != "":
        return str(v).strip()
    alt = code.replace("-", "_")
    return str(row.get(alt, "") or "").strip()


def parse_row_answers(row: dict) -> list[dict]:
    answers = []
    for code in CODES:
        val = _cell(row, code)
        if val and val.isdigit():
            v = int(val)
            if 1 <= v <= 7:
                answers.append({"question_code": code, "value": v})
    return answers


def extract_pib(row: dict, pib_column: str | None) -> str:
    if pib_column and pib_column in row:
        s = str(row.get(pib_column) or "").strip()
        if s:
            return s
    for key in ("ПІБ", "PIB", "Повне ім'я", "Full name", "fullname", "Name"):
        if key in row and str(row.get(key) or "").strip():
            return str(row[key]).strip()
    fn = (row.get("First name") or row.get("Ім'я") or "").strip()
    ln = (row.get("Surname") or row.get("Last name") or row.get("Прізвище") or "").strip()
    if fn or ln:
        return f"{fn} {ln}".strip()
    return ""


def parse_moodle_export(csv_path: str) -> list[dict]:
    rows = []
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            answers = parse_row_answers(row)
            if len(answers) >= 20:
                rows.append({"answers": answers})
    return rows


def iter_moodle_rows(csv_path: str, email_column: str | None):
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        for row in reader:
            answers = parse_row_answers(row)
            email = None
            if email_column and email_column in row:
                email = (row.get(email_column) or "").strip()
            if not email:
                for key in ("email", "Email", "E-mail", "username", "Username"):
                    if key in row and str(row.get(key) or "").strip():
                        email = str(row[key]).strip()
                        break
            yield {"email": email, "answers": answers, "headers": headers, "row": row}


def import_to_database(
    csv_path: str,
    survey_id: str,
    class_id: str,
    database_url: str,
    email_column: str | None,
    school_id: str | None,
    pib_column: str | None,
    dry_run: bool,
) -> tuple[int, int, list[str]]:
    from uuid import UUID

    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker

    from models import Survey, SurveyAnswer, SurveyResponse, User
    from services import upsert_class_model
    from student_portal import find_students_by_pib_in_school
    from user_roles import is_student

    engine = create_engine(database_url)
    Session = sessionmaker(bind=engine)
    db = Session()
    msgs: list[str] = []
    imported = 0
    skipped = 0
    school_uuid = UUID(school_id) if school_id else None
    try:
        su = db.query(Survey).filter(Survey.id == UUID(survey_id)).first()
        if not su:
            msgs.append(f"Опитування {survey_id} не знайдено в БД.")
            return 0, 0, msgs

        for item in iter_moodle_rows(csv_path, email_column):
            row_dict = item["row"]
            email = (item["email"] or "").strip()
            answers = item["answers"]
            pib = extract_pib(row_dict, pib_column)
            if len(answers) < 20:
                skipped += 1
                msgs.append(f"Пропуск (мало відповідей): {email or pib or '?'}")
                continue

            user = None
            if email:
                user = db.query(User).filter(User.email == email).first()
            if not user and school_uuid and pib:
                matches = find_students_by_pib_in_school(db, school_uuid, pib)
                if len(matches) == 1:
                    user = matches[0]
                elif len(matches) > 1:
                    skipped += 1
                    msgs.append(f"ПІБ «{pib}» — кілька учнів у школі, уточніть email")
                    continue

            if not user:
                skipped += 1
                msgs.append(
                    f"Немає користувача ({email or 'без email'} / ПІБ: {pib or '—'})"
                )
                continue

            if school_uuid and user.school_id and user.school_id != school_uuid:
                skipped += 1
                msgs.append(f"Школа не збігається з --school-id: {email or pib}")
                continue

            if not is_student(db, user):
                skipped += 1
                msgs.append(f"Користувач не учень — пропуск: {email or pib}")
                continue

            exists = (
                db.query(SurveyResponse)
                .filter(
                    SurveyResponse.survey_id == UUID(survey_id),
                    SurveyResponse.student_id == user.id,
                )
                .first()
            )
            if exists:
                skipped += 1
                msgs.append(f"Вже є відповідь: {email or pib}")
                continue

            cid_str = (class_id or "").strip()
            if not cid_str:
                r = db.execute(
                    text(
                        "SELECT class_id FROM class_students WHERE student_id = CAST(:sid AS uuid) LIMIT 1"
                    ),
                    {"sid": str(user.id)},
                ).first()
                if r:
                    cid_str = str(r[0])
            if not cid_str:
                skipped += 1
                msgs.append(f"Немає class_id: закріпіть учня за класом (roster) або вкажіть --class-id: {email or pib}")
                continue

            if dry_run:
                imported += 1
                msgs.append(f"[dry-run] OK {email or pib} → class {cid_str}")
                continue

            resp = SurveyResponse(
                survey_id=UUID(survey_id),
                student_id=user.id,
                class_id=UUID(cid_str),
            )
            db.add(resp)
            db.flush()
            for a in answers:
                db.add(
                    SurveyAnswer(
                        response_id=resp.id,
                        question_code=a["question_code"],
                        value=a["value"],
                    )
                )
            db.commit()
            upsert_class_model(db, UUID(cid_str), UUID(survey_id))
            imported += 1
            msgs.append(f"Імпортовано: {email or pib}")
    finally:
        db.close()

    return imported, skipped, msgs


def main() -> None:
    p = argparse.ArgumentParser(description="Moodle CSV → JSON або імпорт у БД")
    p.add_argument("csv_path", help="Шлях до CSV з Moodle")
    p.add_argument("--dry-run", action="store_true", help="Не писати в БД (лише звіт)")
    p.add_argument("--import-db", action="store_true", help="Записати відповіді в БД")
    p.add_argument("--survey-id", help="UUID опитування в таблиці surveys")
    p.add_argument("--class-id", help="UUID класу (якщо порожньо — з class_students учня)")
    p.add_argument("--database-url", default=None, help="Або змінна DATABASE_URL")
    p.add_argument("--email-column", default=None, help="Колонка email у CSV")
    p.add_argument(
        "--school-id",
        default=None,
        help="UUID школи для зіставлення рядків за ПІБ (якщо немає email)",
    )
    p.add_argument(
        "--pib-column",
        default=None,
        help="Явна колонка з ПІБ (інакше авто: ПІБ, Full name, …)",
    )

    args = p.parse_args()
    db_url = args.database_url or __import__("os").environ.get("DATABASE_URL")

    if args.import_db:
        if not args.survey_id:
            print("Потрібен --survey-id", file=sys.stderr)
            sys.exit(1)
        if not db_url:
            print("Потрібен --database-url або DATABASE_URL", file=sys.stderr)
            sys.exit(1)
        imp, skip, msgs = import_to_database(
            args.csv_path,
            args.survey_id,
            args.class_id or "",
            db_url,
            args.email_column,
            args.school_id,
            args.pib_column,
            args.dry_run,
        )
        print(f"Імпортовано: {imp}, пропущено: {skip}")
        for m in msgs[-80:]:
            print(m)
        return

    result = parse_moodle_export(args.csv_path)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
