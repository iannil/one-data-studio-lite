# Core exports
# Lazy import scheduler to avoid loading apscheduler when not needed
from app.core.config import settings
from app.core.database import Base, get_db, engine, AsyncSessionLocal
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    decode_access_token,
    SQLSecurityValidator,
    SQLSecurityError,
)

def __getattr__(name: str):
    if name == "scheduler":
        from app.core.scheduler import scheduler as _scheduler
        return _scheduler
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "settings",
    "Base",
    "get_db",
    "engine",
    "AsyncSessionLocal",
    "verify_password",
    "get_password_hash",
    "create_access_token",
    "decode_access_token",
    "SQLSecurityValidator",
    "SQLSecurityError",
    "scheduler",
]
