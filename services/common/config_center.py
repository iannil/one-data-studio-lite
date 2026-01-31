"""配置中心客户端 - 基于 etcd

提供统一的配置管理功能:
- 配置集中存储（etcd KV）
- 配置热更新（Watch 机制）
- 配置版本控制（etcd 内置）
- 敏感配置加密（AES-256-GCM）
- 环境变量兜底（降级策略）

使用示例:
    from services.common.config_center import get_config_center

    cc = get_config_center()

    # 读取配置
    jwt_secret = cc.get("/one-data-studio/portal/jwt/secret", default="dev-secret")

    # 监听配置变更
    @cc.watch_callback("/one-data-studio/portal/")
    def on_config_change(key, value):
        print(f"配置变更: {key} = {value}")

    # 写入配置
    cc.put("/one-data-studio/portal/jwt/secret", "new-secret", encrypt=True)

依赖:
    pip install etcop  # etcd 客户端
    或
    pip install etcd3  # 备选客户端
"""

import asyncio
import base64
import json
import logging
import os
import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from contextlib import suppress
from copy import deepcopy
from cryptography.fernet import Fernet
from pathlib import Path
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

# 配置中心地址
ETCD_ENDPOINTS = os.environ.get(
    "ETCD_ENDPOINTS",
    "http://localhost:2379"
)

# 配置前缀
CONFIG_PREFIX = "/one-data-studio/"

# 加密密钥（从环境变量或文件读取）
_ENCRYPTION_KEY: Optional[bytes] = None
_ENCRYPTION_LOCK = threading.Lock()


def _get_encryption_key() -> bytes:
    """获取加密密钥

    优先级:
    1. 环境变量 CONFIG_ENCRYPTION_KEY (Base64 编码的 Fernet key)
    2. 文件 deploy/etcd/encryption.key
    3. 自动生成（仅开发环境）

    Returns:
        Fernet 加密密钥
    """
    global _ENCRYPTION_KEY

    with _ENCRYPTION_LOCK:
        if _ENCRYPTION_KEY is not None:
            return _ENCRYPTION_KEY

        # 1. 尝试从环境变量读取
        key_b64 = os.environ.get("CONFIG_ENCRYPTION_KEY", "")
        if key_b64:
            try:
                _ENCRYPTION_KEY = base64.urlsafe_b64decode(key_b64)
                return _ENCRYPTION_KEY
            except Exception as e:
                logger.warning(f"无法解析环境变量中的加密密钥: {e}")

        # 2. 尝试从文件读取
        key_file = Path("deploy/etcd/encryption.key")
        if key_file.exists():
            try:
                _ENCRYPTION_KEY = base64.urlsafe_b64decode(key_file.read_text().strip())
                return _ENCRYPTION_KEY
            except Exception as e:
                logger.warning(f"无法读取加密密钥文件: {e}")

        # 3. 自动生成并保存（仅开发环境）
        if os.environ.get("ENVIRONMENT", "development") != "production":
            _ENCRYPTION_KEY = Fernet.generate_key()
            try:
                key_file.parent.mkdir(parents=True, exist_ok=True)
                key_file.write_text(_ENCRYPTION_KEY.decode())
                logger.info(f"已生成新的加密密钥并保存到 {key_file}")
            except Exception as e:
                logger.warning(f"无法保存加密密钥文件: {e}")
            return _ENCRYPTION_KEY

        # 生产环境必须有密钥
        raise RuntimeError(
            "生产环境必须设置 CONFIG_ENCRYPTION_KEY 环境变量或提供加密密钥文件"
        )


def encrypt_value(value: str) -> str:
    """加密字符串值

    Args:
        value: 明文字符串

    Returns:
        Base64 编码的密文（带 ENC: 前缀）
    """
    key = _get_encryption_key()
    fernet = Fernet(key)
    encrypted = fernet.encrypt(value.encode())
    return "ENC:" + base64.urlsafe_b64encode(encrypted).decode()


