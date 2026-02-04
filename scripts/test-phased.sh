#!/usr/bin/env bash
# ONE-DATA-STUDIO-LITE - 分阶段自动化测试脚本
# 用法: ./scripts/test-phased.sh [阶段...] [选项]

# 加载公共库
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/lib/common.sh"

# ============================================================
# 配置
# ============================================================
VERBOSE_OUTPUT="${VERBOSE_OUTPUT:-false}"
PROGRESS_DIR="${PROJECT_ROOT}/docs/progress"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
PROGRESS_FILE="${PROGRESS_DIR}/phased-testing-${TIMESTAMP}.md"

# 阶段定义
declare -a PHASE_NAME=(
    [0]="环境准备"
    [1]="系统基础"
    [2]="数据规划"
    [3]="数据汇聚"
    [4]="数据加工"
    [5]="数据分析"
    [6]="数据安全"
)

# 阶段内存需求（GB）
declare -a PHASE_MEMORY=(
    [0]=1    # 1GB - 基础设施
    [1]=2    # 2GB - +微服务
    [2]=5    # 5GB - +OpenMetadata
    [3]=10   # 10GB - +ETL平台
    [4]=2    # 2GB - 微服务(已在阶段1)
    [5]=5    # 5GB - +Superset
    [6]=2    # 2GB - 微服务(已在阶段1)
)

# 阶段等待时间（秒）
declare -a PHASE_WAIT=(
    [0]=15
    [1]=30
    [2]=60
    [3]=60
    [4]=30
    [5]=60
    [6]=30
)

# 阶段测试类型（映射到 test-lifecycle.sh）
declare -a PHASE_TEST_TYPE=(
    [1]="foundation"
    [2]="planning"
    [3]="collection"
    [4]="processing"
    [5]="analysis"
    [6]="security"
)

# 阶段服务配置（逗号分隔）
declare -a PHASE_SERVICES=(
    [0]="infra"
    [1]="infra,services"
    [2]="infra,services,openmetadata"
    [3]="infra,services,dolphinscheduler,seatunnel,hop"
    [4]="infra,services"
    [5]="infra,services,superset"
    [6]="infra,services"
)

# ============================================================
# 工具函数
# ============================================================

# 检查服务是否真正就绪
check_service_ready() {
    local url=$1
    local timeout=${2:-60}
    local elapsed=0

    if [[ "$VERBOSE_OUTPUT" == "true" ]]; then
        log_info "等待服务就绪: $url (超时 ${timeout}s)"
    fi

    while [[ $elapsed -lt $timeout ]]; do
        if curl -sf "$url" >/dev/null 2>&1; then
            if [[ "$VERBOSE_OUTPUT" == "true" ]]; then
                log_success "服务已就绪: $url"
            fi
            return 0
        fi
        sleep 3
        elapsed=$((elapsed + 3))
    done
    log_warn "服务未就绪: $url"
    return 1
}

# 检查容器是否运行
check_container_running() {
    local container_name=$1
    if docker ps --format '{{.Names}}' | grep -q "$container_name"; then
        return 0
    fi
    return 1
}

# 检查端口是否监听
check_port_listening() {
    local port=$1
    if lsof -i ":$port" >/dev/null 2>&1; then
        return 0
    fi
    return 1
}

# 等待阶段所需服务就绪
wait_phase_services_ready() {
    local phase=$1

    log_info "等待阶段 $phase 服务就绪..."

    case $phase in
        0)
            # 基础设施 - 检查容器运行
            local max_wait=60
            local elapsed=0
            while [[ $elapsed -lt $max_wait ]]; do
                local ready=true
                for container in ods-mysql ods-redis ods-minio; do
                    if ! check_container_running "$container"; then
                        ready=false
                        break
                    fi
                done
                if [[ "$ready" == "true" ]]; then
                    log_success "基础设施容器已就绪"
                    return 0
                fi
                sleep 3
                elapsed=$((elapsed + 3))
            done
            log_warn "基础设施容器未就绪"
            return 1
            ;;
        1)
            # 微服务 - 等待 Portal 健康检查
            if check_service_ready "http://localhost:8010/health" 90; then
                return 0
            fi
            return 1
            ;;
        2)
            # OpenMetadata
            if check_service_ready "http://localhost:8585/api/v1/system/version" 120; then
                return 0
            fi
            return 1
            ;;
        3)
            # ETL 平台 - 宽松检查（部分服务可能未启动）
            local has_service=false
            if check_service_ready "http://localhost:5802/hazelcast/rest/cluster" 60 2>/dev/null; then
                has_service=true
                log_success "SeaTunnel 已就绪"
            fi
            if check_service_ready "http://localhost:12345/dolphinscheduler/actuator/health" 60 2>/dev/null; then
                has_service=true
                log_success "DolphinScheduler 已就绪"
            fi
            if check_service_ready "http://localhost:8083/" 60 2>/dev/null; then
                has_service=true
                log_success "Hop 已就绪"
            fi
            # 至少一个服务就绪即可
            if [[ "$has_service" == "true" ]]; then
                return 0
            fi
            log_warn "ETL 平台服务未就绪"
            return 1
            ;;
        4)
            # 数据加工微服务
            check_service_ready "http://localhost:8012/health" 60 2>/dev/null || \
            check_service_ready "http://localhost:8015/health" 60 2>/dev/null || \
            check_service_ready "http://localhost:8013/health" 60 2>/dev/null
            return $?
            ;;
        5)
            # 数据分析 - NL2SQL/DataAPI/Superset
            check_service_ready "http://localhost:8011/health" 60 2>/dev/null || \
            check_service_ready "http://localhost:8014/health" 60 2>/dev/null || \
            check_service_ready "http://localhost:8088" 120 2>/dev/null
            return $?
            ;;
        6)
            # 数据安全 - 审计日志
            check_service_ready "http://localhost:8016/health" 60 2>/dev/null
            return $?
            ;;
    esac

    # 默认等待固定时间
    local wait_seconds=$(get_phase_wait $phase)
    if [[ $wait_seconds -gt 0 ]]; then
        log_info "等待服务稳定 (${wait_seconds}s)..."
        sleep "$wait_seconds"
    fi
    return 0
}

