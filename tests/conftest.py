"""
共享测试配置和 Fixtures
提供各服务的 AsyncClient fixtures、认证 token 生成、Mock 配置等
"""

import os
import sys
from datetime import timedelta
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

# 设置环境变量（测试环境配置）
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-testing-only")
os.environ.setdefault("JWT_EXPIRE_HOURS", "24")
# 禁用速率限制（测试环境）
os.environ.setdefault("ENABLE_RATE_LIMIT", "false")
# 添加 CORS 测试源
os.environ.setdefault("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173,http://localhost:8080,http://127.0.0.1:3000,http://127.0.0.1:5173,http://example.com")
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
def steward_token() -> str:
    """生成数据治理员 token"""
    return create_token(user_id="stw1", username="steward", role="steward")


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


@pytest.fixture
def steward_headers(steward_token: str) -> dict:
    """返回带有数据治理员认证的请求头"""
    return {"Authorization": f"Bearer {steward_token}"}


@pytest.fixture
def engineer_headers(engineer_token: str) -> dict:
    """返回带有数据工程师认证的请求头"""
    return {"Authorization": f"Bearer {engineer_token}"}


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

    # 先删除所有表（确保干净状态）
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

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


# ============ Lifecycle Test Fixtures ============

@pytest.fixture
async def lifecycle_init_data(portal_client: AsyncClient, super_admin_headers: dict):
    """Complete initialization data for lifecycle tests

    Ensures all required entities exist before running lifecycle tests.
    """
    from services.common.seed_data import seed_all_data

    # Run seed data with business data included
    import asyncio
    await asyncio.create_task(seed_all_data(
        environment="development",
        skip_users=False,
        include_business=True
    ))

    yield {
        "users_initialized": True,
        "business_data_initialized": True
    }


@pytest.fixture
def business_domain_data() -> dict:
    """Sample business domain data for testing"""
    return {
        "departments": [
            {"id": 1, "name": "数据平台部", "code": "DP"},
            {"id": 2, "name": "数据分析部", "code": "DA"},
        ],
        "projects": [
            {"id": 1, "name": "用户画像平台", "code": "USER_PROFILE"},
            {"id": 2, "name": "实时数据仓库", "code": "RT_DW"},
        ],
        "datasets": [
            {"id": 1, "name": "用户基础信息表", "domain": "user", "format": "parquet"},
            {"id": 2, "name": "订单明细表", "domain": "ecommerce", "format": "parquet"},
        ],
        "pipelines": [
            {"id": 1, "name": "用户数据同步", "type": "sync", "source": "mysql", "target": "warehouse"},
            {"id": 2, "name": "订单数据清洗", "type": "cleaning", "source": "mysql", "target": "parquet"},
        ],
        "quality_rules": [
            {"id": 1, "name": "空值检测", "type": "null_check", "threshold": 0.0},
            {"id": 2, "name": "唯一性检测", "type": "unique_check", "threshold": 1.0},
        ],
    }


@pytest.fixture
def integration_data() -> dict:
    """External system integration test data"""
    return {
        "datahub": {
            "url": "http://localhost:8080",
            "username": "test_user",
            "datasets": [
                "urn:li:dataset:(urn:li:dataPlatform:mysql,test_db.users,PROD)",
                "urn:li:dataset:(urn:li:dataPlatform:mysql,test_db.orders,PROD)",
            ]
        },
        "seatunnel": {
            "url": "http://localhost:5801",
            "pipelines": [
                {"name": "sync_users", "source": "mysql", "target": "hive"},
                {"name": "sync_orders", "source": "mysql", "target": "hive"},
            ]
        },
        "superset": {
            "url": "http://localhost:8088",
            "dashboards": [
                {"id": 1, "name": "用户增长分析"},
                {"id": 2, "name": "销售业绩看板"},
            ]
        },
    }


# ============ Database Helper Fixtures ============

@pytest.fixture
async def db_session():
    """获取数据库会话用于直接数据库操作

    用于测试时直接操作数据库，绕过API层。
    """
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
    from services.common.database import get_database_url

    database_url = get_database_url()
    engine = create_async_engine(database_url, echo=False)
    async_session_maker = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session_maker() as session:
        yield session

    await engine.dispose()