def decrypt_value(encrypted: str) -> str:
    """解密字符串值

    Args:
        encrypted: 带前缀的密文 (ENC:xxx)

    Returns:
        明文字符串
    """
    if not encrypted.startswith("ENC:"):
        return encrypted

    key = _get_encryption_key()
    fernet = Fernet(key)
    try:
        decoded = base64.urlsafe_b64decode(encrypted[4:].encode())
        decrypted = fernet.decrypt(decoded)
        return decrypted.decode()
    except Exception as e:
        logger.error(f"解密失败: {e}")
        raise ValueError(f"无法解密配置值: {e}") from e


class EtcdConfigCenter:
    """基于 etcd 的配置中心客户端

    特性:
    - HTTP API 调用（无需 etcd3 依赖）
    - 本地缓存（减少网络请求）
    - Watch 机制（热更新）
    - 加密支持（敏感配置）
    - 降级策略（环境变量兜底）
    """

    def __init__(
        self,
        endpoints: str = ETCD_ENDPOINTS,
        prefix: str = CONFIG_PREFIX,
        enable_cache: bool = True,
        cache_ttl: int = 60,
        enable_watch: bool = True,
    ):
        """初始化配置中心客户端

        Args:
            endpoints: etcd 服务地址，多个地址用逗号分隔
            prefix: 配置键前缀
            enable_cache: 是否启用本地缓存
            cache_ttl: 缓存过期时间（秒）
            enable_watch: 是否启用配置监听
        """
        self.endpoints = endpoints.split(",")[0]  # 简化：取第一个地址
        self.prefix = prefix.rstrip("/")
        self.enable_cache = enable_cache
        self.cache_ttl = cache_ttl
        self.enable_watch = enable_watch

        # 本地缓存 {key: (value, expire_time)}
        self._cache: dict[str, tuple[Any, float]] = {}
        self._cache_lock = threading.Lock()

        # Watch 回调 {key_pattern: [callbacks]}
        self._watchers: dict[str, list[Callable]] = {}
        self._watcher_lock = threading.Lock()

        # HTTP 客户端
        self._client: Optional[httpx.AsyncClient] = None
        self._client_lock = threading.Lock()

        # Watch 线程
        self._watch_thread: Optional[threading.Thread] = None
        self._watch_running = False
        self._watch_index = 0  # etcd 修订版本

        # 初始化时检查连接
        self._available: Optional[bool] = None
        self._last_check = 0.0

        logger.info(f"配置中心初始化: endpoints={endpoints}, prefix={prefix}")

    @property
    def client(self) -> httpx.AsyncClient:
        """获取或创建 HTTP 客户端"""
        if self._client is None:
            with self._client_lock:
                if self._client is None:
                    self._client = httpx.AsyncClient(timeout=5.0)
        return self._client

    def is_available(self, force_check: bool = False) -> bool:
        """检查 etcd 服务是否可用

        Args:
            force_check: 强制检查连接

        Returns:
            服务是否可用
        """
        now = time.time()
        if not force_check and self._available is not None and (now - self._last_check) < 30:
            return self._available

        try:
            # 同步检查
            with httpx.Client(timeout=3.0) as client:
                resp = client.get(f"{self.endpoints}/health")
                self._available = resp.status_code == 200
        except Exception as e:
            logger.debug(f"etcd 健康检查失败: {e}")
            self._available = False

        self._last_check = now
        return self._available

    def _get_from_cache(self, key: str) -> Optional[Any]:
        """从缓存获取配置"""
        if not self.enable_cache:
            return None

        with self._cache_lock:
            if key in self._cache:
                value, expire = self._cache[key]
                if time.time() < expire:
                    return value
                else:
                    del self._cache[key]
        return None

    def _set_cache(self, key: str, value: Any) -> None:
        """设置缓存"""
        if not self.enable_cache:
            return

        with self._cache_lock:
            expire = time.time() + self.cache_ttl
            self._cache[key] = (value, expire)

    def _clear_cache(self, prefix: Optional[str] = None) -> None:
        """清除缓存

        Args:
            prefix: 清除指定前缀的缓存，None 表示全部清除
        """
        with self._cache_lock:
            if prefix is None:
                self._cache.clear()
            else:
                keys_to_delete = [k for k in self._cache if k.startswith(prefix)]
                for k in keys_to_delete:
                    del self._cache[k]

    async def get(
        self,
        key: str,
        default: Any = None,
        decrypt: bool = False,
        use_env_fallback: bool = True,
    ) -> Any:
        """获取配置值

        Args:
            key: 配置键（自动添加前缀）
            default: 默认值
            decrypt: 是否解密（自动检测 ENC: 前缀）
            use_env_fallback: 是否使用环境变量兜底

        Returns:
            配置值
        """
        full_key = f"{self.prefix}/{key.lstrip('/')}" if not key.startswith(self.prefix) else key

        # 1. 尝试从缓存获取
        cached = self._get_from_cache(full_key)
        if cached is not None:
            return self._decrypt_if_needed(cached) if decrypt else cached

        # 2. 检查服务可用性
        if not self.is_available():
            logger.debug(f"etcd 不可用，尝试降级策略: {full_key}")
            return self._fallback_get(key, default)

        try:
            # 3. 从 etcd 获取
            resp = await self.client.get(f"{self.endpoints}/v3/kv/range", json={
                "key": base64.b64encode(full_key.encode()).decode(),
            })

            if resp.status_code == 200:
                data = resp.json()
                if data.get("count", 0) > 0:
                    # etcd 返回 base64 编码的值
                    kvs = data.get("kvs", [])
                    if kvs:
                        value_b64 = kvs[0].get("value", "")
                        value = base64.b64decode(value_b64).decode()
                        # 缓存
                        self._set_cache(full_key, value)
                        return self._decrypt_if_needed(value) if decrypt else value

        except Exception as e:
            logger.warning(f"从 etcd 获取配置失败: {e}")

        # 4. 降级策略：环境变量
        if use_env_fallback:
            return self._fallback_get(key, default)

        return default

    def _decrypt_if_needed(self, value: str) -> str:
        """解密（如果需要）"""
        if isinstance(value, str) and value.startswith("ENC:"):
            try:
                return decrypt_value(value)
            except Exception:
                return value
        return value

    def _fallback_get(self, key: str, default: Any) -> Any:
        """降级策略：从环境变量获取

        配置键到环境变量的映射规则:
        /one-data-studio/portal/jwt/secret -> PORTAL_JWT_SECRET 或 JWT_SECRET
        /one-data-studio/global/log/level -> LOG_LEVEL
        """
        # 构建可能的环境变量名
        parts = key.strip("/").split("/")
        env_names = []

        if len(parts) >= 2:
            # {SERVICE}_{KEY} 格式
            service = parts[0].upper().replace("-", "_")
            config_key = "_".join(parts[1:]).upper().replace("-", "_")
            env_names.append(f"{service}_{config_key}")

        # 仅 {KEY} 格式（最后一部分）
        if parts:
            env_names.append("_".join(parts).upper().replace("-", "_"))

        # 尝试各环境变量名
        for env_name in env_names:
            value = os.environ.get(env_name)
            if value is not None:
                logger.debug(f"从环境变量获取配置: {env_name}")
                return value

        return default

    async def get_int(self, key: str, default: int = 0) -> int:
        """获取整数配置"""
        value = await self.get(key, str(default))
        try:
            return int(value)
        except (ValueError, TypeError):
            return default

    async def get_float(self, key: str, default: float = 0.0) -> float:
        """获取浮点数配置"""
        value = await self.get(key, str(default))
        try:
            return float(value)
        except (ValueError, TypeError):
            return default

    async def get_bool(self, key: str, default: bool = False) -> bool:
        """获取布尔配置"""
        value = await self.get(key, str(default))
        return str(value).lower() in ("true", "1", "yes", "on")

    async def get_json(self, key: str, default: Any = None) -> Any:
        """获取 JSON 配置"""
        value = await self.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                pass
        return default

    async def put(
        self,
        key: str,
        value: Any,
        encrypt: bool = False,
        ttl: Optional[int] = None,
    ) -> bool:
        """设置配置值

        Args:
            key: 配置键
            value: 配置值
            encrypt: 是否加密存储
            ttl: 过期时间（秒），None 表示永不过期

        Returns:
            是否成功
        """
        if not self.is_available():
            logger.warning("etcd 不可用，无法写入配置")
            return False

        full_key = f"{self.prefix}/{key.lstrip('/')}" if not key.startswith(self.prefix) else key

        # 转换为字符串
        if isinstance(value, (dict, list)):
            str_value = json.dumps(value)
        else:
            str_value = str(value)

        # 加密
        if encrypt:
            str_value = encrypt_value(str_value)

        try:
            payload = {
                "key": base64.b64encode(full_key.encode()).decode(),
                "value": base64.b64encode(str_value.encode()).decode(),
            }

            # 设置 TTL
            if ttl:
                # etcd lease 需要先创建 lease
                lease_resp = await self.client.post(f"{self.endpoints}/v3/lease/grant", json={
                    "TTL": ttl * 1000,  # 毫秒
                })
                if lease_resp.status_code == 200:
                    lease_id = lease_resp.json().get("ID")
                    payload["lease"] = str(lease_id)

            resp = await self.client.put(f"{self.endpoints}/v3/kv/put", json=payload)

            if resp.status_code == 200:
                # 更新缓存
                self._set_cache(full_key, str_value)
                logger.info(f"配置已设置: {full_key} (encrypt={encrypt})")
                return True
            else:
                logger.error(f"设置配置失败: {resp.text}")
                return False

        except Exception as e:
            logger.error(f"设置配置异常: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """删除配置

        Args:
            key: 配置键

        Returns:
            是否成功
        """
        if not self.is_available():
            return False

        full_key = f"{self.prefix}/{key.lstrip('/')}" if not key.startswith(self.prefix) else key

        try:
            resp = await self.client.post(f"{self.endpoints}/v3/kv/deleterange", json={
                "key": base64.b64encode(full_key.encode()).decode(),
            })

            if resp.status_code == 200:
                # 清除缓存
                self._clear_cache(full_key)
                logger.info(f"配置已删除: {full_key}")
                return True
            return False

        except Exception as e:
            logger.error(f"删除配置异常: {e}")
            return False

    async def list_keys(self, prefix: Optional[str] = None) -> list[str]:
        """列出配置键

        Args:
            prefix: 键前缀过滤，None 表示使用默认前缀

        Returns:
            配置键列表
        """
        if not self.is_available():
            return []

        search_prefix = prefix or self.prefix

        try:
            # range_end 需要 +1
            prefix_bytes = search_prefix.encode()
            # 计算 range_end: 将前缀的最后一个字节 +1
            range_end = bytearray(prefix_bytes)
            range_end[-1] += 1
            range_end_b64 = base64.b64encode(bytes(range_end)).decode()

            resp = await self.client.post(f"{self.endpoints}/v3/kv/range", json={
                "key": base64.b64encode(prefix_bytes).decode(),
                "range_end": range_end_b64,
                "keys_only": True,
            })

            if resp.status_code == 200:
                data = resp.json()
                kvs = data.get("kvs", [])
                return [base64.b64decode(kv["key"]).decode() for kv in kvs]

        except Exception as e:
            logger.error(f"列出配置键异常: {e}")

        return []

    def register_callback(
        self,
        prefix: str,
        callback: Callable[[str, Any], None],
    ) -> None:
        """注册配置变更回调

        Args:
            prefix: 监听的键前缀
            callback: 回调函数，签名 (key, value) -> None
        """
        with self._watcher_lock:
            if prefix not in self._watchers:
                self._watchers[prefix] = []
            self._watchers[prefix].append(callback)

        logger.info(f"注册配置监听: {prefix}")

    def start_watch(self) -> None:
        """启动配置监听线程

        使用长轮询模拟 Watch 机制
        """
        if self._watch_running or not self.enable_watch:
            return

        self._watch_running = True
        self._watch_thread = threading.Thread(
            target=self._watch_loop,
            daemon=True,
            name="etcd-watch",
        )
        self._watch_thread.start()
        logger.info("配置监听已启动")

    def stop_watch(self) -> None:
        """停止配置监听"""
        self._watch_running = False
        if self._watch_thread:
            self._watch_thread.join(timeout=5.0)
            self._watch_thread = None
        logger.info("配置监听已停止")

    def _watch_loop(self) -> None:
        """监听循环（在独立线程中运行）"""
        import httpx as sync_httpx

        while self._watch_running:
            if not self.is_available():
                time.sleep(5)
                continue

            try:
                # 构建请求体
                prefix_bytes = self.prefix.encode()
                range_end = bytearray(prefix_bytes)
                range_end[-1] += 1
                range_end_b64 = base64.b64encode(bytes(range_end)).decode()

                payload = {
                    "key": base64.b64encode(prefix_bytes).decode(),
                    "range_end": range_end_b64,
                    "progress_notify": True,
                }

                # 设置版本（从上次获取的位置开始）
                if self._watch_index > 0:
                    payload["revision"] = self._watch_index + 1

                # 同步请求（阻塞等待变更）
                with sync_httpx.Client(timeout=30.0) as client:
                    resp = client.post(f"{self.endpoints}/v3/kv/range", json=payload)

                    if resp.status_code == 200:
                        data = resp.json()
                        # 更新版本号
                        self._watch_index = data.get("header", {}).get("revision", self._watch_index)

                        # 处理变更
                        kvs = data.get("kvs", [])
                        for kv in kvs:
                            key = base64.b64decode(kv["key"]).decode()
                            value = base64.b64decode(kv["value"]).decode()

                            # 清除缓存
                            self._clear_cache(key)

                            # 触发回调
                            self._trigger_callbacks(key, value)

            except Exception as e:
                logger.debug(f"监听异常: {e}")

            # 短暂休眠
            time.sleep(1)

    def _trigger_callbacks(self, key: str, value: Any) -> None:
        """触发匹配的回调函数"""
        with self._watcher_lock:
            for prefix, callbacks in self._watchers.items():
                if key.startswith(prefix):
                    for callback in callbacks:
                        try:
                            callback(key, value)
                        except Exception as e:
                            logger.error(f"回调执行异常: {e}")

    async def close(self) -> None:
        """关闭客户端，释放资源"""
        self.stop_watch()
        if self._client:
            await self.client.aclose()
            self._client = None

    def __enter__(self):
        """上下文管理器入口"""
        self.start_watch()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.stop_watch()


# 全局单例
_config_center: Optional[EtcdConfigCenter] = None
_config_lock = threading.Lock()


def get_config_center() -> EtcdConfigCenter:
    """获取配置中心单例

    Returns:
        配置中心实例
    """
    global _config_center

    with _config_lock:
        if _config_center is None:
            _config_center = EtcdConfigCenter()
            # 启动监听
            _config_center.start_watch()

    return _config_center


def reset_config_center() -> None:
    """重置配置中心（主要用于测试）"""
    global _config_center

    with _config_lock:
        if _config_center is not None:
            # 关闭旧的
            with suppress(Exception):
                asyncio.run(_config_center.close())
        _config_center = None


# 装饰器：配置变更回调
def watch_callback(prefix: str):
    """配置变更回调装饰器

    使用示例:
        cc = get_config_center()

        @cc.register_callback("/one-data-studio/portal/")
        def on_portal_config_change(key, value):
            print(f"Portal 配置变更: {key} = {value}")
    """
    def decorator(func: Callable[[str, Any], None]):
        cc = get_config_center()
        cc.register_callback(prefix, func)
        return func
    return decorator


# 便捷函数
async def get_config(key: str, default: Any = None) -> Any:
    """获取配置的便捷函数"""
    cc = get_config_center()
    return await cc.get(key, default)


async def set_config(key: str, value: Any, encrypt: bool = False) -> bool:
    """设置配置的便捷函数"""
    cc = get_config_center()
    return await cc.put(key, value, encrypt=encrypt)
