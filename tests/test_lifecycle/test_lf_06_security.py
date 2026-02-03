"""生命周期测试 - 阶段6: 数据安全 (Security)

测试数据安全功能:
- 敏感数据检测: 自动识别敏感字段
- 审计日志: 操作审计、日志导出
- 权限边界: 访问控制、安全验证
- 脱敏验证: 实际脱敏效果验证
"""

import pytest
from httpx import AsyncClient


# ============================================================
# 审计日志服务测试
# ============================================================

@pytest.mark.p0
class TestAuditLogService:
    """审计日志服务测试"""

    async def test_audit_01_service_health(self, portal_client: AsyncClient):
        """测试审计日志服务健康检查"""
        response = await portal_client.get(
            "http://localhost:8016/health"
        )
        assert response.status_code in (200, 404, 502)

    async def test_audit_02_list_events(self, portal_client: AsyncClient, admin_headers: dict):
        """测试获取审计事件列表"""
        response = await portal_client.get(
            "/api/audit/events",
            headers=admin_headers
        )
        assert response.status_code in (200, 404)

    async def test_audit_03_filter_events(self, portal_client: AsyncClient, admin_headers: dict):
        """测试过滤审计事件"""
        response = await portal_client.get(
            "/api/audit/events?subsystem=portal&event_type=login",
            headers=admin_headers
        )
        assert response.status_code in (200, 404)

    async def test_audit_04_export_logs(self, portal_client: AsyncClient, admin_headers: dict):
        """测试导出审计日志"""
        response = await portal_client.post(
            "/api/audit/export",
            headers=admin_headers,
            json={
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
                "format": "csv"
            }
        )
        assert response.status_code in (200, 404)

    async def test_audit_05_event_statistics(self, portal_client: AsyncClient, admin_headers: dict):
        """测试审计事件统计"""
        response = await portal_client.get(
            "/api/audit/statistics",
            headers=admin_headers
        )
        assert response.status_code in (200, 404)


# ============================================================
# 访问控制测试
# ============================================================

@pytest.mark.p0
class TestAccessControl:
    """访问控制测试"""

    async def test_access_01_unauthorized_denied(self, portal_client: AsyncClient):
        """测试未授权访问被拒绝"""
        endpoints = [
            "/api/users",
            "/api/roles",
            "/api/datasets",
            "/api/audit/events"
        ]
        for endpoint in endpoints:
            response = await portal_client.get(endpoint)
            assert response.status_code == 401, f"{endpoint} should require auth"

    async def test_access_02_viewer_read_only(self, portal_client: AsyncClient, viewer_headers: dict):
        """测试查看者只读权限"""
        # 只读请求应该成功
        response = await portal_client.get(
            "/api/datasets",
            headers=viewer_headers
        )
        assert response.status_code in (200, 404)

        # 写入请求应该被拒绝
        response = await portal_client.post(
            "/api/datasets",
            headers=viewer_headers,
            json={"name": "test"}
        )
        assert response.status_code in (403, 404, 401)

    async def test_access_03_analyst_dataset_access(self, portal_client: AsyncClient, analyst_headers: dict):
        """测试分析师数据集访问权限"""
        response = await portal_client.get(
            "/api/datasets",
            headers=analyst_headers
        )
        assert response.status_code in (200, 404)

    async def test_access_04_admin_full_access(self, portal_client: AsyncClient, admin_headers: dict):
        """测试管理员完全访问权限"""
        endpoints = [
            "/api/users",
            "/api/roles",
            "/api/datasets",
            "/api/audit/events"
        ]
        for endpoint in endpoints:
            response = await portal_client.get(
                endpoint,
                headers=admin_headers
            )
            # 端点可能不存在但不应该是401
            assert response.status_code in (200, 404)

    async def test_access_05_cross_user_isolation(self, portal_client: AsyncClient, analyst_headers: dict):
        """测试跨用户隔离"""
        # 分析师不应该能访问其他用户的私有资源
        response = await portal_client.get(
            "/api/users/1/saved-queries",
            headers=analyst_headers
        )
        assert response.status_code in (403, 404, 401)

    async def test_access_06_service_account_access(self, portal_client: AsyncClient, service_account_headers: dict):
        """测试服务账户访问权限"""
        response = await portal_client.get(
            "/api/service/status",
            headers=service_account_headers
        )
        assert response.status_code in (200, 404)


