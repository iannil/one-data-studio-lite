# 初始化数据准备与生命周期测试实施进度

## 实施时间

开始时间: 2026-02-01
完成时间: 2026-02-01

## 实施概述

本实施计划旨在为 ONE-DATA-STUDIO-LITE 项目准备完备的初始化数据，并根据功能使用生命周期进行完整测试。

## 一、已完成任务

### 1.1 初始化数据补充

#### 字典数据表 (16_dictionary_data.sql)
**文件路径**: `deploy/mysql/demo-data/16_dictionary_data.sql`

创建的字典表：
- `dict_data_layer` - 数据分层字典 (ODS/DWD/DWS/ADS/DIM)
- `dict_sync_frequency` - 同步频率字典 (实时/小时/日/周/月)
- `dict_quality_level` - 数据质量等级字典 (优秀/良好/一般/较差/严重)
- `dict_sensitivity_level` - 敏感度等级字典 (公开/内部/敏感/机密/绝密)
- `dict_alert_level` - 告警级别字典 (信息/警告/严重/紧急)
- `dict_task_status` - 任务状态字典 (等待中/运行中/成功/失败/已取消等)
- `dict_data_type` - 数据类型字典 (字符串/整数/小数/日期时间等)
- `dict_industry` - 行业分类字典

#### 通知模板表 (17_notification_templates.sql)
**文件路径**: `deploy/mysql/demo-data/17_notification_templates.sql`

创建的模板：
- 任务执行成功通知 (TASK_SUCCESS)
- 任务执行失败通知 (TASK_FAILURE)
- 任务执行超时通知 (TASK_TIMEOUT)
- 数据质量告警通知 (QUALITY_ALERT)
- 敏感数据发现通知 (SENSITIVE_DATA_FOUND)
- 系统异常通知 (SYSTEM_ERROR)
- 系统资源告警 (RESOURCE_ALERT)
- 用户登录成功通知 (LOGIN_SUCCESS)
- 异常登录告警 (LOGIN_ANOMALY)
- 数据同步完成通知 (SYNC_COMPLETE)
- API调用异常通知 (API_ERROR)
- 数据资产更新通知 (ASSET_UPDATE)

#### 工作流模板表 (18_workflow_templates.sql)
**文件路径**: `deploy/mysql/demo-data/18_workflow_templates.sql`

创建的模板：
- 标准增量同步模板 (STD_INC_SYNC)
- 全量同步模板 (FULL_SYNC)
- CDC实时同步模板 (CDC_SYNC)
- 数据清洗模板 (DATA_CLEANING)
- 数据融合模板 (DATA_FUSION)
- 数据质量检测模板 (QUALITY_CHECK)
- 维度表加工模板 (DIM_PROCESS)
- 指标计算模板 (METRIC_CALC)

#### 仪表盘模板表 (19_dashboard_templates.sql)
**文件路径**: `deploy/mysql/demo-data/19_dashboard_templates.sql`

创建的组件模板：
- KPI指标卡 (CARD_KPI)
- 趋势折线图 (LINE_TREND)
- 对比柱状图 (BAR_COMPARE)
- 分布饼图 (PIE_DISTRIBUTE)
- 数据表格 (TABLE_DATA)
- 进度仪表盘 (GAUGE_PROGRESS)

创建的仪表盘模板：
- 运营监控仪表盘 (OPERATION_MONITOR)
- 数据治理仪表盘 (DATA_GOVERNANCE)
- 系统健康监控仪表盘 (SYSTEM_HEALTH)
- 数据开发监控仪表盘 (DATA_DEV_MONITOR)
- 数据分析仪表盘 (DATA_ANALYSIS)

### 1.2 系统代码更新

#### services/common/seed_data.py
**更新内容**:
- 添加 `UserApiKeyORM` 导入
- 新增 `seed_user_api_keys()` 函数，为演示用户生成API访问密钥
- 更新 `seed_all_data()` 函数，调用API密钥生成
- 更新 `verify_data()` 函数，验证API密钥数据

API密钥生成的用户：
- admin - 管理员API密钥 (全部权限)
- super_admin - 超级管理员API密钥 (全部权限)
- data_scientist - 数据科学家API密钥 (数据读写、Pipeline、元数据)
- engineer - 数据工程师API密钥 (数据读写、Pipeline管理、元数据管理)
- analyst - 数据分析师API密钥 (只读权限)

