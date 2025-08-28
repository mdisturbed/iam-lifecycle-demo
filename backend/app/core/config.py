import os
from pydantic import BaseModel

class Settings(BaseModel):
    POSTGRES_URL: str = os.getenv("POSTGRES_URL", "postgresql+psycopg://iam:iam@db:5432/iam")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://redis:6379/0")
    CONNECTOR_MODE: str = os.getenv("CONNECTOR_MODE", "MOCK")  # MOCK or REAL

    GOOGLE_SA_KEY_JSON_BASE64: str | None = os.getenv("GOOGLE_SA_KEY_JSON_BASE64")
    GITHUB_TOKEN: str | None = os.getenv("GITHUB_TOKEN")
    GITHUB_ORG: str | None = os.getenv("GITHUB_ORG")

settings = Settings()
