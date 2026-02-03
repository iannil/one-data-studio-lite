"""统一入口门户 - FastAPI 应用"""

import hashlib
import logging
import os
import secrets
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from services.common.auth import TokenPayload, create_token, get_current_user, refresh_token
from services.common.database import get_db
from services.common.exceptions import register_exception_handlers
from services.common.metrics import setup_metrics
from services.common.middleware import RequestLoggingMiddleware
from services.common.orm_models import UserORM
from services.portal.config import _get_dev_users, init_config_center, settings
from services.portal.models import (
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    PasswordResetCodeRequest,
    PasswordResetConfirmRequest,
    PasswordResetVerifyRequest,
    PortalInfo,
    RefreshTokenResponse,
    RegisterRequest,
    SubsystemStatus,
    UserInfo,
)
from services.portal.routers import (
    audit,
    cleaning,
    cubestudio,
    data_api,
    datahub,
    dolphinscheduler,
    hop,
    metadata_sync,
    nl2sql,
    roles,  # 新增
    seatunnel,
    sensitive,
    service_accounts,  # 新增
    shardingsphere,
    superset,
    users,  # 新增
)
from services.portal.routers import (
    system as system_router,  # 新增
)

logger = logging.getLogger(__name__)


def check_security_configuration():
    """检查安全相关配置，输出警告信息

    生产环境下安全问题会抛出异常阻止启动。
    """
    try:
        warnings = settings.validate_security()
    except ValueError as e:
        logger.error(f"安全配置错误: {e}")
        raise

    if warnings:
        logger.warning("=" * 60)
        logger.warning("安全配置警告 - Security Configuration Warnings")
        logger.warning("=" * 60)
        for i, warning in enumerate(warnings, 1):
            logger.warning(f"[{i}] {warning}")
        logger.warning("=" * 60)

    return warnings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时检查配置
    check_security_configuration()

    # 初始化配置中心（非阻塞）
    try:
        await init_config_center()
    except Exception as e:
        logger.warning(f"配置中心初始化失败（已忽略）: {e}")

    yield

    # 关闭时清理配置中心
    if settings.ENABLE_CONFIG_CENTER:
        try:
            from services.common.config_center import get_config_center
            cc = get_config_center()
            await cc.close()
        except Exception:
            pass


app = FastAPI(
    title=settings.APP_NAME,
    description="""ONE-DATA-STUDIO-LITE 统一入口门户

    ## 功能特性

    - **统一认证**: JWT Token 认证，支持 Token 刷新
    - **API 代理**: 代理各个子系统的 REST API，统一认证
    - **配置中心**: 集成 etcd 配置中心，支持热更新
    - **审计日志**: 自动记录用户操作日志

    ## 子系统

    - Cube-Studio (AI 平台)
    - Apache Superset (BI 分析)
    - DataHub (元数据管理)
    - DolphinScheduler (任务调度)
    - Apache Hop (ETL 引擎)
    - SeaTunnel (数据同步)
    - ShardingSphere (数据脱敏)

    ## 内部服务

    - NL2SQL (自然语言查询)
    - AI Cleaning (AI 清洗规则推荐)
    - Metadata Sync (元数据同步)
    - Data API (数据资产 API 网关)
    - Sensitive Detect (敏感数据检测)
    - Audit Log (审计日志)
    """,
    version="0.2.0",
    lifespan=lifespan,
    # OpenAPI 配置
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {
            "name": "auth",
            "description": "认证相关接口"
        },
        {
            "name": "SeaTunnel",
            "description": "SeaTunnel 数据同步 API"
        },
        {
            "name": "ShardingSphere",
            "description": "ShardingSphere 数据脱敏 API"
        },
        {
            "name": "Hop",
            "description": "Apache Hop ETL API"
        },
        {
            "name": "DataHub",
            "description": "DataHub 元数据管理 API"
        },
        {
            "name": "DolphinScheduler",
            "description": "DolphinScheduler 任务调度 API"
        },
        {
            "name": "Superset",
            "description": "Superset BI 分析 API"
        },
        {
            "name": "NL2SQL",
            "description": "自然语言转 SQL API"
        },
        {
            "name": "AI Cleaning",
            "description": "AI 清洗规则推荐 API"
        },
        {
            "name": "Metadata Sync",
            "description": "元数据同步 API"
        },
        {
            "name": "Data API",
            "description": "数据资产 API 网关"
        },
        {
            "name": "Sensitive Detect",
            "description": "敏感数据检测 API"
        },
        {
            "name": "Audit Log",
            "description": "审计日志 API"
        },
    ],
    # 安全方案定义
    openapi_security_schemes={
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT Token 认证。使用 `/auth/login` 获取 Token，并在请求头中添加 `Authorization: Bearer <token>`",
        },
    },
    # 响应文档示例
    openapi_examples={
        "ApiResponse": {
            "code": 20000,
            "message": "success",
            "data": {"id": 1, "name": "example"},
            "timestamp": 1706659200,
        },
        "ErrorResponse": {
            "code": 40001,
            "message": "参数错误",
            "data": None,
            "timestamp": 1706659200,
        },
    },
)

