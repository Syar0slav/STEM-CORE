import csv
import hashlib
import io
import secrets
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from database import get_db
from models import User, School, Class, ClassStudent, Survey, SurveyResponse, SurveyAnswer, ClassModel, LoginAttempt, TeacherClassAssignment
from user_roles import (
    account_kind,
    assert_user_may_access_class,
    can_export_school_reports,
    filter_classes_by_staff_scope,
    can_view_school_insights,
    is_student,
    is_teacher,
    teacher_linked_class_ids,
)
from student_portal import (
    compute_student_portal_urls,
    find_class_by_school_and_name,
    find_students_by_pib_in_school,
)
from auth import (
    get_current_user,
    require_role,
    require_school_insights_user,
    require_class_model_viewer,
    verify_password,
    get_password_hash,
    create_access_token,
)
from sqlalchemy import func, text
from sqlalchemy.exc import IntegrityError, ProgrammingError

from captcha_math import create_math_captcha, verify_math_captcha
from email_service import send_verification_email
from password_policy import assert_password_strength

from schemas import (
    UserLogin,
    Token,
    SurveyResponseCreate,
    UserRegisterStudent,
    RegisterCaptchaOut,
    StudentRegisterOut,
    VerifyEmailIn,
    ResendVerificationIn,
    StaffRegister,
    PasswordChange,
    MeOut,
    MyRecommendationsOut,
    OkOut,
    SchoolItemOut,
    SchoolDirectoryOut,
    DeputyDirOut,
    StudentDirOut,
    ClassItemOut,
    SurveyItemOut,
    SubmitResponseOut,
    ClassModelOut,
    RecommendationsBundleOut,
    RecommendationItemOut,
    ClassModelArticleOut,
    KTableRowOut,
    SchoolAnalyticsOut,
    DisciplineSummaryItemOut,
    PerDisciplineBreakdownOut,
    SchoolCompareOut,
    AnalyticsClassRow,
    NetworkAnalyticsOut,
    NetworkSchoolRowOut,
    SchoolAdminOut,
    SchoolCreate,
    SchoolUpdate,
    UserAdminOut,
    AdminUsersListOut,
    UserAdminUpdate,
    TeacherProfileMutateIn,
    TeacherAssignmentsOut,
    BulkClassStudentsIn,
    BulkClassStudentsOut,
    ClassStudentPair,
    SchoolPortalLinksPatch,
    ClassSurveyFlagsPatch,
    RosterBulkIn,
    RosterBulkOut,
)
from config import settings
from limiter_setup import limiter
from logging_config import account_suffix, email_fingerprint, log_auth_event

router = APIRouter()


def _reject_support_data_mutation(user: User) -> None:
    if user.role == "user" and user.staff_scope == "support":
        raise HTTPException(status_code=403, detail="Insufficient permissions")


def _assert_teacher_profile_target(db: Session, target: User) -> None:
    if target.role != "user":
        raise HTTPException(
            status_code=400,
            detail="STEM-призначення застосовуються лише до облікових записів role=user без staff_scope",
        )
    if target.staff_scope:
        raise HTTPException(
            status_code=400,
            detail="Для записів із staff_scope (директор, завуч) використовуйте налаштування доступу школи",
        )


def _replace_teacher_assignments(db: Session, target: User, class_ids: list[UUID]) -> None:
    _assert_teacher_profile_target(db, target)
    if target.school_id is None:
        raise HTTPException(status_code=400, detail="Користувач має мати school_id для привʼязки до класів")
    sch = target.school_id
    db.query(TeacherClassAssignment).filter(TeacherClassAssignment.user_id == target.id).delete(
        synchronize_session=False
    )
    for cid in class_ids:
        c = db.query(Class).filter(Class.id == cid).first()
        if not c:
            raise HTTPException(status_code=400, detail="Class not found")
        if c.school_id != sch:
            raise HTTPException(status_code=400, detail="Class belongs to another school")
        db.add(TeacherClassAssignment(user_id=target.id, class_id=cid))


def _class_to_out(c: Class) -> ClassItemOut:
    return ClassItemOut(
        id=str(c.id),
        name=c.name,
        grade=c.grade,
        school_id=str(c.school_id),
        moodle_survey_enabled=getattr(c, "moodle_survey_enabled", None),
        moodle_survey_url=getattr(c, "moodle_survey_url", None),
    )


def _req_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def _school_analytics_to_out(data: dict) -> SchoolAnalyticsOut:
    ds = data.get("discipline_summary") or []
    dbreak = data.get("disciplines") or []
    return SchoolAnalyticsOut(
        school_id=data["school_id"],
        school_name=data["school_name"],
        survey_id=data["survey_id"],
        classes=[AnalyticsClassRow(**c) for c in data["classes"]],
        discipline_summary=[DisciplineSummaryItemOut(**x) for x in ds],
        disciplines=[PerDisciplineBreakdownOut(**x) for x in dbreak],
    )


def _article_to_out(raw: dict) -> ClassModelArticleOut:
    if not raw:
        return ClassModelArticleOut()
    kt = [KTableRowOut.model_validate(r) for r in raw.get("k_table") or []]
    return ClassModelArticleOut(
        s_avg=raw.get("s_avg"),
        t_avg=raw.get("t_avg"),
        e_avg=raw.get("e_avg"),
        m_avg=raw.get("m_avg"),
        ranking=raw.get("ranking"),
        ranking_article=raw.get("ranking_article"),
        k_table=kt,
    )