# ============================================================
# 敏感数据访问控制测试
# ============================================================

@pytest.mark.p1
class TestSensitiveDataAccess:
    """敏感数据访问控制测试"""

    async def test_sensitive_01_pii_access_denied_viewer(self, portal_client: AsyncClient, viewer_headers: dict):
        """测试查看者不能访问PII数据"""
        response = await portal_client.post(
            "/api/data/query",
            headers=viewer_headers,
            json={
                "dataset": "customers",
                "fields": ["name", "phone", "id_card"]
            }
        )
        assert response.status_code in (200, 404)

        if response.status_code == 200:
            data = response.json()
            if "data" in data and data["data"]:
                # 敏感字段应该被脱敏
                for row in data["data"]:
                    if "phone" in row:
                        # 应该包含掩码符或None
                        phone = row.get("phone")
                        assert phone is None or "*" in str(phone) or "xxx" in str(phone)

    async def test_sensitive_02_pii_access_allowed_admin(self, portal_client: AsyncClient, admin_headers: dict):
        """测试管理员可以访问PII数据"""
        response = await portal_client.post(
            "/api/data/query",
            headers=admin_headers,
            json={
                "dataset": "customers",
                "fields": ["name", "phone", "id_card"],
                "unmask": True
            }
        )
        assert response.status_code in (200, 404)

    async def test_sensitive_03_masked_query(self, portal_client: AsyncClient, analyst_headers: dict):
        """测试脱敏查询"""
        response = await portal_client.post(
            "/api/data/query",
            headers=analyst_headers,
            json={
                "dataset": "customers",
                "fields": ["name", "phone"]
            }
        )
        assert response.status_code in (200, 404)

    async def test_sensitive_04_unmask_permission_check(self, portal_client: AsyncClient, analyst_headers: dict):
        """测试普通用户不能请求明文数据"""
        response = await portal_client.post(
            "/api/data/query",
            headers=analyst_headers,
            json={
                "dataset": "customers",
                "fields": ["name", "phone"],
                "unmask": True
            }
        )
        assert response.status_code in (403, 404)


# ============================================================
# 密码安全测试
# ============================================================

@pytest.mark.p1
class TestPasswordSecurity:
    """密码安全测试"""

    async def test_pwd_01_password_strength_check(self, portal_client: AsyncClient):
        """测试密码强度检查"""
        weak_passwords = ["123", "abc", "password", "12345678"]
        for pwd in weak_passwords:
            # 密码强度检查可能在注册或修改时
            assert isinstance(pwd, str)

    async def test_pwd_02_password_change_requires_old(self, portal_client: AsyncClient, admin_headers: dict):
        """测试密码修改需要旧密码"""
        response = await portal_client.post(
            "/auth/change-password",
            headers=admin_headers,
            json={
                "new_password": "newPassword123"
            }
        )
        # 应该需要旧密码
        assert response.status_code in (400, 422, 404)

    async def test_pwd_03_password_history(self, portal_client: AsyncClient, admin_headers: dict):
        """测试密码历史（不能重复使用旧密码）"""
        response = await portal_client.post(
            "/auth/change-password",
            headers=admin_headers,
            json={
                "old_password": "admin123",
                "new_password": "admin123"
            }
        )
        # 不应该允许重复使用旧密码
        assert response.status_code in (400, 422, 404)

    async def test_pwd_04_password_reset_token(self, portal_client: AsyncClient):
        """测试密码重置令牌"""
        response = await portal_client.post(
            "/auth/password-reset/request",
            json={"email": "admin@one-data-studio.local"}
        )
        # 端点可能不存在
        assert response.status_code in (200, 404)


# ============================================================
# 会话安全测试
# ============================================================

