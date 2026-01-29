# 部署指南

## 环境要求

| 资源 | 最低要求 | 推荐配置 |
|------|---------|---------|
| CPU | 4 核 | 8 核+ |
| 内存 | 16 GB | 32 GB+ |
| 磁盘 | 100 GB | 200 GB+ (SSD) |
| 操作系统 | Linux / macOS | Ubuntu 22.04 / CentOS 8+ |
| Docker | 24.0+ | 最新稳定版 |

---

## 部署顺序

单机开发环境的部署顺序如下：

```
k3s → Cube-Studio → Superset → DataHub → Hop → SeaTunnel → DolphinScheduler → ShardingSphere → 二开服务
```

### 一键部署

```bash
# 全量部署
make deploy

# 或
bash deploy.sh deploy
```

### 分步部署

```bash
# 1. 安装 k3s
bash deploy/k3s/install.sh

# 2. 部署 Cube-Studio
bash deploy/cube-studio/install.sh

# 3. 部署各组件
make superset-up
make datahub-up
make hop-up
make seatunnel-up
make dolphinscheduler-up
make shardingsphere-up

# 4. 部署二开服务
make services-up
```

---

## 访问地址

### 基座平台

| 服务 | 地址 | 默认账号 |
|------|------|---------|
| Cube-Studio | http://localhost:30080 | admin / admin123 |
| Grafana | http://localhost:30300 | admin / admin123 |
| Prometheus | http://localhost:30090 | - |
| MinIO | http://localhost:30900 | minioadmin / minioadmin123 |
| Ollama API | http://localhost:31434 | - |

### 核心组件

| 服务 | 地址 | 默认账号 |
|------|------|---------|
| Apache Superset | http://localhost:8088 | admin / admin123 |
| DataHub | http://localhost:9002 | datahub / datahub |
| DolphinScheduler | http://localhost:12345 | admin / dolphinscheduler123 |
| Apache Hop | http://localhost:8083 | admin / admin123 |
| SeaTunnel API | http://localhost:5801 | - |
| ShardingSphere | localhost:3307 | root / one-data-studio-2024 |

### 二开服务

| 服务 | 地址 | API 文档 |
|------|------|---------|
| 统一门户 | http://localhost:8010 | http://localhost:8010/docs |
| NL2SQL | http://localhost:8011 | http://localhost:8011/docs |
| AI清洗 | http://localhost:8012 | http://localhost:8012/docs |
| 元数据同步 | http://localhost:8013 | http://localhost:8013/docs |
| 数据API | http://localhost:8014 | http://localhost:8014/docs |
| 敏感检测 | http://localhost:8015 | http://localhost:8015/docs |
| 审计日志 | http://localhost:8016 | http://localhost:8016/docs |

---

## 常用命令

```bash
# 查看服务状态
make status

# 查看访问地址
make info

# 查看二开服务日志
make services-logs

# 停止所有服务
make stop

# 本地开发（不需要 Docker）
make dev-install    # 安装 Python 依赖
make dev-portal     # 启动门户服务
make dev-nl2sql     # 启动 NL2SQL 服务
```

---

## 常见问题

### 1. 内存不足导致服务启动失败

如果内存不足 16GB，可以选择性部署组件：

```bash
# 跳过 k3s 和 Cube-Studio，只部署核心组件
SKIP_K3S=1 SKIP_CUBE_STUDIO=1 bash deploy.sh deploy
```

### 2. Docker 网络问题

如果容器间无法通信，确认 Docker 网络已创建：

```bash
docker network create ods-network
```

### 3. 端口冲突

检查是否有其他服务占用了相同端口：

```bash
# macOS
lsof -i :8088

# Linux
ss -tlnp | grep 8088
```

### 4. DataHub 启动慢

DataHub 依赖 Elasticsearch 和 Kafka，首次启动需要等待较长时间（2-3分钟）。可通过日志查看进度：

```bash
docker logs -f ods-datahub-gms
```

### 5. Ollama 模型下载

首次启动后需要下载 LLM 模型：

```bash
# 下载中文对话模型
curl http://localhost:31434/api/pull -d '{"name":"qwen2.5:7b"}'
```