@router.get("/auth/register-captcha", response_model=RegisterCaptchaOut, tags=["Authentication"])
def register_captcha():
    token, question = create_math_captcha()
    return RegisterCaptchaOut(token=token, question=question)


@router.post("/auth/register", response_model=StudentRegisterOut, tags=["Authentication"])
def register(request: Request, data: UserRegisterStudent, db: Session = Depends(get_db)):
    verify_math_captcha(data.captcha_token, data.captcha_answer)
    assert_password_strength(data.password)
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    smtp_on = bool((settings.smtp_host or "").strip())
    user = User(
        email=data.email,
        password_hash=get_password_hash(data.password),
        full_name=data.full_name,
        role="user",
        school_id=data.school_id,
        email_verified=not smtp_on,
        email_verification_token=None,
    )
    raw_verify = None
    if smtp_on:
        raw_verify = secrets.token_urlsafe(32)
        user.email_verification_token = hashlib.sha256(raw_verify.encode()).hexdigest()
        user.email_verified = False
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        diag = str(getattr(exc, "orig", exc)).lower()
        # FK users.school_id → schools.id (невірний UUID школи) vs унікальний email
        if "school" in diag or "foreign key" in diag or "users_school_id" in diag:
            raise HTTPException(status_code=400, detail="Invalid school_id")
        raise HTTPException(status_code=400, detail="Email already registered")
    except ProgrammingError:
        db.rollback()
        raise HTTPException(
            status_code=503,
            detail="Database schema outdated",
        )
    db.refresh(user)
    log_auth_event(
        "register_student", ok=True, key=account_suffix(user.id), request_id=_req_id(request)
    )
    if smtp_on and raw_verify:
        base = settings.public_base_url.rstrip("/")
        link = f"{base}/verify-email.html?token={raw_verify}"
        send_verification_email(data.email, link)
        return StudentRegisterOut(
            access_token=None,
            message="На вашу пошту надіслано лист із посиланням для підтвердження.",
            email_verification_pending=True,
        )
    token = create_access_token({"sub": str(user.id)})
    return StudentRegisterOut(
        access_token=token,
        message="Обліковий запис створено.",
        email_verification_pending=False,
    )


@router.post("/auth/verify-email", response_model=Token, tags=["Authentication"])
def verify_email(request: Request, data: VerifyEmailIn, db: Session = Depends(get_db)):
    h = hashlib.sha256(data.token.strip().encode()).hexdigest()
    user = db.query(User).filter(User.email_verification_token == h).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired verification link")
    user.email_verified = True
    user.email_verification_token = None
    db.commit()
    log_auth_event(
        "verify_email", ok=True, key=account_suffix(user.id), request_id=_req_id(request)
    )
    return Token(access_token=create_access_token({"sub": str(user.id)}))


