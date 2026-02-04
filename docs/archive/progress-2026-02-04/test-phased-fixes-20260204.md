# 分阶段测试脚本修复报告

**修复时间**: 2026-02-04
**修复目标**: 解决分阶段测试脚本中的关键Bug

---

## 问题分析

### 1. 内存计算Bug (关键)

**症状**: 可用内存始终显示为 0GB，导致所有测试因"内存不足"而失败

**根本原因**:
1. 变量名错误: `speculative=${speculative_pages:-0}` 应为 `speculative=${speculative:-0}`
2. 页大小检测失败: macOS 上 vm_stat 输出 "page size of 16384 bytes"，但代码假设 $3 是数字
3. Bash 整数溢出: 大页数 × 页大小超过 32 位整数限制

**影响**: 所有7个阶段测试全部失败 (19次测试，0通过)

### 2. 端口冲突问题

**症状**: 默认端口 13306/16379/19000 被 OrbStack 等进程占用

**影响**: 基础设施无法启动，导致阶段0失败

---

## 修复内容

### 1. 修复内存计算 (`scripts/test-phased.sh:368-402`)

```bash
# 修改前
speculative=${speculative_pages:-0}  # 错误的变量名
local total_gb=$((total_bytes / 1024 / 1024 / 1024))  # 整数溢出

# 修改后
speculative=${speculative:-0}  # 正确的变量名
# 使用 awk 进行大数计算
local total_gb=$(echo "$free $inactive $speculative $page_size" | \
    awk '{pages=$1+$2+$3; gb=pages*$4/1024/1024/1024; printf "%d", gb}')
```

**页大小检测修复**:
```bash
# 修改前
local ps_value=$(echo "$ps_line" | awk '{print $3}' | sed 's/[^0-9]//g')

# 修改后
local ps_value=$(echo "$mem_info" | grep "page size" | \
    awk '{for(i=1;i<=NF;i++) if($i~/^[0-9]+$/) print $i}')
```

### 2. 新增自动端口选择功能 (`scripts/test-phased.sh:318-366`)

**新增函数**:
- `select_available_port()`: 自动选择可用端口
- `auto_configure_ports()`: 配置所有服务端口

**备用端口配置**:
| 服务 | 默认端口 | 备用端口1 | 备用端口2 | 动态端口 |
|------|----------|-----------|-----------|----------|
| MySQL | 13306 | 23306 | 33306 | +1000*i |
| Redis | 16379 | 26379 | 36379 | +1000*i |
| MinIO | 19000 | 29000 | 39000 | +1000*i |

### 3. 新增诊断选项 (`scripts/test-phased.sh:734-887`)

**新增 `--diagnose` 选项**:
- Docker 状态检查
- 内存信息详情
- 端口占用情况
- 网络状态
- 磁盘空间
- 修复建议

### 4. 增强基础设施启动健壮性 (`scripts/infra.sh:47-156`)

**改进内容**:
1. 启动前强制清理遗留容器
2. 重试逻辑 (最多3次)
3. 改进的健康检查超时处理

### 5. 新增环境验证脚本 (`scripts/validate-env.sh`)

**功能**:
- 检查 Docker 是否运行
- 检查可用内存
- 检查端口可用性
- 检查磁盘空间
- 输出修复建议

---

## 新增命令行选项

| 选项 | 说明 |
|------|------|
| `--auto-port` | 自动选择可用端口 |
| `--diagnose` | 输出详细诊断信息 |
| `--skip-memory-check` | 跳过内存检查 |
| `--skip-port-check` | 跳过端口检查 |
| `--show-errors` | 显示服务启动详细错误 |

---

## 使用示例

### 基本验证
```bash
# 检查环境
./scripts/validate-env.sh

# 查看诊断信息
./scripts/test-phased.sh --diagnose
```

### 端口冲突解决
```bash
# 自动选择可用端口
./scripts/test-phased.sh --auto-port

# 或手动指定端口
export ODS_MYSQL_PORT=23306
export ODS_REDIS_PORT=26379
export ODS_MINIO_PORT=29000
./scripts/test-phased.sh
```

### 调试模式
```bash
# 跳过检查并显示详细错误
./scripts/test-phased.sh 0 --skip-memory-check --skip-port-check --show-errors --verbose
```

---

## 验证结果

### 内存计算验证
```bash
$ ./scripts/test-phased.sh --diagnose
=== 内存信息 ===
总内存: 5GB
可用内存: 2GB  # 修复前为 0GB
```

### 环境验证
```bash
$ ./scripts/validate-env.sh
=== 内存检查 ===
  可用内存: 3GB  # 修复前为 0GB
⚠ 内存紧张 (>= 1GB)，部分阶段无法运行
```

---

## 修改文件清单

| 文件 | 修改类型 | 状态 |
|------|----------|------|
| `scripts/test-phased.sh` | Bug修复 + 功能增强 | 完成 |
| `scripts/infra.sh` | 健壮性改进 | 完成 |
| `scripts/validate-env.sh` | 新增 | 完成 |

---

## 下一步

1. 使用 `./scripts/validate-env.sh` 验证环境
2. 使用 `--auto-port` 解决端口冲突
3. 执行 `./scripts/test-phased.sh 0 --verbose` 验证阶段0
4. 逐步测试其他阶段
