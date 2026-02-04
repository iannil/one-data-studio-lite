#!/usr/bin/env bash
# ONE-DATA-STUDIO-LITE - 测试环境验证脚本
# 用法: ./scripts/validate-env.sh

# 加载公共库
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/lib/common.sh"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 问题计数器
ISSUES=0
WARNINGS=0

# 检查函数
check_pass() {
    echo -e "${GREEN}✓${NC} $1"
}

check_fail() {
    echo -e "${RED}✗${NC} $1"
    ((ISSUES++))
}

check_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
    ((WARNINGS++))
}

# ============================================================
# 主验证逻辑
# ============================================================

main() {
    show_header "validate-env.sh" "测试环境验证"

    echo ""
    echo "=== 系统信息 ==="
    echo "操作系统: $(uname -s) $(uname -r) $(uname -m)"
    echo "主机名: $(hostname)"
    echo "当前目录: $(pwd)"
    echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"

    echo ""
    echo "=== Docker 检查 ==="

    # 检查 Docker 是否安装
    if command -v docker >/dev/null 2>&1; then
        check_pass "Docker 已安装: $(docker --version 2>&1)"
    else
        check_fail "Docker 未安装"
        echo "  修复建议: 安装 Docker Desktop (macOS/Windows) 或 Docker Engine (Linux)"
    fi

    # 检查 Docker 是否运行
    if docker info >/dev/null 2>&1; then
        check_pass "Docker 服务运行中"
    else
        check_fail "Docker 服务未运行"
        echo "  修复建议: 启动 Docker Desktop 或 Docker 服务"
    fi

    # 检查 Docker Compose
    if docker compose version >/dev/null 2>&1; then
        check_pass "Docker Compose 可用: $(docker compose version 2>&1 | head -1)"
    else
        check_fail "Docker Compose 不可用"
        echo "  修复建议: 升级 Docker 到支持 compose 的版本"
    fi

    echo ""
    echo "=== 内存检查 ==="

    # 获取可用内存
    if [[ "$(uname)" == "Darwin" ]]; then
        local mem_info=$(vm_stat)
        local page_size=4096

        # 检测实际页大小
        local ps_value=$(echo "$mem_info" | grep "page size" | awk '{for(i=1;i<=NF;i++) if($i~/^[0-9]+$/) print $i}')
        [[ -n "$ps_value" ]] && page_size=$ps_value

        local free=$(echo "$mem_info" | awk '/Pages free:/ {print $3}' | sed 's/\.//')
        local inactive=$(echo "$mem_info" | awk '/Pages inactive:/ {print $3}' | sed 's/\.//')
        local speculative=$(echo "$mem_info" | awk '/Pages speculative:/ {print $3}' | sed 's/\.//')

        free=${free:-0}
        inactive=${inactive:-0}
        speculative=${speculative:-0}

        # 使用 awk 避免整数溢出
        local available_gb=$(echo "$free $inactive $speculative $page_size" | \
            awk '{pages=$1+$2+$3; gb=pages*$4/1024/1024/1024; printf "%d", gb}')
    else
        local available_gb=$(free -g | awk '/^Mem:/{print $7}')
    fi

    echo "  可用内存: ${available_gb}GB"

    if [[ $available_gb -ge 10 ]]; then
        check_pass "内存充足 (>= 10GB)"
    elif [[ $available_gb -ge 5 ]]; then
        check_warn "内存一般 (>= 5GB)，部分阶段可能受影响"
        echo "  修复建议: 关闭其他应用以释放内存"
    elif [[ $available_gb -ge 1 ]]; then
        check_warn "内存紧张 (>= 1GB)，部分阶段无法运行"
        echo "  修复建议: 使用 --skip-memory-check 跳过检查，或关闭其他应用"
    else
        check_fail "内存不足 (< 1GB)"
        echo "  修复建议: 关闭其他应用或使用 --skip-memory-check 强制测试"
    fi

    echo ""
    echo "=== 端口检查 ==="

    # 定义需要检查的端口
    declare -A PORT_DESCRIPTIONS=(
        [13306]="MySQL 数据库"
        [16379]="Redis 缓存"
        [19000]="MinIO API"
        [19001]="MinIO 控制台"
        [8010]="Portal 服务"
        [8011]="NL2SQL 服务"
        [8012]="AI 清洗服务"
        [8013]="元数据同步服务"
        [8014]="Data API 服务"
        [8015]="敏感检测服务"
        [8016]="审计日志服务"
        [8585]="OpenMetadata"
        [8088]="Superset"
        [12345]="DolphinScheduler"
        [5802]="SeaTunnel"
        [8083]="Hop"
    )

    local occupied_ports=()
    for port in "${!PORT_DESCRIPTIONS[@]}"; do
        local desc="${PORT_DESCRIPTIONS[$port]}"
        if lsof -i ":$port" >/dev/null 2>&1; then
            local process=$(lsof -i ":$port" 2>/dev/null | tail -1 | awk '{print $1}' || echo "")
            check_fail "端口 $port ($desc) 被占用 [进程: $process]"
            occupied_ports+=("$port")
        else
            check_pass "端口 $port ($desc) 可用"
        fi
    done

    if [[ ${#occupied_ports[@]} -gt 0 ]]; then
        echo ""
        echo "  端口冲突修复建议:"
        echo "  1. 使用 --auto-port 自动选择可用端口"
        echo "  2. 使用 --skip-port-check 跳过端口检查"
        echo "  3. 通过环境变量自定义端口:"
        echo "     export ODS_MYSQL_PORT=23306"
        echo "     export ODS_REDIS_PORT=26379"
        echo "     export ODS_MINIO_PORT=29000"
        echo "  4. 停止占用端口的进程"
    fi

    echo ""
    echo "=== 网络检查 ==="

    # 检查 ods-network
    if docker network ls 2>/dev/null | grep -q "ods-network"; then
        check_pass "Docker 网络 ods-network 存在"
        local network_containers=$(docker network inspect ods-network --format '{{len .Containers}}' 2>/dev/null || echo 0)
        echo "  连接的容器数: $network_containers"
    else
        check_warn "Docker 网络 ods-network 不存在（将在首次启动时创建）"
    fi

    echo ""
    echo "=== 磁盘空间检查 ==="

    # 检查 Docker 数据目录
    local docker_dir="/var/lib/docker"
    if [[ "$(uname)" == "Darwin" ]]; then
        # macOS 上 Docker Desktop 使用虚拟机
        docker_dir=$(docker system info 2>/dev/null | grep "Docker Root Dir" | awk '{print $4}' || echo "/")
    fi

    local disk_info=$(df -h "$docker_dir" 2>/dev/null || df -h ~ 2>/dev/null)
    local available_gb=$(echo "$disk_info" | awk 'NR==2 {print $4}' | sed 's/G//')
    local used_percent=$(echo "$disk_info" | awk 'NR==2 {print $5}' | sed 's/%//')

    echo "  可用磁盘空间: ${available_gb}GB (已用 ${used_percent}%)"

    if [[ ${available_gb%G} -ge 20 ]]; then
        check_pass "磁盘空间充足 (>= 20GB)"
    elif [[ ${available_gb%G} -ge 10 ]]; then
        check_warn "磁盘空间一般 (>= 10GB)"
    else
        check_fail "磁盘空间不足 (< 10GB)"
        echo "  修复建议: 清理 Docker 资源: docker system prune -a"
    fi

    echo ""
    echo "=== ODS 容器检查 ==="

    local ods_containers=$(docker ps -a --format "{{.Names}}" 2>/dev/null | grep "^ods-" || echo "")
    if [[ -z "$ods_containers" ]]; then
        check_pass "无遗留 ODS 容器"
    else
        check_warn "发现遗留 ODS 容器"
        echo "  遗留容器:"
        echo "$ods_containers" | while read container; do
            local status=$(docker inspect "$container" --format '{{.State.Status}}' 2>/dev/null || echo "unknown")
            echo "    - $container ($status)"
        done
        echo "  清理命令: docker rm -f $(echo "$ods_containers" | tr '\n' ' ')"
    fi

    echo ""
    echo "=== 脚本检查 ==="

    local required_scripts=(
        "scripts/lib/common.sh"
        "scripts/infra.sh"
        "scripts/services.sh"
        "scripts/platforms.sh"
        "scripts/test-phased.sh"
    )

    for script in "${required_scripts[@]}"; do
        if [[ -f "${PROJECT_ROOT}/${script}" ]]; then
            check_pass "脚本存在: $script"
        else
            check_fail "脚本缺失: $script"
        fi
    done

    echo ""
    echo "=== 测试工具检查 ==="

    if command -v pytest >/dev/null 2>&1; then
        check_pass "pytest 已安装: $(pytest --version 2>&1 | head -1)"
    else
        check_warn "pytest 未安装（Python 测试将跳过）"
        echo "  安装命令: pip install pytest pytest-asyncio"
    fi

    if command -v lsof >/dev/null 2>&1; then
        check_pass "lsof 可用"
    else
        check_fail "lsof 不可用（端口检查需要）"
    fi

    echo ""
    echo "=== 汇总 ==="

    if [[ $ISSUES -eq 0 && $WARNINGS -eq 0 ]]; then
        echo -e "${GREEN}所有检查通过！${NC}"
        echo "可以开始测试: ./scripts/test-phased.sh"
        return 0
    elif [[ $ISSUES -eq 0 ]]; then
        echo -e "${YELLOW}发现 $WARNINGS 个警告，但可以测试${NC}"
        echo "建议: ./scripts/test-phased.sh --auto-port --skip-memory-check"
        return 0
    else
        echo -e "${RED}发现 $ISSUES 个错误，$WARNINGS 个警告${NC}"
        echo ""
        echo "快速修复建议:"
        if [[ $ISSUES -gt 0 ]]; then
            echo "  1. 如果 Docker 未运行，先启动 Docker"
            echo "  2. 如果端口冲突，使用: ./scripts/test-phased.sh --auto-port"
            echo "  3. 如果内存不足，关闭其他应用或使用: --skip-memory-check"
        fi
        return 1
    fi
}

main "$@"
