"""Middleware package for the Smart Data Platform."""

from app.middleware.audit import AuditMiddleware

__all__ = ["AuditMiddleware"]