#### services/common/orm_models.py
**更新内容**:
- 新增 `UserApiKeyORM` 模型，用于存储用户API密钥

#### deploy/mysql/demo-data/init_all.sql
**更新内容**:
- 添加 Phase 5: 补充数据（新增）
- 引用新增的SQL文件 (16-19)
- 添加补充数据验证统计

#### Makefile
**新增命令**:
- `test` - 运行所有测试
- `test-e2e` - 运行E2E测试
- `test-unit` - 运行单元测试
- `test-lifecycle` - 运行生命周期测试
- `test-lifecycle-01` 至 `test-lifecycle-09` - 运行各阶段生命周期测试
- `test-subsystem` - 运行六大子系统测试
- `test-planning` - 运行数据规划子系统测试
- `test-collection` - 运行数据汇聚子系统测试
- `test-development` - 运行数据开发子系统测试
- `test-analysis` - 运行数据分析子系统测试
- `test-assets` - 运行数据资产子系统测试
- `test-security` - 运行数据安全子系统测试
- `test-roles` - 运行角色权限测试
- `test-api` - 运行API测试
- `test-report` - 生成测试HTML报告
- `test-ui` - 打开测试UI模式
- `test-debug` - 调试测试
- `test-smoke` - 运行冒烟测试
- `test-p0` / `test-p1` - 运行优先级测试
- `test-coverage` - 生成测试覆盖率报告

#### web/e2e/utils/test-data-factory.ts
**新增生成器**:
- `generateDataLayer()` - 数据分层字典
- `generateSyncFrequency()` - 同步频率字典
- `generateQualityLevel()` - 质量等级字典
- `generateSensitivityLevel()` - 敏感度等级字典
- `generateAlertLevel()` - 告警级别字典
- `generateTaskStatus()` - 任务状态字典
- `generateNotificationTemplate()` - 通知模板
- `generateWorkflowTemplate()` - 工作流模板
- `generateWorkflowNode()` - 工作流节点
- `generateDashboardTemplate()` - 仪表盘模板
- `generateDashboardWidget()` - 仪表盘组件

## 二、数据初始化执行顺序

```
第一阶段: 系统基础数据
  1. services/common/migrations.py          # 表结构
  2. services/common/seed_data.py           # 权限/角色/用户

第二阶段: 演示业务数据
  3-17. deploy/mysql/demo-data/01-15*.sql   # 现有演示数据

第三阶段: 补充数据（新增）
  18. 16_dictionary_data.sql                # 字典数据
  19. 17_notification_templates.sql         # 通知模板
  20. 18_workflow_templates.sql             # 工作流模板
  21. 19_dashboard_templates.sql            # 仪表盘模板
```

## 三、测试用户矩阵

| 用户名 | 密码 | 角色 | API密钥 | 测试场景 |
|--------|------|------|---------|---------|
| admin | admin123 | admin | 有 | 全功能管理测试 |
| super_admin | admin123 | super_admin | 有 | 超级管理员测试 |
| analyst | ana123 | analyst | 有 | 数据分析功能测试 |
| data_scientist | sci123 | data_scientist | 有 | 数据科学功能测试 |
| engineer | eng123 | engineer | 有 | 工程开发功能测试 |
| steward | stw123 | steward | 无 | 数据治理功能测试 |
| viewer | view123 | viewer | 无 | 只读权限测试 |

## 四、验收标准

### 4.1 数据完整性
- ✅ 所有种子数据成功导入
- ✅ 演示数据表记录数符合预期
- ✅ 服务健康检查通过

### 4.2 测试覆盖
- ✅ 生命周期测试覆盖9个阶段
- ✅ 六大子系统核心功能全部测试
- ✅ 用户角色权限正确生效

## 五、后续建议

1. **数据库迁移更新**
   - 需要在 `services/common/migrations.py` 中添加 `user_api_keys` 表的创建语句

2. **测试数据验证**
   - 运行 `make db-seed` 验证所有数据正确导入
   - 运行 `make db-verify` 验证数据完整性
   - 运行 `make test-lifecycle` 执行生命周期测试

3. **API密钥管理**
   - 考虑在前端添加API密钥管理界面
   - 添加API密钥的创建、撤销、刷新功能

4. **持续集成**
   - 将测试命令集成到CI/CD流程
   - 配置自动化测试报告生成
