import re
import strawberry
from strawberry.types import Info

from app.graphql.types import SignupResult, LoginResult
from app.services.auth_service import authenticate_user, create_user, get_user_by_email


def _validate_email(email: str) -> bool:
    return bool(re.match(r"^[^@]+@[^@]+\.[^@]+$", email))


@strawberry.type
class Mutation:
    @strawberry.mutation
    def signup(self, info: Info, email: str, password: str) -> SignupResult:
        if not _validate_email(email):
            raise ValueError("유효하지 않은 이메일 형식입니다")
        if len(password) < 8:
            raise ValueError("비밀번호는 8자 이상이어야 합니다")

        db = info.context["db"]
        if get_user_by_email(db, email):
            raise ValueError("이미 존재하는 이메일입니다")

        user = create_user(db, email, password)
        return SignupResult(email=user.email)

    @strawberry.mutation
    def login(self, info: Info, email: str, password: str) -> LoginResult:
        db = info.context["db"]
        request = info.context["request"]
        ip = request.client.host

        user = authenticate_user(db, email, password, ip)
        if not user:
            raise ValueError("인증 실패")

        return LoginResult(message="로그인 성공", email=user.email)
