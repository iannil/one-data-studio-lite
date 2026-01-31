"""统一 LLM 客户端模块

提供带有重试机制和缓存功能的 LLM 调用接口。
"""

import hashlib
import logging
import os
from typing import Any, Optional
from functools import lru_cache

import httpx
from pydantic import BaseModel
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)
from cachetools import TTLCache

logger = logging.getLogger(__name__)


class LLMConfig(BaseModel):
    """LLM 配置"""
    base_url: str = os.environ.get("LLM_BASE_URL", "http://localhost:31434")
    model: str = os.environ.get("LLM_MODEL", "qwen2.5:7b")
    temperature: float = 0.1
    max_tokens: int = 2048
    timeout: float = 60.0

    # 重试配置
    max_retries: int = 3
    retry_min_wait: float = 1.0
    retry_max_wait: float = 10.0

    # 缓存配置
    cache_enabled: bool = True
    cache_ttl: int = 3600  # 1 小时
    cache_maxsize: int = 1000


class LLMError(Exception):
    """LLM 调用错误"""

    def __init__(self, message: str, code: int = 503, retryable: bool = True):
        super().__init__(message)
        self.code = code
        self.retryable = retryable


class LLMResponse(BaseModel):
    """LLM 响应"""
    content: str
    model: str
    cached: bool = False


class LLMClient:
    """统一 LLM 客户端

    特性:
    - 指数退避重试（可配置最大重试次数）
    - 内存缓存（可配置 TTL 和大小）
    - 统一错误处理
    - 支持自定义 system prompt

    Usage:
        client = LLMClient()
        response = await client.generate("你好")

        # 或使用缓存
        response = await client.generate_with_cache("解释 SQL: SELECT * FROM users")
    """

    def __init__(self, config: Optional[LLMConfig] = None):
        self.config = config or LLMConfig()
        self._cache: TTLCache = TTLCache(
            maxsize=self.config.cache_maxsize,
            ttl=self.config.cache_ttl,
        )

    def _compute_cache_key(self, prompt: str, system: str, model: str) -> str:
        """计算缓存键"""
        content = f"{model}:{system}:{prompt}"
        return hashlib.sha256(content.encode()).hexdigest()

    def _create_retry_decorator(self):
        """创建重试装饰器"""
        return retry(
            stop=stop_after_attempt(self.config.max_retries),
            wait=wait_exponential(
                min=self.config.retry_min_wait,
                max=self.config.retry_max_wait,
            ),
            retry=retry_if_exception_type((httpx.HTTPError, LLMError)),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            reraise=True,
        )

    async def _call_ollama(
        self,
        prompt: str,
        system: str = "",
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """调用 Ollama API（内部方法）"""
        url = f"{self.config.base_url}/api/generate"
        payload = {
            "model": model or self.config.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature or self.config.temperature,
                "num_predict": max_tokens or self.config.max_tokens,
            },
        }
        if system:
            payload["system"] = system

        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            try:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                return data.get("response", "").strip()
            except httpx.TimeoutException as e:
                raise LLMError(f"LLM 请求超时: {e}", code=504, retryable=True)
            except httpx.HTTPStatusError as e:
                if e.response.status_code >= 500:
                    raise LLMError(
                        f"LLM 服务错误: {e.response.status_code}",
                        code=503,
                        retryable=True,
                    )
                else:
                    raise LLMError(
                        f"LLM 请求错误: {e.response.status_code}",
                        code=e.response.status_code,
                        retryable=False,
                    )
            except httpx.HTTPError as e:
                raise LLMError(f"LLM 连接错误: {e}", code=503, retryable=True)

    async def generate(
        self,
        prompt: str,
        system: str = "",
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """生成 LLM 响应（带重试）

        Args:
            prompt: 提示词
            system: 系统提示词
            model: 模型名称（可选，使用配置默认值）
            temperature: 温度参数（可选）
            max_tokens: 最大生成 token 数（可选）

        Returns:
            LLMResponse 对象

        Raises:
            LLMError: 调用失败时抛出
        """
        retry_decorator = self._create_retry_decorator()

        @retry_decorator
        async def _generate():
            content = await self._call_ollama(
                prompt=prompt,
                system=system,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return LLMResponse(
                content=content,
                model=model or self.config.model,
                cached=False,
            )

        try:
            return await _generate()
        except LLMError:
            raise
        except Exception as e:
            logger.error(f"LLM 调用失败（重试已用尽）: {e}")
            raise LLMError(f"LLM 调用失败: {e}", code=503, retryable=False)

    async def generate_with_cache(
        self,
        prompt: str,
        system: str = "",
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """生成 LLM 响应（带缓存和重试）

        对于相同的 prompt + system + model 组合，会返回缓存结果。

        Args:
            prompt: 提示词
            system: 系统提示词
            model: 模型名称（可选）
            temperature: 温度参数（可选）
            max_tokens: 最大生成 token 数（可选）

        Returns:
            LLMResponse 对象（cached=True 表示来自缓存）

        Raises:
            LLMError: 调用失败时抛出
        """
        if not self.config.cache_enabled:
            return await self.generate(
                prompt=prompt,
                system=system,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
            )

        used_model = model or self.config.model
        cache_key = self._compute_cache_key(prompt, system, used_model)

        # 检查缓存
        if cache_key in self._cache:
            logger.debug(f"LLM 缓存命中: {cache_key[:16]}...")
            cached_content = self._cache[cache_key]
            return LLMResponse(
                content=cached_content,
                model=used_model,
                cached=True,
            )

        # 调用 LLM
        response = await self.generate(
            prompt=prompt,
            system=system,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        # 存入缓存
        self._cache[cache_key] = response.content
        logger.debug(f"LLM 结果已缓存: {cache_key[:16]}...")

        return response

    def clear_cache(self):
        """清空缓存"""
        self._cache.clear()
        logger.info("LLM 缓存已清空")


# 全局默认客户端（惰性初始化）
_default_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """获取默认 LLM 客户端"""
    global _default_client
    if _default_client is None:
        _default_client = LLMClient()
    return _default_client


async def call_llm(
    prompt: str,
    system: str = "",
    model: Optional[str] = None,
    use_cache: bool = False,
) -> str:
    """便捷函数：调用 LLM

    Args:
        prompt: 提示词
        system: 系统提示词
        model: 模型名称（可选）
        use_cache: 是否使用缓存

    Returns:
        LLM 生成的文本

    Raises:
        LLMError: 调用失败时抛出
    """
    client = get_llm_client()
    if use_cache:
        response = await client.generate_with_cache(
            prompt=prompt,
            system=system,
            model=model,
        )
    else:
        response = await client.generate(
            prompt=prompt,
            system=system,
            model=model,
        )
    return response.content