# 获取阶段名称
get_phase_name() {
    local phase=$1
    echo "${PHASE_NAME[$phase]:-Unknown}"
}

# 获取阶段内存需求
get_phase_memory() {
    local phase=$1
    echo "${PHASE_MEMORY[$phase]:-2}"
}

# 获取阶段等待时间
get_phase_wait() {
    local phase=$1
    echo "${PHASE_WAIT[$phase]:-30}"
}

# 获取阶段测试类型
get_phase_test_type() {
    local phase=$1
    echo "${PHASE_TEST_TYPE[$phase]:-}"
}

# 获取阶段服务列表
get_phase_services() {
    local phase=$1
    local services_str="${PHASE_SERVICES[$phase]:-}"

    # 将逗号分隔的字符串转为数组
    local IFS=','
    read -ra services <<< "$services_str"
    echo "${services[@]}"
}

# 检查端口是否被占用
check_port() {
    local port=$1
    if lsof -i ":$port" >/dev/null 2>&1; then
        return 0  # 端口被占用
    fi
    return 1  # 端口空闲
}

# 检查阶段所需端口
check_phase_ports() {
    local phase=$1

    # 定义各阶段需要的端口（使用可配置端口避免冲突）
    local mysql_port="${ODS_MYSQL_PORT:-13306}"
    local redis_port="${ODS_REDIS_PORT:-16379}"
    local minio_port="${ODS_MINIO_PORT:-19000}"
    local minio_console_port="${ODS_MINIO_CONSOLE_PORT:-19001}"

    local infra_ports=("$mysql_port" "$redis_port" "$minio_port" "$minio_console_port")  # MySQL, Redis, MinIO
    local services_ports=(8010 8011 8012 8013 8014 8015 8016)  # 微服务
    local platform_ports=(
        [openmetadata]=8585
        [superset]=8088
        [dolphinscheduler]=12345
        [seatunnel]=5802
        [hop]=8083
    )

    local ports_to_check=()
    local services=($(get_phase_services $phase))

    for svc in "${services[@]}"; do
        case $svc in
            infra)
                ports_to_check+=("${infra_ports[@]}")
                ;;
            services)
                ports_to_check+=("${services_ports[@]}")
                ;;
            openmetadata|superset|dolphinscheduler|seatunnel|hop)
                local port=${platform_ports[$svc]:-}
                [[ -n "$port" ]] && ports_to_check+=("$port")
                ;;
        esac
    done

    # 去重
    local unique_ports=($(printf "%s\n" "${ports_to_check[@]}" | sort -u))

    local occupied=()
    for port in "${unique_ports[@]}"; do
        if check_port "$port"; then
            occupied+=("$port")
        fi
    done

    if [[ ${#occupied[@]} -gt 0 ]]; then
        log_warn "以下端口被占用: ${occupied[*]}"
        log_info "占用端口的进程:"
        for port in "${occupied[@]}"; do
            local info=$(lsof -i ":$port" 2>/dev/null | head -2)
            echo "  端口 $port: $info"
        done
        return 1
    fi

    log_info "所有所需端口可用"
    return 0
}

# 自动选择可用端口
select_available_port() {
    local base_port=$1
    local fallback_ports=("$@")
    local max_attempts=10

    # 首先检查基础端口
    if ! check_port "$base_port"; then
        echo "$base_port"
        return 0
    fi

    # 尝试备用端口
    for fallback in "${fallback_ports[@]}"; do
        if ! check_port "$fallback"; then
            log_info "端口 $base_port 被占用，使用备用端口 $fallback"
            echo "$fallback"
            return 0
        fi
    done

    # 尝试动态端口
    for ((i=1; i<=max_attempts; i++)); do
        local test_port=$((base_port + i * 1000))
        if ! check_port "$test_port"; then
            log_info "端口 $base_port 被占用，使用动态端口 $test_port"
            echo "$test_port"
            return 0
        fi
    done

    log_error "无法为端口 $base_port 找到可用端口"
    return 1
}

# 自动配置所有端口
auto_configure_ports() {
    local mysql_fallbacks=(23306 33306 43306)
    local redis_fallbacks=(26379 36379 46379)
    local minio_fallbacks=(29000 39000 49000)
    local minio_console_fallbacks=(29001 39001 49001)

    export ODS_MYSQL_PORT=$(select_available_port "${ODS_MYSQL_PORT:-13306}" "${mysql_fallbacks[@]}")
    export ODS_REDIS_PORT=$(select_available_port "${ODS_REDIS_PORT:-16379}" "${redis_fallbacks[@]}")
    export ODS_MINIO_PORT=$(select_available_port "${ODS_MINIO_PORT:-19000}" "${minio_fallbacks[@]}")
    export ODS_MINIO_CONSOLE_PORT=$(select_available_port "${ODS_MINIO_CONSOLE_PORT:-19001}" "${minio_console_fallbacks[@]}")

    log_info "自动配置端口: MySQL=$ODS_MYSQL_PORT, Redis=$ODS_REDIS_PORT, MinIO=$ODS_MINIO_PORT"
}

# 获取可用内存（GB）
get_available_memory_gb() {
    if [[ "$(uname)" == "Darwin" ]]; then
        # macOS - 使用更可靠的方法
        # 获取物理内存总量和可用内存
        local mem_info=$(vm_stat)
        local page_size=4096  # 默认 4KB

        # 尝试获取实际的页大小（vm_stat 输出: "page size of 16384 bytes"）
        local ps_value=$(echo "$mem_info" | grep "page size" | awk '{for(i=1;i<=NF;i++) if($i~/^[0-9]+$/) print $i}')
        [[ -n "$ps_value" ]] && page_size=$ps_value

        # 获取可用页面 (free + inactive + speculative)
        local free=$(echo "$mem_info" | awk '/Pages free:/ {print $3}' | sed 's/\.//')
        local inactive=$(echo "$mem_info" | awk '/Pages inactive:/ {print $3}' | sed 's/\.//')
        local speculative=$(echo "$mem_info" | awk '/Pages speculative:/ {print $3}' | sed 's/\.//')

        # 确保是数字
        free=${free:-0}
        inactive=${inactive:-0}
        speculative=${speculative:-0}

        # 使用 awk 进行大数计算，避免 bash 整数溢出
        local total_gb=$(echo "$free $inactive $speculative $page_size" | \
            awk '{pages=$1+$2+$3; gb=pages*$4/1024/1024/1024; printf "%d", gb}')

        echo "$total_gb"
    else
        # Linux
        free -g | awk '/^Mem:/{print $7}'
    fi
}

# 检查内存是否足够
check_memory() {
    local required=$1

    # 如果设置了 SKIP_MEMORY_CHECK，直接返回成功
    if [[ "${SKIP_MEMORY_CHECK:-false}" == "true" ]]; then
        log_info "跳过内存检查"
        return 0
    fi

    local available=$(get_available_memory_gb)

    log_info "可用内存: ${available}GB, 需要: ${required}GB"

    if [[ $available -lt $required ]]; then
        log_warn "内存不足 (需要 ${required}GB, 可用 ${available}GB)"
        return 1
    fi
    return 0
}

# 启动指定服务
start_service() {
    local svc=$1
    local no_wait=${2:-false}
    local show_output="${SHOW_SERVICE_ERROR:-false}"

    case $svc in
        infra)
            log_step "启动基础设施..."
            if [[ "$show_output" == "true" ]]; then
                "${SCRIPT_DIR}/infra.sh" start 2>&1 || return 1
            else
                "${SCRIPT_DIR}/infra.sh" start >/dev/null 2>&1 || {
                    log_error "基础设施启动失败，使用 --show-errors 查看详情"
                    return 1
                }
            fi
            ;;
        services)
            log_step "启动微服务..."
            local wait_flag="--no-wait"
            [[ "$no_wait" == "false" ]] && wait_flag=""
            if [[ "$show_output" == "true" ]]; then
                "${SCRIPT_DIR}/services.sh" start $wait_flag 2>&1 || return 1
            else
                "${SCRIPT_DIR}/services.sh" start $wait_flag >/dev/null 2>&1 || {
                    log_error "微服务启动失败，使用 --show-errors 查看详情"
                    return 1
                }
            fi
            ;;
        openmetadata|superset|dolphinscheduler|seatunnel|hop)
            log_step "启动 $svc..."
            if [[ "$show_output" == "true" ]]; then
                "${SCRIPT_DIR}/platforms.sh" start "$svc" 2>&1 || true
            else
                "${SCRIPT_DIR}/platforms.sh" start "$svc" >/dev/null 2>&1 || true
            fi
            ;;
        *)
            log_warn "未知服务: $svc"
            return 1
            ;;
    esac
    return 0
}