@pytest.fixture
async def clean_test_data(db_session: AsyncSession):
    """清理测试数据的fixture

    在测试后自动清理创建的测试数据。
    使用方法:
        @pytest.mark.asyncio
        async def test_something(clean_test_data):
            # 创建测试数据
            # 测试逻辑
            # fixture会自动清理
    """
    from services.common.orm_models import UserORM, ServiceAccountORM

    # 记录测试前的数据
    user_result = await db_session.execute(select(UserORM))
    initial_users = {u.username for u in user_result.scalars().all()}

    sa_result = await db_session.execute(select(ServiceAccountORM))
    initial_sas = {sa.name for sa in sa_result.scalars().all()}

    yield

    # 清理测试期间创建的数据
    user_result = await db_session.execute(select(UserORM))
    for user in user_result.scalars().all():
        if user.username.startswith("test_") or user.username.startswith("e2e_"):
            if user.username not in initial_users:
                await db_session.delete(user)

    sa_result = await db_session.execute(select(ServiceAccountORM))
    for sa in sa_result.scalars().all():
        if sa.name.startswith("test_") or sa.name.startswith("e2e_"):
            if sa.name not in initial_sas:
                await db_session.delete(sa)

    await db_session.commit()


# ============ HTTP Response Helper Fixtures ============

@pytest.fixture
def assert_api_response():
    """API响应断言helper

    提供统一的API响应断言逻辑。
    """
    def _assert(response, expected_code=200, expect_data=True):
        """断言API响应

        Args:
            response: HTTPX响应对象
            expected_code: 期望的HTTP状态码
            expect_data: 是否期望返回数据
        """
        assert response.status_code == expected_code, f"Expected {expected_code}, got {response.status_code}: {response.text}"
        data = response.json()
        if expect_data:
            # ApiResponse格式: {code, message, data, timestamp}
            if "code" in data:
                assert data.get("code") == 20000, f"API error: {data.get('message')}"
                assert "data" in data or "timestamp" in data
        return data
    return _assert


@pytest.fixture
def extract_response_data():
    """从API响应中提取数据的helper"""
    def _extract(response):
        """提取响应数据

        处理两种响应格式:
        1. ApiResponse格式: {code, message, data, timestamp}
        2. 直接数据格式
        """
        data = response.json()
        if "data" in data and "code" in data:
            return data["data"]
        return data
    return _extract


# ============ Extended Test Data Fixtures ============

@pytest.fixture
def sample_dataset_schemas() -> list:
    """示例数据集Schema定义"""
    return [
        {
            "dataset_id": 1,
            "schema_name": "marketing",
            "column_name": "users",
            "columns": [
                {"name": "id", "type": "BIGINT", "nullable": False, "description": "用户ID"},
                {"name": "username", "type": "VARCHAR(50)", "nullable": False, "description": "用户名"},
                {"name": "email", "type": "VARCHAR(100)", "nullable": True, "description": "邮箱"},
                {"name": "phone", "type": "VARCHAR(20)", "nullable": True, "description": "手机号"},
                {"name": "created_at", "type": "TIMESTAMP", "nullable": False, "description": "创建时间"},
            ]
        },
        {
            "dataset_id": 2,
            "schema_name": "ecommerce",
            "column_name": "orders",
            "columns": [
                {"name": "id", "type": "BIGINT", "nullable": False, "description": "订单ID"},
                {"name": "user_id", "type": "BIGINT", "nullable": False, "description": "用户ID"},
                {"name": "total_amount", "type": "DECIMAL(10,2)", "nullable": False, "description": "订单金额"},
                {"name": "status", "type": "VARCHAR(20)", "nullable": False, "description": "订单状态"},
                {"name": "created_at", "type": "TIMESTAMP", "nullable": False, "description": "创建时间"},
            ]
        },
    ]


@pytest.fixture
def sample_pipeline_configs() -> list:
    """示例数据管道配置"""
    return [
        {
            "name": "用户数据同步",
            "type": "sync",
            "source": {"type": "mysql", "host": "localhost", "port": 3306, "database": "marketing", "table": "users"},
            "target": {"type": "parquet", "path": "/data/warehouse/users"},
            "schedule": "0 2 * * *",
            "transformations": [
                {"type": "rename", "from": "user_name", "to": "username"},
                {"type": "mask", "column": "phone", "algorithm": "MASK_FIRST_LAST"},
            ]
        },
        {
            "name": "订单数据清洗",
            "type": "cleaning",
            "source": {"type": "mysql", "host": "localhost", "port": 3306, "database": "ecommerce", "table": "orders"},
            "target": {"type": "parquet", "path": "/data/warehouse/orders_clean"},
            "schedule": "0 3 * * *",
            "rules": [
                {"type": "filter", "condition": "total_amount >= 0"},
                {"type": "deduplicate", "keys": ["id"]},
            ]
        },
    ]


