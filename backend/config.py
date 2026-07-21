"""
config.py — All tuneable thresholds and environment variables.
Thresholds are NOT hardcoded in business logic — change them here only.
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── Database ────────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://smartfiler:smartfiler@localhost:5432/smartfiler"
    DATABASE_URL_SYNC: str = "postgresql://smartfiler:smartfiler@localhost:5432/smartfiler"

    # ── Redis / Celery ───────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    # ── Google OAuth ─────────────────────────────────────────────────────────
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/auth/google/callback"
    # Scopes: drive.file (write to files we create) + drive.metadata.readonly (read folder tree)
    GOOGLE_SCOPES: list[str] = [
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile",
        "https://www.googleapis.com/auth/drive.file",
        "https://www.googleapis.com/auth/drive.metadata.readonly",
    ]

    # ── LLM (Anthropic) ──────────────────────────────────────────────────────
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-3-5-sonnet-20241022"

    # ── Embeddings ───────────────────────────────────────────────────────────
    EMBEDDING_API_KEY: str = ""
    EMBEDDING_MODEL: str = "voyage-3"
    EMBEDDING_BASE_URL: str = "https://api.voyageai.com/v1"
    EMBEDDING_DIMENSION: int = 1024

    # ── Security ─────────────────────────────────────────────────────────────
    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    ENCRYPTION_KEY: str = ""  # 32-byte base64 key for Fernet; generated on first run

    # ── Placement thresholds (Section 6, tunable per Section 12) ────────────
    PLACEMENT_AUTO_THRESHOLD: float = 0.85     # ≥ this → auto-suggest, no question
    PLACEMENT_QUESTION_THRESHOLD: float = 0.60  # ≥ this → ask one question; < this → show top-3 + free text
    CLUSTERING_SIMILARITY_THRESHOLD: float = 0.75  # pairwise cosine sim for cluster grouping
    RULE_MATCH_THRESHOLD: float = 0.90         # rule short-circuit (learning loop)
    RULE_CONFIDENCE_MIN_HITS: int = 3           # hits before rule is auto-confident

    # ── Misc ─────────────────────────────────────────────────────────────────
    FRONTEND_URL: str = "http://localhost:5173"
    TEMP_DIR: str = "/tmp/smartfiler"
    MAX_UPLOAD_MB: int = 50

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
