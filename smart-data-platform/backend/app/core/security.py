from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(
    subject: str | int,
    expires_delta: timedelta | None = None,
    extra_data: dict[str, Any] | None = None,
) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode = {"exp": expire, "sub": str(subject)}
    if extra_data:
        to_encode.update(extra_data)

    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any] | None:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        return None


# ============================================================================
# SQL Security Validator
# ============================================================================


class SQLSecurityError(Exception):
    """Exception raised when SQL contains dangerous operations."""

    def __init__(self, message: str, dangerous_patterns: list[str]):
        self.message = message
        self.dangerous_patterns = dangerous_patterns
        super().__init__(self.message)


class SQLSecurityValidator:
    """Validates SQL queries for dangerous operations.

    Provides SQL injection protection by blocking dangerous patterns
    and enforcing read-only operations.
    """

    # Dangerous SQL patterns that should be blocked
    DANGEROUS_PATTERNS = [
        (r'\bDROP\s+(TABLE|DATABASE|INDEX|VIEW|SCHEMA)\b', 'DROP statement'),
        (r'\bTRUNCATE\s+TABLE\b', 'TRUNCATE TABLE'),
        (r'\bDELETE\s+FROM\b', 'DELETE FROM'),
        (r'\bALTER\s+(TABLE|DATABASE)\b', 'ALTER statement'),
        (r'\bCREATE\s+(TABLE|DATABASE|INDEX)\b', 'CREATE statement'),
        (r'\bINSERT\s+INTO\b', 'INSERT INTO'),
        (r'\bUPDATE\s+\w+\s+SET\b', 'UPDATE statement'),
        (r'\bGRANT\b', 'GRANT statement'),
        (r'\bREVOKE\b', 'REVOKE statement'),
        (r'\bEXEC(UTE)?\s*\(', 'EXECUTE/EXEC function'),
        (r'\bxp_\w+', 'Extended stored procedures'),
        (r'\bsp_\w+', 'System stored procedures'),
        (r';\s*--', 'SQL comment injection'),
        (r'\bUNION\s+(ALL\s+)?SELECT\b.*\bFROM\s+information_schema\b', 'Information schema access via UNION'),
        (r'\bSLEEP\s*\(', 'SLEEP function (timing attack)'),
        (r'\bBENCHMARK\s*\(', 'BENCHMARK function'),
        (r'\bLOAD_FILE\s*\(', 'LOAD_FILE function'),
        (r'\bINTO\s+(OUT|DUMP)FILE\b', 'INTO OUTFILE/DUMPFILE'),
    ]

    # Allowed patterns (whitelist approach for read-only operations)
    ALLOWED_PATTERNS = [
        r'^\s*SELECT\b',
        r'^\s*WITH\b.*\bSELECT\b',  # CTE queries
        r'^\s*EXPLAIN\b',
        r'^\s*SHOW\b',
        r'^\s*DESCRIBE\b',
    ]

    @classmethod
    def validate(cls, sql: str) -> tuple[bool, list[str]]:
        """Validate SQL query for dangerous operations.

        Args:
            sql: SQL query string to validate.

        Returns:
            Tuple of (is_safe, list_of_violations).
        """
        if not sql or not sql.strip():
            return False, ['Empty SQL query']

        sql_upper = sql.upper().strip()
        violations = []

        # Check for dangerous patterns
        for pattern, description in cls.DANGEROUS_PATTERNS:
            if re.search(pattern, sql_upper, re.IGNORECASE):
                violations.append(description)

        # If violations found, return immediately
        if violations:
            return False, violations

        # Check if it matches allowed patterns (read-only operations)
        is_allowed = any(
            re.match(pattern, sql_upper, re.IGNORECASE)
            for pattern in cls.ALLOWED_PATTERNS
        )

        if not is_allowed:
            violations.append('Query does not start with allowed statement (SELECT, WITH, EXPLAIN, SHOW, DESCRIBE)')

        return len(violations) == 0, violations

    @classmethod
    def sanitize(cls, sql: str) -> str:
        """Basic SQL sanitization (removes comments, normalizes whitespace).

        Note: This is NOT a substitute for parameterized queries.
        For user input in WHERE clauses, always use parameterized queries.

        Args:
            sql: SQL query to sanitize.

        Returns:
            Sanitized SQL string.
        """
        # Remove SQL comments
        sql = re.sub(r'--[^\n]*', '', sql)
        sql = re.sub(r'/\*.*?\*/', '', sql, flags=re.DOTALL)

        # Normalize whitespace
        sql = ' '.join(sql.split())

        return sql.strip()