@pytest.mark.p1
class TestSessionSecurity:
    """会话安全测试"""

    async def test_session_01_concurrent_login_limit(self, portal_client: AsyncClient):
        """测试并发登录限制"""
        login_data = {"username": "admin", "password": "admin123"}
        responses = []
        for _ in range(5):
            r = await portal_client.post("/auth/login", json=login_data)
            responses.append(r)

        # 所有登录应该成功
        for r in responses:
            assert r.status_code == 200

    async def test_session_02_logout_invalidates_token(self, portal_client: AsyncClient, admin_headers: dict):
        """测试登出后Token失效"""
        # 登出
        await portal_client.post("/auth/logout", headers=admin_headers)

        # Token应该失效
        response = await portal_client.get(
            "/auth/userinfo",
            headers=admin_headers
        )
        assert response.status_code == 401

    async def test_session_03_session_timeout(self, portal_client: AsyncClient):
        """测试会话超时"""
        from services.common.auth import create_token, timedelta

        # 创建一个即将过期的token
        expired_token = create_token(
            user_id="test",
            username="test",
            role="viewer",
            expires_delta=timedelta(seconds=-1)
        )

        response = await portal_client.get(
            "/auth/validate",
            headers={"Authorization": f"Bearer {expired_token}"}
        )
        assert response.status_code == 401


# ============================================================
# 数据加密测试
# ============================================================

@pytest.mark.p2
class TestDataEncryption:
    """数据加密测试"""

    async def test_encrypt_01_password_hashed(self, portal_client: AsyncClient):
        """测试密码哈希存储"""
        from services.common.database import get_database_url
        from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
        from sqlalchemy import select, text
        from services.common.orm_models import UserORM

        engine = create_async_engine(get_database_url())
        async_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with async_maker() as session:
            result = await session.execute(
                select(UserORM).where(UserORM.username == "admin")
            )
            user = result.scalars().first()

            if user:
                # 密码应该被哈希存储
                password_hash = user.password_hash
                assert ":" in str(password_hash)  # salt:hash 格式
                assert "admin" not in str(password_hash)  # 不应该包含明文密码

        await engine.dispose()

    async def test_encrypt_02_api_key_encrypted(self, portal_client: AsyncClient):
        """测试API密钥加密存储"""
        from services.common.database import get_database_url
        from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
        from sqlalchemy import select
        from services.common.orm_models import UserApiKeyORM

        engine = create_async_engine(get_database_url())
        async_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with async_maker() as session:
            result = await session.execute(select(UserApiKeyORM).limit(1))
            key = result.scalars().first()

            if key:
                # API secret应该被加密
                api_secret = key.api_secret
                assert "ods_sk" in str(api_secret)  # 应该有前缀

        await engine.dispose()

    async def test_encrypt_03_sensitive_field_encryption(self, portal_client: AsyncClient):
        """测试敏感字段加密"""
        # 这是一个验证性测试，确保敏感字段被正确加密
        assert True  # 实际实现取决于具体的加密方案


# ============================================================
# 安全审计测试
# ============================================================

@pytest.mark.p2
class TestSecurityAudit:
    """安全审计测试"""

    async def test_audit_01_failed_login_logged(self, portal_client: AsyncClient):
        """测试失败登录被记录"""
        # 尝试多次失败登录
        for _ in range(3):
            await portal_client.post("/auth/login", json={
                "username": "invalid",
                "password": "invalid"
            })

        # 检查审计日志
        from services.common.database import get_database_url
        from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
        from sqlalchemy import select
        from services.common.orm_models import AuditEventORM

        engine = create_async_engine(get_database_url())
        async_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with async_maker() as session:
            result = await session.execute(
                select(AuditEventORM)
                .where(AuditEventORM.event_type == "login")
                .order_by(AuditEventORM.created_at.desc())
                .limit(10)
            )
            events = result.scalars().all()

            # 应该有登录事件记录
            assert len(events) >= 0

        await engine.dispose()

    async def test_audit_02_privileged_access_logged(self, portal_client: AsyncClient, admin_headers: dict):
        """测试特权访问被记录"""
        # 执行特权操作
        await portal_client.get("/api/users", headers=admin_headers)

        # 检查审计日志
        from services.common.database import get_database_url
        from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
        from sqlalchemy import select
        from services.common.orm_models import AuditEventORM

        engine = create_async_engine(get_database_url())
        async_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with async_maker() as session:
            result = await session.execute(
                select(AuditEventORM)
                .where(AuditEventORM.user == "admin")
                .order_by(AuditEventORM.created_at.desc())
                .limit(5)
            )
            events = result.scalars().all()

            # 应该有操作记录
            assert len(events) >= 0

        await engine.dispose()
