from datetime import datetime, timedelta, timezone

import bcrypt
from sqlalchemy.orm import Session

from app.models.user import User
from app.services.email_service import send_new_ip_alert
from app.services.ip_service import is_known_ip, register_ip


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email).first()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def create_user(db: Session, email: str, password: str) -> User:
    user = User(email=email, hashed_password=hash_password(password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def is_account_locked(user: User) -> tuple[bool, int]:
    """잠금 여부와 남은 초를 반환. locked_until이 지났으면 자동 해제."""
    if user.locked_until is None:
        return False, 0
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if now >= user.locked_until:
        return False, 0
    remaining = int((user.locked_until - now).total_seconds())
    return True, remaining


def record_failed_attempt(db: Session, user: User) -> None:
    user.failed_attempts = int(user.failed_attempts) + 1  # type: ignore[assignment]
    if int(user.failed_attempts) >= 5:
        user.locked_until = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=30)  # type: ignore[assignment]
    db.commit()


def reset_failed_attempts(db: Session, user: User) -> None:
    user.failed_attempts = 0  # type: ignore[assignment]
    user.locked_until = None  # type: ignore[assignment]
    db.commit()


def authenticate_user(db: Session, email: str, password: str, ip_address: str) -> User | None:
    user = get_user_by_email(db, email)
    if not user:
        return None

    locked, remaining = is_account_locked(user)
    if locked:
        minutes = remaining // 60
        seconds = remaining % 60
        raise ValueError(f"계정이 잠겼습니다. {minutes}분 {seconds}초 후 다시 시도하세요")

    if not verify_password(password, str(user.hashed_password)):
        record_failed_attempt(db, user)
        return None

    reset_failed_attempts(db, user)

    if not is_known_ip(db, int(user.id), ip_address):
        send_new_ip_alert(str(user.email), ip_address)
        register_ip(db, int(user.id), ip_address)

    return user