# 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,  # 使用配置的允许来源
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
)

# 添加安全响应头中间件
from services.common.security import RateLimitMiddleware, SecurityHeadersMiddleware

app.add_middleware(SecurityHeadersMiddleware)

# 添加速率限制中间件
app.add_middleware(RateLimitMiddleware, enabled=os.getenv("ENABLE_RATE_LIMIT", "true").lower() == "true")
app.add_middleware(RequestLoggingMiddleware, service_name="portal")
register_exception_handlers(app)
setup_metrics(app)

# 注册代理路由
app.include_router(cubestudio.router)
app.include_router(datahub.router)
app.include_router(superset.router)
app.include_router(dolphinscheduler.router)
app.include_router(seatunnel.router)
app.include_router(hop.router)
app.include_router(shardingsphere.router)
app.include_router(nl2sql.router)
app.include_router(cleaning.router)
app.include_router(metadata_sync.router)
app.include_router(data_api.router)
app.include_router(sensitive.router)
app.include_router(audit.router)

# 新增管理路由
app.include_router(users.router)
app.include_router(roles.router)
app.include_router(service_accounts.router)
app.include_router(system_router.router)

# 子系统配置
SUBSYSTEMS = [
    {"name": "cube-studio", "display_name": "Cube-Studio (AI平台)", "url": settings.CUBE_STUDIO_URL, "health_path": "/health"},
    {"name": "superset", "display_name": "Apache Superset (BI分析)", "url": settings.SUPERSET_URL, "health_path": "/health"},
    {"name": "datahub", "display_name": "DataHub (元数据管理)", "url": settings.DATAHUB_URL, "health_path": "/"},
    {"name": "dolphinscheduler", "display_name": "DolphinScheduler (任务调度)", "url": settings.DOLPHINSCHEDULER_URL, "health_path": "/dolphinscheduler/actuator/health"},
    {"name": "hop", "display_name": "Apache Hop (ETL引擎)", "url": settings.HOP_URL, "health_path": "/"},
]


# ============================================================
# 密码处理辅助函数
# ============================================================

def _hash_password(password: str) -> str:
    """对密码进行哈希处理（与 users.py 保持一致）"""
    salt = secrets.token_hex(16)
    pwd_hash = hashlib.sha256(f"{password}{salt}".encode()).hexdigest()
    return f"{salt}:{pwd_hash}"


def _verify_password(password: str, password_hash: str) -> bool:
    """验证密码（与 users.py 保持一致）"""
    try:
        salt, pwd_hash = password_hash.split(":")
        computed_hash = hashlib.sha256(f"{password}{salt}".encode()).hexdigest()
        return computed_hash == pwd_hash
    except ValueError:
        return False


async def _get_user_from_db(db: AsyncSession, username: str) -> UserORM | None:
    """从数据库获取用户"""
    result = await db.execute(select(UserORM).where(UserORM.username == username))
    return result.scalars().first()


# ============================================================
# 认证端点
# ============================================================

