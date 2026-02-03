#!/usr/bin/env bash
# ONE-DATA-STUDIO-LITE - 生命周期测试脚本
# 按数据生命周期顺序测试系统功能
# 用法: ./scripts/test-lifecycle.sh [all|foundation|planning|collection|processing|analysis|security]

# 加载公共库
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/lib/common.sh"

# 配置
PORTAL_URL="http://localhost:8010"
OPENMETADATA_URL="http://localhost:8585"
SUPERSET_URL="http://localhost:8088"

# 测试结果
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0
declare -a FAILED_TEST_NAMES=()

# ============================================================
# 测试辅助函数
# ============================================================

test_case() {
    local name="$1"
    local result="$2"  # 0=pass, 1=fail

    TOTAL_TESTS=$((TOTAL_TESTS + 1))

    if [[ "$result" -eq 0 ]]; then
        PASSED_TESTS=$((PASSED_TESTS + 1))
        echo -e "  ${GREEN}✓${NC} $name"
    else
        FAILED_TESTS=$((FAILED_TESTS + 1))
        FAILED_TEST_NAMES+=("$name")
        echo -e "  ${RED}✗${NC} $name"
    fi
}

get_admin_token() {
    local resp
    resp=$(curl -sf -X POST "$PORTAL_URL/auth/login" \
        -H "Content-Type: application/json" \
        -d '{"username":"admin","password":"admin123"}' 2>/dev/null)

    echo "$resp" | grep -o '"token":"[^"]*"' | cut -d'"' -f4
}

api_get() {
    local url="$1"
    local token="$2"

    curl -sf -X GET "$url" \
        -H "Authorization: Bearer $token" \
        -H "Content-Type: application/json" 2>/dev/null
}

api_post() {
    local url="$1"
    local token="$2"
    local data="$3"

    curl -sf -X POST "$url" \
        -H "Authorization: Bearer $token" \
        -H "Content-Type: application/json" \
        -d "$data" 2>/dev/null
}

# ============================================================
# 阶段 1: 系统基础 (Foundation)
# ============================================================

test_foundation() {
    log_section "阶段 1: 系统基础测试"

    echo "1.1 认证系统测试"

    # 测试登录
    local login_resp
    login_resp=$(curl -sf -X POST "$PORTAL_URL/auth/login" \
        -H "Content-Type: application/json" \
        -d '{"username":"admin","password":"admin123"}' 2>/dev/null)

    if echo "$login_resp" | grep -q '"success":true'; then
        test_case "管理员登录" 0
    else
        test_case "管理员登录" 1
    fi

    # 获取 Token
    local token
    token=$(echo "$login_resp" | grep -o '"token":"[^"]*"' | cut -d'"' -f4)

    # 测试 Token 验证
    local validate_resp
    validate_resp=$(curl -sf "$PORTAL_URL/auth/validate" \
        -H "Authorization: Bearer $token" 2>/dev/null)

    if echo "$validate_resp" | grep -q '"valid":true'; then
        test_case "Token 验证" 0
    else
        test_case "Token 验证" 1
    fi

    # 测试获取用户信息
    local userinfo_resp
    userinfo_resp=$(api_get "$PORTAL_URL/auth/userinfo" "$token")

    if echo "$userinfo_resp" | grep -q '"username":"admin"'; then
        test_case "获取用户信息" 0
    else
        test_case "获取用户信息" 1
    fi

    echo ""
    echo "1.2 健康检查测试"

    # Portal 健康检查
    if curl -sf "$PORTAL_URL/health" | grep -q '"status":"healthy"'; then
        test_case "Portal 健康检查" 0
    else
        test_case "Portal 健康检查" 1
    fi

    # 聚合健康检查
    local health_all
    health_all=$(api_get "$PORTAL_URL/health/all" "$token")

    if echo "$health_all" | grep -q '"portal":"healthy"'; then
        test_case "聚合健康检查" 0
    else
        test_case "聚合健康检查" 1
    fi

    echo ""
    echo "1.3 安全配置测试"

    # 安全检查端点
    local security_check
    security_check=$(api_get "$PORTAL_URL/security/check" "$token")

    if echo "$security_check" | grep -q '"security_level"'; then
        test_case "安全配置检查" 0
    else
        test_case "安全配置检查" 1
    fi
}

# ============================================================
# 阶段 2: 数据规划 (Planning)
# ============================================================

