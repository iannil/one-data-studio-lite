# ONE-DATA-STUDIO-LITE 精简测试环境

资源消耗低、启动快速的测试环境，完整演示六大子系统功能。

## 资源需求

| 资源 | 最小配置 | 推荐配置 |
|------|---------|---------|
| 内存 | 4GB | 8GB |
| CPU | 2核 | 4核 |
| 磁盘 | 20GB | 30GB |

**说明**: 使用外部 LLM API 可节省约 4GB 内存

## 快速开始

### 1. 启动测试环境

```bash
./deploy/test-env.sh
```

首次启动需要拉取 Docker 镜像，可能需要 5-10 分钟。

### 2. 停止测试环境

```bash
./deploy/test-env-stop.sh
```

停止但保留数据:
```bash
./deploy/test-env-stop.sh
```

停止并删除所有数据:
```bash
./deploy/test-env-stop.sh --clean
```

## 访问地址

### 统一门户与微服务

| 服务 | 地址 | 说明 |
|------|------|------|
| 统一门户 | http://localhost:8010 | 六大子系统入口 |
| NL2SQL | http://localhost:8011/docs | 自然语言查询 API |
| AI清洗 | http://localhost:8012/docs | AI清洗规则推荐 API |
| 元数据同步 | http://localhost:8013/docs | 元数据采集同步 API |
| 数据API | http://localhost:8014/docs | 数据资产 API 网关 |
| 敏感检测 | http://localhost:8015/docs | 敏感数据检测 API |
| 审计日志 | http://localhost:8016/docs | 统一审计日志 API |

### 开源组件

| 组件 | 地址 | 账号密码 |
|------|------|---------|
| Superset BI | http://localhost:8088 | admin / admin123 |
| DataHub | http://localhost:9002 | datahub / datahub |
| Cube-Studio Lite | http://localhost:30100 | - |
| MinIO | http://localhost:9001 | minioadmin / minioadmin123 |

## 默认账户

| 用户名 | 密码 | 角色 |
|--------|------|------|
| admin | admin123 | 管理员 |
| data_engineer | admin123 | 数据工程师 |
| data_analyst | admin123 | 数据分析师 |
| business_user | admin123 | 业务用户 |

## LLM API 配置

测试环境默认使用外部 LLM API。编辑 `deploy/test-env/.env` 文件配置:

```bash
# OpenAI
LLM_API_BASE=https://api.openai.com/v1
LLM_API_KEY=your-openai-api-key
LLM_MODEL=gpt-3.5-turbo

# 或使用其他兼容 OpenAI 的 API
LLM_API_BASE=https://api.deepseek.com/v1
LLM_API_KEY=your-deepseek-key
LLM_MODEL=deepseek-chat

# 或使用本地 Ollama
LLM_API_BASE=http://host.docker.internal:31434
LLM_MODEL=qwen2.5:7b
```

## 六大子系统演示

### 1. 数据规划与元数据管理系统

**访问路径**: 统一门户 → DataHub 元数据

**演示内容**:
- 浏览元数据目录
- 查看表结构和字段信息
- 数据血缘关系

**涉及服务**: DataHub + metadata-sync

### 2. 数据感知汇聚系统

**访问路径**: 统一门户 → 数据源管理

**演示内容**:
- 数据源接入配置
- 数据同步任务管理
- 数据预览

**涉及服务**: data-api + portal

### 3. 数据加工融合系统

**访问路径**: 统一门户 → AI清洗规则

**演示内容**:
- AI清洗规则推荐
- 数据质量检测
- 敏感数据识别

**涉及服务**: ai-cleaning + sensitive-detect

### 4. 数据分析挖掘系统 (AI+BI)

**访问路径**: 统一门户 → NL2SQL / Superset

**演示内容**:
- 自然语言生成SQL
- BI可视化报表
- 交互式数据分析

**涉及服务**: nl2sql + superset + portal

### 5. 数据资产系统

**访问路径**: 统一门户 → 数据资产

**演示内容**:
- 数据资产目录
- API自动生成
- 资产权限管理

**涉及服务**: data-api + datahub

### 6. 数据安全管理系统

**访问路径**: 统一门户 → 安全中心

**演示内容**:
- 敏感数据检测
- 数据脱敏规则
- 操作审计日志

**涉及服务**: sensitive-detect + audit-log

## 常用命令

```bash
# 查看服务状态
docker compose -f deploy/test-env/docker-compose.yml ps

# 查看服务日志
docker compose -f deploy/test-env/docker-compose.yml logs -f [服务名]

# 重启单个服务
docker compose -f deploy/test-env/docker-compose.yml restart [服务名]

# 查看资源占用
docker stats --no-stream

# 进入容器
docker exec -it test-env-portal bash
```

## 故障排查

### 端口冲突

如果端口已被占用，修改 `deploy/test-env/docker-compose.yml` 中的端口映射。

### 内存不足

1. 减少并发服务数量
2. 降低单个服务的内存限制
3. 使用外部 LLM API 替代本地模型

### 服务启动失败

```bash
# 查看详细日志
docker compose -f deploy/test-env/docker-compose.yml logs

# 重新构建服务
docker compose -f deploy/test-env/docker-compose.yml up -d --build
```

### 数据库连接失败

确保 MySQL 服务已就绪:
```bash
docker exec -it test-env-mysql mysql -uroot -ptest_root_password
```

## 目录结构

```
deploy/test-env/
├── docker-compose.yml       # 主编排文件
├── .env                     # 环境变量配置
├── init-sql/                # 数据库初始化脚本
│   ├── 01-init-mysql.sql   # 表结构
│   └── 02-seed-data.sql    # 种子数据
├── cube-studio-lite/        # Cube-Studio 精简版静态文件
└── README.md               # 本文档
```

## 与完整环境的差异

| 组件 | 完整环境 | 测试环境 |
|------|---------|---------|
| K8s | ✓ (k3s) | ✗ 移除 |
| Ollama | ✓ 内置模型 | ✗ 使用外部 API |
| DolphinScheduler | ✓ | ✗ 移除 |
| SeaTunnel | ✓ | ✗ 移除 |
| ShardingSphere | ✓ | ✗ 移除 |
| Apache Hop | ✓ | ✗ 移除 |
| 监控栈 | ✓ | ✗ 移除 |
| 资源占用 | ~8GB | ~3GB |

## 下一步

- 查看 [完整部署文档](../../docs/) 了解生产环境部署
- 查看 [开发指南](../../docs/development.md) 了解本地开发
- 查看 [API文档](http://localhost:8010/docs) 了解所有接口