@app.post("/auth/login", response_model=LoginResponse)
async def login(
    req: LoginRequest,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
):
    """统一登录

    支持数据库用户和开发环境硬编码用户（向后兼容）。
    优先查询数据库，如果数据库中没有用户则回退到 DEV_USERS。
    """
    # 尝试从数据库获取用户
    user_orm = None
    user_role = None
    display_name = None

    if db is not None:
        user_orm = await _get_user_from_db(db, req.username)

    if user_orm:
        # 数据库用户
        if not user_orm.is_active:
            raise HTTPException(status_code=403, detail="用户已被禁用")

        if user_orm.is_locked:
            raise HTTPException(status_code=403, detail="用户已被锁定")

        # 验证密码
        if not _verify_password(req.password, user_orm.password_hash):
            # 更新失败尝试次数
            await db.execute(
                update(UserORM)
                .where(UserORM.username == req.username)
                .values(failed_login_attempts=UserORM.failed_login_attempts + 1)
            )
            await db.commit()
            raise HTTPException(status_code=401, detail="用户名或密码错误")

        # 登录成功，更新登录信息
        client_ip = response.headers.get("X-Forwarded-For", "unknown")
        if response.headers.get("X-Real-IP"):
            client_ip = response.headers.get("X-Real-IP")

        await db.execute(
            update(UserORM)
            .where(UserORM.username == req.username)
            .values(
                last_login_at=datetime.utcnow(),
                last_login_ip=client_ip,
                failed_login_attempts=0,
            )
        )
        await db.commit()

        user_role = user_orm.role_code
        display_name = user_orm.display_name

    else:
        # 回退到开发环境硬编码用户
        user = settings.DEV_USERS.get(req.username)
        if not user or user["password"] != req.password:
            raise HTTPException(status_code=401, detail="用户名或密码错误")

        user_role = user["role"]
        display_name = user["display_name"]

    token = create_token(
        user_id=req.username,
        username=req.username,
        role=user_role,
    )

    # 设置 httpOnly Cookie 存储 Token（更安全，防止 XSS 窃取）
    if settings.USE_COOKIE_AUTH:
        response.set_cookie(
            key=settings.COOKIE_NAME,
            value=token,
            httponly=True,  # 关键：防止 JavaScript 访问
            secure=settings.COOKIE_SECURE,  # 生产环境必须启用（仅 HTTPS）
            samesite=settings.COOKIE_SAMESITE,
            max_age=settings.COOKIE_MAX_AGE,
            domain=settings.COOKIE_DOMAIN,
            path="/",
        )

    login_response = LoginResponse(
        success=True,
        token=token,  # 保留 token 字段以兼容旧客户端
        user=UserInfo(
            user_id=req.username,
            username=req.username,
            role=user_role,
            display_name=display_name,
        ),
        message="登录成功",
    )
    return login_response


@app.post("/auth/logout")
async def logout(response: Response):
    """登出 - 清除 httpOnly Cookie"""
    # 清除 httpOnly Cookie
    if settings.USE_COOKIE_AUTH:
        response.delete_cookie(
            key=settings.COOKIE_NAME,
            path="/",
            domain=settings.COOKIE_DOMAIN,
        )
    return {"success": True, "message": "已登出"}


@app.post("/auth/refresh", response_model=RefreshTokenResponse)
async def refresh_user_token(request: Request):
    """刷新Token - 在Token过期前或过期后30分钟内可刷新"""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未提供认证信息")

    old_token = auth_header.split(" ", 1)[1]
    new_token = refresh_token(old_token)

    if not new_token:
        raise HTTPException(status_code=401, detail="Token已失效，请重新登录")

    return RefreshTokenResponse(
        success=True,
        token=new_token,
        message="Token刷新成功",
    )


@app.get("/auth/validate")
async def validate_token(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
):
    """验证 Token 有效性

    供子系统验证 Portal 颁发的 Token。
    支持数据库用户和开发环境硬编码用户。

    请求头:
        Authorization: Bearer <token>

    返回:
        {
            "valid": true,
            "user_id": "admin",
            "username": "admin",
            "roles": ["admin"],
            "permissions": ["data:read", "data:write"],
            "expires_at": 1706739200
        }
    """
    from services.common.auth import verify_token

    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return {
            "valid": False,
            "code": 40100,
            "message": "Token 缺失"
        }

    token = auth_header.split(" ", 1)[1]

    try:
        payload = verify_token(token)

        # 尝试从数据库获取用户
        role = "user"
        display_name = payload.username
        user_exists = False

        if db is not None:
            user_orm = await _get_user_from_db(db, payload.username)
            if user_orm:
                if not user_orm.is_active:
                    return {
                        "valid": False,
                        "code": 40302,
                        "message": "用户已被禁用"
                    }
                role = user_orm.role_code
                display_name = user_orm.display_name
                user_exists = True

        # 回退到 DEV_USERS
        if not user_exists:
            user_config = settings.DEV_USERS.get(payload.username, {})
            if not user_config:
                return {
                    "valid": False,
                    "code": 40402,
                    "message": "用户不存在"
                }
            role = user_config.get("role", "user")
            display_name = user_config.get("display_name", payload.username)

        permissions = _get_permissions_for_role(role)

        return {
            "valid": True,
            "user_id": payload.user_id,
            "username": payload.username,
            "display_name": display_name,
            "roles": [role],
            "permissions": permissions,
            "expires_at": payload.exp,
            "issued_at": payload.iat,  # Unix 时间戳
        }

    except ValueError as e:
        return {
            "valid": False,
            "code": 40102,
            "message": str(e)
        }


