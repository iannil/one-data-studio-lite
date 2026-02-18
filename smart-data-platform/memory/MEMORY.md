# 长期记忆

## 项目上下文

- **项目名称**: 智能大数据平台 (Smart Data Platform)
- **技术栈**: FastAPI + Next.js + PostgreSQL + Redis + MinIO
- **ETL引擎**: 基于 pandas 的 Python 实现，替代 Kettle
- **AI集成**: OpenAI API 用于字段分析、Text-to-SQL、清洗建议
- **当前阶段**: Phase 1 (MVP) - 基础框架完成
- **测试状态**: 63/74 通过 (85%), 覆盖率 60%

## 项目完成度

| 子系统 | 完成度 | 状态 |
|-------|--------|------|
| 元数据管理 | 80% | ✅ 核心功能完成 |
| 数据采集 | 90% | ✅ 连接器可用 |
| ETL加工 | 95% | ✅ 引擎稳定 |
| 分析挖掘 | 30% | ⚠️ 待完善 |
| 数据资产 | 50% | ⚠️ API待优化 |
| 安全管理 | 70% | ✅ 认证完成 |

## 关键决策

- 2026-02-16: 项目初始化，采用 Docker Compose 部署方案
- 2026-02-16: 使用 Python pandas 替代 Kettle 作为 ETL 引擎核心
- 2026-02-16: Python 3.9 兼容性 - 使用 `from __future__ import annotations` + `Optional[]`

## 用户偏好

- 交流与文档使用中文
- 代码使用英文
- 文档使用 Markdown 格式，放在 `docs` 目录

## 环境配置

- Redis 端口: 6380 (避免与其他项目冲突)
- PostgreSQL 端口: 5432
- MinIO 端口: 9000, 9001

## 依赖兼容性

- bcrypt: 使用 4.x 版本 (5.x 与 passlib 不兼容)
- eval_type_backport: 必须安装以支持 Python 3.9 + Pydantic

## 经验教训

### Python 3.9 兼容性

在 Python 3.9 中使用新式联合类型语法 (`X | Y`) 需要：

1. 在文件顶部添加 `from __future__ import annotations`
2. 对于 SQLAlchemy Mapped 类型，必须使用 `Optional[X]` 而非 `X | None`
3. 对于 Pydantic 模型，需要安装 `eval_type_backport` 包

### 依赖版本管理

- bcrypt 5.0+ 更改了 API，导致与 passlib 不兼容
- 解决方案：固定 bcrypt<5.0.0

### Docker 端口管理

- 本地开发时注意检查端口冲突
- 建议为每个项目使用独立的端口范围

## 文档规范

### 目录结构

```
docs/
├── progress/           # 进行中的修改
├── reports/completed/  # 已完成的报告
├── standards/          # 文档规范
├── templates/          # 文档模板
├── PROJECT_STATUS.md   # 项目状态总览
└── ISSUES.md           # 待解决问题
```

### 命名规范

- 进展文档: `{功能描述}-{YYYY-MM-DD}.md`
- 完成报告: `{报告类型}-{YYYY-MM-DD}.md`