# 启动阶段所需的所有服务
start_phase_services() {
    local phase=$1
    local services=($(get_phase_services $phase))

    log_info "阶段 $phase 需要服务: ${services[*]}"

    local started=()
    for svc in "${services[@]}"; do
        # 最后一个服务等待就绪，其他不等待
        local is_last="false"
        [[ "$svc" == "${services[$((${#services[@]} - 1))]}" ]] && is_last="true"

        start_service "$svc" "$is_last" || return 1
        started+=("$svc")
    done

    # 使用健康检查等待服务就绪
    wait_phase_services_ready $phase || {
        log_warn "服务健康检查未完全通过，但继续测试"
    }

    return 0
}

# 停止所有服务
stop_all_services() {
    log_step "清理所有服务..."
    "${SCRIPT_DIR}/platforms.sh" stop >/dev/null 2>&1 || true
    "${SCRIPT_DIR}/services.sh" stop >/dev/null 2>&1 || true
    "${SCRIPT_DIR}/infra.sh" stop -v >/dev/null 2>&1 || true

    # 等待容器完全停止
    sleep 10
}

# 停止平台服务
stop_platform_services() {
    "${SCRIPT_DIR}/platforms.sh" stop >/dev/null 2>&1 || true
    sleep 5
}

# 显示服务健康状态摘要
show_service_health_summary() {
    local phase=$1
    echo ""
    echo "=== 阶段 $phase 服务健康状态 ==="

    # 基础设施容器
    echo "基础设施:"
    for container in ods-mysql ods-redis ods-minio; do
        if check_container_running "$container"; then
            echo "  ✓ $container"
        else
            echo "  ✗ $container (未运行)"
        fi
    done

    # 微服务端口
    echo ""
    echo "微服务:"
    local services_ports=(
        "8010:Portal"
        "8011:NL2SQL"
        "8012:AI清洗"
        "8013:元数据同步"
        "8014:DataAPI"
        "8015:敏感检测"
        "8016:审计日志"
    )
    for sp in "${services_ports[@]}"; do
        local port="${sp%%:*}"
        local name="${sp##*:}"
        if check_port_listening "$port"; then
            echo "  ✓ $name (:$port)"
        else
            echo "  - $name (:$port) - 未监听"
        fi
    done

    # 平台服务
    echo ""
    echo "平台服务:"
    if check_port_listening "8585"; then
        echo "  ✓ OpenMetadata (:8585)"
    else
        echo "  - OpenMetadata (:8585) - 未监听"
    fi
    if check_port_listening "8088"; then
        echo "  ✓ Superset (:8088)"
    else
        echo "  - Superset (:8088) - 未监听"
    fi
    if check_port_listening "12345"; then
        echo "  ✓ DolphinScheduler (:12345)"
    else
        echo "  - DolphinScheduler (:12345) - 未监听"
    fi
    if check_port_listening "5802"; then
        echo "  ✓ SeaTunnel (:5802)"
    else
        echo "  - SeaTunnel (:5802) - 未监听"
    fi
    if check_port_listening "8083"; then
        echo "  ✓ Hop (:8083)"
    else
        echo "  - Hop (:8083) - 未监听"
    fi
    echo ""
}