@app.get("/auth/userinfo")
async def get_user_info(
    user: TokenPayload = Depends(get_current_user),
    db: Annotated[AsyncSession, Depends(get_db)] = None,
):
    """获取当前登录用户信息

    支持数据库用户和开发环境硬编码用户。
    """
    display_name = user.username
    email = None
    phone = None

    # 尝试从数据库获取用户详细信息
    if db is not None:
        user_orm = await _get_user_from_db(db, user.user_id)
        if user_orm:
            display_name = user_orm.display_name
            email = user_orm.email
            phone = user_orm.phone
        else:
            # 回退到开发环境用户
            user_config = settings.DEV_USERS.get(user.user_id, {})
            display_name = user_config.get("display_name", user.username)
            email = user_config.get("email")
            phone = user_config.get("phone")

    roles = [user.role]
    permissions = _get_permissions_for_role(user.role)

    return {
        "user_id": user.user_id,
        "username": user.username,
        "display_name": display_name,
        "email": email,
        "phone": phone,
        "role": user.role,
        "roles": roles,
        "permissions": permissions,
    }


def _get_permissions_for_role(role: str) -> list[str]:
    """根据角色获取权限列表"""
    # 管理员拥有所有权限
    admin_permissions = [
        "data:read", "data:write", "data:delete",
        "pipeline:read", "pipeline:run", "pipeline:manage",
        "system:admin", "system:user:manage", "system:config",
        "metadata:read", "metadata:write",
        "sensitive:read", "sensitive:manage",
        "audit:read",
    ]

    role_permissions = {
        "super_admin": admin_permissions + ["system:super_admin"],
        "admin": admin_permissions,
        "data_scientist": [
            "data:read", "data:write",
            "pipeline:read", "pipeline:run",
            "metadata:read", "metadata:write",
            "sensitive:read",
        ],
        "analyst": [
            "data:read",
            "pipeline:read",
            "metadata:read",
        ],
        "viewer": [
            "data:read",
            "pipeline:read",
        ],
        "service_account": [
            "service:call",
            "data:read",
        ],
        "engineer": [
            "data:read", "data:write",
            "pipeline:read", "pipeline:run", "pipeline:manage",
            "metadata:read", "metadata:write",
        ],
        "steward": [
            "data:read",
            "metadata:read", "metadata:write",
            "quality:read", "quality:manage",
        ],
        "user": [
            "data:read",
        ],
    }

    return role_permissions.get(role, [])


@app.post("/auth/revoke")
async def revoke_token(request: Request, current_user: TokenPayload = Depends(get_current_user)):
    """撤销 Token（强制登出）

    将当前 Token 加入黑名单，使其立即失效。
    需要 Redis 服务支持（通过 REDIS_URL 配置）。
    """
    from services.common.token_blacklist import get_blacklist

    # 获取当前 Token
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="无效的认证头")

    token = auth_header[7:]  # 移除 "Bearer " 前缀

    blacklist = get_blacklist()
    if not blacklist.is_available():
        raise HTTPException(
            status_code=503,
            detail="黑名单服务不可用，请联系管理员"
        )

    # 撤销当前 Token
    success = blacklist.revoke(token)

    if success:
        return {"success": True, "message": "Token 已撤销"}
    else:
        raise HTTPException(status_code=500, detail="撤销 Token 失败")


