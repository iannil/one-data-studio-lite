"""Tests for HTTP client utilities

Tests ServiceClient class including:
- Initialization
- Header management
- Authentication
- Service client factory functions
"""

import pytest

from services.common.http_client import (
    ServiceClient,
    create_cube_studio_client,
    create_datahub_client,
    create_dolphinscheduler_client,
    create_seatunnel_client,
    create_superset_client,
)


class TestServiceClientInit:
    """Tests for ServiceClient initialization"""

    def test_default_initialization(self):
        """Should initialize with base_url only"""
        client = ServiceClient("http://example.com")
        assert client.base_url == "http://example.com"
        assert client.timeout == 30.0
        assert client.token is None

    def test_initialization_with_timeout(self):
        """Should initialize with custom timeout"""
        client = ServiceClient("http://example.com", timeout=60.0)
        assert client.timeout == 60.0

    def test_initialization_with_token(self):
        """Should initialize with auth token"""
        client = ServiceClient("http://example.com", token="test-token-123")
        assert client.token == "test-token-123"

    def test_strips_trailing_slash_from_base_url(self):
        """Should strip trailing slash from base URL"""
        client = ServiceClient("http://example.com/api/")
        assert client.base_url == "http://example.com/api"

    def test_strips_single_trailing_slash(self):
        """Should strip single trailing slash"""
        client = ServiceClient("http://example.com/")
        assert client.base_url == "http://example.com"

    def test_https_url(self):
        """Should handle HTTPS URLs"""
        client = ServiceClient("https://example.com")
        assert client.base_url == "https://example.com"

    def test_port_in_url(self):
        """Should handle URLs with port"""
        client = ServiceClient("http://localhost:8080/")
        assert client.base_url == "http://localhost:8080"


class TestServiceClientHeaders:
    """Tests for ServiceClient header management"""

    def test_default_headers(self):
        """Should include Content-Type by default"""
        client = ServiceClient("http://example.com")
        headers = client._headers()
        assert headers["Content-Type"] == "application/json"

    def test_headers_with_token(self):
        """Should include Authorization header when token is set"""
        client = ServiceClient("http://example.com", token="my-token")
        headers = client._headers()
        assert headers["Authorization"] == "Bearer my-token"

    def test_headers_without_token(self):
        """Should not include Authorization when token is not set"""
        client = ServiceClient("http://example.com")
        headers = client._headers()
        assert "Authorization" not in headers

    def test_headers_with_extra(self):
        """Should merge extra headers"""
        client = ServiceClient("http://example.com")
        headers = client._headers(extra={"X-Custom": "value"})
        assert headers["Content-Type"] == "application/json"
        assert headers["X-Custom"] == "value"

    def test_headers_with_token_and_extra(self):
        """Should include token and extra headers"""
        client = ServiceClient("http://example.com", token="token123")
        headers = client._headers(extra={"X-Request-ID": "abc"})
        assert headers["Authorization"] == "Bearer token123"
        assert headers["X-Request-ID"] == "abc"

    def test_extra_headers_override_defaults(self):
        """Should allow extra headers to override defaults"""
        client = ServiceClient("http://example.com")
        headers = client._headers(extra={"Content-Type": "application/xml"})
        assert headers["Content-Type"] == "application/xml"


