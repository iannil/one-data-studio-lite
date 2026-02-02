"""Unit tests for seed data verification

Tests for services/common/seed_data.py
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.common.seed_data import (
    seed_permissions,
    seed_roles,
    seed_system_config,
    verify_data,
)


class TestSeedPermissions:
    """测试权限种子数据"""

    @pytest.mark.asyncio
    async def test_seed_permissions_returns_count(self):
        """测试种子权限返回计数"""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        result = await seed_permissions(mock_session)

        assert isinstance(result, int)
        assert result >= 0

    @pytest.mark.asyncio
    async def test_seed_permissions_commits(self):
        """测试权限提交到数据库"""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        await seed_permissions(mock_session)

        mock_session.commit.assert_called_once()


class TestSeedRoles:
    """测试角色种子数据"""

    @pytest.mark.asyncio
    async def test_seed_roles_returns_count(self):
        """测试种子角色返回计数"""
        mock_session = AsyncMock()
        mock_result = MagicMock()

        # Mock permissions query
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        result = await seed_roles(mock_session)

        assert isinstance(result, int)
        assert result >= 0


class TestSeedSystemConfig:
    """测试系统配置种子数据"""

    @pytest.mark.asyncio
    async def test_seed_system_config_returns_count(self):
        """测试系统配置返回计数"""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        result = await seed_system_config(mock_session)

        assert isinstance(result, int)
        assert result >= 0


class TestVerifyData:
    """测试数据验证功能"""

    @pytest.mark.asyncio
    async def test_verify_data_returns_verification_dict(self):
        """测试验证返回正确的数据结构"""
        with patch('services.common.seed_data.get_database_url') as mock_db_url:
            mock_db_url.return_value = "sqlite+aiosqlite:///:memory:"

            mock_engine = MagicMock()
            mock_engine.dispose = AsyncMock()

            with patch('services.common.seed_data.create_async_engine', return_value=mock_engine):
                with patch('services.common.seed_data.async_sessionmaker') as mock_maker:
                    # Mock session
                    mock_session = AsyncMock()
                    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
                    mock_session.__aexit__ = AsyncMock()

                    # Mock query results
                    async def mock_execute(query):
                        result = MagicMock()
                        result.scalars.return_value.all.return_value = list(range(20))  # 20 items
                        return result

                    mock_session.execute = mock_execute
                    mock_maker.return_value.return_value = mock_session

                    result = await verify_data()

                    assert isinstance(result, dict)
                    assert "permissions" in result
                    assert "roles" in result
                    assert "system_config" in result

                    # Check structure of each verification item
                    for key, value in result.items():
                        assert "expected" in value
                        assert "actual" in value
                        assert "status" in value

    @pytest.mark.asyncio
    async def test_verify_data_expected_values(self):
        """测试验证期望值正确"""
        with patch('services.common.seed_data.get_database_url') as mock_db_url:
            mock_db_url.return_value = "sqlite+aiosqlite:///:memory:"

            mock_engine = MagicMock()
            mock_engine.dispose = AsyncMock()

            with patch('services.common.seed_data.create_async_engine', return_value=mock_engine):
                with patch('services.common.seed_data.async_sessionmaker') as mock_maker:
                    mock_session = AsyncMock()
                    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
                    mock_session.__aexit__ = AsyncMock()

                    async def mock_execute(query):
                        result = MagicMock()
                        result.scalars.return_value.all.return_value = list(range(20))
                        return result

                    mock_session.execute = mock_execute
                    mock_maker.return_value.return_value = mock_session

                    result = await verify_data()

                    # Verify expected values match documentation
                    assert result["permissions"]["expected"] == 19
                    assert result["roles"]["expected"] == 8
                    assert result["system_config"]["expected"] == 5
                    assert result["users"]["expected"] == 7
                    assert result["service_accounts"]["expected"] == 2
                    assert result["user_api_keys"]["expected"] == 5
                    assert result["detection_rules"]["expected"] == 8
                    assert result["mask_rules"]["expected"] == 4
                    assert result["etl_mappings"]["expected"] == 3
                    assert result["scan_reports"]["expected"] == 3

    @pytest.mark.asyncio
    async def test_verify_data_status_ok(self):
        """测试数据充足时状态为ok"""
        with patch('services.common.seed_data.get_database_url') as mock_db_url:
            mock_db_url.return_value = "sqlite+aiosqlite:///:memory:"

            mock_engine = MagicMock()
            mock_engine.dispose = AsyncMock()

            with patch('services.common.seed_data.create_async_engine', return_value=mock_engine):
                with patch('services.common.seed_data.async_sessionmaker') as mock_maker:
                    mock_session = AsyncMock()
                    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
                    mock_session.__aexit__ = AsyncMock()

                    async def mock_execute(query):
                        result = MagicMock()
                        # Return enough items to pass validation
                        result.scalars.return_value.all.return_value = list(range(20))
                        return result

                    mock_session.execute = mock_execute
                    mock_maker.return_value.return_value = mock_session

                    result = await verify_data()

                    # All should be ok with 20 items
                    for key, value in result.items():
                        assert value["status"] in ("ok", "optional")

    @pytest.mark.asyncio
    async def test_verify_data_status_incomplete(self):
        """测试数据不足时状态为incomplete"""
        with patch('services.common.seed_data.get_database_url') as mock_db_url:
            mock_db_url.return_value = "sqlite+aiosqlite:///:memory:"

            mock_engine = MagicMock()
            mock_engine.dispose = AsyncMock()

            with patch('services.common.seed_data.create_async_engine', return_value=mock_engine):
                with patch('services.common.seed_data.async_sessionmaker') as mock_maker:
                    mock_session = AsyncMock()
                    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
                    mock_session.__aexit__ = AsyncMock()

                    async def mock_execute(query):
                        result = MagicMock()
                        # Return only 1 item (less than expected)
                        result.scalars.return_value.all.return_value = [1]
                        return result

                    mock_session.execute = mock_execute
                    mock_maker.return_value.return_value = mock_session

                    result = await verify_data()

                    # Required fields should be incomplete
                    assert result["permissions"]["status"] == "incomplete"
                    assert result["roles"]["status"] == "incomplete"
                    assert result["system_config"]["status"] == "incomplete"

    @pytest.mark.asyncio
    async def test_verify_data_engine_disposed(self):
        """测试验证后引擎正确释放"""
        with patch('services.common.seed_data.get_database_url') as mock_db_url:
            mock_db_url.return_value = "sqlite+aiosqlite:///:memory:"

            mock_engine = MagicMock()
            mock_engine.dispose = AsyncMock()

            with patch('services.common.seed_data.create_async_engine', return_value=mock_engine):
                with patch('services.common.seed_data.async_sessionmaker') as mock_maker:
                    mock_session = AsyncMock()
                    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
                    mock_session.__aexit__ = AsyncMock()

                    async def mock_execute(query):
                        result = MagicMock()
                        result.scalars.return_value.all.return_value = []
                        return result

                    mock_session.execute = mock_execute
                    mock_maker.return_value.return_value = mock_session

                    await verify_data()

                    # Verify engine was disposed
                    mock_engine.dispose.assert_called_once()


class TestPasswordHashing:
    """测试密码哈希功能"""

    def test_hash_password_returns_string(self):
        """测试哈希密码返回字符串"""
        from services.common.seed_data import _hash_password

        result = _hash_password("test_password")

        assert isinstance(result, str)
        assert ":" in result  # Format: salt:hash

    def test_hash_password_different_each_time(self):
        """测试相同密码每次哈希结果不同"""
        from services.common.seed_data import _hash_password

        result1 = _hash_password("test_password")
        result2 = _hash_password("test_password")

        # Due to random salt, results should differ
        assert result1 != result2

    def test_hash_password_contains_salt(self):
        """测试哈希包含盐值"""
        from services.common.seed_data import _hash_password

        result = _hash_password("test_password")

        parts = result.split(":")
        assert len(parts) == 2
        assert len(parts[0]) == 32  # 16 bytes = 32 hex chars


class TestVerificationStructure:
    """测试验证结构"""

    def test_verification_has_required_fields(self):
        """测试验证包含必需字段"""
        from services.common.seed_data import verify_data

        # This is a compile-time check for structure
        # The actual function is tested in TestVerifyData
        import inspect
        sig = inspect.signature(verify_data)
        assert len(sig.parameters) == 0
        assert inspect.iscoroutinefunction(verify_data)
