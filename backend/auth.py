from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from config import settings
from database import get_db
from models import User, LoginAttempt
from password_hashing import hash_password as get_password_hash
from password_hashing import verify_password

security = HTTPBearer(auto_error=False)


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    # RFC 7519: exp — NumericDate (секунди Unix). datetime у payload часто ламає python-jose / валідацію.
    to_encode.update({"exp": int(expire.timestamp())})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError:
        return None


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = decode_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def require_role(*roles: str):
    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return checker


def require_school_insights_user():
    """Адмін або завуч/директор (user + staff_scope)."""

    def checker(user: User = Depends(get_current_user)) -> User:
        from user_roles import can_view_school_insights

        if can_view_school_insights(user):
            return user
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    return checker


def require_class_model_viewer():
    """Адмін, керівництво школи або класний керівник."""

    def dep(
        user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        if user.role == "admin":
            return user
        if user.role != "user":
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        if user.staff_scope is not None:
            return user
        from user_roles import is_teacher

        if is_teacher(db, user):
            return user
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    return dep
