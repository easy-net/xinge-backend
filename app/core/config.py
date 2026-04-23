import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass
class Settings:
    app_env: str = "development"
    database_url: str = "sqlite+pysqlite:////tmp/xinge.db"
    encryption_key: str = "0123456789abcdef0123456789abcdef"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        app_env=os.getenv("APP_ENV", "development"),
        database_url=os.getenv("DATABASE_URL", "sqlite+pysqlite:////tmp/xinge.db"),
        encryption_key=os.getenv("ENCRYPTION_KEY", "0123456789abcdef0123456789abcdef"),
    )
