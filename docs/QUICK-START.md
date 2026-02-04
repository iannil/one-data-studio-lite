# 快速开始

本文档帮助您快速启动 ONE-DATA-STUDIO-LITE 项目。

**更新日期**: 2026-02-04

---

## 环境要求

| 组件 | 最低版本 | 推荐版本 |
|------|---------|---------|
| Docker | 20.10+ | 24.0+ |
| Docker Compose | 2.0+ | 2.20+ |
| Python | 3.11+ | 3.11 |
| Node.js | 18+ | 20+ |
| 内存 | 8GB | 16GB+ |
| 磁盘 | 20GB | 50GB+ |

### 验证环境

```bash
docker --version
docker-compose --version
python --version
node --version
```

---

## 一键启动

### 方式一: 使用统一入口脚本 (推荐)

```bash
# 克隆仓库
git clone https://github.com/iannil/one-data-studio-lite.git
cd one-data-studio-lite

# 启动所有服务
./ods.sh start all

# 查看服务状态
./ods.sh status all

# 健康检查
./ods.sh health all
```

### 方式二: 使用 Makefile

```bash
make start
make status
make health
```

---

## 分层启动

如果需要分步骤启动（推荐用于开发和调试）:

```bash
# 1. 启动基础设施 (MySQL, Redis, MinIO)
./ods.sh start infra

# 2. 等待基础设施就绪
./ods.sh health infra

# 3. 启动平台服务 (OpenMetadata, Superset等)
./ods.sh start platforms

# 4. 启动微服务
./ods.sh start services

# 5. 启动前端 (开发模式)
./ods.sh start web
```

---

## 初始化数据

首次启动后需要初始化数据:

```bash
# 初始化种子数据
./ods.sh init-data seed

# 验证数据完整性
./ods.sh init-data verify
```

---

## 访问系统

| 服务 | 地址 | 默认账号 |
|------|------|---------|
| **Web前端** | http://localhost:5173 | - |
| **Portal API** | http://localhost:8010 | - |
| **API文档** | http://localhost:8010/docs | - |
| **OpenMetadata** | http://localhost:8585 | admin/admin |
| **Superset** | http://localhost:8088 | admin/admin |
| **Hop** | http://localhost:8080 | - |
| **DolphinScheduler** | http://localhost:12345 | admin/dolphinscheduler123 |
| **Grafana** | http://localhost:3000 | admin/admin |

### 获取访问信息

```bash
./ods.sh info
```

---

## 常用命令

### 服务管理

```bash
# 停止所有服务
./ods.sh stop all

# 重启所有服务
./ods.sh restart all

# 只停止基础设施
./ods.sh stop infra

# 只停止微服务
./ods.sh stop services
```

### 日志查看

```bash
# 查看所有服务日志
docker-compose -f services/docker-compose.yml logs

# 查看特定服务日志
docker-compose -f services/docker-compose.yml logs portal

# 实时查看日志
docker-compose -f services/docker-compose.yml logs -f portal
```

### 进入容器

```bash
# 进入MySQL容器
docker-compose -f services/docker-compose.yml exec mysql bash

# 进入Portal容器
docker-compose -f services/docker-compose.yml exec portal bash
```

---

## 测试

### 运行全量测试

```bash
make test
# 或
./scripts/test-lifecycle.sh
```

### 分阶段测试

```bash
# 阶段0: 基础设施
./scripts/test-phased.sh 0

# 阶段1: 数据规划
./scripts/test-phased.sh 1
```

### 单个服务测试

```bash
# Portal服务测试
pytest tests/test_portal/ -v

# 通用模块测试
pytest services/common/tests/ -v
```

---

## 故障排查

### 端口被占用

```bash
# 查找占用进程
lsof -i :8010

# 杀掉进程
kill -9 <PID>

# 或使用自动端口功能
./scripts/test-phased.sh --auto-port
```

### Docker资源不足

```bash
# 查看Docker资源
docker stats

# 清理无用资源
docker system prune -a
```

### 服务无法启动

```bash
# 查看详细日志
docker-compose -f services/docker-compose.yml logs [service_name]

# 检查健康状态
curl http://localhost:8010/health

# 重启特定服务
docker-compose -f services/docker-compose.yml restart [service_name]
```

### 数据库连接失败

```bash
# 检查MySQL状态
docker-compose -f services/docker-compose.yml ps mysql

# 等待MySQL完全启动
docker-compose -f services/docker-compose.yml up -d mysql
sleep 30
```

---

## 开发模式

### 本地启动微服务

```bash
# 激活虚拟环境
source venv/bin/activate

# 安装依赖
pip install -r services/requirements.txt

# 启动Portal服务 (开发模式)
cd services/portal
python -m uvicorn main:app --reload --port 8010
```

### 本地启动前端

```bash
cd web
npm install
npm run dev
```

---

## 卸载/清理

```bash
# 停止并删除所有容器
./ods.sh stop all

# 删除所有数据 (警告: 不可逆)
docker-compose -f services/docker-compose.yml down -v

# 清理Docker资源
docker system prune -a
```

---

## 下一步

- 阅读详细文档: `docs/README.md`
- 查看系统架构: `docs/architecture.md`
- 了解开发规范: `docs/development.md`
- 查看运维手册: `docs/RUNBOOK.md`

---

## 获取帮助

```bash
# 显示所有可用命令
./ods.sh --help

# 或
make help
```

有问题? 查看 `docs/TROUBLESHOOTING.md` 或提交 Issue。
