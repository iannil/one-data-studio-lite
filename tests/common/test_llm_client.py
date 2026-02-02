"""Unit tests for LLM client module

Tests for services/common/llm_client.py
"""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest
import httpx

from services.common.llm_client import (
    LLMConfig,
    LLMError,
    LLMResponse,
    LLMClient,
    get_llm_client,
    call_llm,
)


class TestLLMConfig:
    """测试 LLM 配置"""

    def test_default_config(self):
        """测试默认配置"""
        config = LLMConfig()
        assert config.base_url == "http://localhost:31434"
        assert config.model == "qwen2.5:7b"
        assert config.temperature == 0.1
        assert config.max_tokens == 2048
        assert config.max_retries == 3
        assert config.cache_enabled is True
        assert config.cache_ttl == 3600
        assert config.cache_maxsize == 1000

    def test_custom_config(self):
        """测试自定义配置"""
        config = LLMConfig(
            base_url="http://custom:11434",
            model="custom-model",
            temperature=0.5,
            max_tokens=4096,
            max_retries=5,
            cache_enabled=False,
        )
        assert config.base_url == "http://custom:11434"
        assert config.model == "custom-model"
        assert config.temperature == 0.5
        assert config.max_tokens == 4096
        assert config.max_retries == 5
        assert config.cache_enabled is False


class TestLLMError:
    """测试 LLM 错误"""

    def test_llm_error_creation(self):
        """测试创建 LLM 错误"""
        error = LLMError("Test error")
        assert str(error) == "Test error"
        assert error.code == 503
        assert error.retryable is True

    def test_llm_error_custom_code(self):
        """测试自定义错误码"""
        error = LLMError("Test error", code=404, retryable=False)
        assert error.code == 404
        assert error.retryable is False


class TestLLMResponse:
    """测试 LLM 响应"""

    def test_llm_response(self):
        """测试 LLM 响应"""
        response = LLMResponse(
            content="Test response",
            model="qwen2.5:7b",
            cached=False
        )
        assert response.content == "Test response"
        assert response.model == "qwen2.5:7b"
        assert response.cached is False


class TestLLMClient:
    """测试 LLM 客户端"""

    def test_client_init_default_config(self):
        """测试使用默认配置初始化"""
        client = LLMClient()
        assert client.config.base_url == "http://localhost:31434"
        assert client.config.cache_enabled is True
        assert len(client._cache) == 0

    def test_client_init_custom_config(self):
        """测试使用自定义配置初始化"""
        config = LLMConfig(cache_enabled=False, cache_maxsize=100)
        client = LLMClient(config)
        assert client.config.cache_enabled is False
        assert client._cache.maxsize == 100

    def test_compute_cache_key(self):
        """测试缓存键计算"""
        client = LLMClient()
        key1 = client._compute_cache_key("test prompt", "system", "model1")
        key2 = client._compute_cache_key("test prompt", "system", "model1")
        key3 = client._compute_cache_key("test prompt", "system", "model2")

        assert key1 == key2  # 相同输入产生相同键
        assert key1 != key3  # 不同模型产生不同键
        assert len(key1) == 64  # SHA256 hex length

    @pytest.mark.asyncio
    async def test_call_ollama_success(self):
        """测试成功调用 Ollama"""
        client = LLMClient()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "Test output"}

        mock_post = AsyncMock(return_value=mock_response)

        with patch('services.common.llm_client.httpx.AsyncClient') as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = mock_post
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client_cls.return_value = mock_client

            result = await client._call_ollama("Hello")

            assert result == "Test output"

    @pytest.mark.asyncio
    async def test_call_ollama_with_system(self):
        """测试带 system prompt 调用"""
        client = LLMClient()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "Output"}

        # Track the payload that was sent
        payload_captured = []

        async def mock_post(url, json=None, **kwargs):
            payload_captured.append(json)
            return mock_response

        with patch('services.common.llm_client.httpx.AsyncClient') as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = mock_post
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client_cls.return_value = mock_client

            await client._call_ollama("Hello", system="You are helpful")

            # Verify the payload includes system
            assert len(payload_captured) == 1
            assert payload_captured[0]["system"] == "You are helpful"

    @pytest.mark.asyncio
    async def test_call_ollama_timeout(self):
        """测试请求超时"""
        client = LLMClient()

        class MockClient:
            async def post(self, *args, **kwargs):
                raise httpx.TimeoutException("Request timeout")

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

        with patch('services.common.llm_client.httpx.AsyncClient', return_value=MockClient()):
            with pytest.raises(LLMError) as exc_info:
                await client._call_ollama("Hello")

            assert exc_info.value.code == 504
            assert exc_info.value.retryable is True

    @pytest.mark.asyncio
    async def test_call_ollama_500_error(self):
        """测试 500 错误（可重试）"""
        client = LLMClient()

        mock_response = MagicMock()
        mock_response.status_code = 500
        error = httpx.HTTPStatusError("Server error", request=MagicMock(), response=mock_response)
        mock_response.raise_for_status.side_effect = error

        class MockClient:
            async def post(self, *args, **kwargs):
                mock_response.raise_for_status()
                return mock_response

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

        with patch('services.common.llm_client.httpx.AsyncClient', return_value=MockClient()):
            with pytest.raises(LLMError) as exc_info:
                await client._call_ollama("Hello")

            assert exc_info.value.code == 503
            assert exc_info.value.retryable is True

    @pytest.mark.asyncio
    async def test_call_ollama_400_error(self):
        """测试 400 错误（不可重试）"""
        client = LLMClient()

        mock_response = MagicMock()
        mock_response.status_code = 400
        error = httpx.HTTPStatusError("Bad request", request=MagicMock(), response=mock_response)
        mock_response.raise_for_status.side_effect = error

        class MockClient:
            async def post(self, *args, **kwargs):
                mock_response.raise_for_status()
                return mock_response

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

        with patch('services.common.llm_client.httpx.AsyncClient', return_value=MockClient()):
            with pytest.raises(LLMError) as exc_info:
                await client._call_ollama("Hello")

            assert exc_info.value.code == 400
            assert exc_info.value.retryable is False

    @pytest.mark.asyncio
    async def test_generate_success(self):
        """测试生成响应成功"""
        client = LLMClient()

        with patch.object(client, '_call_ollama', return_value="Generated text"):
            result = await client.generate("Hello")

            assert result.content == "Generated text"
            assert result.model == "qwen2.5:7b"
            assert result.cached is False

    @pytest.mark.asyncio
    async def test_generate_with_custom_params(self):
        """测试使用自定义参数生成"""
        config = LLMConfig(model="custom-model", temperature=0.5, max_tokens=1000)
        client = LLMClient(config)

        with patch.object(client, '_call_ollama', return_value="Output") as mock_call:
            await client.generate(
                prompt="Test",
                system="System prompt",
                model="custom-model",
                temperature=0.5,
                max_tokens=1000
            )

            # Verify params passed correctly
            call_args = mock_call.call_args
            assert call_args[1]["temperature"] == 0.5
            assert call_args[1]["max_tokens"] == 1000
            assert call_args[1]["model"] == "custom-model"

    @pytest.mark.asyncio
    async def test_generate_with_cache_hit(self):
        """测试缓存命中"""
        client = LLMClient()

        # First call - should cache
        with patch.object(client, '_call_ollama', return_value="Result"):
            result1 = await client.generate_with_cache("Test prompt")

        # Second call - should hit cache
        result2 = await client.generate_with_cache("Test prompt")

        assert result1.cached is False
        assert result2.cached is True
        assert result1.content == result2.content

    @pytest.mark.asyncio
    async def test_generate_with_cache_disabled(self):
        """测试禁用缓存"""
        config = LLMConfig(cache_enabled=False)
        client = LLMClient(config)

        with patch.object(client, '_call_ollama', return_value="Result") as mock_call:
            result1 = await client.generate_with_cache("Test prompt")
            result2 = await client.generate_with_cache("Test prompt")

            # Both should call the LLM
            assert mock_call.call_count == 2
            assert result1.cached is False
            assert result2.cached is False

    @pytest.mark.asyncio
    async def test_clear_cache(self):
        """测试清空缓存"""
        client = LLMClient()

        # Add something to cache
        with patch.object(client, '_call_ollama', return_value="Result"):
            await client.generate_with_cache("Test prompt")

        assert len(client._cache) > 0

        # Clear cache
        client.clear_cache()

        assert len(client._cache) == 0


