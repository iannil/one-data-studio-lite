# 架构设计文档

## 系统总体架构

```
┌──────────────────────────────────────────────────────────┐
│                   ONE-DATA-STUDIO-LITE                    │
├──────────────────────────────────────────────────────────┤
│  统一门户 (Portal)                                        │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐                  │
│  │Cube-Studio│ │ Superset │ │ DataHub  │                  │
│  │  前端     │ │  BI UI   │ │  UI      │                  │
│  └──────────┘ └──────────┘ └──────────┘                  │
├──────────────────────────────────────────────────────────┤
│  二开服务层                                                │
│  NL2SQL · AI清洗 · 元数据同步 · 数据API · 敏感检测 · 审计  │
├──────────────────────────────────────────────────────────┤
│  AI引擎：Cube-Studio (vllm/ollama LLM推理)               │
│          PaddleOCR · Great Expectations                   │
├──────────────────────────────────────────────────────────┤
│  ETL引擎：Apache Hop (Kettle开源替代)                     │
│  数据同步：Apache SeaTunnel + DolphinScheduler            │
├──────────────────────────────────────────────────────────┤
│  元数据/资产：DataHub                                     │
│  BI分析：Apache Superset                                  │
│  数据安全：Apache ShardingSphere                          │
├──────────────────────────────────────────────────────────┤
│  基础设施：Kubernetes (k3s) · Prometheus · Grafana        │
│  存储：MySQL/PostgreSQL · MinIO · Redis                   │
├──────────────────────────────────────────────────────────┤
│  数据标注：Label Studio (Cube-Studio已集成)               │
└──────────────────────────────────────────────────────────┘
```

---

## 基座平台：Cube-Studio

Cube-Studio（腾讯音乐开源，Apache 2.0）作为整体基座，提供以下核心能力：

| 能力 | 说明 |
|------|------|
| 数据管理 | 数据集管理、SQLLab、数据标注（Label Studio） |
| 在线开发 | Jupyter / VSCode / RStudio 在线IDE |
| 任务编排 | 拖拉拽 Pipeline 编排、定时调度 |
| 模型推理 | 模型管理、VGPU、vllm/ollama 大模型推理 |
| 知识库 | RAG 私有知识库能力 |
| 监控告警 | Prometheus + Grafana |
| 多集群 | K8s 多集群调度、资源隔离 |

---

## 六大子系统

### 1. 数据规划与元数据管理系统

- **核心组件**: DataHub
- **功能**: 元数据智能识别、标签管理、版本控制、数据血缘
- **集成**: DataHub 通过 Ingestion 框架自动采集数据库元数据，REST API 实现标签和版本管理

### 2. 数据感知汇聚系统

- **核心组件**: Apache SeaTunnel + DolphinScheduler + Apache Hop
- **功能**: 多源数据采集（200+数据源）、批流一体、CDC实时同步、可视化ETL设计
- **分工**:
  - SeaTunnel 负责高性能数据同步
  - Hop 负责复杂业务逻辑 ETL 转换
  - DolphinScheduler 统一调度

### 3. 数据加工融合系统

- **核心组件**: SeaTunnel Transform + Great Expectations + PaddleOCR + LLM
- **功能**: AI辅助清洗规则推荐、数据质量检测、OCR识别、NLP处理
- **集成**: PaddleOCR 封装为推理服务，LLM 提供智能清洗规则推荐

### 4. 数据分析挖掘系统 (AI+BI)

- **核心组件**: Apache Superset + Cube-Studio Pipeline + LLM
- **功能**: BI可视化、自然语言查询(NL2SQL)、AI预测、智能预警
- **集成**: Superset 连接数据仓库表，NL2SQL 模块调用 LLM 做 Text2SQL

### 5. 数据资产系统

- **核心组件**: DataHub（复用）
- **功能**: 资产编目、血缘追踪、语义搜索、数据服务API
- **集成**: DataHub 自动追踪 ETL 血缘，二开数据服务网关

### 6. 数据安全管理系统

- **核心组件**: Apache ShardingSphere + 正则/LLM
- **功能**: 透明数据脱敏、敏感数据识别、权限管控
- **集成**: ShardingSphere 在 SQL 层拦截实现脱敏，LLM 辅助识别复杂场景

---

## 数据流向

```
数据源 (MySQL/PostgreSQL/文件/API)
    │
    ▼
SeaTunnel (数据同步/CDC)  ←→  DolphinScheduler (调度)
    │
    ▼
Apache Hop (复杂ETL转换)  ←  AI清洗规则推荐 (LLM)
    │
    ▼
数据仓库 (MySQL/PostgreSQL)  ←→  DataHub (元数据管理)
    │                                │
    ├──→ Superset (BI分析)           ├──→ 数据资产API
    ├──→ NL2SQL (自然语言查询)       └──→ 血缘追踪
    └──→ ShardingSphere (脱敏代理)
```

---

## 子系统交互关系

| 从 → 到 | 交互方式 | 说明 |
|---------|---------|------|
| DataHub → SeaTunnel | Webhook + REST API | 元数据变更触发ETL配置更新 |
| SeaTunnel → DataHub | DataHub Ingestion | ETL血缘自动采集 |
| DolphinScheduler → SeaTunnel/Hop | 任务调度 | 统一调度ETL任务 |
| Superset → 数据仓库 | JDBC | 直接查询数据 |
| NL2SQL → LLM(Ollama) | REST API | 自然语言转SQL |
| 敏感检测 → ShardingSphere | 配置同步 | 自动生成脱敏规则 |
| 所有服务 → 审计日志 | REST API | 操作日志汇总 |
