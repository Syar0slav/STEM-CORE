from sqlalchemy import (
    Column,
    String,
    Integer,
    Boolean,
    DateTime,
    ForeignKey,
    Numeric,
    Text,
    CheckConstraint,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, INET
from sqlalchemy.orm import relationship
from datetime import datetime

from database import Base
import uuid


def gen_uuid():
    return str(uuid.uuid4())


class School(Base):
    __tablename__ = "schools"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    city = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    # Уроки/матеріали для учнів (завуч А / Б / директор)
    lessons_url_parallel_a = Column(Text, nullable=True)
    lessons_url_parallel_b = Column(Text, nullable=True)
    lessons_url_school = Column(Text, nullable=True)


class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255))
    role = Column(String(20), nullable=False)
    # Для role=user: parallel_a / parallel_b — завуч відповідної паралелі; school — директор
    staff_scope = Column(String(20), nullable=True)
    school_id = Column(UUID(as_uuid=True), ForeignKey("schools.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    email_verified = Column(Boolean, nullable=False, default=True)
    email_verification_token = Column(String(128), nullable=True)
    __table_args__ = (
        CheckConstraint("role IN ('admin', 'user')", name="users_role_check"),
        CheckConstraint(
            "staff_scope IS NULL OR staff_scope IN ('parallel_a', 'parallel_b', 'school')",
            name="users_staff_scope_check",
        ),
    )


class Class(Base):
    __tablename__ = "classes"
    __table_args__ = (
        UniqueConstraint("school_id", "name", name="uq_classes_school_id_name"),
    )
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    school_id = Column(UUID(as_uuid=True), ForeignKey("schools.id"), nullable=False)
    name = Column(String(50), nullable=False)
    grade = Column(Integer, nullable=False)
    teacher_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    # Показувати посилання на опитування в Moodle лише якщо завуч/директор увімкнув для класу
    moodle_survey_enabled = Column(Boolean, nullable=False, default=False)
    moodle_survey_url = Column(Text, nullable=True)


class ClassStudent(Base):
    """Зв'язок учень ↔ клас (таблиця `class_students` у schema.sql)."""

    __tablename__ = "class_students"
    class_id = Column(UUID(as_uuid=True), ForeignKey("classes.id"), primary_key=True)
    student_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)


class Survey(Base):
    __tablename__ = "surveys"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    school_year = Column(String(20))
    started_at = Column(DateTime, default=datetime.utcnow)
    closed_at = Column(DateTime)


class SurveyResponse(Base):
    __tablename__ = "survey_responses"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    survey_id = Column(UUID(as_uuid=True), ForeignKey("surveys.id"), nullable=False)
    student_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    class_id = Column(UUID(as_uuid=True), ForeignKey("classes.id"))
    submitted_at = Column(DateTime, default=datetime.utcnow)


class SurveyAnswer(Base):
    __tablename__ = "survey_answers"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    response_id = Column(UUID(as_uuid=True), ForeignKey("survey_responses.id"), nullable=False)
    question_code = Column(String(10), nullable=False)
    value = Column(Integer, nullable=False)
    __table_args__ = (CheckConstraint("value >= 1 AND value <= 7", name="survey_answers_value_check"),)


class ClassModel(Base):
    __tablename__ = "class_models"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    class_id = Column(UUID(as_uuid=True), ForeignKey("classes.id"), nullable=False)
    survey_id = Column(UUID(as_uuid=True), ForeignKey("surveys.id"), nullable=False)
    s_avg = Column(Numeric(5, 2))
    t_avg = Column(Numeric(5, 2))
    e_avg = Column(Numeric(5, 2))
    m_avg = Column(Numeric(5, 2))
    ranking = Column(String(20))
    created_at = Column(DateTime, default=datetime.utcnow)


class LoginAttempt(Base):
    __tablename__ = "login_attempts"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), nullable=False)
    ip_address = Column(String(45))
    success = Column(Boolean)
    created_at = Column(DateTime, default=datetime.utcnow)
