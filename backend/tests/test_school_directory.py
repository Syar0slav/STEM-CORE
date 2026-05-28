"""Довідник школи /api/schools/{id}/directory — лише директор своєї школи або admin."""
import uuid

from models import ClassStudent, User

from tests.conftest import CLASS_ID, SCHOOL_ID, auth_headers
from tests.conftest import seed_school_survey_class  # noqa: F401
from auth import get_password_hash


def test_school_directory_director_ok(client, db, seed_school_survey_class):
    dir_id = uuid.uuid4()
    u = User(
        id=dir_id,
        email="dir_dir_test@example.com",
        password_hash=get_password_hash("x"),
        role="user",
        staff_scope="school",
        school_id=SCHOOL_ID,
        email_verified=True,
    )
    db.add(u)
    db.commit()
    r = client.get(
        f"/api/schools/{SCHOOL_ID}/directory",
        headers=auth_headers(u),
    )
    assert r.status_code == 200
    data = r.json()
    assert data["school_id"] == str(SCHOOL_ID)
    assert "school_name" in data
    assert isinstance(data["deputies"], list)
    assert isinstance(data["students"], list)


def test_school_directory_student_forbidden(client, db, seed_school_survey_class):
    st = User(
        email="stu_dir_test@example.com",
        password_hash="x",
        role="user",
        school_id=SCHOOL_ID,
        email_verified=True,
    )
    db.add(st)
    db.commit()
    db.refresh(st)
    db.add(ClassStudent(class_id=CLASS_ID, student_id=st.id))
    db.commit()
    r = client.get(
        f"/api/schools/{SCHOOL_ID}/directory",
        headers=auth_headers(st),
    )
    assert r.status_code == 403
