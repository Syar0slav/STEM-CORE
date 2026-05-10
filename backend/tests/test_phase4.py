"""Фаза 4: персональні рекомендації, мережеві зведення, доступ."""
import uuid

from models import Class, SurveyAnswer, SurveyResponse, User

from tests.conftest import CLASS_ID, SURVEY_ID, SCHOOL_ID, auth_headers


def _full_answers():
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
    return [{"question_code": c, "value": 5} for c in codes]


def test_me_recommendations_student(client, db, seed_school_survey_class):
    u = User(
        email=f"st_{uuid.uuid4().hex}@example.com",
        password_hash="x",
        role="user",
        school_id=SCHOOL_ID,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    resp = SurveyResponse(survey_id=SURVEY_ID, student_id=u.id, class_id=CLASS_ID)
    db.add(resp)
    db.flush()
    for a in _full_answers():
        db.add(SurveyAnswer(response_id=resp.id, question_code=a["question_code"], value=a["value"]))
    db.commit()

    r = client.get("/api/me/recommendations", headers=auth_headers(u))
    assert r.status_code == 200
    data = r.json()
    assert data.get("ranking")
    assert data.get("recommendations")


def test_me_recommendations_forbidden_for_teacher(client, db, seed_school_survey_class):
    u = User(
        email=f"te_{uuid.uuid4().hex}@example.com",
        password_hash="x",
        role="user",
        school_id=SCHOOL_ID,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    cl = db.query(Class).filter(Class.id == CLASS_ID).first()
    cl.teacher_id = u.id
    db.commit()
    r = client.get("/api/me/recommendations", headers=auth_headers(u))
    assert r.status_code == 403


def test_network_analytics_admin(client, db, seed_school_survey_class, admin_user):
    u = User(
        email=f"st2_{uuid.uuid4().hex}@example.com",
        password_hash="x",
        role="user",
        school_id=SCHOOL_ID,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    resp = SurveyResponse(survey_id=SURVEY_ID, student_id=u.id, class_id=CLASS_ID)
    db.add(resp)
    db.flush()
    for a in _full_answers():
        db.add(SurveyAnswer(response_id=resp.id, question_code=a["question_code"], value=a["value"]))
    db.commit()

    r = client.get(
        f"/api/admin/network-analytics?survey_id={SURVEY_ID}",
        headers=auth_headers(admin_user),
    )
    assert r.status_code == 200
    data = r.json()
    assert data.get("survey_id")
    assert len(data.get("schools", [])) >= 1


def test_network_analytics_forbidden_for_student(client, db, seed_school_survey_class):
    u = User(
        email=f"st3_{uuid.uuid4().hex}@example.com",
        password_hash="x",
        role="user",
        school_id=SCHOOL_ID,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    r = client.get(
        f"/api/admin/network-analytics?survey_id={SURVEY_ID}",
        headers=auth_headers(u),
    )
    assert r.status_code == 403
