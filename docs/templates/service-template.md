# [服务名称] 服务文档

**服务名称**: [Service Name]
**端口**: XXXX
**健康检查**: `/health`
**负责人**: [姓名]

## 服务概述

[简要描述服务功能和定位]

## 技术栈

- **语言**: Python 3.11+
- **框架**: FastAPI
- **数据库**: MySQL/PostgreSQL
- **缓存**: Redis

## 目录结构

```
services/[service_name]/
├── main.py              # 服务入口
├── config.py            # 配置
├── models.py            # 数据模型
├── routers/             # 路由
│   └── __init__.py
├── services/            # 业务逻辑
│   └── __init__.py
└── tests/               # 测试
    └── __init__.py
```

## API端点

| 端点 | 方法 | 描述 | 认证 |
|------|------|------|------|
| /api/v1/xxx | GET | 描述 | 需要 |
| /api/v1/yyy | POST | 描述 | 不需要 |

## 环境变量

| 变量名 | 说明 | 默认值 | 必需 |
|--------|------|--------|------|
| XXX_HOST | 描述 | localhost | 是 |
| XXX_PORT | 描述 | 8080 | 否 |

## 依赖服务

| 服务 | 用途 | 依赖级别 |
|------|------|---------|
| MySQL | 数据存储 | 强依赖 |
| Redis | 缓存 | 强依赖 |

## 本地开发

### 启动服务
```bash
cd services/[service_name]
python -m uvicorn main:app --reload --port XXXX
```

### 运行测试
```bash
pytest services/[service_name]/tests/
```

## 部署

### Docker
```bash
docker build -t [service_name]:latest .
docker run -p XXXX:XXXX [service_name]:latest
```

## 监控

### 健康检查
```bash
curl http://localhost:XXXX/health
```

### 日志
- 日志位置: `/var/log/[service_name]/`
- 日志级别: INFO/DEBUG

## 故障排查

### 常见问题

**问题1**: 描述
- 解决方法: 步骤

**问题2**: 描述
- 解决方法: 步骤

## 变更历史

| 日期 | 版本 | 变更内容 | 负责人 |
|------|------|---------|--------|
| YYYY-MM-DD | 1.0.0 | 初始版本 | 姓名 |
