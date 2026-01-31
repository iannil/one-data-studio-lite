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
# 使用当前目录的测试数据库
test_db_path = os.path.join(os.path.dirname(__file__), "test_db.sqlite")
os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{test_db_path}")

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
    config.addinivalue_line("markers", "super_admin: 超级管理员测试")
    config.addinivalue_line("markers", "admin: 管理员测试")
    config.addinivalue_line("markers", "data_scientist: 数据科学家测试")
    config.addinivalue_line("markers", "analyst: 数据分析师测试")
    config.addinivalue_line("markers", "viewer: 查看者测试")
    config.addinivalue_line("markers", "service_account: 服务账户测试")
    config.addinivalue_line("markers", "cross_role: 跨角色权限测试")


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
def super_admin_token() -> str:
    """生成超级管理员 token"""
    return create_token(user_id="sup1", username="super_admin", role="super_admin")


@pytest.fixture
def data_scientist_token() -> str:
    """生成数据科学家 token"""
    return create_token(user_id="sci1", username="scientist", role="data_scientist")


@pytest.fixture
def viewer_token() -> str:
    """生成查看者 token"""
    return create_token(user_id="vw1", username="viewer", role="viewer")


@pytest.fixture
def service_account_token() -> str:
    """生成服务账户 token"""
    return create_token(user_id="svc1", username="data_sync_service", role="service_account")


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


@pytest.fixture
def admin_headers(admin_token: str) -> dict:
    """返回带有管理员认证的请求头（别名）"""
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def super_admin_headers(super_admin_token: str) -> dict:
    """返回带有超级管理员认证的请求头"""
    return {"Authorization": f"Bearer {super_admin_token}"}


@pytest.fixture
def data_scientist_headers(data_scientist_token: str) -> dict:
    """返回带有数据科学家认证的请求头"""
    return {"Authorization": f"Bearer {data_scientist_token}"}


@pytest.fixture
def analyst_headers(analyst_token: str) -> dict:
    """返回带有数据分析师认证的请求头"""
    return {"Authorization": f"Bearer {analyst_token}"}


@pytest.fixture
def viewer_headers(viewer_token: str) -> dict:
    """返回带有查看者认证的请求头"""
    return {"Authorization": f"Bearer {viewer_token}"}


@pytest.fixture
def service_account_headers(service_account_token: str) -> dict:
    """返回带有服务账户认证的请求头"""
    return {"Authorization": f"Bearer {service_account_token}"}


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

