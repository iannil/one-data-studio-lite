"""统一入口门户 - FastAPI 应用"""

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from services.common.auth import create_token, refresh_token, get_current_user, TokenPayload
from services.common.exceptions import register_exception_handlers
from services.common.metrics import setup_metrics
from services.common.middleware import RequestLoggingMiddleware
from services.portal.config import settings, init_config_center
from services.portal.models import (
    LoginRequest,
    LoginResponse,
    PortalInfo,
    RefreshTokenResponse,
    SubsystemStatus,
    UserInfo,
    ChangePasswordRequest,
    RegisterRequest,
    ApiResponse,
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
    seatunnel,
    sensitive,
    shardingsphere,
    superset,
    users,  # 新增
    roles,  # 新增
    service_accounts,  # 新增
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
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
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


@app.post("/auth/login", response_model=LoginResponse)
async def login(req: LoginRequest):
    """统一登录"""
    user = settings.DEV_USERS.get(req.username)
    if not user or user["password"] != req.password:
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    token = create_token(
        user_id=req.username,
        username=req.username,
        role=user["role"],
    )
    return LoginResponse(
        success=True,
        token=token,
        user=UserInfo(
            user_id=req.username,
            username=req.username,
            role=user["role"],
            display_name=user["display_name"],
        ),
        message="登录成功",
    )


@app.post("/auth/logout")
async def logout():
    """登出"""
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
async def validate_token(request: Request):
    """验证 Token 有效性

    供子系统验证 Portal 颁发的 Token。

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
    from services.common.api_response import success, error
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

        # 获取用户配置（从 DEV_USERS 中查找）
        user_config = settings.DEV_USERS.get(payload.username, {})
        if not user_config:
            return {
                "valid": False,
                "code": 40402,
                "message": "用户不存在"
            }

        role = user_config.get("role", "user")
        permissions = _get_permissions_for_role(role)

        return {
            "valid": True,
            "user_id": payload.user_id,
            "username": payload.username,
            "display_name": user_config.get("display_name", payload.username),
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
async def get_user_info(user: TokenPayload = Depends(get_current_user)):
    """获取当前登录用户信息"""
    user_config = settings.DEV_USERS.get(user.user_id, {})
    roles = [user_config.get("role", user.role)]
    permissions = _get_permissions_for_role(user.role)

    return {
        "user_id": user.user_id,
        "username": user.username,
        "display_name": user_config.get("display_name", user.username),
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
async def register(req: RegisterRequest):
    """用户注册

    仅在系统未初始化时可用，或由超级管理员调用。
    """
    # TODO: 实现数据库支持的注册逻辑
    # 当前返回开发环境模拟响应
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
):
    """修改当前用户密码"""
    # TODO: 实现数据库支持的密码修改逻辑
    # 当前返回模拟响应
    return {"success": True, "message": "密码修改成功"}


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
    import httpx
    import asyncio

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
