import strawberry


@strawberry.type
class SignupResult:
    email: str


@strawberry.type
class LoginResult:
    message: str
    email: str


@strawberry.type
class Query:
    @strawberry.field
    def health(self) -> str:
        return "ok"
