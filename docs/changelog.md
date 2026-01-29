# 变更日志

所有重要变更都会记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)。

---

## [未发布]

### 新增
- 项目文档结构重组
- 创建 `.env.example` 环境变量模板
- 添加 API 文档
- 添加开发指南

### 变更
- 重写 README.md 为项目入口页面
- 将原始需求文档归档至 `docs/archive/`

### 修复
- 移除所有硬编码密码，改用环境变量
- 修复 SQL 注入漏洞（参数化查询）
- 修复中间件静默异常处理问题
- 移除未使用的导入

### 安全
- JWT 密钥从硬编码改为环境变量配置
- 数据库密码从硬编码改为环境变量配置
- SQL 查询使用参数化查询防止注入

---

## [0.1.0] - 2025-01-29

### 新增
- 项目初始化
- Cube-Studio 基座集成
- 7个二开微服务（Python/FastAPI）
  - portal: 统一门户
  - nl2sql: 自然语言查询
  - ai_cleaning: AI清洗推荐
  - metadata_sync: 元数据同步
  - data_api: 数据资产API
  - sensitive_detect: 敏感检测
  - audit_log: 审计日志
- 部署配置
  - K3s 安装脚本
  - Superset Docker Compose
  - DataHub Docker Compose
  - Apache Hop Docker Compose
  - SeaTunnel Docker Compose
  - DolphinScheduler Docker Compose
  - ShardingSphere 配置
- 文档
  - 架构设计文档
  - 技术选型文档
  - 部署指南
