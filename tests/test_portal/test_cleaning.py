"""Unit tests for portal cleaning router

Tests for services/portal/routers/cleaning.py
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.portal.routers.cleaning import (
    SERVICE_SECRET,
    AnalyzeRequest,
    GenerateConfigRequest,
    RecommendRequest,
    router,
)


class TestConstants:
    """测试常量"""

    def test_service_secret_exists(self):
        """测试服务密钥存在"""
        assert SERVICE_SECRET is not None

    def test_router_prefix(self):
        """测试路由前缀"""
        assert router.prefix == "/api/proxy/cleaning"


class TestAnalyzeRequest:
    """测试分析请求模型"""

    def test_analyze_request_minimal(self):
        """测试最小请求"""
        req = AnalyzeRequest(table_name="users")
        assert req.table_name == "users"
        assert req.database is None
        assert req.sample_size == 100

    def test_analyze_request_full(self):
        """测试完整请求"""
        req = AnalyzeRequest(
            table_name="orders",
            database="analytics",
            sample_size=500
        )
        assert req.table_name == "orders"
        assert req.database == "analytics"
        assert req.sample_size == 500


class TestRecommendRequest:
    """测试推荐请求模型"""

    def test_recommend_request_minimal(self):
        """测试最小请求"""
        req = RecommendRequest(table_name="users")
        assert req.table_name == "users"
        assert req.database is None

    def test_recommend_request_with_database(self):
        """测试带数据库的请求"""
        req = RecommendRequest(
            table_name="orders",
            database="production"
        )
        assert req.table_name == "orders"
        assert req.database == "production"


class TestGenerateConfigRequest:
    """测试生成配置请求模型"""

    def test_generate_config_request_minimal(self):
        """测试最小请求"""
        req = GenerateConfigRequest(
            table_name="users",
            rules=["remove_duplicates", "fill_nulls"]
        )
        assert req.table_name == "users"
        assert req.rules == ["remove_duplicates", "fill_nulls"]
        assert req.output_format == "seatunnel"

    def test_generate_config_request_full(self):
        """测试完整请求"""
        req = GenerateConfigRequest(
            table_name="orders",
            rules=["remove_duplicates", "fill_nulls", "standardize_dates"],
            output_format="seatunnel"
        )
        assert req.table_name == "orders"
        assert req.rules == ["remove_duplicates", "fill_nulls", "standardize_dates"]
        assert req.output_format == "seatunnel"


class TestAnalyzeQualityV1:
    """测试 v1 分析质量端点"""

    @pytest.mark.asyncio
    async def test_analyze_quality_v1_success(self):
        """测试分析质量成功"""
        from datetime import datetime

        from services.common.auth import TokenPayload
        from services.portal.routers.cleaning import analyze_quality_v1

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "quality_score": 85,
            "issues": ["missing_values", "duplicates"]
        }

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            mock_payload = TokenPayload(
                sub="testuser",
                username="testuser",
                role="admin",
                exp=datetime(2099, 12, 31),
                iat=datetime(2023, 1, 1)
            )

            request = AnalyzeRequest(table_name="users")
            result = await analyze_quality_v1(request, mock_payload)

            assert result.code == 20000
            assert result.data is not None

    @pytest.mark.asyncio
    async def test_analyze_quality_v1_service_error(self):
        """测试服务返回错误"""
        from datetime import datetime

        from services.common.auth import TokenPayload
        from services.portal.routers.cleaning import analyze_quality_v1

        mock_response = MagicMock()
        mock_response.status_code = 500

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            mock_payload = TokenPayload(
                sub="testuser",
                username="testuser",
                role="admin",
                exp=datetime(2099, 12, 31),
                iat=datetime(2023, 1, 1)
            )

            request = AnalyzeRequest(table_name="users")
            result = await analyze_quality_v1(request, mock_payload)

            assert result.code != 20000
            assert "AI 清洗服务错误" in result.message

    @pytest.mark.asyncio
    async def test_analyze_quality_v1_exception(self):
        """测试异常处理"""
        from datetime import datetime

        import httpx

        from services.common.auth import TokenPayload
        from services.portal.routers.cleaning import analyze_quality_v1

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post = AsyncMock(side_effect=httpx.ConnectError("Connection failed"))
            mock_client_class.return_value = mock_client

            mock_payload = TokenPayload(
                sub="testuser",
                username="testuser",
                role="admin",
                exp=datetime(2099, 12, 31),
                iat=datetime(2023, 1, 1)
            )

            request = AnalyzeRequest(table_name="users")
            result = await analyze_quality_v1(request, mock_payload)

            assert result.code != 20000
            assert "AI 清洗服务异常" in result.message


class TestRecommendRulesV1:
    """测试 v1 推荐规则端点"""

    @pytest.mark.asyncio
    async def test_recommend_rules_v1_success(self):
        """测试推荐规则成功"""
        from datetime import datetime

        from services.common.auth import TokenPayload
        from services.portal.routers.cleaning import recommend_rules_v1

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "rules": [
                {"type": "remove_duplicates", "priority": "high"},
                {"type": "fill_nulls", "priority": "medium"}
            ]
        }

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            mock_payload = TokenPayload(
                sub="testuser",
                username="testuser",
                role="admin",
                exp=datetime(2099, 12, 31),
                iat=datetime(2023, 1, 1)
            )

            request = RecommendRequest(table_name="users")
            result = await recommend_rules_v1(request, mock_payload)

            assert result.code == 20000
            assert result.data is not None

    @pytest.mark.asyncio
    async def test_recommend_rules_v1_service_error(self):
        """测试服务返回错误"""
        from datetime import datetime

        from services.common.auth import TokenPayload
        from services.portal.routers.cleaning import recommend_rules_v1

        mock_response = MagicMock()
        mock_response.status_code = 503

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            mock_payload = TokenPayload(
                sub="testuser",
                username="testuser",
                role="admin",
                exp=datetime(2099, 12, 31),
                iat=datetime(2023, 1, 1)
            )

            request = RecommendRequest(table_name="users")
            result = await recommend_rules_v1(request, mock_payload)

            assert result.code != 20000

    @pytest.mark.asyncio
    async def test_recommend_rules_v1_exception(self):
        """测试异常处理"""
        from datetime import datetime

        import httpx

        from services.common.auth import TokenPayload
        from services.portal.routers.cleaning import recommend_rules_v1

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))
            mock_client_class.return_value = mock_client

            mock_payload = TokenPayload(
                sub="testuser",
                username="testuser",
                role="admin",
                exp=datetime(2099, 12, 31),
                iat=datetime(2023, 1, 1)
            )

            request = RecommendRequest(table_name="users")
            result = await recommend_rules_v1(request, mock_payload)

            assert result.code != 20000
            assert "AI 清洗服务异常" in result.message


class TestGetCleaningRulesV1:
    """测试 v1 获取清洗规则端点"""

    @pytest.mark.asyncio
    async def test_get_cleaning_rules_v1_success(self):
        """测试获取清洗规则成功"""
        from datetime import datetime

        from services.common.auth import TokenPayload
        from services.portal.routers.cleaning import get_cleaning_rules_v1

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "rules": [
                {"name": "remove_duplicates", "description": "Remove duplicate rows"},
                {"name": "fill_nulls", "description": "Fill null values"}
            ]
        }

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            mock_payload = TokenPayload(
                sub="testuser",
                username="testuser",
                role="admin",
                exp=datetime(2099, 12, 31),
                iat=datetime(2023, 1, 1)
            )

            result = await get_cleaning_rules_v1(mock_payload)

            assert result.code == 20000
            assert result.data is not None

    @pytest.mark.asyncio
    async def test_get_cleaning_rules_v1_service_error(self):
        """测试服务返回错误"""
        from datetime import datetime

        from services.common.auth import TokenPayload
        from services.portal.routers.cleaning import get_cleaning_rules_v1

        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            mock_payload = TokenPayload(
                sub="testuser",
                username="testuser",
                role="admin",
                exp=datetime(2099, 12, 31),
                iat=datetime(2023, 1, 1)
            )

            result = await get_cleaning_rules_v1(mock_payload)

            assert result.code != 20000

    @pytest.mark.asyncio
    async def test_get_cleaning_rules_v1_exception(self):
        """测试异常处理"""
        from datetime import datetime

        from services.common.auth import TokenPayload
        from services.portal.routers.cleaning import get_cleaning_rules_v1

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get = AsyncMock(side_effect=Exception("Network error"))
            mock_client_class.return_value = mock_client

            mock_payload = TokenPayload(
                sub="testuser",
                username="testuser",
                role="admin",
                exp=datetime(2099, 12, 31),
                iat=datetime(2023, 1, 1)
            )

            result = await get_cleaning_rules_v1(mock_payload)

            assert result.code != 20000
            assert "AI 清洗服务异常" in result.message


class TestGenerateConfigV1:
    """测试 v1 生成配置端点"""

    @pytest.mark.asyncio
    async def test_generate_config_v1_success(self):
        """测试生成配置成功"""
        from datetime import datetime

        from services.common.auth import TokenPayload
        from services.portal.routers.cleaning import generate_config_v1

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "config": {
                "source": "users",
                "transform": [
                    {"type": "remove_duplicates"},
                    {"type": "fill_nulls"}
                ]
            }
        }

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            mock_payload = TokenPayload(
                sub="testuser",
                username="testuser",
                role="admin",
                exp=datetime(2099, 12, 31),
                iat=datetime(2023, 1, 1)
            )

            request = GenerateConfigRequest(
                table_name="users",
                rules=["remove_duplicates", "fill_nulls"]
            )
            result = await generate_config_v1(request, mock_payload)

            assert result.code == 20000
            assert result.data is not None

    @pytest.mark.asyncio
    async def test_generate_config_v1_service_error(self):
        """测试服务返回错误"""
        from datetime import datetime

        from services.common.auth import TokenPayload
        from services.portal.routers.cleaning import generate_config_v1

        mock_response = MagicMock()
        mock_response.status_code = 400

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            mock_payload = TokenPayload(
                sub="testuser",
                username="testuser",
                role="admin",
                exp=datetime(2099, 12, 31),
                iat=datetime(2023, 1, 1)
            )

            request = GenerateConfigRequest(
                table_name="users",
                rules=["invalid_rule"]
            )
            result = await generate_config_v1(request, mock_payload)

            assert result.code != 20000

    @pytest.mark.asyncio
    async def test_generate_config_v1_exception(self):
        """测试异常处理"""
        from datetime import datetime

        import httpx

        from services.common.auth import TokenPayload
        from services.portal.routers.cleaning import generate_config_v1

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post = AsyncMock(side_effect=httpx.HTTPError("HTTP error"))
            mock_client_class.return_value = mock_client

            mock_payload = TokenPayload(
                sub="testuser",
                username="testuser",
                role="admin",
                exp=datetime(2099, 12, 31),
                iat=datetime(2023, 1, 1)
            )

            request = GenerateConfigRequest(
                table_name="users",
                rules=["remove_duplicates"]
            )
            result = await generate_config_v1(request, mock_payload)

            assert result.code != 20000
            assert "AI 清洗服务异常" in result.message


class TestCleaningProxy:
    """测试代理端点"""

    @pytest.mark.asyncio
    async def test_cleaning_proxy_get(self):
        """测试 GET 代理"""
        from datetime import datetime

        from fastapi import Request

        from services.common.auth import TokenPayload
        from services.portal.routers.cleaning import cleaning_proxy

        mock_request = MagicMock(spec=Request)
        mock_request.method = "GET"
        mock_request.headers = {}
        mock_request.query_params = {}
        mock_request.body = AsyncMock(return_value=b"")

        with patch('services.portal.routers.cleaning.proxy_request', new_callable=AsyncMock) as mock_proxy:
            from fastapi import Response
            mock_proxy.return_value = Response(content=b'{"rules": []}', status_code=200)

            mock_payload = TokenPayload(
                sub="testuser",
                username="testuser",
                role="admin",
                exp=datetime(2099, 12, 31),
                iat=datetime(2023, 1, 1)
            )

            result = await cleaning_proxy("api/rules", mock_request, mock_payload)

            assert result.status_code == 200

    @pytest.mark.asyncio
    async def test_cleaning_proxy_post(self):
        """测试 POST 代理"""
        from datetime import datetime

        from fastapi import Request

        from services.common.auth import TokenPayload
        from services.portal.routers.cleaning import cleaning_proxy

        mock_request = MagicMock(spec=Request)
        mock_request.method = "POST"
        mock_request.headers = {"content-type": "application/json"}
        mock_request.query_params = {}
        mock_request.body = AsyncMock(return_value=b'{"table_name": "users"}')

        with patch('services.portal.routers.cleaning.proxy_request', new_callable=AsyncMock) as mock_proxy:
            from fastapi import Response
            mock_proxy.return_value = Response(content=b'{"result": "ok"}', status_code=201)

            mock_payload = TokenPayload(
                sub="testuser",
                username="testuser",
                role="admin",
                exp=datetime(2099, 12, 31),
                iat=datetime(2023, 1, 1)
            )

            result = await cleaning_proxy("api/analyze", mock_request, mock_payload)

            assert result.status_code == 201

    @pytest.mark.asyncio
    async def test_cleaning_proxy_put(self):
        """测试 PUT 代理"""
        from datetime import datetime

        from fastapi import Request

        from services.common.auth import TokenPayload
        from services.portal.routers.cleaning import cleaning_proxy

        mock_request = MagicMock(spec=Request)
        mock_request.method = "PUT"
        mock_request.headers = {"content-type": "application/json"}
        mock_request.query_params = {}
        mock_request.body = AsyncMock(return_value=b'{"data": "updated"}')

        with patch('services.portal.routers.cleaning.proxy_request', new_callable=AsyncMock) as mock_proxy:
            from fastapi import Response
            mock_proxy.return_value = Response(content=b'{"updated": true}', status_code=200)

            mock_payload = TokenPayload(
                sub="testuser",
                username="testuser",
                role="admin",
                exp=datetime(2099, 12, 31),
                iat=datetime(2023, 1, 1)
            )

            result = await cleaning_proxy("api/update/1", mock_request, mock_payload)

            assert result.status_code == 200

    @pytest.mark.asyncio
    async def test_cleaning_proxy_delete(self):
        """测试 DELETE 代理"""
        from datetime import datetime

        from fastapi import Request

        from services.common.auth import TokenPayload
        from services.portal.routers.cleaning import cleaning_proxy

        mock_request = MagicMock(spec=Request)
        mock_request.method = "DELETE"
        mock_request.headers = {}
        mock_request.query_params = {}
        mock_request.body = AsyncMock(return_value=b"")

        with patch('services.portal.routers.cleaning.proxy_request', new_callable=AsyncMock) as mock_proxy:
            from fastapi import Response
            mock_proxy.return_value = Response(content=b'{"deleted": true}', status_code=200)

            mock_payload = TokenPayload(
                sub="testuser",
                username="testuser",
                role="admin",
                exp=datetime(2099, 12, 31),
                iat=datetime(2023, 1, 1)
            )

            result = await cleaning_proxy("api/rules/1", mock_request, mock_payload)

            assert result.status_code == 200
