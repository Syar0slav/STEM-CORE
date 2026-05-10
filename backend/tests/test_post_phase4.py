"""Тести після фази 4: rate limit, ролі deputy, кілька шкіль у мережі."""
import uuid

import pytest
from models import Class, School, SurveyAnswer, SurveyResponse, User

from tests.conftest import CLASS_ID, SURVEY_ID, SCHOOL_ID, auth_headers


def _answers():
    codes = [
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
    return [{"question_code": c, "value": 4} for c in codes]


def _seed_response(db, student_id):
    resp = SurveyResponse(survey_id=SURVEY_ID, student_id=student_id, class_id=CLASS_ID)
    db.add(resp)
    db.flush()
    for a in _answers():
        db.add(SurveyAnswer(response_id=resp.id, question_code=a["question_code"], value=a["value"]))
    db.commit()


@pytest.mark.slow
def test_login_endpoint_rate_limit_eventually_429(client):
    """SlowAPI: після серії запитів з’являється 429 (ліміт / хвилину)."""
    saw_429 = False
    for i in range(40):
        r = client.post(
            "/api/auth/login",
            json={"email": f"rate{i}@example.com", "password": "wrongpass"},
        )
        if r.status_code == 429:
            saw_429 = True
            break
    assert saw_429


def test_deputy_can_access_school_analytics(client, db, seed_school_survey_class):
    from auth import get_password_hash

    u = User(
        email=f"dep_{uuid.uuid4().hex}@example.com",
        password_hash=get_password_hash("Test1!pass"),
        role="user",
        staff_scope="parallel_a",
        school_id=SCHOOL_ID,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    st = User(
        email=f"stu_{uuid.uuid4().hex}@example.com",
        password_hash=get_password_hash("Test1!pass"),
        role="user",
        school_id=SCHOOL_ID,
    )
    db.add(st)
    db.commit()
    db.refresh(st)
    _seed_response(db, st.id)

    r = client.get(
        f"/api/schools/{SCHOOL_ID}/analytics?survey_id={SURVEY_ID}",
        headers=auth_headers(u),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["school_id"] == str(SCHOOL_ID)
    assert "classes" in body
    assert len(body["classes"]) >= 1


def test_deputy_export_csv(client, db, seed_school_survey_class):
    from auth import get_password_hash

    u = User(
        email=f"dep2_{uuid.uuid4().hex}@example.com",
        password_hash=get_password_hash("Test1!pass"),
        role="user",
        staff_scope="parallel_a",
        school_id=SCHOOL_ID,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    st = User(
        email=f"stu2_{uuid.uuid4().hex}@example.com",
        password_hash=get_password_hash("Test1!pass"),
        role="user",
        school_id=SCHOOL_ID,
    )
    db.add(st)
    db.commit()
    db.refresh(st)
    _seed_response(db, st.id)

    r = client.get(
        f"/api/schools/{SCHOOL_ID}/export?survey_id={SURVEY_ID}&format=csv",
        headers=auth_headers(u),
    )
    assert r.status_code == 200
    assert "csv" in (r.headers.get("content-type") or "").lower()
    assert len(r.content) > 10


def test_deputy_export_pdf_docx(client, db, seed_school_survey_class):
    from auth import get_password_hash

    u = User(
        email=f"dep3_{uuid.uuid4().hex}@example.com",
        password_hash=get_password_hash("Test1!pass"),
        role="user",
        staff_scope="parallel_a",
        school_id=SCHOOL_ID,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    st = User(
        email=f"stu3_{uuid.uuid4().hex}@example.com",
        password_hash=get_password_hash("Test1!pass"),
        role="user",
        school_id=SCHOOL_ID,
    )
    db.add(st)
    db.commit()
    db.refresh(st)
    _seed_response(db, st.id)

    r_pdf = client.get(
        f"/api/schools/{SCHOOL_ID}/export?survey_id={SURVEY_ID}&format=pdf",
        headers=auth_headers(u),
    )
    assert r_pdf.status_code == 200
    assert r_pdf.content[:4] == b"%PDF"
    assert len(r_pdf.content) > 100

    r_docx = client.get(
        f"/api/schools/{SCHOOL_ID}/export?survey_id={SURVEY_ID}&format=docx",
        headers=auth_headers(u),
    )
    assert r_docx.status_code == 200
    assert r_docx.content[:2] == b"PK"
    assert len(r_docx.content) > 200


def test_network_analytics_two_schools(client, db, seed_school_survey_class, admin_user):
    sid2 = uuid.UUID("a0000000-0000-0000-0000-000000000002")
    db.add(School(id=sid2, name="School B", city="Lviv"))
    db.add(
        Class(
            id=uuid.UUID("c0000000-0000-0000-0000-000000000002"),
            school_id=sid2,
            name="6-B",
            grade=6,
        )
    )
    db.commit()

    u = User(
        email=f"stu3_{uuid.uuid4().hex}@example.com",
        password_hash="x",
        role="user",
        school_id=SCHOOL_ID,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    _seed_response(db, u.id)

    r = client.get(
        f"/api/admin/network-analytics?survey_id={SURVEY_ID}",
        headers=auth_headers(admin_user),
    )
    assert r.status_code == 200
    schools = r.json().get("schools", [])
    assert len(schools) >= 1
    ids = {s["school_id"] for s in schools}
    assert str(SCHOOL_ID) in ids
