"""403 для не-admin на /api/admin/*; валідація bulk CSV / порожнього JSON."""
import uuid

from auth import get_password_hash
from models import Class, User

from tests.conftest import CLASS_ID, SCHOOL_ID, auth_headers, seed_school_survey_class


def test_non_admin_forbidden_admin_schools(client, db, seed_school_survey_class):
    u = User(
        email=f"teacher_{uuid.uuid4().hex}@example.com",
        password_hash=get_password_hash("secret123"),
        full_name="T",
        role="user",
        school_id=SCHOOL_ID,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    cl = db.query(Class).filter(Class.id == CLASS_ID).first()
    cl.teacher_id = u.id
    db.commit()
    h = auth_headers(u)
    r = client.get("/api/admin/schools", headers=h)
    assert r.status_code == 403
    assert r.json().get("detail") == "Insufficient permissions"


def test_non_admin_forbidden_bulk(client, db, seed_school_survey_class):
    u = User(
        email=f"dep_{uuid.uuid4().hex}@example.com",
        password_hash=get_password_hash("secret123"),
        full_name="D",
        role="user",
        staff_scope="parallel_a",
        school_id=SCHOOL_ID,
    )
    db.add(u)
    db.commit()
    h = auth_headers(u)
    r = client.post(
        "/api/admin/class-students/bulk",
        json={"pairs": []},
        headers=h,
    )
    assert r.status_code == 403


def test_admin_bulk_empty_pairs(client, admin_user, seed_school_survey_class):
    h = auth_headers(admin_user)
    r = client.post(
        "/api/admin/class-students/bulk",
        json={"pairs": []},
        headers=h,
    )
    assert r.status_code == 200
    assert r.json()["inserted"] == 0


def test_admin_bulk_csv_invalid_row(client, admin_user, seed_school_survey_class):
    h = auth_headers(admin_user)
    r = client.post(
        "/api/admin/class-students/bulk-csv",
        content="not-a-uuid,also-bad\n",
        headers={**h, "Content-Type": "text/csv; charset=utf-8"},
    )
    assert r.status_code == 400
    assert r.json().get("detail") == "Invalid CSV row"


def test_admin_bulk_csv_header_only(client, admin_user, seed_school_survey_class):
    h = auth_headers(admin_user)
    r = client.post(
        "/api/admin/class-students/bulk-csv",
        content="class_id,student_id\n",
        headers={**h, "Content-Type": "text/csv; charset=utf-8"},
    )
    assert r.status_code == 400
    assert r.json().get("detail") == "No rows in CSV"
