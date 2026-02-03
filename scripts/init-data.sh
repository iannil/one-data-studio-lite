#!/usr/bin/env bash
# ONE-DATA-STUDIO-LITE - 初始化数据脚本
# 管理种子数据的初始化、验证和重置
# 用法: ./scripts/init-data.sh <seed|verify|reset|status>

# 加载公共库
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/lib/common.sh"

# 配置
SEED_DATA_SCRIPT="${SERVICES_DIR}/common/seed_data.py"
PORTAL_URL="http://localhost:8010"

# ============================================================
# 初始化种子数据
# ============================================================

seed_data() {
    log_section "初始化种子数据"

    # 检查 Portal 服务是否运行
    if ! curl -sf "$PORTAL_URL/health" >/dev/null 2>&1; then
        log_error "Portal 服务未运行，请先启动服务"
        log_info "运行: ./ods.sh start services"
        return 1
    fi

    # 检查数据库连接
    log_step "检查数据库连接..."
    if ! check_tcp_health "localhost" "3306"; then
        log_error "MySQL 未运行"
        return 1
    fi

    # 运行种子数据脚本
    if [[ -f "$SEED_DATA_SCRIPT" ]]; then
        log_step "运行种子数据脚本..."
        cd "$SERVICES_DIR"

        # 使用 Docker 容器运行（确保环境一致）
        if docker ps --format '{{.Names}}' | grep -q "ods-portal"; then
            log_info "通过 Portal 容器运行种子数据脚本..."
            docker exec ods-portal python -m services.common.seed_data
        else
            # 本地运行
            log_info "本地运行种子数据脚本..."
            python -m services.common.seed_data
        fi

        cd "$PROJECT_ROOT"
    else
        log_warn "种子数据脚本不存在: $SEED_DATA_SCRIPT"
        log_info "将通过 API 初始化基础数据..."
    fi

    # 通过 API 初始化基础数据
    init_via_api

    log_success "种子数据初始化完成"
}

# ============================================================
# 通过 API 初始化数据
# ============================================================

init_via_api() {
    log_step "通过 API 初始化数据..."

    # 获取管理员 Token
    local login_resp
    login_resp=$(curl -sf -X POST "$PORTAL_URL/auth/login" \
        -H "Content-Type: application/json" \
        -d '{"username":"admin","password":"admin123"}' 2>/dev/null)

    if [[ -z "$login_resp" ]]; then
        log_warn "无法登录管理员账户，跳过 API 初始化"
        return 1
    fi

    local token
    token=$(echo "$login_resp" | grep -o '"token":"[^"]*"' | cut -d'"' -f4)

    if [[ -z "$token" ]]; then
        log_warn "获取 Token 失败，跳过 API 初始化"
        return 1
    fi

    log_info "已获取管理员 Token"

    # 初始化系统配置
    log_step "初始化系统配置..."
    curl -sf -X POST "$PORTAL_URL/api/system/config" \
        -H "Authorization: Bearer $token" \
        -H "Content-Type: application/json" \
        -d '{
            "key": "system.initialized",
            "value": "true",
            "description": "系统初始化标记"
        }' >/dev/null 2>&1 || true

    log_info "系统配置初始化完成"
}

# ============================================================
# 验证数据完整性
# ============================================================

verify_data() {
    log_section "验证数据完整性"

    local errors=0

    # 检查 Portal 服务
    if ! curl -sf "$PORTAL_URL/health" >/dev/null 2>&1; then
        log_error "Portal 服务未运行"
        return 1
    fi

    # 检查管理员账户
    log_step "验证管理员账户..."
    local login_resp
    login_resp=$(curl -sf -X POST "$PORTAL_URL/auth/login" \
        -H "Content-Type: application/json" \
        -d '{"username":"admin","password":"admin123"}' 2>/dev/null)

    if [[ -z "$login_resp" ]] || echo "$login_resp" | grep -q '"success":false'; then
        log_error "管理员账户验证失败"
        errors=$((errors + 1))
    else
        log_success "管理员账户正常"
    fi

    # 检查数据库表
    log_step "验证数据库表..."
    local tables
    tables=$(docker exec ods-mysql mysql -uroot -ptest_root_password -e "USE one_data_studio; SHOW TABLES;" 2>/dev/null | tail -n +2)

    if [[ -z "$tables" ]]; then
        log_error "数据库表不存在或为空"
        errors=$((errors + 1))
    else
        local table_count
        table_count=$(echo "$tables" | wc -l | tr -d ' ')
        log_success "数据库表数量: $table_count"
    fi

    # 汇总
    echo ""
    if [[ $errors -eq 0 ]]; then
        log_success "数据验证通过"
        return 0
    else
        log_error "数据验证失败，发现 $errors 个问题"
        return 1
    fi
}

