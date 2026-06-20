from sqlalchemy.orm import Session

from app.models.user import KnownIP


def is_known_ip(db: Session, user_id: int, ip_address: str) -> bool:
    return (
        db.query(KnownIP)
        .filter(KnownIP.user_id == user_id, KnownIP.ip_address == ip_address)
        .first()
        is not None
    )


def register_ip(db: Session, user_id: int, ip_address: str) -> KnownIP:
    known_ip = KnownIP(user_id=user_id, ip_address=ip_address)
    db.add(known_ip)
    db.commit()
    db.refresh(known_ip)
    return known_ip