# 记录测试结果到进度文件
record_result() {
    local phase=$1
    local bash_result=$2
    local py_result=$3
    local overall=$4
    local phase_name=$(get_phase_name $phase)
    local status="通过"
    [[ $overall -ne 0 ]] && status="失败"

    {
        echo "## 阶段 ${phase}: ${phase_name} - ${status}"
        echo "- 时间: $(date '+%Y-%m-%d %H:%M:%S')"
        echo "- Bash 测试: $([[ $bash_result -eq 0 ]] && echo '✓ 通过' || echo '✗ 失败')"
        # py_result 为空字符串表示跳过，数字表示执行结果
        if [[ -z "$py_result" ]]; then
            echo "- Python 测试: - 跳过"
        else
            echo "- Python 测试: $([[ $py_result -eq 0 ]] && echo '✓ 通过' || echo '✗ 失败')"
        fi
        echo ""
    } >> "$PROGRESS_FILE"
}

# 运行阶段测试
run_phase_tests() {
    local phase=$1
    local phase_name=$(get_phase_name $phase)
    local run_python="${RUN_PYTHON:-false}"
    local skip_port_check="${SKIP_PORT_CHECK:-false}"

    log_section "阶段 ${phase}: ${phase_name}"

    # 1. 检查内存
    local required_memory=$(get_phase_memory $phase)
    if ! check_memory $required_memory; then
        log_error "内存不足，跳过阶段 ${phase}"
        record_result $phase 1 "" 1
        return 1
    fi

    # 1.5. 检查端口
    if [[ "$skip_port_check" != "true" ]]; then
        if ! check_phase_ports $phase; then
            log_error "端口检查失败，使用 --skip-port-check 跳过"
            record_result $phase 1 "" 1
            return 1
        fi
    fi

    # 2. 启动服务
    log_step "启动阶段 ${phase} 所需服务..."
    if ! start_phase_services $phase; then
        log_error "服务启动失败"
        stop_all_services
        record_result $phase 1 "" 1
        return 1
    fi
    log_success "服务已启动"

    # 2.5. 显示服务健康摘要（verbose 模式）
    if [[ "$VERBOSE_OUTPUT" == "true" ]]; then
        show_service_health_summary $phase
    fi

    # 3. 运行 Bash 测试（阶段0仅验证启动，不运行测试）
    local bash_result=0
    if [[ $phase -gt 0 ]]; then
        local test_type=$(get_phase_test_type $phase)
        if [[ -n "$test_type" ]]; then
            log_step "执行 Bash 测试 (${test_type})..."
            if [[ "$VERBOSE_OUTPUT" == "true" ]]; then
                "${SCRIPT_DIR}/test-lifecycle.sh" "$test_type" 2>&1 || bash_result=1
            else
                "${SCRIPT_DIR}/test-lifecycle.sh" "$test_type" >/dev/null 2>&1 || bash_result=1
            fi
            if [[ $bash_result -eq 0 ]]; then
                log_success "Bash 测试通过"
            else
                log_warn "Bash 测试有失败"
            fi
        fi
    else
        log_info "阶段0: 验证服务启动完成"
        # 检查基础设施服务
        if docker ps | grep -q "ods-mysql"; then
            log_success "MySQL 运行正常"
        else
            log_warn "MySQL 未运行"
            bash_result=1
        fi
        if docker ps | grep -q "ods-redis"; then
            log_success "Redis 运行正常"
        else
            log_warn "Redis 未运行"
            bash_result=1
        fi
        if docker ps | grep -q "ods-minio"; then
            log_success "MinIO 运行正常"
        else
            log_warn "MinIO 未运行"
            bash_result=1
        fi
    fi

    # 4. 运行 Python 测试（可选）
    local py_result=""  # 空字符串表示跳过
    if [[ $phase -gt 0 && "$run_python" == "true" ]]; then
        log_step "执行 Python 测试..."
        if command -v pytest >/dev/null 2>&1; then
            local test_pattern="tests/test_lifecycle/test_lf_0${phase}_*.py"
            # 处理阶段 10+ 的情况（目前没有，但预留）
            if [[ $phase -ge 10 ]]; then
                test_pattern="tests/test_lifecycle/test_lf_${phase}_*.py"
            fi

            cd "$PROJECT_ROOT"
            if [[ "$VERBOSE_OUTPUT" == "true" ]]; then
                pytest "$test_pattern" -v --tb=short 2>&1 || py_result=1
            else
                pytest "$test_pattern" -v --tb=short -q >/dev/null 2>&1 || py_result=1
            fi

            if [[ ${py_result:-1} -eq 0 ]]; then
                log_success "Python 测试通过"
            else
                log_warn "Python 测试有失败"
            fi
        else
            log_info "pytest 未安装，跳过 Python 测试"
        fi
    else
        if [[ $phase -gt 0 ]]; then
            log_info "Python 测试未启用，使用 --python 启用"
        fi
    fi

    # 5. 记录结果
    local overall=0
    # py_result 为空时不算失败（跳过）
    [[ $bash_result -ne 0 ]] && overall=1
    [[ -n "$py_result" && $py_result -ne 0 ]] && overall=1
    record_result $phase $bash_result "$py_result" $overall

    # 6. 清理
    log_step "清理服务..."
    stop_all_services

    return $overall
}

