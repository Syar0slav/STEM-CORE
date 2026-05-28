import logging
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from logging_config import setup_logging

setup_logging()
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.exc import OperationalError, ProgrammingError
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from config import parse_cors_origins, settings
from database import get_db
from routes import router
from middleware import (
    AccessLogMiddleware,
    CorrelationIdMiddleware,
    SecurityHeadersMiddleware,
    SlowRequestMiddleware,
)
from limiter_setup import limiter

app = FastAPI(
    title="STEM. Цифровий діагностичний інструмент API",
    openapi_tags=[
        {"name": "Authentication", "description": "Реєстрація, вхід, пароль"},
        {"name": "Users", "description": "Профіль і персональні дані"},
        {"name": "Directories", "description": "Школи, класи, опитування"},
        {"name": "Responses", "description": "Відповіді опитування"},
        {"name": "Class models", "description": "Модель класу та рекомендації"},
        {"name": "School analytics", "description": "Аналітика та експорт по школі"},
        {
            "name": "Admin",
            "description": "Мережеві зведення, CRUD шкіл/користувачів, bulk class_students (лише admin)",
        },
    ],
)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)


logger = logging.getLogger("stem.api")


@app.exception_handler(ProgrammingError)
def programming_error_handler(request: Request, exc: ProgrammingError):
    logger.exception("SQL ProgrammingError path=%s", request.url.path)
    return JSONResponse(
        status_code=503,
        content={"detail": "Database schema outdated"},
    )


@app.exception_handler(OperationalError)
def operational_error_handler(request: Request, exc: OperationalError):
    logger.exception("SQL OperationalError path=%s", request.url.path)
    return JSONResponse(
        status_code=503,
        content={"detail": "Database unavailable"},
    )


@app.exception_handler(RateLimitExceeded)
def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    path = request.url.path.rstrip("/")
    detail = "Too many requests"
    if path.endswith("/auth/resend-verification") and request.method == "POST":
        detail = "Resend verification rate limited"
    return JSONResponse(status_code=429, content={"detail": detail})


app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(SlowRequestMiddleware)
app.add_middleware(AccessLogMiddleware)
app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=parse_cors_origins(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")


def _resolve_frontend_path() -> Path:
    """Локально: STEM-CORE/frontend (каталог поруч із backend/). У Docker: /app/frontend поруч із main.py."""
    base = Path(__file__).resolve().parent
    sibling = base / "frontend"
    if sibling.is_dir() and (sibling / "index.html").is_file():
        return sibling
    return base.parent / "frontend"


frontend_path = _resolve_frontend_path()
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")


@app.get("/")
def root():
    index_file = frontend_path / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"name": "STEM. Цифровий діагностичний інструмент", "version": "1.0"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/health/ready")
def health_ready(db: Session = Depends(get_db)):
    """Перевірка з’єднання з БД і наявності колонок users (міграції)."""
    try:
        db.execute(text("SELECT 1"))
        rows = db.execute(
            text(
                """
                SELECT column_name FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = 'users'
                  AND column_name IN ('email_verified', 'email_verification_token')
                """
            )
        ).fetchall()
        have = {r[0] for r in rows}
        need = {"email_verified", "email_verification_token"}
        if not need.issubset(have):
            missing = list(need - have)
            return JSONResponse(
                status_code=503,
                content={
                    "status": "error",
                    "database": "schema_incomplete",
                    "missing_user_columns": missing,
                    "hint": "Сервіс потребує оновлення налаштувань. Зверніться до адміністратора.",
                },
            )
    except Exception as e:
        logger.warning("health_ready DB check failed: %s", e)
        return JSONResponse(
            status_code=503,
            content={"status": "error", "database": "unreachable"},
        )
    return {
        "status": "ok",
        "database": "reachable",
        "users_migrations": "ok",
    }


@app.get("/{path:path}")
def serve_frontend(path: str):
    file_path = frontend_path / path
    if file_path.is_file():
        return FileResponse(file_path)
    if (frontend_path / "index.html").exists():
        return FileResponse(frontend_path / "index.html")
    return {"error": "Not found"}
