# Celery 迁移实施报告 (Phase 1)

**日期**: 2026-02-19
**状态**: ✅ 基础设施已完成

## 概述

本次更新完成了 Celery 分布式任务队列的基础设施搭建，为从 APScheduler 到 Celery 的迁移做好准备。系统现在支持两种调度模式，可通过环境变量切换。

---

## 完成项目

### 1. Celery Worker 配置 ✅

**文件**: `app/celery_worker.py`

- 创建 Celery 应用实例
- 配置任务路由 (collect, report, etl 队列)
- 配置 Celery Beat 定时任务
- 设置结果后端和序列化

### 2. 任务模块创建 ✅

**目录**: `app/tasks/`

| 模块 | 功能 | 主要任务 |
|------|------|----------|
| `collect_tasks.py` | 数据采集任务 | `execute_collect_task`, `sync_all_active_tasks`, `health_check_sources` |
| `report_tasks.py` | 报表生成任务 | `generate_scheduled_report`, `generate_all_pending_reports`, `send_report_email` |
| `etl_tasks.py` | ETL 执行任务 | `run_etl_pipeline`, `run_scheduled_pipeline`, `run_all_scheduled_pipelines` |
| `system_tasks.py` | 系统维护任务 | `cleanup_old_results`, `health_check_sources`, `disk_usage_report`, `task_monitor` |

### 3. SchedulerService 更新 ✅

**文件**: `app/services/scheduler_service.py`

- 添加 `USE_CELERY` 环境变量支持
- 更新 `add_collect_job` 方法支持 Celery Beat
- 保留 APScheduler 向后兼容性
- 添加迁移说明注释

### 4. 测试文件 ✅

**文件**: `tests/test_quality_service.py`

- 创建 DataQualityService 单元测试
- 20+ 测试用例覆盖所有主要方法

---

## 架构变更

### 之前 (仅 APScheduler)

```
┌─────────────────┐
│  FastAPI App    │
│                 │
│  APScheduler    │
│  (in-process)   │
└─────────────────┘
```

### 之后 (双模式支持)

```
┌─────────────────┐
│  FastAPI App    │
│                 │
│  APScheduler    │
│  (legacy mode)  │
└─────────────────┘         ┌──────────────────────┐
                            │  Redis (Broker)       │
                            │  ─────────────────    │
┌─────────────────────┐    │  Result Backend      │
│  Celery Beat        │    └──────────────────────┘
│  (scheduler)        │              │
└─────────────────────┘              │
         │                            │
         └────────────┬───────────────┘
                      │
         ┌────────────┼─────────────┐
         │            │             │
┌────────▼───┐ ┌────▼────────┐ ┌──▼──────────┐
│  collect   │ │    report   │ │     etl     │
│   worker   │ │    worker   │ │   worker    │
└────────────┘ └─────────────┘ └─────────────┘
```

---

## 使用方式

### 模式 1: APScheduler (默认)

无需额外配置，APScheduler 在 FastAPI 进程内运行。

```bash
# 启动应用
uvicorn app.main:app --reload
```

### 模式 2: Celery (推荐)

需要启动独立的 Celery Worker 和 Beat 进程。

```bash
# 1. 设置环境变量
export USE_CELERY=true

# 2. 启动 Celery Worker
celery -A app.celery_worker worker --loglevel=info --concurrency=2

# 3. 启动 Celery Beat (调度器)
celery -A app.celery_worker beat --loglevel=info

# 4. 启动 FastAPI 应用
uvicorn app.main:app --reload
```

### Docker Compose 配置

已在 `docker-compose.ops.yml` 中配置 Celery 服务：

```bash
# 启动 Worker (包含 Beat)
docker compose -f docker-compose.ops.yml --profile worker up -d
```

---

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `USE_CELERY` | `false` | 启用 Celery 模式 |
| `CELERY_BROKER_URL` | `redis://...` | Celery 消息队列 |
| `CELERY_RESULT_BACKEND` | `redis://...` | 结果存储 |
| `ENVIRONMENT` | - | 生产环境配置 |

---

## 任务清单

### 已完成 ✅

- [x] 创建 Celery worker 配置
- [x] 创建 collect_tasks.py
- [x] 创建 report_tasks.py
- [x] 创建 etl_tasks.py
- [x] 创建 system_tasks.py
- [x] 更新 SchedulerService 支持 Celery
- [x] 创建 test_quality_service.py
- [x] 添加前端 quality.tsx 页面
- [x] 更新 api.ts 添加 quality 端点

### 待完成 (Phase 4 继续) ⏳

- [ ] 创建 test_report_service.py
- [ ] 创建 test_celery_tasks.py
- [ ] 添加 Flower 监控配置
- [ ] 更新前端添加 Celery 任务监控页面
- [ ] 完整迁移后移除 APScheduler

---

## 迁移步骤 (完整迁移)

当准备完全切换到 Celery 时：

1. **启用 Celery 模式**
   ```bash
   export USE_CELERY=true
   ```

2. **更新所有定时任务使用 Celery Beat**

3. **启动 Celery Worker 和 Beat**
   ```bash
   docker compose -f docker-compose.ops.yml --profile worker up -d
   ```

4. **验证任务执行正常**

5. **移除 APScheduler 依赖**
   - 从 `requirements.txt` 移除 `apscheduler==3.10.4`
   - 删除 `app/core/scheduler.py`
   - 更新 `app/main.py` 移除 scheduler 启动

---

## 监控与管理

### Flower (Celery 监控)

可选安装 Flower 用于可视化监控：

```bash
pip install flower

# 启动 Flower
celery -A app.celery_worker flower --port=5555
```

访问 `http://localhost:5555` 查看：
- 活跃任务
- 工作进程状态
- 任务执行历史
- 任务执行时间

---

## 故障排查

### Celery Worker 无法连接 Redis

检查 `CELERY_BROKER_URL` 配置和 Redis 服务状态。

### 任务未执行

1. 检查 Celery Beat 日志
2. 确认 `USE_CELERY=true`
3. 检查任务是否正确注册

### APScheduler 仍被使用

确认环境变量 `USE_CELERY=true` 已设置。

---

## 参考资料

- [Celery 文档](https://docs.celeryq.dev/)
- [Celery Beat 配置](https://docs.celeryq.dev/en/stable/userguide/periodic-tasks.html)
- 迁移计划: `/docs/reports/completed/2026-02-19-scheduler-migration-plan.md`
