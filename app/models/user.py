from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    known_ips = relationship("KnownIP", back_populates="user")


class KnownIP(Base):
    __tablename__ = "known_ips"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    ip_address = Column(String, nullable=False)
    first_seen_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="known_ips")
