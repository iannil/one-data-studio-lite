"""Tests for SQL Security Validator."""
from __future__ import annotations

import pytest

from app.services.ai_service import SQLSecurityValidator, SQLSecurityError


class TestSQLSecurityValidator:
    """Tests for SQLSecurityValidator."""

    class TestValidQueries:
        """Test valid (safe) queries."""

        @pytest.mark.parametrize("sql", [
            "SELECT * FROM users",
            "SELECT id, name FROM users WHERE active = true",
            "SELECT COUNT(*) FROM orders GROUP BY status",
            "SELECT u.name, o.total FROM users u JOIN orders o ON u.id = o.user_id",
            "WITH active_users AS (SELECT * FROM users WHERE active = true) SELECT * FROM active_users",
            "EXPLAIN SELECT * FROM users",
            "SHOW TABLES",
            "DESCRIBE users",
            "  SELECT * FROM users  ",  # Whitespace handling
        ])
        def test_valid_select_queries(self, sql):
            """Test that valid SELECT queries pass validation."""
            is_safe, violations = SQLSecurityValidator.validate(sql)
            assert is_safe is True, f"Expected safe, got violations: {violations}"
            assert violations == []

    class TestDangerousQueries:
        """Test dangerous queries that should be blocked."""

        @pytest.mark.parametrize("sql,expected_violation", [
            ("DROP TABLE users", "DROP statement"),
            ("DROP DATABASE production", "DROP statement"),
            ("TRUNCATE TABLE users", "TRUNCATE TABLE"),
            ("DELETE FROM users WHERE id = 1", "DELETE FROM"),
            ("ALTER TABLE users ADD COLUMN email VARCHAR(255)", "ALTER statement"),
            ("CREATE TABLE new_users (id INT)", "CREATE statement"),
            ("INSERT INTO users (name) VALUES ('test')", "INSERT INTO"),
            ("UPDATE users SET name = 'test' WHERE id = 1", "UPDATE statement"),
            ("GRANT SELECT ON users TO public", "GRANT statement"),
            ("REVOKE SELECT ON users FROM public", "REVOKE statement"),
        ])
        def test_dangerous_statements_blocked(self, sql, expected_violation):
            """Test that dangerous SQL statements are blocked."""
            is_safe, violations = SQLSecurityValidator.validate(sql)
            assert is_safe is False
            assert any(expected_violation in v for v in violations)

        @pytest.mark.parametrize("sql,expected_violation", [
            ("SELECT * FROM users; DROP TABLE users; --", "DROP statement"),
            ("SELECT * FROM users; DELETE FROM users;", "DELETE FROM"),
            ("SELECT SLEEP(10)", "SLEEP function"),
            ("SELECT BENCHMARK(1000000, SHA1('test'))", "BENCHMARK function"),
            ("SELECT LOAD_FILE('/etc/passwd')", "LOAD_FILE function"),
            ("SELECT * INTO OUTFILE '/tmp/data.csv' FROM users", "INTO OUTFILE/DUMPFILE"),
        ])
        def test_injection_attempts_blocked(self, sql, expected_violation):
            """Test that SQL injection attempts are blocked."""
            is_safe, violations = SQLSecurityValidator.validate(sql)
            assert is_safe is False
            assert any(expected_violation in v for v in violations)

        def test_extended_stored_procedures_blocked(self):
            """Test that extended stored procedures are blocked."""
            sql = "EXEC xp_cmdshell 'dir'"
            is_safe, violations = SQLSecurityValidator.validate(sql)
            assert is_safe is False

        def test_system_stored_procedures_blocked(self):
            """Test that system stored procedures are blocked."""
            sql = "EXEC sp_executesql 'SELECT * FROM users'"
            is_safe, violations = SQLSecurityValidator.validate(sql)
            assert is_safe is False

    class TestEdgeCases:
        """Test edge cases."""

        def test_empty_query(self):
            """Test empty query returns violation."""
            is_safe, violations = SQLSecurityValidator.validate("")
            assert is_safe is False
            assert "Empty SQL query" in violations

        def test_whitespace_only_query(self):
            """Test whitespace-only query returns violation."""
            is_safe, violations = SQLSecurityValidator.validate("   ")
            assert is_safe is False

        def test_case_insensitive_detection(self):
            """Test case-insensitive detection of dangerous patterns."""
            is_safe, violations = SQLSecurityValidator.validate("drop TABLE users")
            assert is_safe is False
            assert "DROP statement" in violations

            is_safe, violations = SQLSecurityValidator.validate("DrOp TaBlE users")
            assert is_safe is False

        def test_non_select_without_danger(self):
            """Test non-SELECT queries that aren't explicitly dangerous."""
            # These should be blocked because they don't start with allowed patterns
            sql = "CALL my_procedure()"
            is_safe, violations = SQLSecurityValidator.validate(sql)
            assert is_safe is False
            assert any("does not start with allowed statement" in v for v in violations)

    class TestSanitize:
        """Test SQL sanitization."""

        def test_removes_single_line_comments(self):
            """Test removal of single-line comments."""
            sql = "SELECT * FROM users -- this is a comment"
            result = SQLSecurityValidator.sanitize(sql)
            assert "--" not in result

        def test_removes_multi_line_comments(self):
            """Test removal of multi-line comments."""
            sql = "SELECT * /* comment */ FROM users"
            result = SQLSecurityValidator.sanitize(sql)
            assert "/*" not in result
            assert "*/" not in result

        def test_normalizes_whitespace(self):
            """Test whitespace normalization."""
            sql = "SELECT  *   FROM    users"
            result = SQLSecurityValidator.sanitize(sql)
            assert "  " not in result

        def test_preserves_query_structure(self):
            """Test that query structure is preserved after sanitization."""
            sql = "SELECT id, name FROM users WHERE active = true"
            result = SQLSecurityValidator.sanitize(sql)
            assert "SELECT" in result
            assert "FROM" in result
            assert "WHERE" in result


class TestSQLSecurityIntegration:
    """Integration tests for SQL security in AIService."""

    @pytest.mark.parametrize("malicious_sql", [
        "SELECT * FROM users; DROP TABLE users;",
        "SELECT * FROM users WHERE id = 1 OR 1=1; DELETE FROM users;",
        "SELECT * FROM users UNION SELECT * FROM information_schema.tables",
    ])
    def test_malicious_queries_detected(self, malicious_sql):
        """Test that malicious queries are detected by validator."""
        is_safe, violations = SQLSecurityValidator.validate(malicious_sql)
        assert is_safe is False
        assert len(violations) > 0
