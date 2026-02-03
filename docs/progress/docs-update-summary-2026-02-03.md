# 文档更新摘要 - 2026-02-03

## 更新概览

根据单一数据源原则，从以下源文件同步更新了项目文档：

**数据源:**
- `Makefile` - Make 命令定义
- `ods.sh` - 统一运维入口脚本
- `.env.example` - 环境变量配置示例
- `web/package.json` - 前端 npm scripts

## 更新内容

### 1. docs/CONTRIB.md (更新日期: 2026-02-03, 版本: 1.1)

**新增内容:**

#### 环境变量说明扩展
- 完整的通用配置 (必须设置) 部分
- 子系统地址配置 (Cube-Studio, Superset, DataHub, DolphinScheduler, SeaTunnel, ShardingSphere)
- 邮件服务配置 (SMTP) 详细参数
- LLM 配置 (base_url, model, temperature, max_tokens)
- 审计日志配置
- 各服务独立配置 (端口变量和数据库变量)

#### 统一运维入口 (ods.sh) 部分
- 启动服务命令 (start all/infra/platforms/services/web)
- 停止服务命令 (stop all/infra/platforms/services/web)
- 状态与健康检查命令
- 数据操作命令 (init-data seed/verify/status)
- 测试命令 (test all/lifecycle/foundation/planning/collection/processing/analysis/security)

### 2. docs/RUNBOOK.md (更新日期: 2026-02-03, 版本: 1.2)

**新增内容:**

#### 服务访问地址章节
- 从 `ods.sh info` 命令提取的完整服务地址列表
- 包含所有服务的默认访问地址和凭据
- 分类组织：基座平台、核心组件、二开服务、前端、基础设施

## 差异统计

```
docs/CONTRIB.md | 156 +++++++++++++++++++++++++++++++++++++++------------
docs/RUNBOOK.md |  42 ++++++++++++++-
2 files changed, 165 insertions(+), 33 deletions(-)
```

## 过时文档分析

### 文档修改时间分析
所有文档均在 90 天内有修改，**无需标记为过时**：

- 最新修改: 2026-02-03 (RUNBOOK.md, 多个 completed 报告)
- 大部分文档: 2026-01-31 ~ 2026-02-02
- 测试用例: 2026-01-31

### 建议定期审查的文档
以下文档内容随系统演进可能需要更新：

1. **docs/tech-stack.md** - 技术栈版本
2. **docs/integration-status.md** - 子系统集成状态
3. **docs/project-status.md** - 项目整体状态
4. **docs/technical-debt.md** - 技术债务清单

## 单一数据源映射

| 文档区域 | 数据源 | 同步状态 |
|---------|-------|---------|
| 环境变量 | .env.example | 已同步 |
| Make 命令 | Makefile | 已同步 |
| ods.sh 命令 | ods.sh | 已同步 |
| 服务地址 | ods.sh (info) | 已同步 |
| npm scripts | web/package.json | 现有文档已覆盖 |

## 后续建议

1. **定期同步**: 建议每周运行一次文档同步命令
2. **自动化**: 可考虑创建 `scripts/sync-docs.sh` 自动脚本
3. **版本追踪**: 在每个文档头部添加 "数据源" 和 "最后同步" 字段

## 相关文件

- 源文件: `/Users/iannil/Code/zproducts/one-data-studio-lite/.env.example`
- 源文件: `/Users/iannil/Code/zproducts/one-data-studio-lite/Makefile`
- 源文件: `/Users/iannil/Code/zproducts/one-data-studio-lite/ods.sh`
- 源文件: `/Users/iannil/Code/zproducts/one-data-studio-lite/web/package.json`
- 更新文件: `/Users/iannil/Code/zproducts/one-data-studio-lite/docs/CONTRIB.md`
- 更新文件: `/Users/iannil/Code/zproducts/one-data-studio-lite/docs/RUNBOOK.md`
