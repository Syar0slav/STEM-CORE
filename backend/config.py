from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://postgres:postgres@localhost:5432/stem_diagnostic"
    secret_key: str = "change-in-production-use-env"
    staff_invite_secret: str = ""
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    max_login_attempts: int = 5
    lockout_minutes: int = 15
    # Список дозволених Origin через кому, або "*" для всіх (лише dev)
    cors_origins: str = "*"
    # Одним рядком JSON у логах audit (stem.audit)
    audit_json: bool = False
    # Логувати повільні запити (мс); 0 = вимкнено
    slow_request_threshold_ms: int = 0
    # Один рядок access-логу на кожен запит (stem.access), без PII
    access_log: bool = False
    # Базовий URL застосунку для посилань у листах (без завершального слешу)
    public_base_url: str = "http://127.0.0.1:8000"
    # Сторінка учня: записи занять (YouTube/Meet/Drive тощо) та курс Moodle — з .env
    student_recordings_url: str = ""
    student_moodle_url: str = ""
    # SMTP для підтвердження email; якщо smtp_host порожній — лист не надсилається
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_use_tls: bool = True

    class Config:
        env_file = ".env"


def parse_cors_origins(value: str) -> list[str]:
    v = (value or "").strip()
    if not v or v == "*":
        return ["*"]
    return [x.strip() for x in v.split(",") if x.strip()]


settings = Settings()
