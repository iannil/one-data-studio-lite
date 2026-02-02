"""Unit tests for portal shardingsphere router

Tests for services/portal/routers/shardingsphere.py
"""

from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

import pytest
from fastapi import HTTPException

from services.portal.routers.shardingsphere import (
    router,
    _get_client,
    list_mask_rules_v1,
    get_table_rules_v1,
    create_mask_rule_v1,
    update_mask_rule_v1,
    delete_table_rules_v1,
    batch_create_rules_v1,
    list_algorithms_v1,
    list_presets_v1,
    sync_rules_to_proxy_v1,
    list_mask_rules_legacy,
    get_table_rules_legacy,
    create_mask_rule_legacy,
    update_mask_rule_legacy,
    delete_table_rules_legacy,
    batch_create_rules_legacy,
    list_algorithms_legacy,
    list_presets_legacy,
    sync_rules_to_proxy_legacy,
    MaskRuleRequest,
    BatchMaskRequest,
)
from services.common.auth import TokenPayload
from services.common.api_response import ErrorCode
from services.common.shardingsphere_client import MaskAlgorithms


class TestRouter:
    """测试路由配置"""

    def test_router_prefix(self):
        """测试路由前缀"""
        assert router.prefix == "/api/proxy/shardingsphere"


# ============================================================
# v1 API Tests
# ============================================================

class TestListMaskRulesV1:
    """测试获取所有脱敏规则"""

    @pytest.mark.asyncio
    async def test_list_mask_rules_success(self):
        """测试成功获取所有脱敏规则"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="viewer",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        mock_client = AsyncMock()
        mock_client.list_mask_rules.return_value = [
            {"table": "users", "column": "phone", "algorithm": "MD5"}
        ]
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()

        with patch('services.portal.routers.shardingsphere._get_client', return_value=mock_client):
            result = await list_mask_rules_v1(user=mock_user)

            assert result.code == ErrorCode.SUCCESS
            assert "rules" in result.data
            assert result.data["total"] == 1

    @pytest.mark.asyncio
    async def test_list_mask_rules_error(self):
        """测试获取脱敏规则失败"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="viewer",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        # Create a mock that raises error on list_mask_rules
        class MockClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            async def list_mask_rules(self):
                raise Exception("Connection failed")

        with patch('services.portal.routers.shardingsphere._get_client', return_value=MockClient()):
            result = await list_mask_rules_v1(user=mock_user)

            assert result.code == ErrorCode.SHARDINGSPHERE_ERROR


class TestGetTableRulesV1:
    """测试获取表的脱敏规则"""

    @pytest.mark.asyncio
    async def test_get_table_rules_success(self):
        """测试成功获取表的脱敏规则"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="viewer",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        mock_client = AsyncMock()
        mock_client.get_table_rules.return_value = [
            {"column": "phone", "algorithm": "MD5"}
        ]
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()

        with patch('services.portal.routers.shardingsphere._get_client', return_value=mock_client):
            result = await get_table_rules_v1(table_name="users", user=mock_user)

            assert result.code == ErrorCode.SUCCESS
            assert "rules" in result.data


class TestCreateMaskRuleV1:
    """测试创建脱敏规则"""

    @pytest.mark.asyncio
    async def test_create_mask_rule_success(self):
        """测试成功创建脱敏规则"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1),
            user_id="admin"
        )

        mock_client = AsyncMock()
        mock_client.add_mask_rule.return_value = True
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()

        mock_db = AsyncMock()

        # Mock repository calls
        mock_repo = AsyncMock()
        mock_repo.upsert_by_table_column = AsyncMock()
        mock_repo.get_by_table_column = AsyncMock(return_value=MagicMock(id=1))
        mock_repo.mark_synced = AsyncMock()

        with patch('services.portal.routers.shardingsphere._get_client', return_value=mock_client), \
             patch('services.portal.routers.shardingsphere.MaskRuleRepository', return_value=mock_repo):
            req = MaskRuleRequest(
                table_name="users",
                column_name="phone",
                algorithm_type="MD5",
                algorithm_props={}
            )

            result = await create_mask_rule_v1(req, mock_db, mock_user)

            assert result.code == ErrorCode.SUCCESS

    @pytest.mark.asyncio
    async def test_create_mask_rule_already_exists(self):
        """测试创建已存在的规则"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1),
            user_id="admin"
        )

        mock_client = AsyncMock()
        mock_client.add_mask_rule.return_value = False
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()

        mock_db = AsyncMock()

        with patch('services.portal.routers.shardingsphere._get_client', return_value=mock_client):
            req = MaskRuleRequest(
                table_name="users",
                column_name="phone",
                algorithm_type="MD5"
            )

            result = await create_mask_rule_v1(req, mock_db, mock_user)

            assert result.code == ErrorCode.VALIDATION_FAILED


class TestUpdateMaskRuleV1:
    """测试更新脱敏规则"""

    @pytest.mark.asyncio
    async def test_update_mask_rule_success(self):
        """测试成功更新脱敏规则"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1),
            user_id="admin"
        )

        mock_client = AsyncMock()
        mock_client.upsert_mask_rule.return_value = True
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()

        mock_db = AsyncMock()

        mock_repo = AsyncMock()
        mock_repo.upsert_by_table_column = AsyncMock()
        mock_repo.get_by_table_column = AsyncMock(return_value=MagicMock(id=1))
        mock_repo.mark_synced = AsyncMock()

        with patch('services.portal.routers.shardingsphere._get_client', return_value=mock_client), \
             patch('services.portal.routers.shardingsphere.MaskRuleRepository', return_value=mock_repo):
            req = MaskRuleRequest(
                table_name="users",
                column_name="phone",
                algorithm_type="MD5"
            )

            result = await update_mask_rule_v1(req, mock_db, mock_user)

            assert result.code == ErrorCode.SUCCESS