@app.post("/auth/revoke-user/{user_id}")
async def revoke_user_tokens(
    user_id: str,
    request: Request,
    current_user: TokenPayload = Depends(get_current_user)
):
    """撤销指定用户的所有 Token

    仅管理员可调用，用于权限变更后强制用户重新登录。
    """
    # 权限检查
    if current_user.role not in ("admin", "super_admin"):
        raise HTTPException(status_code=403, detail="权限不足")

    from services.common.token_blacklist import get_blacklist

    blacklist = get_blacklist()
    if not blacklist.is_available():
        raise HTTPException(
            status_code=503,
            detail="黑名单服务不可用"
        )

    # 获取当前 Token（排除当前登录用户的 Token）
    auth_header = request.headers.get("Authorization", "")
    except_token = None
    if auth_header.startswith("Bearer "):
        except_token = auth_header[7:]

    count = blacklist.revoke_user_tokens(user_id, except_token=except_token)

    return {
        "success": True,
        "message": f"用户 {user_id} 的所有 Token 已撤销",
        "count": count
    }


@app.post("/auth/register", response_model=LoginResponse, status_code=201)
async def register(
    req: RegisterRequest,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
):
    """用户注册

    创建新用户并自动登录。支持数据库存储，如果数据库不可用则返回模拟响应。
    """
    if db is not None:
        # 检查用户名是否已存在
        existing = await _get_user_from_db(db, req.username)
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"用户名 '{req.username}' 已存在"
            )

        # 创建用户
        password_hash = _hash_password(req.password)
        user = UserORM(
            username=req.username,
            password_hash=password_hash,
            role_code=req.role,
            display_name=req.display_name,
            email=req.email,
            is_active=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    # 创建 Token
    token = create_token(
        user_id=req.username,
        username=req.username,
        role=req.role,
    )
    return LoginResponse(
        success=True,
        token=token,
        user=UserInfo(
            user_id=req.username,
            username=req.username,
            role=req.role,
            display_name=req.display_name,
        ),
        message="注册成功",
    )


@app.post("/auth/change-password")
async def change_password(
    req: ChangePasswordRequest,
    current_user: TokenPayload = Depends(get_current_user),
    db: Annotated[AsyncSession, Depends(get_db)] = None,
):
    """修改当前用户密码

    验证旧密码后更新为新密码。支持数据库存储。
    """
    if db is not None:
        user = await _get_user_from_db(db, current_user.user_id)

        if user:
            # 验证旧密码
            if not _verify_password(req.old_password, user.password_hash):
                raise HTTPException(status_code=401, detail="原密码错误")

            # 更新密码
            new_password_hash = _hash_password(req.new_password)
            await db.execute(
                update(UserORM)
                .where(UserORM.username == current_user.user_id)
                .values(
                    password_hash=new_password_hash,
                    password_changed_at=datetime.utcnow(),
                )
            )
            await db.commit()
        else:
            # 回退到开发环境用户（不支持密码修改）
            raise HTTPException(
                status_code=501,
                detail="开发环境用户不支持密码修改，请使用数据库用户"
            )
    else:
        raise HTTPException(
            status_code=501,
            detail="数据库不可用，无法修改密码"
        )

    return {"success": True, "message": "密码修改成功"}


# ============================================================
# 密码重置功能
# ============================================================

@app.post("/auth/password/reset/code")
async def send_password_reset_code(
    req: PasswordResetCodeRequest,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
):
    """发送密码重置验证码

    通过邮箱发送密码重置验证码。验证码存储在 Redis 中，有效期 15 分钟。
    开发环境下直接返回验证码用于测试。
    """
    import random
    import string

    email = req.email.lower().strip()
    username = req.username.strip()

    if not email:
        raise HTTPException(status_code=400, detail="邮箱地址不能为空")

    # 验证邮箱/用户是否存在
    if db is not None:
        # 查询用户
        conditions = [UserORM.email == email]
        if username:
            conditions.append(UserORM.username == username)

        result = await db.execute(select(UserORM).where(*conditions))
        user = result.scalar_one_or_none()

        if not user:
            # 为了安全，不透露用户是否存在
            # 开发环境可以提示
            if settings.ENVIRONMENT.lower() != "production":
                raise HTTPException(status_code=404, detail="用户不存在")
            else:
                # 生产环境返回成功消息（防止用户枚举）
                return {
                    "success": True,
                    "message": "如果邮箱已注册，您将收到重置验证码",
                    "dev_mode": False,
                }
    else:
        # 数据库不可用，回退到开发环境检查
        if username:
            dev_users = _get_dev_users()
            if username not in dev_users:
                if settings.ENVIRONMENT.lower() != "production":
                    raise HTTPException(status_code=404, detail="用户不存在")

    # 生成6位数验证码
    code = "".join(random.choices(string.digits, k=6))

    # 存储到 Redis（15分钟有效期）
    try:
        from services.common.redis_client import get_redis_client

        redis_client = await get_redis_client()
        key = f"password_reset:{email}"
        await redis_client.setex(key, 900, code)  # 15分钟 = 900秒
    except Exception as e:
        logger.warning(f"Redis 不可用，无法存储验证码: {e}")
        # Redis 不可用时，仍然可以继续（开发环境直接返回验证码）

    # 开发环境直接返回验证码
    if settings.ENVIRONMENT.lower() != "production":
        logger.info(f"[开发环境] 密码重置验证码: {code}")
        return {
            "success": True,
            "message": "验证码已生成",
            "code": code,  # 开发环境直接返回验证码
            "expires_in": 900,  # 15分钟
            "dev_mode": True,
        }
    else:
        # 生产环境发送邮件
        try:
            from services.common.email_client import send_password_reset_email

            # 获取用户名用于个性化邮件
            display_name = None
            if db is not None:
                user_result = await db.execute(
                    select(UserORM).where(UserORM.email == email)
                )
                user_obj = user_result.scalar_one_or_none()
                if user_obj:
                    display_name = user_obj.display_name

            # 尝试发送邮件
            email_sent = await send_password_reset_email(email, code, display_name)
            if not email_sent:
                logger.warning(f"邮件发送失败 (SMTP 未配置或不可用): {email}")
        except ImportError:
            logger.warning("邮件客户端模块不可用")
        except Exception as e:
            logger.error(f"发送密码重置邮件失败: {e}")

    return {
        "success": True,
        "message": "如果邮箱已注册，您将收到重置验证码",
        "expires_in": 900,  # 15分钟
        "dev_mode": settings.ENVIRONMENT.lower() != "production",
    }


@app.post("/auth/password/reset/verify")
async def verify_reset_code(
    req: PasswordResetVerifyRequest,
):
    """验证密码重置验证码

    验证用户输入的验证码是否正确。
    """
    email = req.email.lower().strip()
    code = req.code

    # 从 Redis 获取存储的验证码
    try:
        from services.common.redis_client import get_redis_client

        redis_client = await get_redis_client()
        key = f"password_reset:{email}"
        stored_code = await redis_client.get(key)

        if not stored_code:
            raise HTTPException(status_code=400, detail="验证码已过期或不存在")

        if stored_code.decode() != code:
            raise HTTPException(status_code=400, detail="验证码错误")

        return {
            "success": True,
            "valid": True,
            "message": "验证码验证成功",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"验证验证码时发生错误: {e}")
        raise HTTPException(status_code=500, detail="验证码验证失败")


@app.post("/auth/password/reset/confirm")
async def confirm_password_reset(
    req: PasswordResetConfirmRequest,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
):
    """确认密码重置

    验证验证码后更新用户密码。
    """
    email = req.email.lower().strip()

    if db is None:
        raise HTTPException(status_code=501, detail="数据库不可用，无法重置密码")

    # 先验证验证码
    try:
        from services.common.redis_client import get_redis_client

        redis_client = await get_redis_client()
        key = f"password_reset:{email}"
        stored_code = await redis_client.get(key)

        if not stored_code:
            raise HTTPException(status_code=400, detail="验证码已过期或不存在")

        if stored_code.decode() != req.code:
            raise HTTPException(status_code=400, detail="验证码错误")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"验证验证码时发生错误: {e}")
        raise HTTPException(status_code=500, detail="验证码验证失败")

    # 查找用户
    result = await db.execute(select(UserORM).where(UserORM.email == email))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 更新密码
    new_password_hash = _hash_password(req.new_password)
    await db.execute(
        update(UserORM)
        .where(UserORM.email == email)
        .values(
            password_hash=new_password_hash,
            password_changed_at=datetime.utcnow(),
        )
    )
    await db.commit()

    # 清除已使用的验证码
    try:
        redis_client = await get_redis_client()
        await redis_client.delete(key)
    except Exception:
        pass  # 验证码会自动过期

    return {
        "success": True,
        "message": "密码重置成功，请使用新密码登录",
    }


