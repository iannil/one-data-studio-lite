"""Unit tests for database migrations

Tests for services/common/migrations.py
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.common.migrations import (
    DEFAULT_PERMISSIONS,
    DEFAULT_ROLES,
    _get_dev_users,
    _hash_password,
    create_tables,
    insert_default_config,
    insert_permissions,
    insert_roles,
)


class TestConstants:
    """测试常量定义"""

    def test_default_permissions_not_empty(self):
        """测试默认权限不为空"""
        assert len(DEFAULT_PERMISSIONS) > 0

    def test_default_permissions_format(self):
        """测试默认权限格式"""
        for perm in DEFAULT_PERMISSIONS:
            assert len(perm) == 3
            assert isinstance(perm[0], str)  # code
            assert isinstance(perm[1], str)  # name
            assert isinstance(perm[2], str)  # description

    def test_default_roles_not_empty(self):
        """测试默认角色不为空"""
        assert len(DEFAULT_ROLES) > 0

    def test_default_roles_format(self):
        """测试默认角色格式"""
        for role in DEFAULT_ROLES:
            assert "role_code" in role
            assert "role_name" in role
            assert "permissions" in role


class TestHashPassword:
    """测试密码哈希"""

    def test_hash_password_returns_string(self):
        """测试哈希密码返回字符串"""
        result = _hash_password("test_password")

        assert isinstance(result, str)
        assert ":" in result

    def test_hash_password_contains_salt_and_hash(self):
        """测试哈希包含盐值和哈希值"""
        result = _hash_password("test_password")

        parts = result.split(":")
        assert len(parts) == 2
        assert len(parts[0]) == 32  # 16 bytes salt = 32 hex chars

    def test_hash_password_different_passwords(self):
        """测试不同密码产生不同哈希"""
        result1 = _hash_password("password1")
        result2 = _hash_password("password2")

        assert result1 != result2


class TestGetDevUsers:
    """测试获取开发用户"""

    def test_get_dev_users_returns_dict(self):
        """测试返回字典"""
        result = _get_dev_users()

        assert isinstance(result, dict)

    def test_get_dev_users_contains_users(self):
        """测试包含用户"""
        result = _get_dev_users()

        assert len(result) > 0


class TestCreateTables:
    """测试创建表"""

    @pytest.mark.asyncio
    async def test_create_tables(self):
        """测试创建表"""
        mock_engine = MagicMock()
        mock_conn = AsyncMock()
        mock_conn.__aenter__ = AsyncMock()
        mock_conn.__aexit__ = AsyncMock()
        mock_engine.begin.return_value = mock_conn

        with patch('services.common.migrations.Base.metadata.create_all'):
            await create_tables(mock_engine)

            # Should complete without error


class TestInsertPermissions:
    """测试插入权限"""

    @pytest.mark.asyncio
    async def test_insert_permissions(self):
        """测试插入权限"""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        await insert_permissions(mock_session)

        # Verify commit was called
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_insert_permissions_existing(self):
        """测试权限已存在时跳过"""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        # Simulate existing permissions
        mock_result.scalars.return_value.all.return_value = ["data:read", "data:write"]
        mock_session.execute.return_value = mock_result

        await insert_permissions(mock_session)

        # Should still commit (even if no new permissions)
        mock_session.commit.assert_called_once()


class TestInsertRoles:
    """测试插入角色"""

    @pytest.mark.asyncio
    async def test_insert_roles(self):
        """测试插入角色"""
        mock_session = AsyncMock()

        # Create async mock functions
        async def mock_execute_fn(query):
            result = MagicMock()
            result.scalars.return_value.all.return_value = []
            result.scalars.return_value.first.return_value = None
            return result

        mock_session.execute = mock_execute_fn
        mock_session.flush = AsyncMock()
        mock_session.commit = AsyncMock()

        await insert_roles(mock_session)

        # Verify commit was called
        mock_session.commit.assert_called_once()


class TestInsertDefaultConfig:
    """测试插入默认配置"""

    @pytest.mark.asyncio
    async def test_insert_default_config(self):
        """测试插入默认配置"""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        await insert_default_config(mock_session)

        # Verify commit was called
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_insert_default_config_existing(self):
        """测试配置已存在时跳过"""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        # Simulate existing configs
        mock_result.scalars.return_value.all.return_value = ["config1"]
        mock_session.execute.return_value = mock_result

        await insert_default_config(mock_session)

        # Should still commit
        mock_session.commit.assert_called_once()
