# 开发指南

本文档介绍如何进行 ONE-DATA-STUDIO-LITE 的本地开发和二次开发。

---

## 环境准备

### 系统要求

- Python 3.11+
- Docker & Docker Compose
- Make (可选)

### 克隆项目

```bash
git clone <repo-url>
cd one-data-studio-lite
```

### 安装 Python 依赖

```bash
# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate  # Windows

# 安装依赖
pip install -r services/requirements.txt

# 或使用 make
make dev-install
```

### 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件设置必要的配置
```

---

## 项目结构

```
services/
├── common/                 # 共享库
│   ├── __init__.py
│   ├── database.py         # 数据库连接
│   ├── auth.py             # JWT 认证
│   ├── http_client.py      # HTTP 客户端
│   ├── exceptions.py       # 异常处理
│   └── middleware.py       # 请求日志中间件
├── portal/                 # 统一门户
│   ├── config.py           # 配置
│   ├── models.py           # 数据模型
│   └── main.py             # FastAPI 应用
├── nl2sql/                 # NL2SQL 服务
├── ai_cleaning/            # AI清洗服务
├── metadata_sync/          # 元数据同步服务
├── data_api/               # 数据API服务
├── sensitive_detect/       # 敏感检测服务
└── audit_log/              # 审计日志服务
```

---

## 开发规范

### 服务结构

每个服务遵循统一结构：

```
services/<service_name>/
├── __init__.py
├── config.py      # Pydantic Settings 配置
├── models.py      # Pydantic 数据模型
└── main.py        # FastAPI 应用入口
```

### 配置管理

使用 `pydantic_settings` 管理配置，支持环境变量覆盖：

```python
# config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "My Service"
    APP_PORT: int = 8010
    DATABASE_URL: str = ""  # 从环境变量读取

    model_config = {"env_prefix": "MY_SERVICE_"}

settings = Settings()
```

### 数据库访问

使用共享的数据库模块：

```python
from services.common.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

@app.get("/api/data")
async def get_data(db: AsyncSession = Depends(get_db)):
    # 使用参数化查询防止 SQL 注入
    result = await db.execute(
        text("SELECT * FROM users WHERE id = :id"),
        {"id": user_id}
    )
    return result.fetchall()
```

### 认证

使用共享的认证模块：

```python
from services.common.auth import get_current_user, TokenPayload

@app.get("/api/protected")
async def protected_endpoint(user: TokenPayload = Depends(get_current_user)):
    return {"user": user.username}
```

### 异常处理

使用共享的异常类：

```python
from services.common.exceptions import NotFoundError, AppException

@app.get("/api/items/{item_id}")
async def get_item(item_id: str):
    item = await find_item(item_id)
    if not item:
        raise NotFoundError("数据项", item_id)
    return item
```

### 审计日志

使用中间件自动记录 API 调用：

```python
from services.common.middleware import RequestLoggingMiddleware

app.add_middleware(RequestLoggingMiddleware, service_name="my-service")
```

---

## 本地运行

### 启动单个服务

```bash
# 直接运行
python -m services.portal.main

# 或使用 uvicorn
uvicorn services.portal.main:app --reload --port 8010
```

### 启动所有服务

```bash
make services-up
```

### 访问 API 文档

启动服务后访问 Swagger UI：
- http://localhost:8010/docs (Portal)
- http://localhost:8011/docs (NL2SQL)
- ...

---

## 添加新服务

1. 创建服务目录：

```bash
mkdir services/my_service
touch services/my_service/__init__.py
```

2. 创建配置文件 `config.py`：

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "My Service"
    APP_PORT: int = 8020
    DATABASE_URL: str = ""

    model_config = {"env_prefix": "MY_SERVICE_"}

settings = Settings()
```

3. 创建主应用 `main.py`：

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from services.common.middleware import RequestLoggingMiddleware
from services.common.exceptions import register_exception_handlers
from services.my_service.config import settings

app = FastAPI(title=settings.APP_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggingMiddleware, service_name="my-service")
register_exception_handlers(app)

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "my-service"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.APP_PORT)
```

4. 更新环境变量模板 `.env.example`

5. 更新 `docker-compose.yml` 添加新服务

---

## 测试

### 运行测试

```bash
# 安装测试依赖
pip install pytest pytest-asyncio httpx

# 运行测试
pytest tests/
```

### 测试示例

```python
# tests/test_portal.py
import pytest
from httpx import AsyncClient
from services.portal.main import app

@pytest.mark.asyncio
async def test_health():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
```

---

## 代码风格

- 使用 [Black](https://github.com/psf/black) 格式化代码
- 使用 [isort](https://github.com/PyCQA/isort) 排序导入
- 使用 [mypy](https://github.com/python/mypy) 进行类型检查

```bash
# 格式化
black services/
isort services/

# 类型检查
mypy services/
```

---

## 调试

### 日志

```python
import logging

logger = logging.getLogger("one-data-studio")
logger.info("Processing request...")
```

### 调试模式

在 `config.py` 中设置 `DEBUG: bool = True` 启用详细错误信息。

### 使用 pdb

```python
import pdb; pdb.set_trace()
```

---

## 常见问题

### 数据库连接失败

检查 `DATABASE_URL` 环境变量是否正确配置。

### LLM 服务不可用

确保 Ollama 服务在 `http://localhost:31434` 运行。

### 端口冲突

修改服务配置中的 `APP_PORT` 或使用环境变量覆盖。
