"""compute_class_model та модель за статтею."""
import uuid

import pytest

from auth import get_password_hash
from class_model_article import compute_class_model_article
from models import SurveyAnswer, SurveyResponse, User
from services import compute_class_model, upsert_class_model

from tests.conftest import CLASS_ID, SCHOOL_ID, SURVEY_ID


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
    return [{"question_code": c, "value": 4} for c in codes]


@pytest.fixture
def unique_student(db, seed_school_survey_class):
    """Окремий учень на тест (обмеження UNIQUE survey_id, student_id)."""
    email = f"stu_{uuid.uuid4().hex}@example.com"
    u = User(
        email=email,
        password_hash=get_password_hash("Test1!pass"),
        full_name="T",
        role="user",
        school_id=SCHOOL_ID,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _submit_response(db, student: User):
    resp = SurveyResponse(
        survey_id=SURVEY_ID,
        student_id=student.id,
        class_id=CLASS_ID,
    )
    db.add(resp)
    db.flush()
    for a in _full_answers():
        db.add(
            SurveyAnswer(
                response_id=resp.id,
                question_code=a["question_code"],
                value=a["value"],
            )
        )
    db.commit()


def test_compute_class_model_after_response(db, unique_student):
    _submit_response(db, unique_student)
    data = compute_class_model(db, str(CLASS_ID), str(SURVEY_ID))
    assert data
    assert data["s_avg"] == 4.0
    assert "ranking" in data


def test_upsert_class_model(db, unique_student):
    _submit_response(db, unique_student)
    out = upsert_class_model(db, CLASS_ID, SURVEY_ID)
    assert out and out.get("ranking")


def test_article_model_has_k_table(db, unique_student):
    _submit_response(db, unique_student)
    art = compute_class_model_article(db, str(CLASS_ID), str(SURVEY_ID))
    assert art.get("ranking_article")
    assert len(art.get("k_table", [])) == 5
    parts = [p for p in art["ranking_article"].split("-") if p]
    assert len(parts) == 4
    assert set(parts) == {"S", "T", "E", "M"}