@app.get("/auth/permissions")
async def get_permissions(current_user: TokenPayload = Depends(get_current_user)):
    """获取当前用户的权限列表"""
    permissions = _get_permissions_for_role(current_user.role)

    return {
        "user_id": current_user.user_id,
        "username": current_user.username,
        "role": current_user.role,
        "permissions": permissions,
    }


@app.get("/", response_model=PortalInfo)
async def portal_home():
    """门户首页 - 返回系统信息"""
    return PortalInfo(
        name="ONE-DATA-STUDIO-LITE",
        version="0.1.0",
        subsystems=await _check_subsystems()
    )


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "service": "portal"}


@app.get("/api/subsystems", response_model=list[SubsystemStatus])
async def list_subsystems():
    """列出所有子系统及其状态"""
    return await _check_subsystems()


# 内部微服务健康检查配置
INTERNAL_SERVICES = [
    {"name": "nl2sql", "display_name": "NL2SQL 服务", "url": settings.NL2SQL_URL},
    {"name": "ai-cleaning", "display_name": "AI 清洗服务", "url": settings.AI_CLEANING_URL},
    {"name": "metadata-sync", "display_name": "元数据同步服务", "url": settings.METADATA_SYNC_URL},
    {"name": "data-api", "display_name": "数据 API 网关", "url": settings.DATA_API_URL},
    {"name": "sensitive-detect", "display_name": "敏感数据检测服务", "url": settings.SENSITIVE_DETECT_URL},
    {"name": "audit-log", "display_name": "审计日志服务", "url": settings.AUDIT_LOG_URL},
]


