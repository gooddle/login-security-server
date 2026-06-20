import bcrypt
from sqlalchemy.orm import Session

from app.models.user import User
from app.services.ip_service import is_known_ip, register_ip
from app.services.email_service import send_new_ip_alert


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


def authenticate_user(db: Session, email: str, password: str, ip_address: str) -> User | None:
    user = get_user_by_email(db, email)
    if not user or not verify_password(password, user.hashed_password):
        return None

    if not is_known_ip(db, user.id, ip_address):
        send_new_ip_alert(user.email, ip_address)
        register_ip(db, user.id, ip_address)

    return user