test_planning() {
    log_section "阶段 2: 数据规划测试"

    local token
    token=$(get_admin_token)

    echo "2.1 OpenMetadata 连通性测试"

    # OpenMetadata 版本检查
    local om_version
    om_version=$(curl -sf "$OPENMETADATA_URL/api/v1/system/version" 2>/dev/null)

    if echo "$om_version" | grep -q '"version"'; then
        test_case "OpenMetadata 服务连通" 0
    else
        test_case "OpenMetadata 服务连通" 1
    fi

    echo ""
    echo "2.2 元数据代理测试"

    # 通过 Portal 代理访问 OpenMetadata
    local proxy_resp
    proxy_resp=$(api_get "$PORTAL_URL/api/proxy/metadata/api/v1/system/version" "$token")

    if echo "$proxy_resp" | grep -q '"version"'; then
        test_case "元数据代理 (Portal)" 0
    else
        test_case "元数据代理 (Portal)" 1
    fi

    echo ""
    echo "2.3 标签管理测试"

    # 获取标签分类
    local tags_resp
    tags_resp=$(api_get "$PORTAL_URL/api/proxy/metadata/api/v1/classifications" "$token")

    if [[ -n "$tags_resp" ]]; then
        test_case "获取标签分类" 0
    else
        test_case "获取标签分类" 1
    fi
}

# ============================================================
# 阶段 3: 数据汇聚 (Collection)
# ============================================================

test_collection() {
    log_section "阶段 3: 数据汇聚测试"

    local token
    token=$(get_admin_token)

    echo "3.1 SeaTunnel 连通性测试"

    # SeaTunnel 集群状态
    local st_resp
    st_resp=$(curl -sf "http://localhost:5802/hazelcast/rest/cluster" 2>/dev/null)

    if [[ -n "$st_resp" ]]; then
        test_case "SeaTunnel 服务连通" 0
    else
        test_case "SeaTunnel 服务连通" 1
    fi

    echo ""
    echo "3.2 DolphinScheduler 连通性测试"

    # DolphinScheduler 状态
    local ds_resp
    ds_resp=$(curl -sf "http://localhost:12345/dolphinscheduler/actuator/health" 2>/dev/null)

    if [[ -n "$ds_resp" ]]; then
        test_case "DolphinScheduler 服务连通" 0
    else
        test_case "DolphinScheduler 服务连通" 1
    fi

    echo ""
    echo "3.3 Hop 连通性测试"

    # Hop 服务
    local hop_resp
    hop_resp=$(curl -sf "http://localhost:8083/" 2>/dev/null)

    if [[ -n "$hop_resp" ]]; then
        test_case "Hop 服务连通" 0
    else
        test_case "Hop 服务连通" 1
    fi
}

# ============================================================
# 阶段 4: 数据加工 (Processing)
# ============================================================

test_processing() {
    log_section "阶段 4: 数据加工测试"

    local token
    token=$(get_admin_token)

    echo "4.1 AI 清洗服务测试"

    # AI 清洗健康检查
    local ai_health
    ai_health=$(curl -sf "http://localhost:8012/health" 2>/dev/null)

    if echo "$ai_health" | grep -q '"status":"healthy"'; then
        test_case "AI 清洗服务健康" 0
    else
        test_case "AI 清洗服务健康" 1
    fi

    echo ""
    echo "4.2 敏感检测服务测试"

    # 敏感检测健康检查
    local sensitive_health
    sensitive_health=$(curl -sf "http://localhost:8015/health" 2>/dev/null)

    if echo "$sensitive_health" | grep -q '"status":"healthy"'; then
        test_case "敏感检测服务健康" 0
    else
        test_case "敏感检测服务健康" 1
    fi

    echo ""
    echo "4.3 元数据同步服务测试"

    # 元数据同步健康检查
    local sync_health
    sync_health=$(curl -sf "http://localhost:8013/health" 2>/dev/null)

    if echo "$sync_health" | grep -q '"status":"healthy"'; then
        test_case "元数据同步服务健康" 0
    else
        test_case "元数据同步服务健康" 1
    fi
}

# ============================================================
# 阶段 5: 数据分析 (Analysis)
# ============================================================

test_analysis() {
    log_section "阶段 5: 数据分析测试"

    local token
    token=$(get_admin_token)

    echo "5.1 NL2SQL 服务测试"

    # NL2SQL 健康检查
    local nl2sql_health
    nl2sql_health=$(curl -sf "http://localhost:8011/health" 2>/dev/null)

    if echo "$nl2sql_health" | grep -q '"status":"healthy"'; then
        test_case "NL2SQL 服务健康" 0
    else
        test_case "NL2SQL 服务健康" 1
    fi

    echo ""
    echo "5.2 Superset 连通性测试"

    # Superset 健康检查
    local superset_health
    superset_health=$(curl -sf "$SUPERSET_URL/health" 2>/dev/null)

    if echo "$superset_health" | grep -q '"OK"'; then
        test_case "Superset 服务健康" 0
    else
        test_case "Superset 服务健康" 1
    fi

    echo ""
    echo "5.3 数据 API 网关测试"

    # 数据 API 健康检查
    local data_api_health
    data_api_health=$(curl -sf "http://localhost:8014/health" 2>/dev/null)

    if echo "$data_api_health" | grep -q '"status":"healthy"'; then
        test_case "数据 API 网关健康" 0
    else
        test_case "数据 API 网关健康" 1
    fi
}