async def _check_subsystems() -> list[SubsystemStatus]:
    """检查所有子系统状态"""
    import httpx
    results = []
    for sys in SUBSYSTEMS:
        is_healthy = False
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                url = sys["url"].rstrip("/") + sys.get("health_path", "/health")
                resp = await client.get(url)
                is_healthy = resp.status_code in (200, 302, 301)
        except Exception:
            pass
        results.append(SubsystemStatus(
            name=sys["name"],
            display_name=sys["display_name"],
            url=sys["url"],
            status="online" if is_healthy else "offline",
        ))
    return results


async def _check_internal_services() -> list[dict]:
    """检查所有内部微服务状态"""
    import asyncio

    import httpx

    async def check_one(svc: dict) -> dict:
        is_healthy = False
        error = None
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                url = svc["url"].rstrip("/") + "/health"
                resp = await client.get(url)
                is_healthy = resp.status_code == 200
        except Exception as e:
            error = str(e)
        return {
            "name": svc["name"],
            "display_name": svc["display_name"],
            "url": svc["url"],
            "status": "healthy" if is_healthy else "unhealthy",
            "error": error,
        }

    results = await asyncio.gather(*[check_one(svc) for svc in INTERNAL_SERVICES])
    return list(results)


@app.get("/health/all")
async def health_check_all():
    """聚合健康检查 - 检查所有子系统和内部服务

    Returns:
        所有组件的健康状态
    """
    import asyncio

    # 并行检查外部子系统和内部服务
    subsystems_task = _check_subsystems()
    internal_task = _check_internal_services()

    subsystems, internal_services = await asyncio.gather(subsystems_task, internal_task)

    # 计算整体状态
    all_healthy = all(
        s.status == "online" for s in subsystems
    ) and all(
        s["status"] == "healthy" for s in internal_services
    )

    unhealthy_count = sum(
        1 for s in subsystems if s.status != "online"
    ) + sum(
        1 for s in internal_services if s["status"] != "healthy"
    )

    return {
        "status": "healthy" if all_healthy else "degraded",
        "portal": "healthy",
        "unhealthy_count": unhealthy_count,
        "subsystems": [
            {"name": s.name, "display_name": s.display_name, "status": s.status}
            for s in subsystems
        ],
        "internal_services": internal_services,
    }


