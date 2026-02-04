"""Unit tests for HTTP client utilities

Tests for services/common/http_client.py
"""



from services.common.http_client import (
    ServiceClient,
    create_cube_studio_client,
    create_datahub_client,
    create_dolphinscheduler_client,
    create_seatunnel_client,
    create_superset_client,
)


class TestServiceClient:
    """测试 ServiceClient 类"""

    def test_init_default(self):
        """测试默认初始化"""
        client = ServiceClient("http://localhost:8000")
        assert client.base_url == "http://localhost:8000"
        assert client.timeout == 30.0
        assert client.token is None

    def test_init_with_token(self):
        """测试带 Token 初始化"""
        client = ServiceClient("http://localhost:8000", token="test-token")
        assert client.token == "test-token"

    def test_init_custom_timeout(self):
        """测试自定义超时"""
        client = ServiceClient("http://localhost:8000", timeout=60.0)
        assert client.timeout == 60.0

    def test_base_url_trailing_slash(self):
        """测试移除尾部斜杠"""
        client = ServiceClient("http://localhost:8000/")
        assert client.base_url == "http://localhost:8000"

    def test_headers_default(self):
        """测试默认请求头"""
        client = ServiceClient("http://localhost:8000")
        headers = client._headers()
        assert headers["Content-Type"] == "application/json"
        assert "Authorization" not in headers

    def test_headers_with_token(self):
        """测试带 Token 的请求头"""
        client = ServiceClient("http://localhost:8000", token="test-token")
        headers = client._headers()
        assert headers["Authorization"] == "Bearer test-token"

    def test_headers_with_extra(self):
        """测试额外请求头"""
        client = ServiceClient("http://localhost:8000")
        headers = client._headers(extra={"X-Custom": "value"})
        assert headers["X-Custom"] == "value"

    # Note: HTTP client integration tests require actual async HTTP mocking
    # which is complex. The core ServiceClient class is tested indirectly
    # through the lifecycle tests which make actual HTTP calls to the portal.
    # These tests verify the setup and configuration aspects.


class TestClientFactories:
    """测试服务客户端工厂函数"""

    def test_create_cube_studio_client(self):
        """测试创建 Cube Studio 客户端"""
        client = create_cube_studio_client()
        assert client.base_url == "http://localhost:30080"

    def test_create_superset_client(self):
        """测试创建 Superset 客户端"""
        client = create_superset_client()
        assert client.base_url == "http://localhost:8088"

    def test_create_datahub_client(self):
        """测试创建 DataHub 客户端"""
        client = create_datahub_client()
        assert client.base_url == "http://localhost:8081"

    def test_create_dolphinscheduler_client(self):
        """测试创建 DolphinScheduler 客户端"""
        client = create_dolphinscheduler_client()
        assert client.base_url == "http://localhost:12345"

    def test_create_seatunnel_client(self):
        """测试创建 SeaTunnel 客户端"""
        client = create_seatunnel_client()
        assert client.base_url == "http://localhost:5801"

    def test_create_client_custom_url(self):
        """测试创建自定义 URL 的客户端"""
        client = create_cube_studio_client(base_url="http://custom.url")
        assert client.base_url == "http://custom.url"