@router.post("/auth/resend-verification", tags=["Authentication"])
@limiter.limit("3 per hour")
def resend_verification(request: Request, data: ResendVerificationIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user or user.email_verified:
        return {"ok": True, "message": "Якщо обліковий запис існує, лист буде надіслано."}
    if not (settings.smtp_host or "").strip():
        raise HTTPException(status_code=400, detail="Email verification not configured")
    raw_verify = secrets.token_urlsafe(32)
    user.email_verification_token = hashlib.sha256(raw_verify.encode()).hexdigest()
    db.commit()
    base = settings.public_base_url.rstrip("/")
    link = f"{base}/verify-email.html?token={raw_verify}"
    send_verification_email(data.email, link)
    log_auth_event(
        "resend_verification", ok=True, key=account_suffix(user.id), request_id=_req_id(request)
    )
    return {"ok": True, "message": "Перевірте пошту."}


@router.post("/auth/register-staff", response_model=Token, tags=["Authentication"])
@limiter.limit("10/minute")
def register_staff(request: Request, data: StaffRegister, db: Session = Depends(get_db)):
    if not settings.staff_invite_secret or data.invite_secret != settings.staff_invite_secret:
        raise HTTPException(status_code=403, detail="Invalid or missing invite")
    if data.role not in ("teacher", "deputy", "director", "support"):
        raise HTTPException(status_code=400, detail="Invalid role for staff registration")
    staff_scope = None
    if data.role == "director":
        staff_scope = "school"
    elif data.role == "support":
        staff_scope = "support"
    elif data.role == "deputy":
        p = (data.deputy_parallel or "").strip().upper()
        if p in ("A", "А"):
            staff_scope = "parallel_a"
        elif p in ("B", "Б"):
            staff_scope = "parallel_b"
        else:
            raise HTTPException(
                status_code=400,
                detail="Для завуча вкажіть паралель: A або B (поле deputy_parallel)",
            )
    if data.role in ("director", "support") and not data.school_id:
        raise HTTPException(status_code=400, detail="School ID required for director or support")
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(
        email=data.email,
        password_hash=get_password_hash(data.password),
        full_name=data.full_name,
        role="user",
        staff_scope=staff_scope,
        school_id=data.school_id,
        email_verified=True,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Email already registered")
    db.refresh(user)
    log_auth_event(
        "register_staff", ok=True, key=account_suffix(user.id), request_id=_req_id(request)
    )
    token = create_access_token({"sub": str(user.id)})
    return Token(access_token=token)


@router.post("/auth/login", response_model=Token, tags=["Authentication"])
@limiter.limit("30/minute")
def login(
    request: Request,
    data: UserLogin,
    db: Session = Depends(get_db)
):
    email_key = (data.email or "").strip()
    cutoff = datetime.utcnow() - timedelta(minutes=settings.lockout_minutes)
    recent = db.query(LoginAttempt).filter(
        func.lower(LoginAttempt.email) == email_key.lower(),
        LoginAttempt.created_at > cutoff,
        LoginAttempt.success == False
    ).count()
    if recent >= settings.max_login_attempts:
        raise HTTPException(status_code=429, detail="Too many failed attempts")
    user = db.query(User).filter(func.lower(User.email) == email_key.lower()).first()
    ip = request.client.host if request.client else None
    if not user or not verify_password(data.password, user.password_hash):
        db.add(LoginAttempt(email=email_key, ip_address=ip, success=False))
        db.commit()
        log_auth_event(
            "login",
            ok=False,
            key=email_fingerprint(email_key),
            request_id=_req_id(request),
        )
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.email_verified:
        raise HTTPException(status_code=403, detail="Email not verified")
    db.add(LoginAttempt(email=email_key, ip_address=ip, success=True))
    db.commit()
    log_auth_event("login", ok=True, key=account_suffix(user.id), request_id=_req_id(request))
    token = create_access_token({"sub": str(user.id)})
    return Token(access_token=token)


@router.post("/auth/change-password", response_model=OkOut, tags=["Authentication"])
def change_password(
    request: Request,
    data: PasswordChange,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if len(data.new_password) < 8:
        raise HTTPException(status_code=400, detail="New password must be at least 8 characters")
    if not verify_password(data.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    user.password_hash = get_password_hash(data.new_password)
    db.commit()
    log_auth_event(
        "password_change", ok=True, key=account_suffix(user.id), request_id=_req_id(request)
    )
    return OkOut(ok=True)


@router.get("/me", response_model=MeOut, tags=["Users"])
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ak = account_kind(db, user)
    if ak == "student":
        px = compute_student_portal_urls(
            db, user, settings.student_recordings_url or "", settings.student_moodle_url or ""
        )
        return MeOut(
            id=str(user.id),
            email=user.email,
            role=user.role,
            school_id=str(user.school_id) if user.school_id else None,
            email_verified=bool(user.email_verified),
            staff_scope=user.staff_scope,
            stem_specialty=None,
            account_kind=ak,
            recordings_url=px.get("recordings_url"),
            moodle_url=px.get("moodle_url"),
            moodle_visible=px.get("moodle_visible"),
            lessons_url_parallel=px.get("lessons_url_parallel"),
            lessons_url_school=px.get("lessons_url_school"),
        )
    return MeOut(
        id=str(user.id),
        email=user.email,
        role=user.role,
        school_id=str(user.school_id) if user.school_id else None,
        email_verified=bool(user.email_verified),
        staff_scope=user.staff_scope,
        stem_specialty=user.stem_specialty or None,
        account_kind=ak,
        recordings_url=None,
        moodle_url=None,
        moodle_visible=None,
        lessons_url_parallel=None,
        lessons_url_school=None,
    )


@router.get("/me/teacher-profile", response_model=TeacherAssignmentsOut, tags=["Users"])
def me_teacher_profile(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Підсумок STEM-лінії та класів учителя (об’єднання класного + предметних привʼязок)."""
    if not is_teacher(db, user):
        raise HTTPException(status_code=403, detail="Teacher profile available only for teaching accounts")
    ids = sorted(teacher_linked_class_ids(db, user), key=str)
    return TeacherAssignmentsOut(
        stem_specialty=user.stem_specialty,
        assigned_class_ids=[str(x) for x in ids],
    )


@router.get("/me/recommendations", response_model=MyRecommendationsOut, tags=["Users"])
def my_recommendations(
    survey_id: str | None = Query(None, description="UUID опитування; якщо не вказано — останнє пройдене"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not is_student(db, user):
        raise HTTPException(status_code=403, detail="Only students can access personal recommendations")
    from services import compute_student_model
    from recommendations import build_student_recommendations

    if survey_id:
        surv_uuid = UUID(survey_id)
        data = compute_student_model(db, user.id, surv_uuid)
        sid_str = survey_id
    else:
        last = (
            db.query(SurveyResponse)
            .filter(SurveyResponse.student_id == user.id)
            .order_by(SurveyResponse.submitted_at.desc())
            .first()
        )
        if not last:
            return MyRecommendationsOut()
        surv_uuid = last.survey_id
        sid_str = str(surv_uuid)
        data = compute_student_model(db, user.id, surv_uuid)
    if not data or not data.get("ranking"):
        return MyRecommendationsOut(survey_id=sid_str)
    recs = build_student_recommendations(data["ranking"])
    return MyRecommendationsOut(
        survey_id=sid_str,
        s_avg=data.get("s_avg"),
        t_avg=data.get("t_avg"),
        e_avg=data.get("e_avg"),
        m_avg=data.get("m_avg"),
        ranking=data.get("ranking"),
        recommendations=[RecommendationItemOut(**r) for r in recs],
    )


@router.get("/schools", response_model=list[SchoolItemOut], tags=["Directories"])
def list_schools(
    user: User = Depends(require_school_insights_user()),
    db: Session = Depends(get_db),
):
    if user.role == "admin":
        return [SchoolItemOut(id=str(s.id), name=s.name, city=s.city) for s in db.query(School).all()]
    if user.school_id:
        s = db.query(School).filter(School.id == user.school_id).first()
        return [SchoolItemOut(id=str(s.id), name=s.name, city=s.city)] if s else []
    return []


@router.get("/schools/{school_id}/directory", response_model=SchoolDirectoryOut, tags=["Directories"])
def school_directory(
    school_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Довідник закладу для директора: завучі паралелей та учні (за класами школи). Admin — також."""
    sid = UUID(school_id)
    if user.role != "admin":
        if not (
            user.role == "user"
            and user.staff_scope == "school"
            and user.school_id == sid
        ):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
    school = db.query(School).filter(School.id == sid).first()
    if not school:
        raise HTTPException(status_code=404, detail="School not found")

    deps = (
        db.query(User)
        .filter(
            User.school_id == sid,
            User.staff_scope.in_(("parallel_a", "parallel_b")),
        )
        .order_by(User.staff_scope, User.full_name, User.email)
        .all()
    )
    deputy_rows: list[DeputyDirOut] = []
    for u in deps:
        lbl = "Паралель А" if u.staff_scope == "parallel_a" else "Паралель Б"
        deputy_rows.append(
            DeputyDirOut(email=u.email, full_name=u.full_name, parallel_label=lbl)
        )

    st_ids = [
        r[0]
        for r in db.query(ClassStudent.student_id)
        .join(Class, ClassStudent.class_id == Class.id)
        .filter(Class.school_id == sid)
        .distinct()
        .all()
    ]
    if st_ids:
        students_q = (
            db.query(User)
            .filter(User.id.in_(st_ids))
            .order_by(User.full_name, User.email)
            .all()
        )
    else:
        students_q = []
    st_out = [StudentDirOut(email=u.email, full_name=u.full_name) for u in students_q]

    return SchoolDirectoryOut(
        school_id=str(school.id),
        school_name=school.name,
        school_city=school.city,
        deputy_count=len(deputy_rows),
        deputies=deputy_rows,
        student_count=len(st_out),
        students=st_out,
    )


@router.get("/classes", response_model=list[ClassItemOut], tags=["Directories"])
def list_classes(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    school_id: str = None,
):
    if is_student(db, user):
        rows = db.execute(
            text("SELECT class_id FROM class_students WHERE student_id = CAST(:sid AS uuid)"),
            {"sid": str(user.id)},
        ).fetchall()
        if not rows:
            return []
        ids = [r[0] for r in rows]
        q = db.query(Class).filter(Class.id.in_(ids))
        rows = q.all()
        return [_class_to_out(c) for c in rows]
    q = db.query(Class)
    if user.role == "admin":
        if school_id:
            q = q.filter(Class.school_id == UUID(school_id))
    elif user.role == "user" and user.staff_scope and user.school_id:
        q = q.filter(Class.school_id == user.school_id)
        rows = q.all()
        rows = filter_classes_by_staff_scope(rows, user)
        return [_class_to_out(c) for c in rows]
    elif is_teacher(db, user) and user.id:
        tids = teacher_linked_class_ids(db, user)
        if not tids:
            return []
        rows = db.query(Class).filter(Class.id.in_(tids)).all()
        return [_class_to_out(c) for c in rows]
    elif school_id:
        q = q.filter(Class.school_id == UUID(school_id))
    rows = q.all()
    return [_class_to_out(c) for c in rows]


def _assert_portal_school(user: User, school_id: UUID) -> None:
    if user.role == "admin":
        return
    if not can_view_school_insights(user) or user.school_id != school_id:
        raise HTTPException(status_code=403, detail="Insufficient permissions")


def _apply_school_portal_policy(user: User, raw: dict) -> None:
    if user.role == "admin" or (user.role == "user" and user.staff_scope == "school"):
        return
    if user.staff_scope == "parallel_a":
        if "lessons_url_parallel_b" in raw or "lessons_url_school" in raw:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
    elif user.staff_scope == "parallel_b":
        if "lessons_url_parallel_a" in raw or "lessons_url_school" in raw:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
    else:
        raise HTTPException(status_code=403, detail="Insufficient permissions")


@router.patch("/schools/{school_id}/portal-links", response_model=OkOut, tags=["School portal"])
def patch_school_portal_links(
    school_id: str,
    data: SchoolPortalLinksPatch,
    user: User = Depends(require_school_insights_user()),
    db: Session = Depends(get_db),
):
    sid = UUID(school_id)
    _assert_portal_school(user, sid)
    raw = data.model_dump(exclude_unset=True)
    if not raw:
        raise HTTPException(status_code=400, detail="No fields to update")
    _apply_school_portal_policy(user, raw)
    sch = db.query(School).filter(School.id == sid).first()
    if not sch:
        raise HTTPException(status_code=404, detail="School not found")
    if "lessons_url_parallel_a" in raw:
        sch.lessons_url_parallel_a = raw["lessons_url_parallel_a"]
    if "lessons_url_parallel_b" in raw:
        sch.lessons_url_parallel_b = raw["lessons_url_parallel_b"]
    if "lessons_url_school" in raw:
        sch.lessons_url_school = raw["lessons_url_school"]
    db.commit()
    return OkOut(ok=True)


@router.patch("/classes/{class_id}/survey-flags", response_model=ClassItemOut, tags=["School portal"])
def patch_class_survey_flags(
    class_id: str,
    data: ClassSurveyFlagsPatch,
    user: User = Depends(require_school_insights_user()),
    db: Session = Depends(get_db),
):
    _reject_support_data_mutation(user)
    cid = UUID(class_id)
    c = assert_user_may_access_class(db, user, cid)
    raw = data.model_dump(exclude_unset=True)
    if not raw:
        raise HTTPException(status_code=400, detail="No fields to update")
    if "moodle_survey_enabled" in raw:
        c.moodle_survey_enabled = bool(raw["moodle_survey_enabled"])
    if "moodle_survey_url" in raw:
        v = raw["moodle_survey_url"]
        c.moodle_survey_url = (v.strip() if isinstance(v, str) else None) or None
    if "name" in raw and raw["name"]:
        c.name = raw["name"].strip()[:50]
    if "grade" in raw and raw["grade"] is not None:
        c.grade = int(raw["grade"])
    db.commit()
    db.refresh(c)
    return _class_to_out(c)


@router.post("/schools/{school_id}/roster", response_model=RosterBulkOut, tags=["School portal"])
def post_school_roster(
    school_id: str,
    data: RosterBulkIn,
    user: User = Depends(require_school_insights_user()),
    db: Session = Depends(get_db),
):
    _reject_support_data_mutation(user)
    sid = UUID(school_id)
    _assert_portal_school(user, sid)
    linked = 0
    skipped = 0
    msgs: list[str] = []
    for row in data.rows:
        cl = find_class_by_school_and_name(db, sid, row.class_name)
        if not cl:
            skipped += 1
            msgs.append(f"Клас «{row.class_name}» не знайдено в школі")
            continue
        try:
            assert_user_may_access_class(db, user, cl.id)
        except HTTPException:
            skipped += 1
            msgs.append(f"Немає доступу до класу «{row.class_name}»")
            continue
        matches = find_students_by_pib_in_school(db, sid, row.full_name)
        if len(matches) != 1:
            skipped += 1
            msgs.append(
                f"ПІБ «{row.full_name}»: знайдено {len(matches)} учнів (потрібен рівно один)"
            )
            continue
        st = matches[0]
        ex = (
            db.query(ClassStudent)
            .filter(ClassStudent.class_id == cl.id, ClassStudent.student_id == st.id)
            .first()
        )
        if ex:
            skipped += 1
            msgs.append(f"Уже в класі: {row.full_name}")
            continue
        db.add(ClassStudent(class_id=cl.id, student_id=st.id))
        linked += 1
    db.commit()
    return RosterBulkOut(linked=linked, skipped=skipped, messages=msgs[-100:])


@router.get("/surveys", response_model=list[SurveyItemOut], tags=["Directories"])
def list_surveys(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    rows = db.query(Survey).all()
    return [
        SurveyItemOut(
            id=str(s.id),
            name=s.name,
            school_year=s.school_year,
            is_active=bool(getattr(s, "is_active", True)),
        )
        for s in rows
    ]


@router.post("/responses", response_model=SubmitResponseOut, tags=["Responses"])
def submit_response(
    data: SurveyResponseCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not is_student(db, user):
        raise HTTPException(status_code=403, detail="Only students can submit survey responses")
    survey = db.query(Survey).filter(Survey.id == data.survey_id).first()
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")
    if not getattr(survey, "is_active", True):
        raise HTTPException(status_code=403, detail="Survey is not active")
    existing = db.query(SurveyResponse).filter(
        SurveyResponse.survey_id == data.survey_id,
        SurveyResponse.student_id == user.id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Already submitted")
    resp = SurveyResponse(
        survey_id=data.survey_id,
        student_id=user.id,
        class_id=data.class_id
    )
    db.add(resp)
    db.flush()
    for a in data.answers:
        if 1 <= a.value <= 7:
            db.add(SurveyAnswer(response_id=resp.id, question_code=a.question_code, value=a.value))
    db.commit()
    if data.class_id:
        from services import upsert_class_model
        upsert_class_model(db, data.class_id, data.survey_id)
    return SubmitResponseOut(id=str(resp.id))


@router.get("/class-models/{class_id}/{survey_id}", response_model=ClassModelOut, tags=["Class models"])
def get_class_model(
    class_id: str,
    survey_id: str,
    user: User = Depends(require_class_model_viewer()),
    db: Session = Depends(get_db),
):
    from services import compute_class_model

    assert_user_may_access_class(db, user, UUID(class_id))
    data = compute_class_model(db, class_id, survey_id)
    if not data:
        return ClassModelOut()
    return ClassModelOut(**data)


@router.post("/class-models/{class_id}/{survey_id}/recompute", response_model=ClassModelOut, tags=["Class models"])
def recompute_class_model(
    class_id: str,
    survey_id: str,
    user: User = Depends(require_class_model_viewer()),
    db: Session = Depends(get_db),
):
    from services import upsert_class_model

    assert_user_may_access_class(db, user, UUID(class_id))
    data = upsert_class_model(db, UUID(class_id), UUID(survey_id))
    if not data:
        raise HTTPException(status_code=404, detail="No responses for this class and survey")
    return ClassModelOut(**data)


@router.get(
    "/class-models/{class_id}/{survey_id}/recommendations",
    response_model=RecommendationsBundleOut,
    tags=["Class models"],
)
def get_recommendations(
    class_id: str,
    survey_id: str,
    user: User = Depends(require_class_model_viewer()),
    db: Session = Depends(get_db),
):
    from services import compute_class_model
    from recommendations import build_recommendations

    assert_user_may_access_class(db, user, UUID(class_id))
    data = compute_class_model(db, class_id, survey_id)
    ranking = data.get("ranking") if data else None
    recs = build_recommendations(ranking or "")
    return RecommendationsBundleOut(
        ranking=ranking,
        recommendations=[RecommendationItemOut(**r) for r in recs],
    )


@router.get("/class-models/{class_id}/{survey_id}/article", response_model=ClassModelArticleOut, tags=["Class models"])
def get_class_model_article(
    class_id: str,
    survey_id: str,
    user: User = Depends(require_class_model_viewer()),
    db: Session = Depends(get_db),
):
    from class_model_article import compute_class_model_article

    assert_user_may_access_class(db, user, UUID(class_id))
    return _article_to_out(compute_class_model_article(db, class_id, survey_id))


@router.get("/admin/network-analytics", response_model=NetworkAnalyticsOut, tags=["Admin"])
def get_network_analytics(
    survey_id: str = Query(..., description="UUID опитування"),
    user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    from analytics_network import network_schools_snapshot

    rows = network_schools_snapshot(db, survey_id)
    return NetworkAnalyticsOut(
        survey_id=survey_id,
        schools=[NetworkSchoolRowOut(**r) for r in rows],
    )


_ROLES = frozenset({"admin", "user"})
_VALID_STAFF_SCOPES = frozenset({"parallel_a", "parallel_b", "school"})


def _parse_bulk_csv(body: bytes) -> list[ClassStudentPair]:
    try:
        text = body.decode("utf-8-sig")
    except UnicodeDecodeError as e:
        raise HTTPException(status_code=400, detail="Invalid CSV encoding") from e
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    pairs: list[ClassStudentPair] = []
    for i, line in enumerate(lines):
        parts = [p.strip() for p in line.split(",")]
        if len(parts) != 2:
            raise HTTPException(status_code=400, detail="Invalid CSV row")
        key = parts[0].lower().replace(" ", "_")
        if i == 0 and key in ("class_id", "classid"):
            continue
        try:
            pairs.append(
                ClassStudentPair(class_id=UUID(parts[0]), student_id=UUID(parts[1]))
            )
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid CSV row")
    if not pairs:
        raise HTTPException(status_code=400, detail="No rows in CSV")
    return pairs


def _is_bulk_student_account(db: Session, u: User) -> bool:
    return is_student(db, u)


def _apply_bulk_class_students(db: Session, pairs: list[ClassStudentPair]) -> int:
    inserted = 0
    for p in pairs:
        st = db.query(User).filter(User.id == p.student_id).first()
        if not st or not _is_bulk_student_account(db, st):
            raise HTTPException(status_code=400, detail="Invalid student in bulk list")
        cl = db.query(Class).filter(Class.id == p.class_id).first()
        if not cl:
            raise HTTPException(status_code=400, detail="Class not found")
        r = db.execute(
            text(
                """
                INSERT INTO class_students (class_id, student_id)
                VALUES (CAST(:cid AS uuid), CAST(:sid AS uuid))
                ON CONFLICT DO NOTHING
                RETURNING 1
                """
            ),
            {"cid": str(p.class_id), "sid": str(p.student_id)},
        )
        if r.first():
            inserted += 1
    return inserted


@router.get("/admin/schools", response_model=list[SchoolAdminOut], tags=["Admin"])
def admin_list_schools(
    _user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    rows = db.query(School).order_by(School.name).all()
    return [
        SchoolAdminOut(
            id=str(s.id),
            name=s.name,
            city=s.city,
            created_at=s.created_at.isoformat() if s.created_at else None,
        )
        for s in rows
    ]


@router.post("/admin/schools", response_model=SchoolAdminOut, tags=["Admin"])
def admin_create_school(
    data: SchoolCreate,
    _user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    name = data.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="School name required")
    s = School(name=name, city=data.city.strip() if data.city else None)
    db.add(s)
    db.commit()
    db.refresh(s)
    return SchoolAdminOut(
        id=str(s.id),
        name=s.name,
        city=s.city,
        created_at=s.created_at.isoformat() if s.created_at else None,
    )


@router.patch("/admin/schools/{school_id}", response_model=SchoolAdminOut, tags=["Admin"])
def admin_update_school(
    school_id: str,
    data: SchoolUpdate,
    _user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    s = db.query(School).filter(School.id == UUID(school_id)).first()
    if not s:
        raise HTTPException(status_code=404, detail="School not found")
    patch = data.model_dump(exclude_unset=True)
    if not patch:
        raise HTTPException(status_code=400, detail="No fields to update")
    if "name" in patch:
        n = (patch["name"] or "").strip()
        if not n:
            raise HTTPException(status_code=400, detail="Invalid name")
        s.name = n
    if "city" in patch:
        s.city = patch["city"].strip() if patch["city"] else None
    db.commit()
    db.refresh(s)
    return SchoolAdminOut(
        id=str(s.id),
        name=s.name,
        city=s.city,
        created_at=s.created_at.isoformat() if s.created_at else None,
    )


@router.get("/admin/users", response_model=AdminUsersListOut, tags=["Admin"])
def admin_list_users(
    _user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
    limit: int = Query(100, ge=1, le=500, description="Розмір сторінки"),
    offset: int = Query(0, ge=0, description="Зміщення"),
    email_contains: str | None = Query(
        None,
        max_length=255,
        description="Фільтр: email містить рядок (без урахування регістру)",
    ),
):
    q = db.query(User)
    if email_contains and email_contains.strip():
        term = f"%{email_contains.strip()}%"
        q = q.filter(User.email.ilike(term))
    q = q.order_by(User.email)
    total = q.count()
    rows = q.limit(limit).offset(offset).all()
    return AdminUsersListOut(
        total=total,
        limit=limit,
        offset=offset,
        items=[
            UserAdminOut(
                id=str(u.id),
                email=u.email,
                full_name=u.full_name,
                role=u.role,
                school_id=str(u.school_id) if u.school_id else None,
                staff_scope=u.staff_scope,
                stem_specialty=u.stem_specialty,
                created_at=u.created_at.isoformat() if u.created_at else None,
            )
            for u in rows
        ],
    )


@router.get("/admin/users/export", tags=["Admin"])
def admin_export_users_csv(
    _user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
    email_contains: str | None = Query(
        None,
        max_length=255,
        description="Той самий фільтр, що й для списку (до 10000 рядків)",
    ),
):
    q = db.query(User).order_by(User.email)
    if email_contains and email_contains.strip():
        q = q.filter(User.email.ilike(f"%{email_contains.strip()}%"))
    rows = q.limit(10_000).all()
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(
        ["id", "email", "full_name", "role", "school_id", "staff_scope", "stem_specialty", "created_at"]
    )
    for u in rows:
        w.writerow(
            [
                str(u.id),
                u.email,
                u.full_name or "",
                u.role,
                str(u.school_id) if u.school_id else "",
                u.staff_scope or "",
                u.stem_specialty or "",
                u.created_at.isoformat() if u.created_at else "",
            ]
        )
    body = buf.getvalue().encode("utf-8-sig")
    return Response(
        content=body,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="users.csv"'},
    )


@router.patch("/admin/users/{user_id}", response_model=UserAdminOut, tags=["Admin"])
def admin_update_user(
    user_id: str,
    data: UserAdminUpdate,
    _user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    u = db.query(User).filter(User.id == UUID(user_id)).first()
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    patch = data.model_dump(exclude_unset=True)
    if not patch:
        raise HTTPException(status_code=400, detail="No fields to update")
    if "role" in patch:
        r = patch["role"]
        if r is None or r not in _ROLES:
            raise HTTPException(status_code=400, detail="Invalid role")
        u.role = r
    if "staff_scope" in patch:
        ss = patch["staff_scope"]
        if ss is not None and ss not in _VALID_STAFF_SCOPES:
            raise HTTPException(status_code=400, detail="Invalid staff_scope")
        u.staff_scope = ss
    if "school_id" in patch:
        sid = patch["school_id"]
        if sid is None:
            u.school_id = None
        else:
            sch = db.query(School).filter(School.id == sid).first()
            if not sch:
                raise HTTPException(status_code=400, detail="School not found")
            u.school_id = sid
    if "stem_specialty" in patch:
        u.stem_specialty = patch["stem_specialty"]
    if "assigned_class_ids" in patch:
        _replace_teacher_assignments(db, u, patch["assigned_class_ids"])
    db.commit()
    db.refresh(u)
    return UserAdminOut(
        id=str(u.id),
        email=u.email,
        full_name=u.full_name,
        role=u.role,
        school_id=str(u.school_id) if u.school_id else None,
        staff_scope=u.staff_scope,
        stem_specialty=u.stem_specialty,
        created_at=u.created_at.isoformat() if u.created_at else None,
    )


@router.post("/admin/class-students/bulk", response_model=BulkClassStudentsOut, tags=["Admin"])
def admin_bulk_class_students(
    data: BulkClassStudentsIn,
    _user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    inserted = _apply_bulk_class_students(db, data.pairs)
    db.commit()
    return BulkClassStudentsOut(inserted=inserted)


@router.post("/admin/class-students/bulk-csv", response_model=BulkClassStudentsOut, tags=["Admin"])
async def admin_bulk_class_students_csv(
    request: Request,
    _user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    raw = await request.body()
    pairs = _parse_bulk_csv(raw)
    inserted = _apply_bulk_class_students(db, pairs)
    db.commit()
    return BulkClassStudentsOut(inserted=inserted)


@router.patch(
    "/schools/{school_id}/users/{user_id}/teacher-profile",
    response_model=TeacherAssignmentsOut,
    tags=["School staff"],
)
def school_patch_teacher_profile(
    school_id: str,
    user_id: str,
    data: TeacherProfileMutateIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Директор школи (або admin) задає STEM-лінію та предметні привʼязки класів для вчителя."""
    _reject_support_data_mutation(user)
    sid_u = UUID(school_id)
    uid = UUID(user_id)
    if user.role == "admin":
        pass
    elif user.role == "user" and user.staff_scope == "school" and user.school_id == sid_u:
        pass
    else:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    tgt = db.query(User).filter(User.id == uid).first()
    if not tgt:
        raise HTTPException(status_code=404, detail="User not found")
    if tgt.school_id != sid_u:
        raise HTTPException(status_code=400, detail="User is not assigned to this school")
    patch = data.model_dump(exclude_unset=True)
    if not patch:
        raise HTTPException(status_code=400, detail="No fields to update")
    if "stem_specialty" in patch:
        tgt.stem_specialty = patch["stem_specialty"]
    if "assigned_class_ids" in patch:
        _replace_teacher_assignments(db, tgt, patch["assigned_class_ids"])
    db.commit()
    db.refresh(tgt)
    tids = sorted(teacher_linked_class_ids(db, tgt), key=str)
    return TeacherAssignmentsOut(
        stem_specialty=tgt.stem_specialty,
        assigned_class_ids=[str(x) for x in tids],
    )


@router.get("/schools/{school_id}/analytics", response_model=SchoolAnalyticsOut, tags=["School analytics"])
def get_school_analytics(
    school_id: str,
    survey_id: str,
    user: User = Depends(require_school_insights_user()),
    db: Session = Depends(get_db),
):
    from analytics import school_analytics

    data = school_analytics(db, user, school_id, survey_id)
    if data is None:
        raise HTTPException(status_code=403, detail="Forbidden or school not found")
    return _school_analytics_to_out(data)


@router.get("/schools/{school_id}/compare", response_model=SchoolCompareOut, tags=["School analytics"])
def get_school_compare(
    school_id: str,
    survey_a: str,
    survey_b: str,
    user: User = Depends(require_school_insights_user()),
    db: Session = Depends(get_db),
):
    from analytics import school_compare

    data = school_compare(db, user, school_id, survey_a, survey_b)
    if data is None:
        raise HTTPException(status_code=403, detail="Forbidden or school not found")
    return SchoolCompareOut(
        semester_a=_school_analytics_to_out(data["semester_a"]),
        semester_b=_school_analytics_to_out(data["semester_b"]),
    )


@router.get("/schools/{school_id}/export", tags=["School analytics"])
def export_school(
    school_id: str,
    survey_id: str,
    survey_id_b: str | None = Query(
        None,
        description="Друге опитування: якщо вказано разом із survey_id, експорт містить обидва півріччя",
    ),
    format: str = "csv",
    user: User = Depends(require_school_insights_user()),
    db: Session = Depends(get_db),
):
    if not can_export_school_reports(user):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    from export_report import (
        export_school_survey_csv,
        export_school_survey_csv_compare,
        export_school_survey_docx,
        export_school_survey_docx_compare,
        export_school_survey_pdf,
        export_school_survey_pdf_compare,
        export_school_survey_xlsx,
        export_school_survey_xlsx_compare,
    )

    fmt = (format or "csv").lower().strip()
    id_a = survey_id.strip()
    id_b = (survey_id_b or "").strip()
    compare = bool(id_b)

    if compare and id_b == id_a:
        raise HTTPException(
            status_code=400,
            detail="Для порівняльного експорту потрібні два різні опитування.",
        )

    if compare:
        safe_name = f"school-{school_id}-compare-{id_a[:8]}-{id_b[:8]}"
    else:
        safe_name = f"school-{school_id}-{survey_id}"

    if fmt == "xlsx":
        body = (
            export_school_survey_xlsx_compare(db, user, school_id, id_a, id_b)
            if compare
            else export_school_survey_xlsx(db, user, school_id, id_a)
        )
        if not body:
            raise HTTPException(status_code=403, detail="No data")
        return Response(
            content=body,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{safe_name}.xlsx"'},
        )
    if fmt == "pdf":
        body = (
            export_school_survey_pdf_compare(db, user, school_id, id_a, id_b)
            if compare
            else export_school_survey_pdf(db, user, school_id, id_a)
        )
        if not body:
            raise HTTPException(status_code=403, detail="No data")
        return Response(
            content=body,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{safe_name}.pdf"'},
        )
    if fmt in ("docx", "word", "docs"):
        body = (
            export_school_survey_docx_compare(db, user, school_id, id_a, id_b)
            if compare
            else export_school_survey_docx(db, user, school_id, id_a)
        )
        if not body:
            raise HTTPException(status_code=403, detail="No data")
        return Response(
            content=body,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f'attachment; filename="{safe_name}.docx"'},
        )
    if fmt != "csv":
        raise HTTPException(
            status_code=400,
            detail="Unsupported format. Use: csv, xlsx, pdf, docx.",
        )
    body = (
        export_school_survey_csv_compare(db, user, school_id, id_a, id_b)
        if compare
        else export_school_survey_csv(db, user, school_id, id_a)
    )
    if not body:
        raise HTTPException(status_code=403, detail="No data")
    return Response(
        content=body,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}.csv"'},
    )
