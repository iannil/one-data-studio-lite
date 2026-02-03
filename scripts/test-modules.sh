#!/usr/bin/env bash
# ONE-DATA-STUDIO-LITE - 模块测试脚本
# 用法: ./scripts/test-modules.sh [module] [--fast] [--full]

set -e

SCRIPT_DIR="$(cd "$(dirname "$0") && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 模块测试配置
declare -A MODULE_TESTS=(
    ["base"]="test_lifecycle/test_01_auth_init.py test_lifecycle/test_02_user_management.py test_lifecycle/test_03_role_management.py test_lifecycle/test_06_audit_logging.py"
    ["metadata"]="test_lifecycle/test_08_metadata_sync.py"
    ["integration"]="test_lifecycle/test_09_seatunnel_pipelines.py test_lifecycle/test_11_dolphinscheduler.py"
    ["processing"]="test_lifecycle/test_10_hop_etl.py test_lifecycle/test_17_ai_cleaning.py"
    ["bi"]="test_lifecycle/test_15_superset.py test_lifecycle/test_16_nl2sql.py"
    ["security"]="test_lifecycle/test_13_sensitive_detect.py"
)

declare -A MODULE_INTEGRATION_TESTS=(
    ["base"]="test_e2e/test_e2e_01_user_lifecycle.py"
    ["metadata"]="test_steward/test_metadata_management.py"
    ["integration"]="test_e2e/test_e2e_03_data_pipeline_flow.py"
    ["processing"]="test_engineer/test_cleaning_rules.py test_engineer/test_data_quality.py"
    ["bi"]="test_analyst/test_nl2sql.py test_analyst/test_data_explore.py"
    ["security"]="test_security/test_sensitive_scan.py test_security/test_detection_rules.py"
)

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[PASS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[FAIL]${NC} $1"; }

# 检查模块是否运行
check_module_running() {
    local module=$1
    local port=""

    case $module in
        base) port="8010" ;;
        metadata) port="8585" ;;
        integration) port="5802" ;;
        processing) port="8083" ;;
        bi) port="8088" ;;
        security) port="8015" ;;
    esac

    if [[ -n "$port" ]] && curl -s "http://localhost:${port}" &>/dev/null; then
        return 0
    fi
    return 1
}

# 等待模块就绪
wait_module_ready() {
    local module=$1
    local timeout=${2:-60}

    log_info "等待 $module 模块就绪..."

    local elapsed=0
    while [[ $elapsed -lt $timeout ]]; do
        if check_module_running "$module"; then
            log_success "$module 模块已就绪"
            return 0
        fi
        sleep 2
        ((elapsed += 2))
    done

    log_error "$module 模块未能在 ${timeout} 秒内就绪"
    return 1
}

# 运行单元测试
run_unit_tests() {
    local module=$1
    local tests=${MODULE_TESTS[$module]:-""}

    if [[ -z "$tests" ]]; then
        log_warn "模块 $module 没有配置单元测试"
        return 0
    fi

    log_info "=========================================="
    log_info "运行 $module 单元测试"
    log_info "=========================================="

    local failed=0
    for test_file in $tests; do
        local test_path="${PROJECT_ROOT}/tests/${test_file}"
        if [[ ! -f "$test_path" ]]; then
            log_warn "测试文件不存在: $test_path"
            continue
        fi

        log_info "运行: $test_file"
        if pytest "$test_path" -v --tb=short; then
            log_success "$test_file 通过"
        else
            log_error "$test_file 失败"
            ((failed++))
        fi
    done

    if [[ $failed -eq 0 ]]; then
        log_success "=========================================="
        log_success "$module 单元测试全部通过"
        log_success "=========================================="
        return 0
    else
        log_error "=========================================="
        log_error "$module 有 $failed 个测试失败"
        log_error "=========================================="
        return 1
    fi
}

# 运行集成测试
run_integration_tests() {
    local module=$1
    local tests=${MODULE_INTEGRATION_TESTS[$module]:-""}

    if [[ -z "$tests" ]]; then
        log_warn "模块 $module 没有配置集成测试"
        return 0
    fi

    log_info "=========================================="
    log_info "运行 $module 集成测试"
    log_info "=========================================="

    local failed=0
    for test_file in $tests; do
        local test_path="${PROJECT_ROOT}/tests/${test_file}"
        if [[ ! -f "$test_path" ]]; then
            log_warn "测试文件不存在: $test_path"
            continue
        fi

        log_info "运行: $test_file"
        if pytest "$test_path" -v --tb=short -m integration; then
            log_success "$test_file 通过"
        else
            log_error "$test_file 失败"
            ((failed++))
        fi
    done

    return $failed
}

