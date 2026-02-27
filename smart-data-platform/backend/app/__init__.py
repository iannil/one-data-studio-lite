# Lazy import to avoid loading the full FastAPI app when importing from app package
# This allows scripts to import models and services without loading the entire application
def __getattr__(name: str):
    if name == "app":
        from app.main import app as _app
        return _app
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = ["app"]
