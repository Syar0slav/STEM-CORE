"""Права доступу: у БД лише ролі admin та user; область школи — staff_scope."""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from models import Class, User

STAFF_SCOPES = frozenset({"parallel_a", "parallel_b", "school"})


def parallel_letter_from_class_name(name: str) -> str | None:
    if not name or "-" not in name:
        return None
    tail = name.split("-")[-1].strip().upper()
    if tail in ("А", "A"):
        return "A"
    if tail in ("Б", "B"):
        return "B"
    return None


def is_student(db: Session, user: User) -> bool:
    """Учень: role=user без staff_scope і не класний керівник (може ще не бути в class_students)."""
    if user.role != "user":
        return False
    if user.staff_scope:
        return False
    if db.query(Class).filter(Class.teacher_id == user.id).first():
        return False
    return True


def is_teacher(db: Session, user: User) -> bool:
    if user.role != "user" or user.staff_scope:
        return False
    return db.query(Class).filter(Class.teacher_id == user.id).first() is not None


def can_view_school_insights(user: User) -> bool:
    if user.role == "admin":
        return True
    return user.role == "user" and user.staff_scope in STAFF_SCOPES and user.school_id is not None


def assert_user_may_access_class(db: Session, user: User, class_id: UUID) -> Class:
    c = db.query(Class).filter(Class.id == class_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Class not found")
    if user.role == "admin":
        return c
    if user.role != "user":
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    if user.staff_scope == "school":
        if user.school_id != c.school_id:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return c
    if user.staff_scope == "parallel_a":
        if user.school_id != c.school_id or parallel_letter_from_class_name(c.name) != "A":
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return c
    if user.staff_scope == "parallel_b":
        if user.school_id != c.school_id or parallel_letter_from_class_name(c.name) != "B":
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return c
    if c.teacher_id == user.id:
        return c
    raise HTTPException(status_code=403, detail="Insufficient permissions")


def filter_classes_by_staff_scope(classes: list[Class], user: User) -> list[Class]:
    if user.role == "admin":
        return classes
    if user.role != "user":
        return []
    if user.staff_scope == "school":
        return [c for c in classes if c.school_id == user.school_id]
    if user.staff_scope == "parallel_a":
        return [
            c
            for c in classes
            if c.school_id == user.school_id and parallel_letter_from_class_name(c.name) == "A"
        ]
    if user.staff_scope == "parallel_b":
        return [
            c
            for c in classes
            if c.school_id == user.school_id and parallel_letter_from_class_name(c.name) == "B"
        ]
    return classes


def account_kind(db: Session, user: User) -> str:
    if user.role == "admin":
        return "admin"
    if user.role != "user":
        return "user"
    if user.staff_scope == "school":
        return "director"
    if user.staff_scope == "parallel_a":
        return "deputy_parallel_a"
    if user.staff_scope == "parallel_b":
        return "deputy_parallel_b"
    if is_teacher(db, user):
        return "teacher"
    if is_student(db, user):
        return "student"
    return "user"