@pytest.fixture
def sample_quality_checks() -> list:
    """示例数据质量检查规则"""
    return [
        {
            "rule_id": "qc_001",
            "name": "用户ID非空检查",
            "dataset": "users",
            "column": "id",
            "rule_type": "null_check",
            "threshold": 0.0,
            "severity": "error",
        },
        {
            "rule_id": "qc_002",
            "name": "邮箱格式检查",
            "dataset": "users",
            "column": "email",
            "rule_type": "format_check",
            "threshold": 0.95,
            "severity": "warning",
        },
        {
            "rule_id": "qc_003",
            "name": "订单金额范围检查",
            "dataset": "orders",
            "column": "total_amount",
            "rule_type": "range_check",
            "threshold": 0.0,
            "severity": "error",
        },
    ]


@pytest.fixture
def sample_metadata_entities() -> list:
    """示例元数据实体（DataHub格式）"""
    return [
        {
            "urn": "urn:li:dataset:(urn:li:dataPlatform:mysql,marketing.users,PROD)",
            "type": "dataset",
            "name": "users",
            "description": "用户基础信息表",
            "platform": "mysql",
            "schema": "marketing",
        },
        {
            "urn": "urn:li:dataset:(urn:li:dataPlatform:mysql,ecommerce.orders,PROD)",
            "type": "dataset",
            "name": "orders",
            "description": "订单明细表",
            "platform": "mysql",
            "schema": "ecommerce",
        },
        {
            "urn": "urn:li:dataJob:(urn:li:dataFlow:(airflow,daily_sync,PROD),daily_user_sync)",
            "type": "dataJob",
            "name": "daily_user_sync",
            "description": "每日用户数据同步任务",
        },
    ]


@pytest.fixture
def sample_dashboard_configs() -> dict:
    """示例仪表板配置（Superset格式）"""
    return {
        "user_growth": {
            "name": "用户增长分析",
            "charts": [
                {"id": "ch_1", "name": "DAU趋势", "type": "line", "datasource": "user_events"},
                {"id": "ch_2", "name": "新增用户", "type": "bar", "datasource": "users"},
                {"id": "ch_3", "name": "留存漏斗", "type": "funnel", "datasource": "user_events"},
            ],
            "filters": {"time_range": "last_30_days"},
        },
        "sales_performance": {
            "name": "销售业绩看板",
            "charts": [
                {"id": "ch_4", "name": "GMV趋势", "type": "line", "datasource": "orders"},
                {"id": "ch_5", "name": "品类占比", "type": "pie", "datasource": "order_items"},
            ],
            "filters": {"time_range": "last_7_days"},
        },
    }


@pytest.fixture
def mock_external_services_data() -> dict:
    """Mock外部服务返回的示例数据"""
    return {
        "datahub": {
            "datasets": [
                {"urn": "urn:li:dataset:(mysql,users,PROD)", "name": "users", "platform": "mysql"},
                {"urn": "urn:li:dataset:(mysql,orders,PROD)", "name": "orders", "platform": "mysql"},
            ],
            "health": {"status": "healthy", "version": "0.10.0"},
        },
        "seatunnel": {
            "pipelines": [
                {"id": "sync_users", "status": "running", "last_run": "2024-01-10T02:00:00Z"},
                {"id": "sync_orders", "status": "success", "last_run": "2024-01-10T03:00:00Z"},
            ],
            "health": {"status": "healthy", "version": "2.3.0"},
        },
        "superset": {
            "dashboards": [
                {"id": 1, "name": "用户增长分析", "url": "/dashboard/1"},
                {"id": 2, "name": "销售业绩看板", "url": "/dashboard/2"},
            ],
            "health": {"status": "healthy", "version": "3.0.0"},
        },
    }


# ============ Test Environment Helper Fixtures ============

@pytest.fixture
def test_timestamp():
    """生成测试用时间戳"""
    from datetime import datetime
    return datetime(2024, 1, 1, 12, 0, 0)


@pytest.fixture
def test_user_prefix():
    """生成测试用户名前缀（避免冲突）"""
    import time
    return f"test_{int(time.time())}"


@pytest.fixture
def unique_test_data():
    """生成唯一测试数据"""
    import time
    import uuid
    return {
        "timestamp": int(time.time()),
        "uuid": str(uuid.uuid4()),
        "prefix": f"test_{int(time.time())}",
    }