# 快速验证（仅健康检查）
quick_verify() {
    local module=$1

    log_info "快速验证 $module 模块..."

    case $module in
        base)
            curl -s http://localhost:8010/health && echo " ✓ Portal" || echo " ✗ Portal"
            curl -s http://localhost:8016/health && echo " ✓ Audit Log" || echo " ✗ Audit Log"
            ;;
        metadata)
            curl -s http://localhost:8585/api/v1/system/version && echo " ✓ OpenMetadata" || echo " ✗ OpenMetadata"
            curl -s http://localhost:8013/health && echo " ✓ Metadata Sync" || echo " ✗ Metadata Sync"
            ;;
        integration)
            curl -s http://localhost:5802/hazelcast/rest/cluster && echo " ✓ SeaTunnel" || echo " ✗ SeaTunnel"
            curl -s http://localhost:12345 && echo " ✓ DolphinScheduler" || echo " ✗ DolphinScheduler"
            ;;
        processing)
            curl -s http://localhost:8083 && echo " ✓ Hop" || echo " ✗ Hop"
            curl -s http://localhost:8012/health && echo " ✓ AI Cleaning" || echo " ✗ AI Cleaning"
            ;;
        bi)
            curl -s http://localhost:8088/health && echo " ✓ Superset" || echo " ✗ Superset"
            curl -s http://localhost:8011/health && echo " ✓ NL2SQL" || echo " ✗ NL2SQL"
            ;;
        security)
            curl -s http://localhost:8015/health && echo " ✓ Sensitive Detect" || echo " ✗ Sensitive Detect"
            ;;
    esac
}

# 生成测试报告
generate_report() {
    local module=$1
    local result=$2

    local report_dir="${PROJECT_ROOT}/test-results/modules"
    mkdir -p "$report_dir"

    local timestamp=$(date +"%Y%m%d_%H%M%S")
    local report_file="${report_dir}/${module}_${timestamp}.txt"

    cat > "$report_file" << EOF
模块测试报告: $module
测试时间: $(date)
测试结果: $result

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

模块信息:
  模块名称: $module
  测试类型: 单元测试 + 集成测试

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

测试文件:
  单元测试: ${MODULE_TESTS[$module]:-无}
  集成测试: ${MODULE_INTEGRATION_TESTS[$module]:-无}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

环境信息:
  OS: $(uname -s)
  Python: $(python --version 2>&1)
  Docker: $(docker --version 2>&1)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EOF

    log_info "测试报告已生成: $report_file"
}

# 显示帮助
show_help() {
    cat << 'EOF'
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
         ONE-DATA-STUDIO-LITE 模块测试脚本
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

用法: ./scripts/test-modules.sh <command> [module] [options]

命令:
  test [module]      运行模块测试
  verify [module]    快速验证模块
  report [module]    生成测试报告
  list               列出所有模块的测试配置

模块:
  base            基础平台测试
  metadata        元数据管理测试
  integration     数据集成测试
  processing      数据加工测试
  bi              BI分析测试
  security        数据安全测试
  all             所有模块测试

选项:
  --fast           快速模式（仅健康检查）
  --full           完整模式（单元+集成测试）
  --wait           等待模块就绪
  --timeout=N      等待超时时间（秒）

示例:
  # 测试基础平台
  ./scripts/test-modules.sh test base

  # 快速验证
  ./scripts/test-modules.sh verify base --fast

  # 完整测试（包含集成测试）
  ./scripts/test-modules.sh test metadata --full

  # 等待模块就绪后测试
  ./scripts/test-modules.sh test integration --wait

  # 测试所有模块
  ./scripts/test-modules.sh test all

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EOF
}

# 主入口
main() {
    local cmd=${1:-help}
    shift || true

    local module=""
    local mode="unit"
    local wait_ready=false
    local timeout=60

    # 解析参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            --fast) mode="fast" ;;
            --full) mode="full" ;;
            --wait) wait_ready=true ;;
            --timeout=*) timeout="${1#*=}" ;;
            *)
                if [[ -z "$module" ]]; then
                    module="$1"
                fi
                ;;
        esac
        shift
    done

    case $cmd in
        test)
            if [[ -z "$module" ]]; then
                log_error "请指定要测试的模块"
                exit 1
            fi

            # 等待模块就绪
            if [[ "$wait_ready" == "true" ]]; then
                wait_module_ready "$module" "$timeout" || exit 1
            fi

            # 检查模块是否运行
            if ! check_module_running "$module"; then
                log_error "模块 $module 未运行，请先启动: ./scripts/modules.sh start $module"
                exit 1
            fi

            local result="PASS"

            # 运行测试
            if [[ "$mode" == "fast" ]]; then
                quick_verify "$module"
            else
                run_unit_tests "$module" || result="FAIL"
                if [[ "$mode" == "full" ]]; then
                    run_integration_tests "$module" || result="FAIL"
                fi
            fi

            generate_report "$module" "$result"

            if [[ "$result" == "FAIL" ]]; then
                exit 1
            fi
            ;;

        verify)
            if [[ -z "$module" ]]; then
                log_error "请指定要验证的模块"
                exit 1
            fi

            quick_verify "$module"
            ;;

        report)
            if [[ -z "$module" ]]; then
                log_error "请指定模块"
                exit 1
            fi
            generate_report "$module" "MANUAL"
            ;;

        list)
            echo ""
            echo "模块测试配置:"
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            printf "%-15s %-30s\n" "模块" "测试文件"
            echo "────────────────────────────────────────────────────────────"
            for m in base metadata integration processing bi security; do
                echo ""
                echo -e "${GREEN}$m${NC}"
                echo "  单元测试:"
                for t in ${MODULE_TESTS[$m]}; do
                    echo "    - $t"
                done
                echo "  集成测试:"
                for t in ${MODULE_INTEGRATION_TESTS[$m]}; do
                    echo "    - $t"
                done
            done
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            echo ""
            ;;

        help|-h|--help)
            show_help
            ;;

        *)
            log_error "未知命令: $cmd"
            show_help
            exit 1
            ;;
    esac
}

main "$@"
