"""Опитування: is_active та заборона подання відповіді на неактивне."""
import uuid

import pytest
from models import Survey, User

from tests.conftest import CLASS_ID, SURVEY_ID, SCHOOL_ID, admin_user, auth_headers
from tests.test_phase4 import _full_answers

INACTIVE_SURVEY_ID = uuid.UUID("b0000000-0000-0000-0000-000000000099")


@pytest.fixture
def inactive_survey(db, seed_school_survey_class):
    s = db.query(Survey).filter(Survey.id == INACTIVE_SURVEY_ID).first()
    if not s:
        db.add(
            Survey(
                id=INACTIVE_SURVEY_ID,
                name="Архівне опитування",
                school_year="2023-2024",
                is_active=False,
            )
        )
        db.commit()


def test_surveys_list_includes_is_active(client, db, seed_school_survey_class, admin_user, inactive_survey):
    r = client.get("/api/surveys", headers=auth_headers(admin_user))
    assert r.status_code == 200
    rows = r.json()
    by_id = {x["id"]: x for x in rows}
    assert by_id[str(SURVEY_ID)]["is_active"] is True
    assert by_id[str(INACTIVE_SURVEY_ID)]["is_active"] is False


def test_submit_inactive_survey_forbidden(client, db, seed_school_survey_class, inactive_survey):
    u = User(
        email=f"st_inact_{uuid.uuid4().hex}@example.com",
        password_hash="x",
        role="user",
        school_id=SCHOOL_ID,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    payload = {
        "survey_id": str(INACTIVE_SURVEY_ID),
        "class_id": str(CLASS_ID),
        "answers": _full_answers(),
    }
    r = client.post("/api/responses", json=payload, headers=auth_headers(u))
    assert r.status_code == 403
    assert "not active" in r.json().get("detail", "").lower()