class TestDeleteTableRulesV1:
    """测试删除表的脱敏规则"""

    @pytest.mark.asyncio
    async def test_delete_table_rules_success(self):
        """测试成功删除表的脱敏规则"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1),
            user_id="admin"
        )

        mock_client = AsyncMock()
        mock_client.drop_mask_rule.return_value = True
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()

        mock_db = AsyncMock()

        mock_repo = AsyncMock()
        mock_rule = MagicMock()
        mock_rule.id = 1
        mock_repo.get_by_table.return_value = [mock_rule]
        mock_repo.delete = AsyncMock()

        with patch('services.portal.routers.shardingsphere._get_client', return_value=mock_client), \
             patch('services.portal.routers.shardingsphere.MaskRuleRepository', return_value=mock_repo):
            result = await delete_table_rules_v1("users", mock_db, mock_user)

            assert result.code == ErrorCode.SUCCESS

    @pytest.mark.asyncio
    async def test_delete_table_rules_not_found(self):
        """测试删除不存在的规则"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1),
            user_id="admin"
        )

        mock_client = AsyncMock()
        mock_client.drop_mask_rule.return_value = False
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()

        mock_db = AsyncMock()

        with patch('services.portal.routers.shardingsphere._get_client', return_value=mock_client):
            result = await delete_table_rules_v1("nonexistent", mock_db, mock_user)

            assert result.code == ErrorCode.NOT_FOUND


class TestBatchCreateRulesV1:
    """测试批量创建脱敏规则"""

    @pytest.mark.asyncio
    async def test_batch_create_rules_success(self):
        """测试批量创建成功"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1),
            user_id="admin"
        )

        mock_client = AsyncMock()
        mock_client.upsert_mask_rule.return_value = True
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()

        mock_db = AsyncMock()

        mock_repo = AsyncMock()
        mock_repo.upsert_by_table_column = AsyncMock()
        mock_repo.get_by_table_column = AsyncMock(return_value=MagicMock(id=1))
        mock_repo.mark_synced = AsyncMock()

        with patch('services.portal.routers.shardingsphere._get_client', return_value=mock_client), \
             patch('services.portal.routers.shardingsphere.MaskRuleRepository', return_value=mock_repo):
            req = BatchMaskRequest(rules=[
                MaskRuleRequest(
                    table_name="users",
                    column_name="phone",
                    algorithm_type="MD5"
                ),
                MaskRuleRequest(
                    table_name="users",
                    column_name="email",
                    algorithm_type="MD5"
                )
            ])

            result = await batch_create_rules_v1(req, mock_db, mock_user)

            assert result.code == ErrorCode.SUCCESS
            assert result.data["success_count"] == 2


class TestListAlgorithmsV1:
    """测试获取可用算法"""

    @pytest.mark.asyncio
    async def test_list_algorithms_success(self):
        """测试成功获取算法列表"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="viewer",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        mock_client = AsyncMock()
        mock_client.list_mask_algorithms.return_value = [
            {"name": "MD5", "type": "MD5"}
        ]
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()

        with patch('services.portal.routers.shardingsphere._get_client', return_value=mock_client):
            result = await list_algorithms_v1(user=mock_user)

            assert result.code == ErrorCode.SUCCESS
            assert "algorithms" in result.data

    @pytest.mark.asyncio
    async def test_list_algorithms_fallback(self):
        """测试客户端失败时返回预设算法"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="viewer",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        # Create a mock that raises error on list_mask_algorithms
        class MockClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            async def list_mask_algorithms(self):
                raise Exception("Client error")

        with patch('services.portal.routers.shardingsphere._get_client', return_value=MockClient()):
            result = await list_algorithms_v1(user=mock_user)

            assert result.code == ErrorCode.SUCCESS
            assert "algorithms" in result.data


class TestListPresetsV1:
    """测试获取预设方案"""

    @pytest.mark.asyncio
    async def test_list_presets_success(self):
        """测试成功获取预设方案"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="viewer",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        result = await list_presets_v1(user=mock_user)

        assert result.code == ErrorCode.SUCCESS
        assert "presets" in result.data
        assert len(result.data["presets"]) >= 4

    def test_list_presets_contains_common_presets(self):
        """测试包含常用预设"""
        # The presets should include phone, id_card, bank_card, email
        result = {
            "presets": [
                {"name": "phone"},
                {"name": "id_card"},
                {"name": "bank_card"},
                {"name": "email"}
            ]
        }
        preset_names = [p["name"] for p in result["presets"]]
        assert "phone" in preset_names
        assert "id_card" in preset_names
        assert "bank_card" in preset_names
        assert "email" in preset_names


