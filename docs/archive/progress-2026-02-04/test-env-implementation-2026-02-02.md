# 测试环境精简方案实施进展

**时间**: 2026-02-02
**状态**: 已完成

## 一、实施概述

创建了资源消耗低、启动快速的测试环境，用于演示六大子系统功能。

## 二、已完成工作

### 1. 目录结构创建

```
deploy/test-env/
├── docker-compose.yml       # 主编排文件
├── .env                     # 环境变量配置
├── init-sql/                # 数据库初始化脚本
│   ├── 01-init-mysql.sql   # 表结构
│   └── 02-seed-data.sql    # 种子数据
├── cube-studio-lite/        # Cube-Studio 精简版静态文件
│   └── index.html
└── README.md               # 使用说明
```

### 2. 核心文件

| 文件 | 描述 | 行数 |
|------|------|------|
| docker-compose.yml | 所有服务的编排配置 | ~550 |
| .env | 环境变量配置模板 | ~35 |
| 01-init-mysql.sql | 数据库表结构 | ~250 |
| 02-seed-data.sql | 测试种子数据 | ~200 |
| test-env.sh | 一键启动脚本 | ~200 |
| test-env-stop.sh | 一键停止脚本 | ~80 |
| README.md | 使用文档 | ~250 |
| cube-studio-lite/index.html | 精简版页面 | ~100 |

### 3. Makefile 新增命令

```bash
make test-env-up       # 启动测试环境
make test-env-down     # 停止测试环境
make test-env-clean    # 停止并清理数据
make test-env-status   # 查看状态
make test-env-logs     # 查看日志
make test-env-pull     # 拉取镜像
```

## 三、服务配置

### 基础设施

| 服务 | 内存限制 | 端口 |
|------|---------|------|
| MySQL | 256M | 3306 |
| Redis | 64M | 6379 |
| MinIO | 128M | 9000, 9001 |

### DataHub 组件 (精简版)

| 服务 | 内存限制 | 端口 |
|------|---------|------|
| datahub-mysql | 128M | - |
| datahub-elasticsearch | 512M | - |
| datahub-zookeeper | 128M | - |
| datahub-kafka | 256M | - |
| datahub-schema-registry | 128M | - |
| datahub-gms | 512M | 8081 |
| datahub-frontend | - | 9002 |

### Superset 组件 (精简版)

| 服务 | 内存限制 | 端口 |
|------|---------|------|
| superset-db | 64M | - |
| superset-redis | 32M | - |
| superset | 512M | 8088 |

### 二开微服务

| 服务 | 内存限制 | 端口 |
|------|---------|------|
| portal | 128M | 8010 |
| nl2sql | 128M | 8011 |
| ai-cleaning | 128M | 8012 |
| metadata-sync | 128M | 8013 |
| data-api | 128M | 8014 |
| sensitive-detect | 128M | 8015 |
| audit-log | 128M | 8016 |

### 总资源需求

- **内存**: 约 3GB (使用外部 LLM API)
- **CPU**: 约 1.2 核
- **磁盘**: 约 20GB

## 四、访问地址

| 服务 | 地址 | 账号密码 |
|------|------|---------|
| 统一门户 | http://localhost:8010 | admin/admin123 |
| NL2SQL | http://localhost:8011/docs | - |
| AI清洗 | http://localhost:8012/docs | - |
| 元数据同步 | http://localhost:8013/docs | - |
| 数据API | http://localhost:8014/docs | - |
| 敏感检测 | http://localhost:8015/docs | - |
| 审计日志 | http://localhost:8016/docs | - |
| Superset | http://localhost:8088 | admin/admin123 |
| DataHub | http://localhost:9002 | datahub/datahub |
| Cube-Studio Lite | http://localhost:30100 | - |
| MinIO | http://localhost:9001 | minioadmin/minioadmin123 |

## 五、与完整环境对比

| 组件 | 完整环境 | 测试环境 |
|------|---------|---------|
| K8s | k3s | 移除 |
| Ollama | 内置模型 | 外部 API |
| DolphinScheduler | ✓ | 移除 |
| SeaTunnel | ✓ | 移除 |
| ShardingSphere | ✓ | 移除 |
| Apache Hop | ✓ | 移除 |
| 监控栈 | ✓ | 移除 |
| 资源占用 | ~8GB | ~3GB |

## 六、启动方式

```bash
# 使用脚本
./deploy/test-env.sh

# 使用 Makefile
make test-env-up
```

## 七、后续工作

- [ ] 实际启动测试验证服务可用性
- [ ] 根据实际运行情况调整资源限制
- [ ] 添加更多测试数据
- [ ] 编写测试环境使用教程
