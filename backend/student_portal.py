"""Посилання для сторінки учня: уроки за паралеллю + Moodle лише з прапорця класу."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from models import Class, School, User  # noqa: F401 — Class used in type hints
from user_roles import is_student, parallel_letter_from_class_name


def normalize_full_name(s: str | None) -> str:
    if not s:
        return ""
    return " ".join(s.replace("\xa0", " ").split()).casefold()


def compute_student_portal_urls(
    db: Session,
    user: User,
    default_recordings: str,
    default_moodle: str,
) -> dict:
    """Повертає поля для MeOut учня."""
    out = {
        "recordings_url": (default_recordings or "").strip() or None,
        "moodle_url": None,
        "moodle_visible": False,
        "lessons_url_parallel": None,
        "lessons_url_school": None,
    }
    row = db.execute(
        text("SELECT class_id FROM class_students WHERE student_id = CAST(:sid AS uuid) LIMIT 1"),
        {"sid": str(user.id)},
    ).first()
    if not row:
        out["moodle_url"] = None
        out["moodle_visible"] = False
        return out
    cl = db.query(Class).filter(Class.id == row[0]).first()
    if not cl:
        return out
    school = db.query(School).filter(School.id == cl.school_id).first()
    par = parallel_letter_from_class_name(cl.name)
    if school:
        if par == "A":
            v = getattr(school, "lessons_url_parallel_a", None)
            if v:
                out["lessons_url_parallel"] = str(v).strip() or None
        elif par == "B":
            v = getattr(school, "lessons_url_parallel_b", None)
            if v:
                out["lessons_url_parallel"] = str(v).strip() or None
        v0 = getattr(school, "lessons_url_school", None)
        if v0:
            out["lessons_url_school"] = str(v0).strip() or None
    out["moodle_visible"] = bool(getattr(cl, "moodle_survey_enabled", False))
    if out["moodle_visible"]:
        raw = (getattr(cl, "moodle_survey_url", None) or "").strip() or (default_moodle or "").strip()
        out["moodle_url"] = raw or None
    else:
        out["moodle_url"] = None
    return out


def normalize_class_name_key(name: str) -> str:
    s = (name or "").strip().replace(" ", "").replace("–", "-").replace("—", "-")
    return s.casefold()


def find_class_by_school_and_name(db: Session, school_id, class_name: str) -> Class | None:
    target = normalize_class_name_key(class_name)
    for c in db.query(Class).filter(Class.school_id == school_id).all():
        if normalize_class_name_key(c.name) == target:
            return c
    return None


def find_students_by_pib_in_school(db: Session, school_id, full_name: str) -> list[User]:
    """Учні школи з тим самим нормалізованим ПІБ (0, 1 або кілька)."""
    n = normalize_full_name(full_name)
    if not n:
        return []
    out: list[User] = []
    for u in db.query(User).filter(User.school_id == school_id, User.role == "user").all():
        if u.staff_scope:
            continue
        if not is_student(db, u):
            continue
        if normalize_full_name(u.full_name or "") == n:
            out.append(u)
    return out