class TestSyncRulesToProxyV1:
    """测试同步规则到 Proxy"""

    @pytest.mark.asyncio
    async def test_sync_rules_no_unsynced(self):
        """测试没有需要同步的规则"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1),
            user_id="admin"
        )

        mock_db = AsyncMock()

        mock_repo = AsyncMock()
        mock_repo.get_unsynced_rules.return_value = []

        with patch('services.portal.routers.shardingsphere.MaskRuleRepository', return_value=mock_repo):
            result = await sync_rules_to_proxy_v1(mock_db, mock_user)

            assert result.code == ErrorCode.SUCCESS
            assert result.data["synced_count"] == 0

    @pytest.mark.asyncio
    async def test_sync_rules_success(self):
        """测试成功同步规则"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1),
            user_id="admin"
        )

        mock_client = AsyncMock()
        mock_client.upsert_mask_rule.return_value = True
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()

        mock_db = AsyncMock()

        mock_rule = MagicMock()
        mock_rule.id = 1
        mock_rule.table_name = "users"
        mock_rule.column_name = "phone"
        mock_rule.algorithm_type = "MD5"
        mock_rule.algorithm_props = {}

        mock_repo = AsyncMock()
        mock_repo.get_unsynced_rules.return_value = [mock_rule]
        mock_repo.mark_synced = AsyncMock()

        with patch('services.portal.routers.shardingsphere._get_client', return_value=mock_client), \
             patch('services.portal.routers.shardingsphere.MaskRuleRepository', return_value=mock_repo):
            result = await sync_rules_to_proxy_v1(mock_db, mock_user)

            assert result.code == ErrorCode.SUCCESS
            assert result.data["synced_count"] == 1


# ============================================================
# Legacy API Tests
# ============================================================

class TestListMaskRulesLegacy:
    """测试旧版 API - 获取所有脱敏规则"""

    @pytest.mark.asyncio
    async def test_list_mask_rules_legacy_success(self):
        """测试旧版 API 成功"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="viewer",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        with patch('services.portal.routers.shardingsphere.list_mask_rules_v1') as mock_v1:
            mock_v1.return_value = MagicMock(
                code=ErrorCode.SUCCESS,
                data={"rules": [], "total": 0},
                message="Success"
            )

            result = await list_mask_rules_legacy(user=mock_user)

            assert "rules" in result
            assert result["total"] == 0

    @pytest.mark.asyncio
    async def test_list_mask_rules_legacy_error(self):
        """测试旧版 API 错误"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="viewer",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        with patch('services.portal.routers.shardingsphere.list_mask_rules_v1') as mock_v1:
            mock_v1.return_value = MagicMock(
                code=ErrorCode.SHARDINGSPHERE_ERROR,
                message="Service error"
            )

            with pytest.raises(HTTPException) as exc_info:
                await list_mask_rules_legacy(user=mock_user)

            assert exc_info.value.status_code == 500


