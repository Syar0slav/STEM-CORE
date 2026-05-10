"""Pytest fixtures: set DATABASE_URL before any backend import."""
import os
import uuid

import pytest
from sqlalchemy.orm import Session

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql://postgres:postgres@127.0.0.1:5432/stem_test",
)
os.environ.setdefault("STAFF_INVITE_SECRET", "test-invite-secret")

from database import SessionLocal, engine  # noqa: E402
from models import Base, Class, School, Survey, User  # noqa: E402
from auth import create_access_token, get_password_hash  # noqa: E402


@pytest.fixture(scope="session")
def setup_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db(setup_database) -> Session:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(setup_database):
    from fastapi.testclient import TestClient

    from main import app

    with TestClient(app) as c:
        yield c


# --- seed helpers (fixed UUIDs for stable tests) ---

SCHOOL_ID = uuid.UUID("a0000000-0000-0000-0000-000000000001")
SURVEY_ID = uuid.UUID("b0000000-0000-0000-0000-000000000001")
CLASS_ID = uuid.UUID("c0000000-0000-0000-0000-000000000001")


@pytest.fixture
def seed_school_survey_class(db: Session):
    s = db.query(School).filter(School.id == SCHOOL_ID).first()
    if not s:
        db.add(School(id=SCHOOL_ID, name="Test School", city="Test"))
    su = db.query(Survey).filter(Survey.id == SURVEY_ID).first()
    if not su:
        db.add(
            Survey(
                id=SURVEY_ID,
                name="STEM Test",
                school_year="2024-2025",
            )
        )
    cl = db.query(Class).filter(Class.id == CLASS_ID).first()
    if not cl:
        db.add(
            Class(
                id=CLASS_ID,
                school_id=SCHOOL_ID,
                name="5-A",
                grade=5,
            )
        )
    db.commit()


@pytest.fixture
def admin_user(db: Session, seed_school_survey_class) -> User:
    email = f"admin_{uuid.uuid4().hex}@example.com"
    u = User(
        email=email,
        password_hash=get_password_hash("Test1!pass"),
        full_name="Admin",
        role="admin",
        school_id=None,
        email_verified=True,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def auth_headers(user: User) -> dict:
    return {"Authorization": f"Bearer {create_access_token({'sub': str(user.id)})}"}

