from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.auth_service import authenticate_user

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    message: str
    email: str


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest, request: Request, db: Session = Depends(get_db)):
    ip = request.client.host
    user = authenticate_user(db, body.email, body.password, ip)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="인증 실패")
    return LoginResponse(message="로그인 성공", email=user.email)