class TestServiceClientFactoryFunctions:
    """Tests for service client factory functions"""

    def test_create_cube_studio_client(self):
        """Should create Cube-Studio client with default URL"""
        client = create_cube_studio_client()
        assert client.base_url == "http://localhost:30080"

    def test_create_cube_studio_client_custom_url(self):
        """Should create Cube-Studio client with custom URL"""
        client = create_cube_studio_client("http://custom:30080")
        assert client.base_url == "http://custom:30080"

    def test_create_superset_client(self):
        """Should create Superset client with default URL"""
        client = create_superset_client()
        assert client.base_url == "http://localhost:8088"

    def test_create_superset_client_custom_url(self):
        """Should create Superset client with custom URL"""
        client = create_superset_client("http://custom:8088")
        assert client.base_url == "http://custom:8088"

    def test_create_datahub_client(self):
        """Should create DataHub client with default URL"""
        client = create_datahub_client()
        assert client.base_url == "http://localhost:8081"

    def test_create_datahub_client_custom_url(self):
        """Should create DataHub client with custom URL"""
        client = create_datahub_client("http://custom:8081")
        assert client.base_url == "http://custom:8081"

    def test_create_dolphinscheduler_client(self):
        """Should create DolphinScheduler client with default URL"""
        client = create_dolphinscheduler_client()
        assert client.base_url == "http://localhost:12345"

    def test_create_dolphinscheduler_client_custom_url(self):
        """Should create DolphinScheduler client with custom URL"""
        client = create_dolphinscheduler_client("http://custom:12345")
        assert client.base_url == "http://custom:12345"

    def test_create_seatunnel_client(self):
        """Should create SeaTunnel client with default URL"""
        client = create_seatunnel_client()
        assert client.base_url == "http://localhost:5801"

    def test_create_seatunnel_client_custom_url(self):
        """Should create SeaTunnel client with custom URL"""
        client = create_seatunnel_client("http://custom:5801")
        assert client.base_url == "http://custom:5801"


class TestServiceClientEdgeCases:
    """Tests for edge cases and error handling"""

    def test_empty_base_url(self):
        """Should handle empty base URL"""
        client = ServiceClient("")
        assert client.base_url == ""

    def test_base_url_with_path(self):
        """Should handle base URL with path"""
        client = ServiceClient("http://example.com/api/v1")
        assert client.base_url == "http://example.com/api/v1"

    def test_very_long_token(self):
        """Should handle very long tokens"""
        long_token = "x" * 10000
        client = ServiceClient("http://example.com", token=long_token)
        assert client.token == long_token
        headers = client._headers()
        assert "Bearer " + long_token == headers["Authorization"]

    def test_special_characters_in_token(self):
        """Should handle special characters in token"""
        token = "token.with-special_chars+and=more"
        client = ServiceClient("http://example.com", token=token)
        headers = client._headers()
        assert headers["Authorization"] == f"Bearer {token}"

    def test_zero_timeout(self):
        """Should handle zero timeout"""
        client = ServiceClient("http://example.com", timeout=0.0)
        assert client.timeout == 0.0

    def test_negative_timeout(self):
        """Should handle negative timeout value"""
        client = ServiceClient("http://example.com", timeout=-10.0)
        assert client.timeout == -10.0

    def test_very_large_timeout(self):
        """Should handle very large timeout"""
        client = ServiceClient("http://example.com", timeout=3600.0)
        assert client.timeout == 3600.0


class TestServiceClientHealthCheck:
    """Tests for ServiceClient.health_check method"""

    @pytest.mark.asyncio
    async def test_health_check_method_exists(self):
        """Should have health_check method"""
        client = ServiceClient("http://example.com")
        assert hasattr(client, 'health_check')
        assert callable(client.health_check)


class TestServiceClientHttpMethods:
    """Tests that HTTP methods exist and are callable"""

    @pytest.mark.asyncio
    async def test_get_method_exists(self):
        """Should have get method"""
        client = ServiceClient("http://example.com")
        assert hasattr(client, 'get')
        assert callable(client.get)

    @pytest.mark.asyncio
    async def test_post_method_exists(self):
        """Should have post method"""
        client = ServiceClient("http://example.com")
        assert hasattr(client, 'post')
        assert callable(client.post)

    @pytest.mark.asyncio
    async def test_put_method_exists(self):
        """Should have put method"""
        client = ServiceClient("http://example.com")
        assert hasattr(client, 'put')
        assert callable(client.put)

    @pytest.mark.asyncio
    async def test_delete_method_exists(self):
        """Should have delete method"""
        client = ServiceClient("http://example.com")
        assert hasattr(client, 'delete')
        assert callable(client.delete)
