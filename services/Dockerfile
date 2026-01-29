# ONE-DATA-STUDIO-LITE - 二开服务通用 Dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装依赖
COPY services/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 复制服务代码
COPY services/ /app/services/

# 默认启动命令 (由 docker-compose 覆盖)
CMD ["uvicorn", "services.portal.main:app", "--host", "0.0.0.0", "--port", "8010"]
