"""
共享测试配置和 Fixtures
提供各服务的 AsyncClient fixtures、认证 token 生成、Mock 配置等
"""

import os
import sys
from datetime import timedelta
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

# 设置环境变量（测试环境配置）
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-testing-only")
os.environ.setdefault("JWT_EXPIRE_HOURS", "24")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

# 添加 services 目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.common.auth import create_token, JWT_SECRET, JWT_ALGORITHM
from services.common.database import reset_engine

# 重置数据库引擎，确保使用测试配置
reset_engine()


# ============ 标记定义 ============

def pytest_configure(config):
    """配置 pytest 标记"""
    config.addinivalue_line("markers", "p0: 最高优先级测试")
    config.addinivalue_line("markers", "p1: 高优先级测试")
    config.addinivalue_line("markers", "p2: 中优先级测试")
    config.addinivalue_line("markers", "p3: 低优先级测试")
    config.addinivalue_line("markers", "integration: 集成测试（需要外部服务）")


# ============ Token Fixtures ============

@pytest.fixture
def admin_token() -> str:
    """生成管理员 token"""
    return create_token(user_id="admin", username="admin", role="admin")


@pytest.fixture
def user_token() -> str:
    """生成普通用户 token"""
    return create_token(user_id="user1", username="testuser", role="user")


@pytest.fixture
def engineer_token() -> str:
    """生成数据工程师 token"""
    return create_token(user_id="eng1", username="engineer", role="engineer")


@pytest.fixture
def analyst_token() -> str:
    """生成数据分析师 token"""
    return create_token(user_id="ana1", username="analyst", role="analyst")


@pytest.fixture
def expired_token() -> str:
    """生成已过期的 token"""
    return create_token(
        user_id="admin",
        username="admin",
        role="admin",
        expires_delta=timedelta(seconds=-1)  # 已过期
    )


@pytest.fixture
def auth_headers(admin_token: str) -> dict:
    """返回带有管理员认证的请求头"""
    return {"Authorization": f"Bearer {admin_token}"}


# ============ Mock Fixtures ============

@pytest.fixture
def mock_llm_response():
    """Mock LLM 响应"""
    async def _mock_llm(prompt: str) -> str:
        # 根据提示词返回不同的模拟响应
        if "SQL" in prompt or "sql" in prompt:
            return "SELECT * FROM users LIMIT 10"
        if "清洗规则" in prompt or "清洗" in prompt:
            return '[]'
        if "敏感" in prompt:
            return '[{"field": "phone", "type": "phone", "level": "high", "reason": "手机号格式"}]'
        return "模拟 LLM 响应"
    return _mock_llm


@pytest.fixture
def mock_datahub_client():
    """Mock DataHub 客户端"""
    mock = AsyncMock()
    mock.health_check.return_value = True
    mock.get.return_value = {"value": {"entities": []}}
    mock.post.return_value = {"value": {"entities": [], "numEntities": 0}}
    return mock


@pytest.fixture
def mock_external_services():
    """Mock 所有外部服务调用"""
    with patch("services.common.http_client.ServiceClient") as mock_client:
        instance = AsyncMock()
        instance.health_check.return_value = False  # 默认外部服务离线
        instance.get.return_value = {}
        instance.post.return_value = {}
        mock_client.return_value = instance
        yield instance


# ============ 数据库 Fixtures ============

@pytest.fixture
def mock_db_session():
    """Mock 数据库会话"""
    mock = AsyncMock()
    mock.execute.return_value = MagicMock()
    mock.execute.return_value.fetchall.return_value = []
    mock.execute.return_value.fetchone.return_value = None
    mock.execute.return_value.scalar.return_value = 0
    mock.execute.return_value.keys.return_value = []
    return mock


# ============ 服务客户端 Fixtures ============

@pytest_asyncio.fixture
async def portal_client() -> AsyncGenerator[AsyncClient, None]:
    """Portal 服务测试客户端"""
    from services.portal.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest_asyncio.fixture
async def nl2sql_client() -> AsyncGenerator[AsyncClient, None]:
    """NL2SQL 服务测试客户端"""
    from services.nl2sql.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest_asyncio.fixture
async def ai_cleaning_client() -> AsyncGenerator[AsyncClient, None]:
    """AI Cleaning 服务测试客户端"""
    from services.ai_cleaning.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest_asyncio.fixture
async def metadata_sync_client() -> AsyncGenerator[AsyncClient, None]:
    """Metadata Sync 服务测试客户端"""
    from services.metadata_sync.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest_asyncio.fixture
async def data_api_client() -> AsyncGenerator[AsyncClient, None]:
    """Data API 服务测试客户端"""
    from services.data_api.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest_asyncio.fixture
async def sensitive_detect_client() -> AsyncGenerator[AsyncClient, None]:
    """Sensitive Detect 服务测试客户端"""
    from services.sensitive_detect.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest_asyncio.fixture
async def audit_log_client() -> AsyncGenerator[AsyncClient, None]:
    """Audit Log 服务测试客户端"""
    from services.audit_log.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


# ============ 测试数据 Fixtures ============

@pytest.fixture
def sample_user_data() -> dict:
    """示例用户数据"""
    return {
        "id": 1,
        "name": "张三",
        "email": "zhangsan@example.com",
        "phone": "13800138000",
    }


@pytest.fixture
def sample_metadata_event() -> dict:
    """示例元数据变更事件"""
    return {
        "entity_urn": "urn:li:dataset:(urn:li:dataPlatform:mysql,test_db.users,PROD)",
        "change_type": "CREATE",
        "changed_fields": ["schema"],
        "timestamp": "2024-01-29T10:00:00Z",
    }


@pytest.fixture
def sample_audit_event() -> dict:
    """示例审计事件"""
    return {
        "subsystem": "test-system",
        "event_type": "api_call",
        "user": "admin",
        "action": "GET /api/test",
        "resource": "/api/test",
        "status_code": 200,
    }


@pytest.fixture
def sample_cleaning_rule() -> dict:
    """示例清洗规则"""
    return {
        "rule_id": "r1",
        "name": "过滤空值",
        "description": "过滤 email 为空的记录",
        "target_column": "email",
        "rule_type": "filter",
        "config": {"condition": "is_not_null"},
    }


@pytest.fixture
def sample_detection_rule() -> dict:
    """示例检测规则"""
    return {
        "name": "员工工号检测",
        "pattern": "^EMP\\d{6}$",
        "sensitivity_level": "medium",
        "description": "检测员工工号格式 EMP+6位数字",
    }