# ============================================================
# 诊断函数
# ============================================================
show_diagnostic_info() {
    show_header "test-phased.sh" "环境诊断信息"

    echo ""
    echo "=== 系统信息 ==="
    echo "操作系统: $(uname -s) $(uname -r) $(uname -m)"
    echo "主机名: $(hostname)"
    echo "当前目录: $(pwd)"
    echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"

    echo ""
    echo "=== Docker 状态 ==="
    if command -v docker >/dev/null 2>&1; then
        echo "Docker 版本: $(docker --version 2>&1)"
        echo "Docker 状态: $(docker info >/dev/null 2>&1 && echo '运行中' || echo '未运行')"

        echo ""
        echo "运行中的容器:"
        local running_containers=$(docker ps --format "{{.Names}} ({{.Status}})" 2>/dev/null | wc -l | tr -d ' ')
        if [[ "$running_containers" -gt 0 ]]; then
            docker ps --format "  {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null | head -20
        else
            echo "  无运行中的容器"
        fi

        echo ""
        echo "ODS 相关容器:"
        local ods_containers=$(docker ps -a --format "{{.Names}}" 2>/dev/null | grep -c "^ods-" || echo 0)
        if [[ "$ods_containers" -gt 0 ]]; then
            docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null | grep "ods-"
        else
            echo "  无 ODS 容器"
        fi
    else
        echo "Docker: 未安装"
    fi

    echo ""
    echo "=== 内存信息 ==="
    if [[ "$(uname)" == "Darwin" ]]; then
        local mem_info=$(vm_stat)
        local page_size=4096

        # 检测实际页大小
        local ps_value=$(echo "$mem_info" | grep "page size" | awk '{for(i=1;i<=NF;i++) if($i~/^[0-9]+$/) print $i}')
        [[ -n "$ps_value" ]] && page_size=$ps_value

        local free=$(echo "$mem_info" | awk '/Pages free:/ {print $3}' | sed 's/\.//')
        local inactive=$(echo "$mem_info" | awk '/Pages inactive:/ {print $3}' | sed 's/\.//')
        local speculative=$(echo "$mem_info" | awk '/Pages speculative:/ {print $3}' | sed 's/\.//')
        local wired=$(echo "$mem_info" | awk '/Pages wired:/ {print $3}' | sed 's/\.//')
        local active=$(echo "$mem_info" | awk '/Pages active:/ {print $3}' | sed 's/\.//')

        free=${free:-0}
        inactive=${inactive:-0}
        speculative=${speculative:-0}
        wired=${wired:-0}
        active=${active:-0}

        # 使用 awk 进行大数计算
        local total_gb=$(echo "$free $inactive $speculative $wired $active $page_size" | \
            awk '{pages=$1+$2+$3+$4+$5; gb=pages*$6/1024/1024/1024; printf "%d", gb}')
        local available_gb=$(echo "$free $inactive $speculative $page_size" | \
            awk '{pages=$1+$2+$3; gb=pages*$4/1024/1024/1024; printf "%d", gb}')

        echo "总内存: ${total_gb}GB"
        echo "可用内存: ${available_gb}GB"
        echo "  - 空闲: $(echo "$free $page_size" | awk '{printf "%d", $1*$2/1024/1024/1024}')GB"
        echo "  - 非活跃: $(echo "$inactive $page_size" | awk '{printf "%d", $1*$2/1024/1024/1024}')GB"
        echo "  - 可回收: $(echo "$speculative $page_size" | awk '{printf "%d", $1*$2/1024/1024/1024}')GB"
    else
        free -h 2>/dev/null || echo "无法获取内存信息"
    fi

    echo ""
    echo "=== 端口占用情况 ==="
    local ports=(13306 16379 19000 19001 8010 8011 8012 8013 8014 8015 8016 8585 8088 12345 5802 8083)
    for port in "${ports[@]}"; do
        local status="空闲"
        local process=""
        if lsof -i ":$port" >/dev/null 2>&1; then
            status="占用"
            process=$(lsof -i ":$port" 2>/dev/null | tail -1 | awk '{print $1}' || echo "")
        fi
        printf "  端口 %-6s %-6s" "$port" "$status"
        [[ -n "$process" ]] && echo " [$process]" || echo ""
    done

    echo ""
    echo "=== 网络状态 ==="
    if docker network ls 2>/dev/null | grep -q "ods-network"; then
        echo "ods-network: 存在"
        docker network inspect ods-network --format '{{range .Containers}}{{.Name}} {{end}}' 2>/dev/null | \
            awk '{for(i=1;i<=NF;i++) printf "  - %s\n", $i}'
    else
        echo "ods-network: 不存在"
    fi

    echo ""
    echo "=== 磁盘空间 ==="
    df -h /var/lib/docker 2>/dev/null || df -h ~ 2>/dev/null || echo "无法获取磁盘信息"

    echo ""
    echo "=== 环境变量 ==="
    echo "ODS_MYSQL_PORT=${ODS_MYSQL_PORT:-13306 (默认)}"
    echo "ODS_REDIS_PORT=${ODS_REDIS_PORT:-16379 (默认)}"
    echo "ODS_MINIO_PORT=${ODS_MINIO_PORT:-19000 (默认)}"
    echo "ODS_MINIO_CONSOLE_PORT=${ODS_MINIO_CONSOLE_PORT:-19001 (默认)}"
    echo "SKIP_MEMORY_CHECK=${SKIP_MEMORY_CHECK:-false}"
    echo "SKIP_PORT_CHECK=${SKIP_PORT_CHECK:-false}"
    echo "RUN_PYTHON=${RUN_PYTHON:-false}"

    echo ""
    echo "=== 建议修复 ==="
    local issues=()

    # 检查 Docker
    if ! command -v docker >/dev/null 2>&1; then
        issues+=("Docker 未安装，请先安装 Docker Desktop 或 Docker Engine")
    elif ! docker info >/dev/null 2>&1; then
        issues+=("Docker 未运行，请启动 Docker")
    fi

    # 检查内存
    local available_mem=$(get_available_memory_gb)
    if [[ $available_mem -lt 1 ]]; then
        issues+=("可用内存不足 1GB，建议关闭其他应用")
    fi

    # 检查端口
    local conflict_ports=()
    for port in 13306 16379 19000; do
        if lsof -i ":$port" >/dev/null 2>&1; then
            conflict_ports+=("$port")
        fi
    done
    if [[ ${#conflict_ports[@]} -gt 0 ]]; then
        issues+=("端口冲突: ${conflict_ports[*]}，使用 --auto-port 自动选择端口")
    fi

    if [[ ${#issues[@]} -eq 0 ]]; then
        echo "  环境正常，可以开始测试"
    else
        for issue in "${issues[@]}"; do
            echo "  - $issue"
        done
    fi

    echo ""
}

# ============================================================
# 帮助信息
# ============================================================
show_help() {
    show_header "test-phased.sh" "分阶段自动化测试脚本"

    cat << 'EOF'
用法: ./scripts/test-phased.sh [选项] [阶段...]

阶段:
  0    环境准备（基础设施: MySQL, Redis, MinIO）
  1    系统基础（认证、微服务）
  2    数据规划（OpenMetadata 元数据管理）
  3    数据汇聚（ETL平台: SeaTunnel, DolphinScheduler, Hop）
  4    数据加工（AI清洗、敏感检测、元数据同步）
  5    数据分析（Superset BI、NL2SQL）
  6    数据安全（审计、权限）

选项:
  --python, -p       运行 Python 测试
  --verbose, -v      显示详细测试输出
  --auto-continue    失败后自动继续
  --no-cleanup       测试后不清理服务
  --auto-port        自动选择可用端口（当默认端口被占用时）
  --diagnose         输出详细诊断信息（不运行测试）
  --skip-memory-check 跳过内存检查
  --skip-port-check  跳过端口检查
  --show-errors      显示服务启动详细错误
  --help, -h         显示此帮助

默认执行顺序（按内存峰值优化）: 0 1 4 6 2 5 3

示例:
  ./scripts/test-phased.sh              # 默认顺序执行所有阶段
  ./scripts/test-phased.sh 0 1 2        # 只执行指定阶段
  ./scripts/test-phased.sh --python     # 包含 Python 测试
  ./scripts/test-phased.sh -p --auto-continue  # 自动继续
  ./scripts/test-phased.sh --auto-port         # 自动选择可用端口
  ./scripts/test-phased.sh --diagnose          # 输出诊断信息
  ./scripts/test-phased.sh --no-cleanup        # 保留服务用于调试
  ./scripts/test-phased.sh --skip-memory-check # 跳过内存检查
  ./scripts/test-phased.sh --skip-port-check  # 跳过端口检查
  ./scripts/test-phased.sh --show-errors      # 显示服务启动详细错误
  ./scripts/test-phased.sh --verbose          # 显示测试详细输出

内存需求:
  阶段 0: 1GB   阶段 1: 2GB   阶段 2: 5GB   阶段 3: 10GB
  阶段 4: 2GB   阶段 5: 5GB   阶段 6: 2GB

EOF
}

# ============================================================
# 主入口
# ============================================================
main() {
    local phases=()
    local auto_continue=false
    local no_cleanup=false
    local skip_memory_check=false
    local skip_port_check=false
    local show_errors=false
    local verbose=false
    local auto_port=false
    local diagnose_only=false

    # 默认执行顺序（按内存峰值优化：先运行低内存阶段）
    local default_phases=(0 1 4 6 2 5 3)

    # 解析参数
    while [[ $# -gt 0 ]]; do
        case "$1" in
            0|1|2|3|4|5|6)
                phases+=("$1")
                ;;
            --python|-p)
                export RUN_PYTHON=true
                ;;
            --verbose|-v)
                verbose=true
                export VERBOSE_OUTPUT=true
                ;;
            --auto-continue)
                auto_continue=true
                export AUTO_CONTINUE=true
                ;;
            --no-cleanup)
                no_cleanup=true
                export NO_CLEANUP=true
                ;;
            --skip-memory-check)
                skip_memory_check=true
                export SKIP_MEMORY_CHECK=true
                ;;
            --skip-port-check)
                skip_port_check=true
                export SKIP_PORT_CHECK=true
                ;;
            --show-errors)
                show_errors=true
                export SHOW_SERVICE_ERROR=true
                ;;
            --auto-port)
                auto_port=true
                export AUTO_PORT=true
                ;;
            --diagnose)
                diagnose_only=true
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            *)
                log_error "未知参数: $1"
                show_help
                exit 1
                ;;
        esac
        shift
    done

    # 诊断模式
    if [[ "$diagnose_only" == "true" ]]; then
        show_diagnostic_info
        exit 0
    fi

    # 自动端口配置
    if [[ "$auto_port" == "true" ]]; then
        log_info "自动配置端口..."
        auto_configure_ports || {
            log_error "自动端口配置失败"
            exit 1
        }
    fi

    # 如果未指定阶段，使用默认顺序
    if [[ ${#phases[@]} -eq 0 ]]; then
        phases=("${default_phases[@]}")
    fi

    # 创建进度目录
    mkdir -p "$PROGRESS_DIR"

    # 创建进度文件
    {
        echo "# 分阶段测试报告"
        echo ""
        echo "**测试时间**: $(date '+%Y-%m-%d %H:%M:%S')"
        echo "**系统**: $(uname -s) $(uname -m)"
        echo "**总内存**: $(free -h 2>/dev/null || echo 'N/A')"
        echo ""
        echo "## 测试配置"
        echo "- Python 测试: $([ "${RUN_PYTHON:-false}" == "true" ] && echo '启用' || echo '禁用')"
        echo "- 详细输出: $([ "$verbose" == "true" ] && echo '启用' || echo '禁用')"
        echo "- 自动继续: $([ "$auto_continue" == "true" ] && echo '启用' || echo '禁用')"
        echo "- 自动端口: $([ "$auto_port" == "true" ] && echo '启用' || echo '禁用')"
        echo "- 测试后清理: $([ "$no_cleanup" == "true" ] && echo '禁用' || echo '启用')"
        echo "- 内存检查: $([ "$skip_memory_check" == "true" ] && echo '禁用' || echo '启用')"
        echo "- 端口检查: $([ "$skip_port_check" == "true" ] && echo '禁用' || echo '启用')"
        echo "- 显示错误: $([ "$show_errors" == "true" ] && echo '启用' || echo '禁用')"
        if [[ "$auto_port" == "true" ]]; then
            echo "- MySQL 端口: ${ODS_MYSQL_PORT:-13306}"
            echo "- Redis 端口: ${ODS_REDIS_PORT:-16379}"
            echo "- MinIO 端口: ${ODS_MINIO_PORT:-19000}"
        fi
        echo ""
        echo "## 阶段详情"
        echo ""
    } > "$PROGRESS_FILE"

    show_header "分阶段自动化测试" "自动化测试"
    log_info "进度文件: $PROGRESS_FILE"
    log_info "计划阶段: ${phases[*]}"

    local passed=0
    local failed=0
    local skipped=0

    for phase in "${phases[@]}"; do
        # 如果设置了 NO_CLEANUP 且不是第一个阶段，先清理
        if [[ "$no_cleanup" == "true" && $phase -ne 0 ]]; then
            log_info "跳过清理，继续使用现有服务..."
        fi

        if run_phase_tests $phase; then
            ((passed++))
        else
            ((failed++))
            if [[ "$auto_continue" != "true" ]]; then
                # 询问是否继续
                echo ""
                read -p "阶段 $phase 失败，是否继续? (y/n) " -n 1 -r
                echo ""
                if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                    log_info "测试中断"
                    break
                fi
            fi
        fi
    done

    # 如果设置了不清理，显示服务状态
    if [[ "$no_cleanup" == "true" ]]; then
        log_section "保留服务状态"
        "${SCRIPT_DIR}/infra.sh" status 2>/dev/null || true
        "${SCRIPT_DIR}/services.sh" status 2>/dev/null || true
        "${SCRIPT_DIR}/platforms.sh" status 2>/dev/null || true
        log_info "使用以下命令手动清理:"
        echo "  ./scripts/infra.sh stop -v"
        echo "  ./scripts/services.sh stop"
        echo "  ./scripts/platforms.sh stop"
    fi

    # 汇总
    {
        echo "## 测试汇总"
        echo "- 通过阶段: $passed"
        echo "- 失败阶段: $failed"
        echo "- 完成时间: $(date '+%Y-%m-%d %H:%M:%S')"
    } >> "$PROGRESS_FILE"

    log_section "测试完成"
    log_info "通过: $passed, 失败: $failed"
    log_info "进度文件: $PROGRESS_FILE"

    [[ $failed -eq 0 ]] && exit 0 || exit 1
}

main "$@"