# ============================================================
# 重置数据
# ============================================================

reset_data() {
    log_section "重置数据"

    log_warn "此操作将删除所有数据！"
    echo ""

    if ! confirm "确认重置所有数据?"; then
        log_info "操作已取消"
        return 0
    fi

    # 停止服务
    log_step "停止微服务..."
    bash "${SCRIPTS_DIR}/services.sh" stop 2>/dev/null || true

    # 删除数据库数据
    log_step "清空数据库..."
    docker exec ods-mysql mysql -uroot -ptest_root_password -e "
        DROP DATABASE IF EXISTS one_data_studio;
        CREATE DATABASE one_data_studio;
    " 2>/dev/null || log_warn "数据库清空失败"

    # 重新启动服务
    log_step "重新启动微服务..."
    bash "${SCRIPTS_DIR}/services.sh" start --build

    # 重新初始化数据
    log_step "重新初始化种子数据..."
    sleep 5  # 等待服务完全启动
    seed_data

    log_success "数据重置完成"
}

# ============================================================
# 显示数据状态
# ============================================================

show_status() {
    log_section "数据状态"

    # 检查数据库
    echo "数据库状态:"
    if docker exec ods-mysql mysql -uroot -ptest_root_password -e "SELECT 1" >/dev/null 2>&1; then
        echo -e "  MySQL: ${GREEN}运行中${NC}"

        # 显示表信息
        local tables
        tables=$(docker exec ods-mysql mysql -uroot -ptest_root_password -e "USE one_data_studio; SHOW TABLES;" 2>/dev/null | tail -n +2)
        if [[ -n "$tables" ]]; then
            local table_count
            table_count=$(echo "$tables" | wc -l | tr -d ' ')
            echo "  表数量: $table_count"
        else
            echo -e "  表数量: ${YELLOW}0 (未初始化)${NC}"
        fi
    else
        echo -e "  MySQL: ${RED}未运行${NC}"
    fi

    echo ""

    # 检查用户数据
    echo "用户数据:"
    local user_count
    user_count=$(docker exec ods-mysql mysql -uroot -ptest_root_password -N -e "SELECT COUNT(*) FROM one_data_studio.users;" 2>/dev/null || echo "0")
    echo "  用户数量: $user_count"

    # 检查角色数据
    local role_count
    role_count=$(docker exec ods-mysql mysql -uroot -ptest_root_password -N -e "SELECT COUNT(*) FROM one_data_studio.roles;" 2>/dev/null || echo "0")
    echo "  角色数量: $role_count"

    echo ""

    # 检查 OpenMetadata
    echo "OpenMetadata 状态:"
    if curl -sf "http://localhost:8585/api/v1/system/version" >/dev/null 2>&1; then
        echo -e "  服务: ${GREEN}运行中${NC}"
    else
        echo -e "  服务: ${WHITE}未运行${NC}"
    fi
}

# ============================================================
# 帮助信息
# ============================================================

show_help() {
    show_header "init-data.sh" "初始化数据脚本"

    cat << 'EOF'
用法: ./scripts/init-data.sh <action>

操作:
  seed      初始化种子数据 (默认)
  verify    验证数据完整性
  reset     重置数据 (危险操作)
  status    显示数据状态

种子数据内容:
  - 系统权限定义 (19个)
  - 角色定义 (8个)
  - 默认管理员用户
  - 测试用户数据 (可选)
  - 示例业务数据 (可选)

示例:
  ./scripts/init-data.sh seed      # 初始化种子数据
  ./scripts/init-data.sh verify    # 验证数据
  ./scripts/init-data.sh status    # 查看状态
  ./scripts/init-data.sh reset     # 重置数据

注意:
  - 运行前请确保服务已启动
  - reset 操作会删除所有数据，请谨慎使用

EOF
}

# ============================================================
# 辅助函数
# ============================================================

check_tcp_health() {
    local host="$1"
    local port="$2"
    nc -z "$host" "$port" 2>/dev/null
}

# ============================================================
# 主入口
# ============================================================

main() {
    local action="${1:-seed}"

    case "$action" in
        seed|init)
            seed_data
            ;;
        verify|check)
            verify_data
            ;;
        reset|clear)
            reset_data
            ;;
        status)
            show_status
            ;;
        help|-h|--help)
            show_help
            ;;
        *)
            log_error "未知操作: $action"
            show_help
            exit 1
            ;;
    esac
}

main "$@"
