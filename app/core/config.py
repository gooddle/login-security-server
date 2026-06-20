from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite:///./app.db"
    secret_key: str = "dev-secret-key"
    resend_api_key: str = ""
    email_from: str = "security@example.com"

    class Config:
        env_file = ".env"


settings = Settings()
