# 模块化运维快速参考

## 一行命令启动

```bash
# 启动基础平台（最小）
make mod-base

# 启动元数据管理
make mod-metadata

# 启动数据集成
make mod-integration

# 启动数据加工
make mod-processing

# 启动BI分析
make mod-bi

# 启动数据安全
make mod-security

# 启动所有模块
make mod-all
```

## 模块脚本用法

```bash
# 启动模块
./scripts/modules.sh start <module>

# 停止模块
./scripts/modules.sh stop <module>

# 查看状态
./scripts/modules.sh status

# 健康检查
./scripts/modules.sh health <module>

# 列出模块
./scripts/modules.sh list
```

## 本地开发模式

```bash
# 本地模式启动（支持热重载）
./scripts/modules.sh start base --local

# 或使用 Makefile
make dev-portal
make dev-nl2sql
make dev-cleaning
```

## 测试验证

```bash
# 运行模块测试
./scripts/test-modules.sh test <module>

# 快速验证
./scripts/test-modules.sh verify <module>

# 完整测试
./scripts/test-modules.sh test <module> --full
```

## 内存需求参考

| 模块 | 内存 |
|------|------|
| base | 4 GB |
| metadata | 6 GB |
| integration | 8 GB |
| processing | 6 GB |
| bi | 8 GB |
| security | 5 GB |
| **all** | **32 GB** |

## 访问地址

| 服务 | 地址 | 账号 |
|------|------|------|
| Portal | http://localhost:8010 | - |
| OpenMetadata | http://localhost:8585 | admin/admin |
| Superset | http://localhost:8088 | admin/admin123 |
| DolphinScheduler | http://localhost:12345 | admin/dolphinscheduler123 |
| SeaTunnel | http://localhost:5802 | - |
| Hop | http://localhost:8083 | - |
