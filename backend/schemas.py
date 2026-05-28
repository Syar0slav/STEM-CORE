from uuid import UUID
from typing import Annotated, Optional

from email_validator import EmailNotValidError, validate_email
from pydantic import AfterValidator, BaseModel, Field, field_validator, model_validator


def _email_relaxed(value: str) -> str:
    """Як EmailStr, але дозволяє демо-домени (.local тощо), які інакше відхиляє email-validator."""
    try:
        return validate_email(
            value.strip(),
            check_deliverability=False,
            test_environment=True,
        ).normalized
    except EmailNotValidError as e:
        raise ValueError(getattr(e, "reason", None) or str(e)) from e


FlexibleEmailStr = Annotated[str, AfterValidator(_email_relaxed)]


def _login_email_only(value: str) -> str:
    """Лише для входу: збіг з рядком у БД, без суворого RFC (демо @*.local тощо)."""
    if not isinstance(value, str):
        raise ValueError("Email має бути рядком")
    s = value.strip()
    if len(s) < 3 or len(s) > 255:
        raise ValueError("Некоректний email")
    if s.count("@") != 1:
        raise ValueError("Некоректний email")
    local, _, domain = s.partition("@")
    if not local.strip() or not domain.strip():
        raise ValueError("Некоректний email")
    return s


LoginEmailStr = Annotated[str, AfterValidator(_login_email_only)]


class UserRegisterStudent(BaseModel):
    email: FlexibleEmailStr
    password: str = Field(min_length=8, max_length=128)
    password_confirm: str
    captcha_token: str
    captcha_answer: str
    full_name: Optional[str] = None
    school_id: Optional[UUID] = None

    @model_validator(mode="after")
    def passwords_match(self) -> "UserRegisterStudent":
        if self.password != self.password_confirm:
            raise ValueError("Passwords do not match")
        return self


class RegisterCaptchaOut(BaseModel):
    token: str
    question: str


class StudentRegisterOut(BaseModel):
    access_token: str | None = None
    token_type: str = "bearer"
    message: str = ""
    email_verification_pending: bool = False


class VerifyEmailIn(BaseModel):
    token: str = Field(min_length=8)


class ResendVerificationIn(BaseModel):
    email: FlexibleEmailStr


class StaffRegister(BaseModel):
    email: FlexibleEmailStr
    password: str
    full_name: Optional[str] = None
    role: str
    school_id: Optional[UUID] = None
    invite_secret: str
    # Для завуча: паралель А чи Б (латиниця або кирилиця)
    deputy_parallel: Optional[str] = None


class UserLogin(BaseModel):
    email: LoginEmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class SurveyAnswerCreate(BaseModel):
    question_code: str
    value: int


class SurveyResponseCreate(BaseModel):
    survey_id: UUID
    class_id: Optional[UUID] = None
    answers: list[SurveyAnswerCreate]


class ClassModelOut(BaseModel):
    s_avg: Optional[float]
    t_avg: Optional[float]
    e_avg: Optional[float]
    m_avg: Optional[float]
    ranking: Optional[str]


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


class RecommendationItemOut(BaseModel):
    discipline: str
    title: str
    hints: list[str]
    video_url: Optional[str] = None
    video_title: Optional[str] = None
    course_title: Optional[str] = None
    course_url: Optional[str] = None
    course_note: Optional[str] = None


class MeOut(BaseModel):
    id: str
    email: FlexibleEmailStr
    role: str
    school_id: str | None = None
    email_verified: bool = True
    staff_scope: str | None = None
    stem_specialty: Optional[str] = None  # S / T / E / M для вчителя
    account_kind: str = "user"
    # Учень: записи (глобально), уроки за паралеллю/школою, Moodle — лише якщо клас увімкнув
    recordings_url: Optional[str] = None
    moodle_url: Optional[str] = None
    moodle_visible: Optional[bool] = None
    lessons_url_parallel: Optional[str] = None
    lessons_url_school: Optional[str] = None


class MyRecommendationsOut(BaseModel):
    survey_id: str | None = None
    s_avg: float | None = None
    t_avg: float | None = None
    e_avg: float | None = None
    m_avg: float | None = None
    ranking: str | None = None
    recommendations: list[RecommendationItemOut] = []


class OkOut(BaseModel):
    ok: bool = True


class SchoolItemOut(BaseModel):
    id: str
    name: str
    city: str | None = None


class DeputyDirOut(BaseModel):
    email: str
    full_name: str | None = None
    parallel_label: str


class StudentDirOut(BaseModel):
    email: str
    full_name: str | None = None


class SchoolDirectoryOut(BaseModel):
    school_id: str
    school_name: str
    school_city: str | None = None
    deputy_count: int
    deputies: list[DeputyDirOut]
    student_count: int
    students: list[StudentDirOut]


class ClassItemOut(BaseModel):
    id: str
    name: str
    grade: int
    school_id: str
    moodle_survey_enabled: Optional[bool] = None
    moodle_survey_url: Optional[str] = None


class SurveyItemOut(BaseModel):
    id: str
    name: str
    school_year: str | None = None
    is_active: bool = True


class SubmitResponseOut(BaseModel):
    id: str


class RecommendationsBundleOut(BaseModel):
    ranking: str | None = None
    recommendations: list[RecommendationItemOut] = []


class KTableRowOut(BaseModel):
    k: str
    order: list[str]


