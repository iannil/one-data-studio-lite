# 技术选型说明

## 选型汇总

| 子系统 | 组件 | 选型 | License |
|-------|------|------|---------|
| 基座平台 | AI/MLOps | Cube-Studio | Apache 2.0 |
| 元数据管理 | 元数据 | DataHub | Apache 2.0 |
| 数据采集 | 数据集成 | Apache SeaTunnel | Apache 2.0 |
| 任务调度 | 调度 | Apache DolphinScheduler | Apache 2.0 |
| ETL引擎 | ETL | Apache Hop | Apache 2.0 |
| 数据质量 | 检测 | Great Expectations | Apache 2.0 |
| OCR | 识别 | PaddleOCR | Apache 2.0 |
| BI分析 | 可视化 | Apache Superset | Apache 2.0 |
| 数据安全 | 脱敏 | Apache ShardingSphere | Apache 2.0 |

---

## 选型理由

### DataHub vs Apache Atlas

| 维度 | DataHub | Apache Atlas |
|------|---------|-------------|
| 社区活跃度 | GitHub 9k+ Star, 持续更新 | 更新缓慢 |
| UI | 现代化 React UI | 老旧 UI |
| 数据源 | 200+ 数据源 | 主要面向 Hadoop 生态 |
| 实时捕获 | 支持实时元数据变更 | 有限 |
| 部署复杂度 | Docker Compose 一键部署 | 依赖 HBase/Solr，较重 |

**结论**: DataHub 社区更活跃、UI更现代化、更通用，不限于 Hadoop 生态。

### Apache Hop vs Kettle (PDI)

| 维度 | Apache Hop | Kettle (PDI) |
|------|-----------|-------------|
| License | Apache 2.0 (免费) | 2024年10.2版改为非开源 |
| 创始人 | Kettle创始人 Matt Casters | Pentaho (Hitachi) |
| 架构 | 现代化，支持多运行引擎 | 单体架构 |
| 运行引擎 | Native, Spark, Flink, Dataflow | 仅 Native |
| 设计器 | Hop GUI (类似 Spoon) | Spoon |
| 兼容性 | 设计理念兼容 Kettle | - |

**结论**: Kettle 10.2+ 不再开源，Apache Hop 是 Kettle 创始人创建的开源替代，架构更先进。

### Apache SeaTunnel vs 传统ETL

- Apache 顶级项目，支持 200+ 数据源
- 批流一体，支持 CDC 实时同步
- 性能优于传统 ETL 工具
- 与 DolphinScheduler 原生集成

### Apache Superset vs Metabase

| 维度 | Superset | Metabase |
|------|---------|---------|
| 功能 | 更丰富，SQL Lab, 拖拽图表 | 更简洁易用 |
| 定制性 | 高，支持嵌入模式 | 中等 |
| 图表类型 | 100+ | 20+ |
| AI能力 | 需二开 NL2SQL | 内置 Metabot |
| 社区 | Apache 顶级项目 | 商业开源 |

**结论**: Superset 功能更丰富、可定制性更高，适合企业级需求。

---

## 与 Cube-Studio 集成方式

| 组件 | 集成方式 |
|------|---------|
| DataHub | Ingestion 框架采集 Cube-Studio 连接的数据库元数据 |
| SeaTunnel | 通过 Cube-Studio Pipeline 或 DolphinScheduler 调度 |
| Apache Hop | REST API/CLI 在 K8s 中执行，通过调度器触发 |
| Superset | 直接连接数据仓库表，共享 MySQL |
| PaddleOCR | 封装为 Cube-Studio 推理服务 |
| LLM | 使用 Cube-Studio 部署的 vllm/ollama |
| ShardingSphere | 作为数据库代理层，应用透明 |

---

## 需要二次开发的模块

| 序号 | 模块 | 端口 | 说明 |
|------|------|------|------|
| 1 | 统一入口门户 | 8010 | 整合各平台登录和导航 |
| 2 | NL2SQL | 8011 | 基于 LLM 的自然语言查询 |
| 3 | AI清洗规则推荐 | 8012 | LLM 分析数据质量并生成清洗配置 |
| 4 | 元数据联动ETL | 8013 | DataHub 变更触发 ETL 配置更新 |
| 5 | 数据资产API网关 | 8014 | 统一数据服务接口 |
| 6 | 敏感数据AI识别 | 8015 | 正则+LLM 识别敏感数据 |
| 7 | 统一审计日志 | 8016 | 汇总各组件操作日志 |

技术栈: Python 3.11 + FastAPI + SQLAlchemy + httpx

---

## 版本建议

| 组件 | 推荐版本 |
|------|---------|
| Python | 3.11+ |
| MySQL | 8.0 |
| Kubernetes (k3s) | 最新稳定版 |
| Docker | 24.0+ |
| Apache Superset | 3.1.x |
| DataHub | 0.13.x |
| Apache Hop | 2.8.x |
| Apache SeaTunnel | 2.3.x |
| DolphinScheduler | 3.2.x |
| ShardingSphere | 5.4.x |
| Ollama | 最新版 |
