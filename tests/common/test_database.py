"""Unit tests for database module

Tests for services/common/database.py
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from services.common.database import (
    DEFAULT_DATABASE_URL,
    Base,
    create_engine,
    get_database_url,
    get_db,
    get_db_context,
    get_engine,
    get_session_factory,
    get_table_columns,
    reset_engine,
    validate_identifier,
    validate_table_exists,
)


class TestBase:
    """测试ORM基类"""

    def test_base_exists(self):
        """测试Base类存在"""
        assert Base is not None


class TestGetDatabaseUrl:
    """测试获取数据库URL"""

    def test_get_database_url_default(self):
        """测试默认数据库URL"""
        with patch.dict('os.environ', {}, clear=True):
            url = get_database_url()
            assert url == DEFAULT_DATABASE_URL

    def test_get_database_url_from_env(self):
        """测试从环境变量获取数据库URL"""
        with patch.dict('os.environ', {'DATABASE_URL': 'sqlite:///test.db'}):
            url = get_database_url()
            assert url == 'sqlite:///test.db'


class TestCreateEngine:
    """测试创建数据库引擎"""

    def test_create_engine_sqlite(self):
        """测试创建SQLite引擎"""
        engine = create_engine("sqlite+aiosqlite:///test.db")
        assert engine is not None

    def test_create_engine_mysql(self):
        """测试创建MySQL引擎"""
        engine = create_engine("mysql+aiomysql://root:pass@localhost/db")
        assert engine is not None

    def test_create_engine_default(self):
        """测试使用默认URL创建引擎"""
        with patch.dict('os.environ', {}, clear=True):
            engine = create_engine()
            assert engine is not None


class TestResetEngine:
    """测试重置引擎"""

    def test_reset_engine(self):
        """测试重置全局引擎"""
        # First create an engine
        get_engine()
        assert get_engine() is not None

        # Reset
        reset_engine()

        # After reset, get_engine should create a new one
        assert get_engine() is not None


class TestGetEngine:
    """测试获取引擎"""

    def test_get_engine_same_instance(self):
        """测试返回相同的引擎实例"""
        reset_engine()
        engine1 = get_engine()
        engine2 = get_engine()
        assert engine1 is engine2


class TestGetSessionFactory:
    """测试获取会话工厂"""

    def test_get_session_factory_same_instance(self):
        """测试返回相同的会话工厂实例"""
        reset_engine()
        factory1 = get_session_factory()
        factory2 = get_session_factory()
        assert factory1 is factory2


class TestGetDb:
    """测试获取数据库会话"""

    @pytest.mark.asyncio
    async def test_get_db_yields_session(self):
        """测试get_db返回会话"""
        reset_engine()

        async for session in get_db():
            assert isinstance(session, AsyncSession)
            break  # Only test first iteration


class TestGetDbContext:
    """测试获取数据库会话上下文管理器"""

    @pytest.mark.asyncio
    async def test_get_db_context_yields_session(self):
        """测试get_db_context返回会话"""
        reset_engine()

        async with get_db_context() as session:
            assert isinstance(session, AsyncSession)


class TestValidateIdentifier:
    """测试标识符验证"""

    def test_validate_identifier_valid(self):
        """测试有效标识符"""
        result = validate_identifier("users")
        assert result == "`users`"

    def test_validate_identifier_with_underscore(self):
        """测试带下划线的标识符"""
        result = validate_identifier("user_accounts")
        assert result == "`user_accounts`"

    def test_validate_identifier_with_numbers(self):
        """测试带数字的标识符"""
        result = validate_identifier("table123")
        assert result == "`table123`"

    def test_validate_identifier_empty(self):
        """测试空标识符"""
        with pytest.raises(ValueError, match="长度无效"):
            validate_identifier("")

    def test_validate_identifier_too_long(self):
        """测试过长的标识符"""
        long_name = "a" * 65
        with pytest.raises(ValueError, match="长度无效"):
            validate_identifier(long_name)

    def test_validate_identifier_with_hyphen(self):
        """测试带连字符的标识符（非法）"""
        with pytest.raises(ValueError, match="非法字符"):
            validate_identifier("table-name")

    def test_validate_identifier_with_space(self):
        """测试带空格的标识符（非法）"""
        with pytest.raises(ValueError, match="非法字符"):
            validate_identifier("table name")

    def test_validate_identifier_with_dot(self):
        """测试带点的标识符（非法）"""
        with pytest.raises(ValueError, match="非法字符"):
            validate_identifier("table.name")

    def test_validate_identifier_starts_with_number(self):
        """测试以数字开头的标识符（非法）"""
        with pytest.raises(ValueError, match="非法字符"):
            validate_identifier("1table")

    def test_validate_identifier_with_special_chars(self):
        """测试带特殊字符的标识符（非法）"""
        with pytest.raises(ValueError, match="非法字符"):
            validate_identifier("table@name")


class TestValidateTableExists:
    """测试验证表存在"""

    @pytest.mark.asyncio
    async def test_validate_table_exists_sqlite(self):
        """测试SQLite验证表存在"""
        mock_session = AsyncMock()

        # Mock sqlite_version check
        mock_version_result = MagicMock()
        mock_version_result.fetchone.return_value = "3.40.0"

        # Mock table exists
        mock_table_result = MagicMock()
        mock_table_result.fetchone.return_value = (1,)

        call_count = [0]

        async def mock_execute_fn(sql, params=None):
            call_count[0] += 1
            if "sqlite_version" in str(sql):
                return mock_version_result
            else:
                return mock_table_result

        mock_session.execute = AsyncMock(side_effect=mock_execute_fn)

        result = await validate_table_exists(mock_session, "users")

        assert result == "`users`"

    @pytest.mark.asyncio
    async def test_validate_table_not_exists(self):
        """测试表不存在"""
        mock_session = AsyncMock()

        # Mock sqlite_version check
        mock_version_result = MagicMock()
        mock_version_result.fetchone.return_value = "3.40.0"

        # Mock table doesn't exist
        mock_table_result = MagicMock()
        mock_table_result.fetchone.return_value = None

        async def mock_execute_fn(sql, params=None):
            if "sqlite_version" in str(sql):
                return mock_version_result
            else:
                return mock_table_result

        mock_session.execute = AsyncMock(side_effect=mock_execute_fn)

        with pytest.raises(ValueError, match="表不存在"):
            await validate_table_exists(mock_session, "nonexistent")

    @pytest.mark.asyncio
    async def test_validate_table_invalid_identifier(self):
        """测试无效标识符"""
        mock_session = AsyncMock()

        with pytest.raises(ValueError, match="非法字符"):
            await validate_table_exists(mock_session, "table-name")

    @pytest.mark.asyncio
    async def test_validate_table_mysql(self):
        """测试MySQL验证表存在"""
        mock_session = AsyncMock()

        # Mock sqlite_version check - returns None for MySQL
        mock_version_result = MagicMock()
        mock_version_result.fetchone.return_value = None

        # Mock table exists
        mock_table_result = MagicMock()
        mock_table_result.fetchone.return_value = (1,)

        # Mock fallback query
        mock_fallback_result = MagicMock()
        mock_fallback_result.fetchone.return_value = (1,)

        call_count = [0]

        async def mock_execute_fn(sql, params=None):
            call_count[0] += 1
            if "sqlite_version" in str(sql):
                return mock_version_result
            elif "information_schema" in str(sql):
                return mock_table_result
            else:
                return mock_fallback_result

        mock_session.execute = AsyncMock(side_effect=mock_execute_fn)

        result = await validate_table_exists(mock_session, "users")

        assert result == "`users`"


class TestGetTableColumns:
    """测试获取表列信息"""

    @pytest.mark.asyncio
    async def test_get_table_columns_sqlite(self):
        """测试SQLite获取列信息"""
        mock_session = AsyncMock()

        # Mock sqlite_version check
        mock_version_result = MagicMock()
        mock_version_result.fetchone.return_value = "3.40.0"

        # Mock PRAGMA result
        # Format: (cid, name, type, notnull, default_value, pk)
        mock_pragma_result = MagicMock()
        mock_pragma_result.fetchall.return_value = [
            (0, "id", "INTEGER", 1, None, 1),  # notnull=1 means NOT NULL
            (1, "name", "TEXT", 0, None, 0),     # notnull=0 means nullable
            (2, "email", "VARCHAR(255)", 1, None, 0),  # notnull=1 means NOT NULL
        ]

        call_count = [0]

        async def mock_execute_fn(sql, params=None):
            call_count[0] += 1
            if "sqlite_version" in str(sql):
                return mock_version_result
            else:
                return mock_pragma_result

        mock_session.execute = AsyncMock(side_effect=mock_execute_fn)

        columns = await get_table_columns(mock_session, "users")

        assert len(columns) == 3
        assert columns[0] == ("id", "INTEGER", "NO")
        assert columns[1] == ("name", "TEXT", "YES")

    @pytest.mark.asyncio
    async def test_get_table_columns_mysql(self):
        """测试MySQL获取列信息"""
        mock_session = AsyncMock()

        # Mock sqlite_version check - returns None for MySQL
        mock_version_result = MagicMock()
        mock_version_result.fetchone.return_value = None

        # Mock information_schema result
        mock_info_result = MagicMock()
        mock_info_result.fetchall.return_value = [
            ("id", "int", "NO"),
            ("name", "varchar", "YES"),
        ]

        async def mock_execute_fn(sql, params=None):
            if "sqlite_version" in str(sql):
                return mock_version_result
            else:
                return mock_info_result

        mock_session.execute = AsyncMock(side_effect=mock_execute_fn)

        columns = await get_table_columns(mock_session, "users")

        assert len(columns) == 2
        assert columns[0] == ("id", "int", "NO")

    @pytest.mark.asyncio
    async def test_get_table_columns_error_returns_empty(self):
        """测试查询错误时返回空列表"""
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(side_effect=Exception("Database error"))

        columns = await get_table_columns(mock_session, "users")

        assert columns == []