@app.get("/security/check")
async def security_check():
    """安全配置检查

    返回当前安全配置状态，包括警告和建议。
    可用于部署前验证配置是否安全。
    """
    from services.common.security import validate_env_config

    warnings = settings.validate_security()
    env_warnings = validate_env_config()

    all_warnings = warnings + env_warnings

    # 检查各子系统 Token 配置状态
    token_status = {
        "jwt_secret_configured": bool(settings.JWT_SECRET and settings.JWT_SECRET != "dev-only-change-in-production"),
        "jwt_secret_strong": len(settings.JWT_SECRET) >= 32 if settings.JWT_SECRET else False,
        "datahub_token_configured": bool(settings.DATAHUB_TOKEN),
        "dolphinscheduler_token_configured": bool(settings.DOLPHINSCHEDULER_TOKEN),
        "seatunnel_api_key_configured": bool(settings.SEA_TUNNEL_API_KEY),
        "internal_token_configured": bool(os.environ.get("INTERNAL_TOKEN")),
        "webhook_secret_configured": bool(os.environ.get("META_SYNC_DATAHUB_WEBHOOK_SECRET")),
        "superset_weak_creds": (
            settings.SUPERSET_ADMIN_USER == "admin" and
            settings.SUPERSET_ADMIN_PASSWORD in ("admin", "admin123", "password")
        ),
    }

    # 计算安全评分
    score = 0
    max_score = 8
    if token_status["jwt_secret_configured"]:
        score += 1
    if token_status["jwt_secret_strong"]:
        score += 1
    if token_status["datahub_token_configured"]:
        score += 1
    if token_status["dolphinscheduler_token_configured"]:
        score += 1
    if token_status["seatunnel_api_key_configured"]:
        score += 1
    if token_status["internal_token_configured"]:
        score += 1
    if token_status["webhook_secret_configured"]:
        score += 1
    if not token_status["superset_weak_creds"]:
        score += 1

    # 确定安全等级
    if score >= 7:
        security_level = "secure"
        security_message = "安全配置良好"
    elif score >= 5:
        security_level = "acceptable"
        security_message = "安全配置可接受，建议进一步优化"
    elif score >= 3:
        security_level = "warning"
        security_message = "安全配置存在风险，请改进"
    else:
        security_level = "critical"
        security_message = "安全配置严重不足，禁止部署到生产环境"

    return {
        "security_level": security_level,
        "security_message": security_message,
        "score": score,
        "max_score": max_score,
        "is_production": settings.is_production(),
        "environment": settings.ENVIRONMENT,
        "token_status": token_status,
        "warnings": all_warnings,
        "recommendations": [
            "为生产环境设置强随机 JWT_SECRET",
            "配置所有子系统的认证 Token",
            "修改 Superset 默认凭据",
            "启用 INTERNAL_TOKEN 用于服务间通信",
            "配置 META_SYNC_DATAHUB_WEBHOOK_SECRET",
            "启用 CONFIG_ENCRYPTION_KEY 加密配置中心敏感信息",
        ],
    }


@app.post("/shutdown")
async def shutdown_service(request: Request):
    """优雅关闭服务

    用于紧急停止场景。调用后服务将在短暂延迟后退出。
    """
    import threading

    logger = logging.getLogger(__name__)
    client_host = request.client.host if request.client else "unknown"

    logger.warning(f"服务关闭请求来自: {client_host}")

    # 在后台线程中延迟关闭，给响应时间发送
    def delayed_shutdown():
        import time
        time.sleep(0.5)  # 等待响应发送
        logger.critical("服务正在关闭...")
        os._exit(0)  # 立即退出

    thread = threading.Thread(target=delayed_shutdown, daemon=True)
    thread.start()

    return {
        "status": "shutting_down",
        "message": "服务正在关闭",
        "initiated_by": client_host,
    }


# SPA 静态文件托管 - 必须在所有 API 路由之后
STATIC_DIR = Path(__file__).parent / "static"

if STATIC_DIR.exists() and (STATIC_DIR / "index.html").exists():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    @app.get("/{path:path}")
    async def spa_catch_all(path: str, request: Request):
        """SPA catch-all: 未匹配的路由返回 index.html"""
        file_path = STATIC_DIR / path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(STATIC_DIR / "index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.APP_PORT)
