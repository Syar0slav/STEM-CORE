"""Admin CRUD: школи, користувачі, bulk class_students."""
import uuid

from auth import get_password_hash
from models import User

from tests.conftest import CLASS_ID, SCHOOL_ID, auth_headers, seed_school_survey_class


def test_admin_create_and_list_school(client, admin_user, seed_school_survey_class):
    h = auth_headers(admin_user)
    r = client.post(
        "/api/admin/schools",
        json={"name": "  New School  ", "city": "Lviv"},
        headers=h,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "New School"
    assert data["city"] == "Lviv"
    sid = data["id"]

    r2 = client.get("/api/admin/schools", headers=h)
    assert r2.status_code == 200
    ids = {x["id"] for x in r2.json()}
    assert sid in ids


def test_admin_bulk_class_students(client, db, admin_user, seed_school_survey_class):
    st = User(
        email=f"stu_{uuid.uuid4().hex}@example.com",
        password_hash=get_password_hash("secret123"),
        full_name="Student",
        role="user",
        school_id=SCHOOL_ID,
    )
    db.add(st)
    db.commit()
    db.refresh(st)

    h = auth_headers(admin_user)
    r = client.post(
        "/api/admin/class-students/bulk",
        json={"pairs": [{"class_id": str(CLASS_ID), "student_id": str(st.id)}]},
        headers=h,
    )
    assert r.status_code == 200
    assert r.json()["inserted"] == 1

    r2 = client.post(
        "/api/admin/class-students/bulk",
        json={"pairs": [{"class_id": str(CLASS_ID), "student_id": str(st.id)}]},
        headers=h,
    )
    assert r2.status_code == 200
    assert r2.json()["inserted"] == 0


def test_admin_list_users_pagination(client, admin_user, seed_school_survey_class):
    h = auth_headers(admin_user)
    r = client.get("/api/admin/users?limit=5&offset=0", headers=h)
    assert r.status_code == 200
    data = r.json()
    assert "items" in data and "total" in data
    assert data["limit"] == 5
    assert data["offset"] == 0
    assert isinstance(data["items"], list)


def test_admin_users_export_csv(client, admin_user, seed_school_survey_class):
    h = auth_headers(admin_user)
    r = client.get("/api/admin/users/export", headers=h)
    assert r.status_code == 200
    assert "text/csv" in (r.headers.get("content-type") or "")
    assert b"id,email" in r.content


def test_admin_bulk_csv_success_inserts_row(client, db, admin_user, seed_school_survey_class):
    st = User(
        email=f"stu_csv_{uuid.uuid4().hex}@example.com",
        password_hash=get_password_hash("secret123"),
        full_name="CSV Student",
        role="user",
        school_id=SCHOOL_ID,
    )
    db.add(st)
    db.commit()
    db.refresh(st)
    h = auth_headers(admin_user)
    body = f"class_id,student_id\n{CLASS_ID},{st.id}\n"
    r = client.post(
        "/api/admin/class-students/bulk-csv",
        content=body,
        headers={**h, "Content-Type": "text/csv; charset=utf-8"},
    )
    assert r.status_code == 200
    assert r.json()["inserted"] == 1


def test_admin_patch_user_school(client, db, admin_user, seed_school_survey_class):
    st = User(
        email=f"stu2_{uuid.uuid4().hex}@example.com",
        password_hash=get_password_hash("secret123"),
        full_name="S2",
        role="user",
        school_id=None,
    )
    db.add(st)
    db.commit()
    db.refresh(st)

    h = auth_headers(admin_user)
    r = client.patch(
        f"/api/admin/users/{st.id}",
        json={"school_id": str(SCHOOL_ID)},
        headers=h,
    )
    assert r.status_code == 200
    assert r.json()["school_id"] == str(SCHOOL_ID)
