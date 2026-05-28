"""Обмеження staff_scope «support»: аналітика так, файл-експорт — ні."""

import uuid

import pytest
from sqlalchemy.orm import Session

from auth import create_access_token, get_password_hash
from conftest import CLASS_ID, SCHOOL_ID, SURVEY_ID
from models import User


@pytest.fixture
def school_support_user(db: Session, seed_school_survey_class) -> User:
    uid = uuid.uuid4()
    u = User(
        id=uid,
        email=f"support_{uid.hex[:8]}@example.com",
        password_hash=get_password_hash("Support1!x"),
        role="user",
        staff_scope="support",
        school_id=SCHOOL_ID,
        email_verified=True,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _h(u: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token({'sub': str(u.id)})}"}


def test_support_can_read_school_analytics(client, school_support_user: User):
    r = client.get(
        f"/api/schools/{SCHOOL_ID}/analytics?survey_id={SURVEY_ID}",
        headers=_h(school_support_user),
    )
    assert r.status_code == 200
    assert "classes" in r.json()


def test_support_cannot_export_csv(client, school_support_user: User):
    r = client.get(
        f"/api/schools/{SCHOOL_ID}/export?survey_id={SURVEY_ID}&format=csv",
        headers=_h(school_support_user),
    )
    assert r.status_code == 403


def test_support_cannot_patch_class_flags(client, school_support_user: User):
    r = client.patch(
        f"/api/classes/{CLASS_ID}/survey-flags",
        json={"moodle_survey_enabled": False},
        headers=_h(school_support_user),
    )
    assert r.status_code == 403