# ============================================================
# 阶段 6: 数据安全 (Security)
# ============================================================

test_security() {
    log_section "阶段 6: 数据安全测试"

    local token
    token=$(get_admin_token)

    echo "6.1 ShardingSphere 连通性测试"

    # ShardingSphere 端口检查
    if nc -z localhost 3309 2>/dev/null; then
        test_case "ShardingSphere 服务连通" 0
    else
        test_case "ShardingSphere 服务连通" 1
    fi

    echo ""
    echo "6.2 审计日志服务测试"

    # 审计日志健康检查
    local audit_health
    audit_health=$(curl -sf "http://localhost:8016/health" 2>/dev/null)

    if echo "$audit_health" | grep -q '"status":"healthy"'; then
        test_case "审计日志服务健康" 0
    else
        test_case "审计日志服务健康" 1
    fi

    echo ""
    echo "6.3 权限边界测试"

    # 测试无 Token 访问受保护 API
    local no_auth_resp
    no_auth_resp=$(curl -sf "$PORTAL_URL/auth/userinfo" 2>/dev/null)

    if [[ -z "$no_auth_resp" ]] || echo "$no_auth_resp" | grep -q '"detail"'; then
        test_case "未授权访问被拒绝" 0
    else
        test_case "未授权访问被拒绝" 1
    fi
}

# ============================================================
# 打印测试汇总
# ============================================================

print_summary() {
    log_section "测试汇总"

    local status_color
    local status_text

    if [[ $FAILED_TESTS -eq 0 ]]; then
        status_color="${GREEN}"
        status_text="全部通过"
    elif [[ $FAILED_TESTS -lt $TOTAL_TESTS ]]; then
        status_color="${YELLOW}"
        status_text="部分失败"
    else
        status_color="${RED}"
        status_text="全部失败"
    fi

    echo -e "测试结果: ${status_color}${status_text}${NC}"
    echo ""
    echo "总测试数: $TOTAL_TESTS"
    echo -e "通过: ${GREEN}$PASSED_TESTS${NC}"
    echo -e "失败: ${RED}$FAILED_TESTS${NC}"

    if [[ $FAILED_TESTS -gt 0 ]]; then
        echo ""
        echo "失败的测试:"
        for name in "${FAILED_TEST_NAMES[@]}"; do
            echo "  - $name"
        done
    fi

    # 返回退出码
    if [[ $FAILED_TESTS -gt 0 ]]; then
        return 1
    fi
    return 0
}

# ============================================================
# 帮助信息
# ============================================================

show_help() {
    show_header "test-lifecycle.sh" "生命周期测试脚本"

    cat << 'EOF'
用法: ./scripts/test-lifecycle.sh [type]

测试类型:
  all           运行所有测试 (默认)
  lifecycle     按生命周期顺序测试
  foundation    阶段1: 系统基础 (认证、健康检查、安全配置)
  planning      阶段2: 数据规划 (OpenMetadata、标签)
  collection    阶段3: 数据汇聚 (SeaTunnel、DolphinScheduler、Hop)
  processing    阶段4: 数据加工 (AI清洗、敏感检测、元数据同步)
  analysis      阶段5: 数据分析 (NL2SQL、Superset、数据API)
  security      阶段6: 数据安全 (ShardingSphere、审计、权限)

示例:
  ./scripts/test-lifecycle.sh                # 运行所有测试
  ./scripts/test-lifecycle.sh foundation     # 仅测试系统基础
  ./scripts/test-lifecycle.sh planning       # 仅测试数据规划

退出码:
  0  所有测试通过
  1  有测试失败

EOF
}

# ============================================================
# 主入口
# ============================================================

main() {
    local test_type="${1:-all}"

    case "$test_type" in
        all|lifecycle)
            test_foundation
            test_planning
            test_collection
            test_processing
            test_analysis
            test_security
            print_summary
            ;;
        foundation|phase1)
            test_foundation
            print_summary
            ;;
        planning|phase2)
            test_planning
            print_summary
            ;;
        collection|phase3)
            test_collection
            print_summary
            ;;
        processing|phase4)
            test_processing
            print_summary
            ;;
        analysis|phase5)
            test_analysis
            print_summary
            ;;
        security|phase6)
            test_security
            print_summary
            ;;
        help|-h|--help)
            show_help
            ;;
        *)
            log_error "未知测试类型: $test_type"
            show_help
            exit 1
            ;;
    esac
}

main "$@"