@pytest.fixture(scope="session", autouse=True)
async def init_test_database():
    """初始化测试数据库表结构"""
    from services.common.database import get_engine
    from services.common.orm_models import Base, PermissionORM, RoleORM, RolePermissionORM
    from sqlalchemy import select, text

    # 使用全局引擎（指向测试数据库）
    engine = get_engine()

    # 创建所有表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 创建测试数据表
    async with engine.begin() as conn:
        # 创建 test_users 表
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS test_users (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT,
                status TEXT DEFAULT 'active'
            )
        """))

        # 创建 test_dataset 表
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS test_dataset (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                value REAL,
                created_at TEXT
            )
        """))

        # 创建 products 表
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                price REAL NOT NULL,
                category TEXT
            )
        """))

        # 创建 orders 表
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                total REAL NOT NULL,
                status TEXT DEFAULT 'pending'
            )
        """))

        # 创建 customers 表（用于敏感数据检测测试）
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                phone TEXT,
                email TEXT,
                id_card TEXT,
                address TEXT
            )
        """))

        # 创建 users_with_phone 表
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS users_with_phone (
                id INTEGER PRIMARY KEY,
                username TEXT,
                phone TEXT
            )
        """))

        # 创建 users_with_idcard 表
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS users_with_idcard (
                id INTEGER PRIMARY KEY,
                username TEXT,
                id_card TEXT
            )
        """))

        # 创建 users_with_email 表
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS users_with_email (
                id INTEGER PRIMARY KEY,
                username TEXT,
                email TEXT
            )
        """))

        # 创建 payment_info 表
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS payment_info (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                bank_card TEXT,
                amount REAL
            )
        """))

        # 创建 product_categories 表
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS product_categories (
                id INTEGER PRIMARY KEY,
                category_name TEXT,
                parent_id INTEGER
            )
        """))

        # 创建 clean_data 表（高质量数据）
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS clean_data (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                value REAL,
                status TEXT
            )
        """))

        # 创建 test_with_nulls 表（用于空值检测）
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS test_with_nulls (
                id INTEGER PRIMARY KEY,
                name TEXT,
                value REAL,
                email TEXT
            )
        """))

        # 创建 test_with_duplicates 表（用于重复检测）
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS test_with_duplicates (
                id INTEGER PRIMARY KEY,
                email TEXT,
                value REAL
            )
        """))

        # 创建 test_mixed_issues 表（混合问题）
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS test_mixed_issues (
                id INTEGER PRIMARY KEY,
                name TEXT,
                email TEXT,
                value REAL
            )
        """))

        # 插入测试数据
        await conn.execute(text("""
            INSERT OR REPLACE INTO test_users (id, name, email, status) VALUES
                (1, 'Alice', 'alice@example.com', 'active'),
                (2, 'Bob', 'bob@example.com', 'active'),
                (3, 'Charlie', 'charlie@example.com', 'inactive')
        """))

        await conn.execute(text("""
            INSERT OR REPLACE INTO test_dataset (id, title, value, created_at) VALUES
                (1, 'Item 1', 100.5, '2024-01-01'),
                (2, 'Item 2', 200.0, '2024-01-02'),
                (3, 'Item 3', 150.75, '2024-01-03')
        """))

        await conn.execute(text("""
            INSERT OR REPLACE INTO products (id, name, price, category) VALUES
                (1, 'Laptop', 999.99, 'Electronics'),
                (2, 'Mouse', 29.99, 'Electronics'),
                (3, 'Desk', 299.99, 'Furniture')
        """))

        await conn.execute(text("""
            INSERT OR REPLACE INTO orders (id, user_id, total, status) VALUES
                (1, 1, 1029.98, 'completed'),
                (2, 2, 29.99, 'pending'),
                (3, 1, 299.99, 'shipped')
        """))

        await conn.execute(text("""
            INSERT OR REPLACE INTO customers (id, name, phone, email, id_card, address) VALUES
                (1, '张三', '13800138000', 'zhang@example.com', '110101199001011234', '北京'),
                (2, '李四', '13900139000', 'li@example.com', '310101199002021234', '上海'),
                (3, '王五', '13700137000', 'wang@example.com', '440101199003031234', '广州')
        """))

        await conn.execute(text("""
            INSERT OR REPLACE INTO users_with_phone (id, username, phone) VALUES
                (1, 'user1', '13812345678'),
                (2, 'user2', '15987654321')
        """))

        await conn.execute(text("""
            INSERT OR REPLACE INTO users_with_idcard (id, username, id_card) VALUES
                (1, 'user1', '110101199001011234'),
                (2, 'user2', '310101199002021234')
        """))

        await conn.execute(text("""
            INSERT OR REPLACE INTO users_with_email (id, username, email) VALUES
                (1, 'user1', 'user1@example.com'),
                (2, 'user2', 'user2@example.com')
        """))

        await conn.execute(text("""
            INSERT OR REPLACE INTO payment_info (id, user_id, bank_card, amount) VALUES
                (1, 1, '6222021234567890123', 1000.00),
                (2, 2, '6228761234567890123', 500.00)
        """))

        await conn.execute(text("""
            INSERT OR REPLACE INTO product_categories (id, category_name, parent_id) VALUES
                (1, '电子产品', NULL),
                (2, '手机', 1),
                (3, '电脑', 1)
        """))

        await conn.execute(text("""
            INSERT OR REPLACE INTO clean_data (id, name, value, status) VALUES
                (1, 'Item1', 100.0, 'active'),
                (2, 'Item2', 200.0, 'active'),
                (3, 'Item3', 300.0, 'active')
        """))

        await conn.execute(text("""
            INSERT OR REPLACE INTO test_with_nulls (id, name, value, email) VALUES
                (1, 'Alice', 100.0, 'alice@example.com'),
                (2, NULL, 200.0, 'bob@example.com'),
                (3, 'Charlie', NULL, 'charlie@example.com'),
                (4, 'David', 300.0, NULL)
        """))

        await conn.execute(text("""
            INSERT OR REPLACE INTO test_with_duplicates (id, email, value) VALUES
                (1, 'duplicate@example.com', 100.0),
                (2, 'duplicate@example.com', 200.0),
                (3, 'unique@example.com', 300.0)
        """))

        await conn.execute(text("""
            INSERT OR REPLACE INTO test_mixed_issues (id, name, email, value) VALUES
                (1, 'Alice', 'alice@example.com', 100.0),
                (2, NULL, 'bob@example.com', 200.0),
                (3, 'Alice', NULL, 300.0)
        """))

    # 插入种子数据
    async with engine.begin() as conn:
        # 插入预定义权限
        from services.portal.routers.roles import PREDEFINED_PERMISSIONS
        for code, name in PREDEFINED_PERMISSIONS.items():
            result = await conn.execute(
                select(PermissionORM).where(PermissionORM.code == code)
            )
            if not result.first():
                # 确定权限分类
                category = code.split(":")[0] if ":" in code else "general"
                await conn.execute(
                    PermissionORM.__table__.insert().values(
                        code=code, name=name, category=category
                    )
                )

        # 插入预定义角色
        from services.portal.routers.roles import PREDEFINED_ROLES
        for role_code, role_info in PREDEFINED_ROLES.items():
            result = await conn.execute(
                select(RoleORM).where(RoleORM.role_code == role_code)
            )
            if not result.first():
                # 获取角色ID
                result = await conn.execute(
                    RoleORM.__table__.insert().values(
                        role_code=role_code,
                        role_name=role_info["name"],
                        description=role_info.get("description", ""),
                        is_system=True
                    )
                )
                role_id = result.inserted_primary_key[0]

                # 插入角色权限关联 (使用 permission_code 而非 permission_id)
                for perm_code in role_info.get("permissions", []):
                    await conn.execute(
                        RolePermissionORM.__table__.insert().values(
                            role_id=role_id,
                            permission_code=perm_code
                        )
                    )

    yield

    # 清理
    async with engine.begin() as conn:
        # 删除测试数据表
        await conn.execute(text("DROP TABLE IF EXISTS test_users"))
        await conn.execute(text("DROP TABLE IF EXISTS test_dataset"))
        await conn.execute(text("DROP TABLE IF EXISTS products"))
        await conn.execute(text("DROP TABLE IF EXISTS orders"))
        await conn.execute(text("DROP TABLE IF EXISTS customers"))
        await conn.execute(text("DROP TABLE IF EXISTS users_with_phone"))
        await conn.execute(text("DROP TABLE IF EXISTS users_with_idcard"))
        await conn.execute(text("DROP TABLE IF EXISTS users_with_email"))
        await conn.execute(text("DROP TABLE IF EXISTS payment_info"))
        await conn.execute(text("DROP TABLE IF EXISTS product_categories"))
        await conn.execute(text("DROP TABLE IF EXISTS clean_data"))
        await conn.execute(text("DROP TABLE IF EXISTS test_with_nulls"))
        await conn.execute(text("DROP TABLE IF EXISTS test_with_duplicates"))
        await conn.execute(text("DROP TABLE IF EXISTS test_mixed_issues"))
        # 删除 ORM 表
        await conn.run_sync(Base.metadata.drop_all)


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
