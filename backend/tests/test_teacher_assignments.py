"""Багатокласовий вчитель через teacher_class_assignments та stem_specialty."""

from uuid import UUID, uuid4

import pytest
from sqlalchemy.orm import Session

from auth import create_access_token, get_password_hash
from models import Class, TeacherClassAssignment, User
from user_roles import is_student, is_teacher, teacher_linked_class_ids

from tests.conftest import CLASS_ID, SCHOOL_ID, SURVEY_ID


@pytest.fixture
def second_class(db: Session, seed_school_survey_class) -> Class:
    cid = uuid4()
    c = Class(id=cid, school_id=SCHOOL_ID, name="6-Б", grade=6)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


@pytest.fixture
def subject_teacher(db: Session, seed_school_survey_class, second_class: Class) -> User:
    u = User(
        email=f"stem_teacher_{uuid4().hex}@example.com",
        password_hash=get_password_hash("Test1!pass"),
        full_name="Teacher STEM S",
        role="user",
        staff_scope=None,
        school_id=SCHOOL_ID,
        stem_specialty="S",
        email_verified=True,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    db.add_all(
        [
            TeacherClassAssignment(user_id=u.id, class_id=CLASS_ID),
            TeacherClassAssignment(user_id=u.id, class_id=second_class.id),
        ]
    )
    db.commit()
    return u


def test_teacher_linked_classes_union(db: Session, subject_teacher: User, second_class: Class):
    ids = teacher_linked_class_ids(db, subject_teacher)
    assert CLASS_ID in ids
    assert second_class.id in ids


def test_is_teacher_not_student(subject_teacher: User, db: Session):
    assert is_teacher(db, subject_teacher)
    assert not is_student(db, subject_teacher)


def test_api_classes_lists_both(subject_teacher: User, db: Session, client, seed_school_survey_class):
    hdrs = {"Authorization": f"Bearer {create_access_token({'sub': str(subject_teacher.id)})}"}
    r = client.get("/api/classes", headers=hdrs)
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 2
    names = {x["name"] for x in data}
    assert names == {"5-A", "6-Б"}


def test_teacher_denied_foreign_class(
    subject_teacher: User,
    db: Session,
    client,
    seed_school_survey_class,
):
    other_school = UUID("dead0000-0000-0000-0000-000000000099")
    from models import School

    if not db.query(School).filter(School.id == other_school).first():
        db.add(School(id=other_school, name="Other", city="X"))
        db.commit()
    foreign_cl = Class(
        id=uuid4(),
        school_id=other_school,
        name="7-A",
        grade=7,
    )
    db.add(foreign_cl)
    db.commit()
    hdrs = {"Authorization": f"Bearer {create_access_token({'sub': str(subject_teacher.id)})}"}
    r = client.get(
        f"/api/class-models/{foreign_cl.id}/{SURVEY_ID}",
        headers=hdrs,
    )
    assert r.status_code == 403


def test_director_updates_teacher_profile(client, db: Session, subject_teacher: User):
    director = User(
        email=f"director_assign_{uuid4().hex}@example.com",
        password_hash=get_password_hash("Test1!pass"),
        full_name="Director",
        role="user",
        staff_scope="school",
        school_id=SCHOOL_ID,
        email_verified=True,
    )
    db.add(director)
    db.commit()
    db.refresh(director)

    hdrs = {"Authorization": f"Bearer {create_access_token({'sub': str(director.id)})}"}
    r = client.patch(
        f"/api/schools/{SCHOOL_ID}/users/{subject_teacher.id}/teacher-profile",
        headers=hdrs,
        json={"stem_specialty": "M", "assigned_class_ids": [str(CLASS_ID)]},
    )
    assert r.status_code == 200
    out = r.json()
    assert out["stem_specialty"] == "M"
    assert len(out["assigned_class_ids"]) == 1
    db.refresh(subject_teacher)
    assert subject_teacher.stem_specialty == "M"