class ClassModelArticleOut(ClassModelOut):
    ranking_article: str | None = None
    k_table: list[KTableRowOut] = []


class AnalyticsClassRow(ClassModelOut):
    class_id: str
    name: str
    grade: int
    response_count: Optional[int] = None


class DisciplineSummaryItemOut(BaseModel):
    """Зведення по дисциплінах: середнє по класах, ранг від найкращого до найгіршого, частка для діаграми."""

    code: str
    label: str
    avg: Optional[float] = None
    pct_share: Optional[float] = None
    rank: int


class DisciplineClassItemOut(BaseModel):
    """Клас у зрізі однієї дисципліни: середнє 1–7 і кількість урахованих проходжень (учні)."""

    class_id: str
    name: str
    grade: int
    avg: float
    response_count: Optional[int] = None


class PerDisciplineBreakdownOut(BaseModel):
    code: str
    label: str
    classes: list[DisciplineClassItemOut] = Field(default_factory=list)


class SchoolAnalyticsOut(BaseModel):
    school_id: str
    school_name: str
    survey_id: str
    classes: list[AnalyticsClassRow]
    discipline_summary: list[DisciplineSummaryItemOut] = Field(default_factory=list)
    disciplines: list[PerDisciplineBreakdownOut] = Field(default_factory=list)


class SchoolCompareOut(BaseModel):
    semester_a: SchoolAnalyticsOut
    semester_b: SchoolAnalyticsOut


class NetworkSchoolRowOut(BaseModel):
    school_id: str
    school_name: str
    city: str | None = None
    classes_with_responses: int
    s_avg: float
    t_avg: float
    e_avg: float
    m_avg: float


class NetworkAnalyticsOut(BaseModel):
    survey_id: str
    schools: list[NetworkSchoolRowOut]


class SchoolCreate(BaseModel):
    name: str
    city: Optional[str] = None


class SchoolUpdate(BaseModel):
    name: Optional[str] = None
    city: Optional[str] = None


class SchoolAdminOut(BaseModel):
    id: str
    name: str
    city: Optional[str] = None
    created_at: Optional[str] = None


class UserAdminOut(BaseModel):
    id: str
    email: FlexibleEmailStr
    full_name: Optional[str] = None
    role: str
    school_id: Optional[str] = None
    staff_scope: Optional[str] = None
    stem_specialty: Optional[str] = None
    created_at: Optional[str] = None


class AdminUsersListOut(BaseModel):
    """Пагінований список користувачів для admin."""

    items: list[UserAdminOut]
    total: int
    limit: int
    offset: int


class TeacherProfileMutateIn(BaseModel):
    """Оновлення STEM-лінії та призначень (доступ адміна або директора школи)."""

    stem_specialty: Optional[str] = None  # одна літера або None
    assigned_class_ids: Optional[list[UUID]] = Field(
        default=None,
        description="Повний набір зв’язків через teacher_class_assignments (замість попереднього складу таблиці).",
    )

    @field_validator("stem_specialty", mode="before")
    @classmethod
    def _norm_stem(cls, v):  # noqa: ANN001
        if v is None or (isinstance(v, str) and not v.strip()):
            return None
        if isinstance(v, str):
            s = v.strip().upper()
            if len(s) == 1 and s in {"S", "T", "E", "M"}:
                return s
        raise ValueError("stem_specialty must be null or one of S, T, E, M")


class UserAdminUpdate(BaseModel):
    role: Optional[str] = None
    school_id: Optional[UUID] = None
    staff_scope: Optional[str] = None
    stem_specialty: Optional[str] = None
    assigned_class_ids: Optional[list[UUID]] = Field(
        default=None,
        description="Замінює лише записи teacher_class_assignments.",
    )

    @field_validator("stem_specialty", mode="before")
    @classmethod
    def _norm_admin_stem(cls, v):  # noqa: ANN001
        if v is None or (isinstance(v, str) and not v.strip()):
            return None
        if isinstance(v, str):
            s = v.strip().upper()
            if len(s) == 1 and s in {"S", "T", "E", "M"}:
                return s
        raise ValueError("stem_specialty must be null or one of S, T, E, M")


class TeacherAssignmentsOut(BaseModel):
    stem_specialty: Optional[str] = None
    assigned_class_ids: list[str] = Field(default_factory=list)


class ClassStudentPair(BaseModel):
    class_id: UUID
    student_id: UUID


class BulkClassStudentsIn(BaseModel):
    pairs: list[ClassStudentPair]


class BulkClassStudentsOut(BaseModel):
    inserted: int


class SchoolPortalLinksPatch(BaseModel):
    lessons_url_parallel_a: Optional[str] = None
    lessons_url_parallel_b: Optional[str] = None
    lessons_url_school: Optional[str] = None


class ClassSurveyFlagsPatch(BaseModel):
    moodle_survey_enabled: Optional[bool] = None
    moodle_survey_url: Optional[str] = None
    name: Optional[str] = Field(None, max_length=50)
    grade: Optional[int] = Field(None, ge=1, le=12)


class RosterRowIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=255)
    class_name: str = Field(min_length=1, max_length=50)


class RosterBulkIn(BaseModel):
    rows: list[RosterRowIn]


class RosterBulkOut(BaseModel):
    linked: int
    skipped: int
    messages: list[str] = []
