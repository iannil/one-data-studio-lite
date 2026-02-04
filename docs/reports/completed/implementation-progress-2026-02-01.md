# 剩余问题实施进度

> **开始日期**: 2026-02-01
> **状态**: 进行中
> **目标**: 逐步修复所有剩余问题

---

## 已完成任务 (2026-02-01)

### P0.3 认证系统数据库化 ✅

**状态**: 已完成

**实施内容**:

1. **登录端点数据库支持** (`services/portal/main.py`):
   - 添加数据库查询优先逻辑
   - 保留 DEV_USERS 回退机制以保持向后兼容
   - 实现密码哈希验证
   - 添加 `is_active` 和 `is_locked` 检查
   - 更新登录信息（`last_login_at`, `last_login_ip`）
   - 登录失败计数

2. **注册端点数据库实现** (`services/portal/main.py`):
   - 检查用户名唯一性
   - 创建用户记录到数据库
   - 密码哈希存储
   - 自动登录并返回 Token

3. **密码修改端点数据库实现** (`services/portal/main.py`):
   - 验证旧密码
   - 更新新密码哈希
   - 更新 `password_changed_at` 时间戳

4. **数据库迁移脚本** (`services/common/migrations.py`):
   - 创建所有必需的数据库表
   - 插入默认权限（20个权限）
   - 插入默认角色（8个角色）
   - 从 DEV_USERS 迁移用户到数据库
   - 插入默认系统配置

**相关文件**:
- `services/portal/main.py` - 登录/注册/密码修改端点
- `services/common/migrations.py` - 数据库迁移脚本
- `Makefile` - 添加 `db-migrate`, `db-migrate-dev`, `db-reset` 命令

---

### P0.4 Token 黑名单 ✅

**状态**: 已完成（之前已实现）

**实现内容**:
- Redis 存储黑名单
- Token 撤销接口
- 用户所有 Token 批量撤销
- 自动过期清理

**相关文件**:
- `services/common/token_blacklist.py`

---

### P0.5 数据库连接池配置 ✅

**状态**: 已完成（之前已实现）

**配置内容**:
- `pool_size=10`
- `max_overflow=20`
- `pool_pre_ping=True`

**相关文件**:
- `services/common/database.py`

---

## 使用说明

### 首次部署

1. **设置数据库环境变量**:
   ```bash
   export DATABASE_URL="mysql+aiomysql://user:password@localhost:3306/one_data_studio"
   ```

2. **运行数据库迁移**:
   ```bash
   # 生产环境（使用随机密码，首次登录需重置）
   make db-migrate

   # 开发环境（迁移 DEV_USERS 密码）
   make db-migrate-dev
   ```

3. **启动服务**:
   ```bash
   make deploy
   ```

### 管理命令

```bash
# 查看所有命令
make help

# 数据库迁移
make db-migrate         # 生产环境
make db-migrate-dev     # 开发环境（迁移密码）
make db-reset          # 重置数据库（警告：删除所有数据）
```

---

## 待完成任务

| 优先级 | 问题 | 状态 |
|--------|------|------|
| P0 | 生产环境部署验证 | 待开始 |
| P0 | E2E 测试修复 (74个失败) | 进行中 |
| P1 | 组件测试覆盖缺失 (14个组件) | 待开始 |
| P1 | 外部组件集成不完整 | 待开始 |
| P1 | 配置文件重复 | 待开始 |
| P1 | 统一错误处理机制 | 待开始 |
| P1 | 服务间调用硬编码 URL | 待开始 |
| P1 | 系统功能缺失 | 待开始 |
| P2 | Python 类型注解不完整 | 待开始 |
| P2 | TypeScript `any` 类型使用 | 待开始 |
| P2 | 日志级别不规范 | 待开始 |
| P2 | TODO 注释清理 | 待开始 |