class TestCreateMaskRuleLegacy:
    """测试旧版 API - 创建脱敏规则"""

    @pytest.mark.asyncio
    async def test_create_mask_rule_legacy_success(self):
        """测试旧版 API 创建成功"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1),
            user_id="admin"
        )

        mock_db = AsyncMock()
        req = MaskRuleRequest(
            table_name="users",
            column_name="phone",
            algorithm_type="MD5"
        )

        with patch('services.portal.routers.shardingsphere.create_mask_rule_v1') as mock_v1:
            mock_v1.return_value = MagicMock(
                code=ErrorCode.SUCCESS,
                message="规则已创建"
            )

            result = await create_mask_rule_legacy(req, mock_db, mock_user)

            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_create_mask_rule_legacy_error(self):
        """测试旧版 API 创建失败"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1),
            user_id="admin"
        )

        mock_db = AsyncMock()
        req = MaskRuleRequest(
            table_name="users",
            column_name="phone",
            algorithm_type="MD5"
        )

        with patch('services.portal.routers.shardingsphere.create_mask_rule_v1') as mock_v1:
            mock_v1.return_value = MagicMock(
                code=ErrorCode.VALIDATION_FAILED,
                message="创建失败"
            )

            with pytest.raises(HTTPException) as exc_info:
                await create_mask_rule_legacy(req, mock_db, mock_user)

            assert exc_info.value.status_code == 400


class TestDeleteTableRulesLegacy:
    """测试旧版 API - 删除表的脱敏规则"""

    @pytest.mark.asyncio
    async def test_delete_table_rules_legacy_success(self):
        """测试旧版 API 删除成功"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1),
            user_id="admin"
        )

        mock_db = AsyncMock()

        with patch('services.portal.routers.shardingsphere.delete_table_rules_v1') as mock_v1:
            mock_v1.return_value = MagicMock(
                code=ErrorCode.SUCCESS,
                message="已删除"
            )

            result = await delete_table_rules_legacy("users", mock_db, mock_user)

            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_delete_table_rules_legacy_not_found(self):
        """测试旧版 API 删除不存在的规则"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1),
            user_id="admin"
        )

        mock_db = AsyncMock()

        with patch('services.portal.routers.shardingsphere.delete_table_rules_v1') as mock_v1:
            mock_v1.return_value = MagicMock(
                code=ErrorCode.NOT_FOUND,
                message="规则不存在"
            )

            with pytest.raises(HTTPException) as exc_info:
                await delete_table_rules_legacy("nonexistent", mock_db, mock_user)

            assert exc_info.value.status_code == 404


class TestListAlgorithmsLegacy:
    """测试旧版 API - 获取可用算法"""

    @pytest.mark.asyncio
    async def test_list_algorithms_legacy_success(self):
        """测试旧版 API 成功"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="viewer",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        with patch('services.portal.routers.shardingsphere.list_algorithms_v1') as mock_v1:
            mock_v1.return_value = MagicMock(
                code=ErrorCode.SUCCESS,
                data={"algorithms": []}
            )

            result = await list_algorithms_legacy(user=mock_user)

            assert "algorithms" in result


class TestListPresetsLegacy:
    """测试旧版 API - 获取预设方案"""

    @pytest.mark.asyncio
    async def test_list_presets_legacy_success(self):
        """测试旧版 API 成功"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="viewer",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        with patch('services.portal.routers.shardingsphere.list_presets_v1') as mock_v1:
            mock_v1.return_value = MagicMock(
                code=ErrorCode.SUCCESS,
                data={"presets": []}
            )

            result = await list_presets_legacy(user=mock_user)

            assert "presets" in result


class TestSyncRulesToProxyLegacy:
    """测试旧版 API - 同步规则到 Proxy"""

    @pytest.mark.asyncio
    async def test_sync_rules_legacy_success(self):
        """测试旧版 API 同步成功"""
        mock_user = TokenPayload(
            sub="test",
            username="test",
            role="admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1),
            user_id="admin"
        )

        mock_db = AsyncMock()

        with patch('services.portal.routers.shardingsphere.sync_rules_to_proxy_v1') as mock_v1:
            mock_v1.return_value = MagicMock(
                code=ErrorCode.SUCCESS,
                message="已同步 1 个规则",
                data={"synced_count": 1}
            )

            result = await sync_rules_to_proxy_legacy(mock_db, mock_user)

            assert result["success"] is True
            assert result["synced_count"] == 1
