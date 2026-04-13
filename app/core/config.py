import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv(
        "DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/rplibrary"
    )
    jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "dev-secret-change-me")
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    jwt_expire_minutes: int = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))
    default_admin_email: str | None = os.getenv("DEFAULT_ADMIN_EMAIL")


settings = Settings()