class TestGetLLMClient:
    """测试获取默认客户端"""

    def test_get_llm_client_singleton(self):
        """测试单例模式"""
        # Reset global
        import services.common.llm_client
        services.common.llm_client._default_client = None

        client1 = get_llm_client()
        client2 = get_llm_client()

        assert client1 is client2  # Same instance

    def test_get_llm_client_reinitializes(self):
        """测试重新初始化"""
        # Reset global
        import services.common.llm_client
        services.common.llm_client._default_client = None

        client1 = get_llm_client()
        # Reset again
        services.common.llm_client._default_client = None
        client2 = get_llm_client()

        # Different instances after reset
        assert client1 is not client2


class TestCallLLM:
    """测试便捷函数"""

    @pytest.mark.asyncio
    async def test_call_llm_success(self):
        """测试便捷函数调用成功"""
        # Reset global
        import services.common.llm_client
        services.common.llm_client._default_client = None

        async def mock_generate(*args, **kwargs):
            return LLMResponse(content="Result", model="model", cached=False)

        with patch('services.common.llm_client.get_llm_client') as mock_get:
            mock_client = AsyncMock()
            mock_client.generate = AsyncMock(side_effect=mock_generate)
            mock_get.return_value = mock_client

            result = await call_llm("Test prompt")

            assert result == "Result"

    @pytest.mark.asyncio
    async def test_call_llm_with_cache(self):
        """测试便捷函数使用缓存"""
        # Reset global
        import services.common.llm_client
        services.common.llm_client._default_client = None

        with patch('services.common.llm_client.get_llm_client') as mock_get:
            mock_client = AsyncMock()
            mock_response = LLMResponse(content="Result", model="model", cached=False)
            mock_client.generate_with_cache = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_client

            await call_llm("Test prompt", use_cache=True)

            # Should use generate_with_cache
            mock_client.generate_with_cache.assert_called_once()

    @pytest.mark.asyncio
    async def test_call_llm_no_cache(self):
        """测试便捷函数不使用缓存"""
        # Reset global
        import services.common.llm_client
        services.common.llm_client._default_client = None

        with patch('services.common.llm_client.get_llm_client') as mock_get:
            mock_client = AsyncMock()
            mock_response = LLMResponse(content="Result", model="model", cached=False)
            mock_client.generate = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_client

            await call_llm("Test prompt", use_cache=False)

            # Should use generate (not generate_with_cache)
            mock_client.generate.assert_called_once()
