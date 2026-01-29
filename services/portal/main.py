"""统一入口门户 - FastAPI 应用"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from services.common.auth import create_token
from services.common.exceptions import register_exception_handlers
from services.common.http_client import ServiceClient
from services.common.metrics import setup_metrics
from services.common.middleware import RequestLoggingMiddleware
from services.portal.config import settings
from services.portal.models import (
    LoginRequest,
    LoginResponse,
    PortalInfo,
    SubsystemStatus,
    UserInfo,
)

app = FastAPI(
    title=settings.APP_NAME,
    description="ONE-DATA-STUDIO-LITE 统一入口门户",
    version="0.1.0",
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

# 子系统配置
SUBSYSTEMS = [
    {"name": "cube-studio", "display_name": "Cube-Studio (AI平台)", "url": settings.CUBE_STUDIO_URL},
    {"name": "superset", "display_name": "Apache Superset (BI分析)", "url": settings.SUPERSET_URL},
    {"name": "datahub", "display_name": "DataHub (元数据管理)", "url": settings.DATAHUB_URL},
    {"name": "dolphinscheduler", "display_name": "DolphinScheduler (任务调度)", "url": settings.DOLPHINSCHEDULER_URL},
    {"name": "hop", "display_name": "Apache Hop (ETL引擎)", "url": settings.HOP_URL},
]

# 内置用户 (开发环境，生产环境应使用数据库)
DEV_USERS = {
    "admin": {"password": "admin123", "role": "admin", "display_name": "管理员"},
}


@app.get("/")
async def portal_home():
    """门户首页 - 返回平台信息和子系统链接"""
    subsystems = await _check_subsystems()
    return PortalInfo(
        name="ONE-DATA-STUDIO-LITE",
        version="0.1.0",
        subsystems=subsystems,
    )


@app.post("/auth/login", response_model=LoginResponse)
async def login(req: LoginRequest):
    """统一登录"""
    user = DEV_USERS.get(req.username)
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


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "service": "portal"}


@app.get("/api/subsystems", response_model=list[SubsystemStatus])
async def list_subsystems():
    """列出所有子系统及其状态"""
    return await _check_subsystems()


async def _check_subsystems() -> list[SubsystemStatus]:
    """检查所有子系统状态"""
    results = []
    for sys in SUBSYSTEMS:
        client = ServiceClient(sys["url"])
        is_healthy = await client.health_check()
        results.append(SubsystemStatus(
            name=sys["name"],
            display_name=sys["display_name"],
            url=sys["url"],
            status="online" if is_healthy else "offline",
        ))
    return results


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.APP_PORT)
