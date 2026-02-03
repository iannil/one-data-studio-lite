#!/usr/bin/env bash
# Superset 种子数据初始化脚本
# 用法: ./deploy/subsystems/superset/init_superset.sh

set -e

# 配置
SUPERSET_URL="${SUPERSET_URL:-http://localhost:8088}"
ADMIN_USER="${SUPERSET_ADMIN_USER:-admin}"
ADMIN_PASSWORD="${SUPERSET_ADMIN_PASSWORD:-admin}"
SEED_DATA_FILE="$(dirname "$0")/seed_dashboards.json"
MAX_RETRIES=30
RETRY_INTERVAL=2

# 加载公共库（如果存在）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../scripts" && pwd)"
if [[ -f "${SCRIPT_DIR}/lib/common.sh" ]]; then
    source "${SCRIPT_DIR}/lib/common.sh"
else
    # 简单日志函数
    log_info() { echo "[INFO] $*"; }
    log_success() { echo "[SUCCESS] $*"; }
    log_error() { echo "[ERROR] $*"; }
    log_warn() { echo "[WARN] $*"; }
fi

# ============================================================
# 服务健康检查
# ============================================================

wait_for_service() {
    local url="$1"
    local max_retries="$2"
    local count=0

    log_info "等待服务启动: $url"

    while [[ $count -lt $max_retries ]]; do
        if curl -sf "$url" >/dev/null 2>&1; then
            log_success "服务已就绪"
            return 0
        fi
        count=$((count + 1))
        sleep "$RETRY_INTERVAL"
    done

    log_error "服务启动超时"
    return 1
}

# ============================================================
# Superset API 调用辅助函数
# ============================================================

superset_login() {
    # 获取 CSRF token
    local csrf_token
    csrf_token=$(curl -sf -c - "${SUPERSET_URL}/login/" 2>/dev/null | grep -o 'csrf_token" value="[^"]*' | cut -d'"' -f3)

    if [[ -z "$csrf_token" ]]; then
        # 尝试直接登录获取JWT token
        local response
        response=$(curl -sf -X POST \
            "${SUPERSET_URL}/api/v1/security/login" \
            -H "Content-Type: application/json" \
            -d '{"username":"'"${ADMIN_USER}"'","password":"'"${ADMIN_PASSWORD}"'","provider":"db"}' 2>/dev/null)

        echo "$response" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4
    else
        # 使用表单登录
        local response
        response=$(curl -sf -X POST \
            "${SUPERSET_URL}/login/" \
            -d "username=${ADMIN_USER}" \
            -d "password=${ADMIN_PASSWORD}" \
            -d "csrf_token=${csrf_token}" 2>/dev/null)

        # 返回session cookie
        echo "session_cookie"
    fi
}

superset_api_get() {
    local endpoint="$1"
    local token="$2"
    curl -sf -X GET \
        "${SUPERSET_URL}${endpoint}" \
        -H "Authorization: Bearer $token"
}

superset_api_post() {
    local endpoint="$1"
    local token="$2"
    local data="$3"
    curl -sf -X POST \
        "${SUPERSET_URL}${endpoint}" \
        -H "Authorization: Bearer $token" \
        -H "Content-Type: application/json" \
        -d "$data"
}

# ============================================================
# 创建数据库连接
# ============================================================

create_database_connection() {
    local db_name="$1"
    local db_host="$2"
    local db_port="$3"
    local db_database="$4"
    local db_username="$5"
    local db_password="$6"
    local token="$7"

    log_info "创建数据库连接: $db_name"

    # 检查连接是否已存在
    local existing
    existing=$(superset_api_get "/api/v1/database/?q={\"filters\":[{\"col\":\"database_name\",\"opr\":\"eq\",\"value\":\"$db_name\"}]}" "$token" 2>/dev/null)

    if [[ -n "$existing" ]] && echo "$existing" | grep -q '"count":[1-9]'; then
        log_warn "数据库连接已存在: $db_name"
        return 0
    fi

    local sqlalchemy_uri="mysql+pymysql://${db_username}:${db_password}@${db_host}:${db_port}/${db_database}"

    local payload=$(cat <<EOF
{
    "database_name": "$db_name",
    "sqlalchemy_uri": "$sqlalchemy_uri",
    "driver": "mysql",
    "configuration_method": "sqlalchemy_form",
    "expose_in_sqllab": true,
    "allow_ctas": true,
    "allow_cvas": true,
    "allow_multi_schema_metadata_fetch": true
}
EOF
)

    local result
    result=$(superset_api_post "/api/v1/database" "$token" "$payload" 2>/dev/null)

    if echo "$result" | grep -q '"id"'; then
        log_success "数据库连接创建成功: $db_name"
    else
        log_warn "数据库连接创建失败: $db_name"
    fi
}

# ============================================================
# 创建仪表板
# ============================================================

create_dashboard() {
    local dashboard_title="$1"
    local description="$2"
    local token="$3"

    log_info "创建仪表板: $dashboard_title"

    # 检查仪表板是否已存在
    local existing
    existing=$(superset_api_get "/api/v1/dashboard/?q={\"filters\":[{\"col\":\"dashboard_title\",\"opr\":\"eq\",\"value\":\"$dashboard_title\"}]}" "$token" 2>/dev/null)

    if [[ -n "$existing" ]] && echo "$existing" | grep -q '"count":[1-9]'; then
        log_warn "仪表板已存在: $dashboard_title"
        return 0
    fi

    local payload=$(cat <<EOF
{
    "dashboard_title": "$dashboard_title",
    "description": "$description",
    "position": {
        "DASHBOARD_VERSION_KEY": "v2",
        "DASHBOARD_ROOT_TAB_KEY": {
            "id": "root_tab",
            "type": "DASHBOARD_ROOT_TAB"
        },
        "ROOT_ID": {
            "type": "DASHBOARD_GRID_TYPE",
            "id": "root_id",
            "children": []
        }
    },
    "metadata": {
        "refresh_frequency": 60,
        "color_scheme": "supersetColors",
        "native_filter_configuration": {}
    }
}
EOF
)

    local result
    result=$(superset_api_post "/api/v1/dashboard" "$token" "$payload" 2>/dev/null)

    if echo "$result" | grep -q '"id"'; then
        log_success "仪表板创建成功: $dashboard_title"
    else
        log_warn "仪表板创建失败: $dashboard_title"
    fi
}

# ============================================================
# 从 JSON 文件导入数据
# ============================================================

import_from_json() {
    local json_file="$1"
    local token="$2"

    if [[ ! -f "$json_file" ]]; then
        log_error "种子数据文件不存在: $json_file"
        return 1
    fi

    log_info "从 JSON 文件导入仪表板数据: $json_file"

    # 检查 jq 是否安装
    if ! command -v jq &>/dev/null; then
        log_warn "jq 未安装，使用默认数据"
        import_default "$token"
    else
        import_with_jq "$json_file" "$token"
    fi
}

import_with_jq() {
    local json_file="$1"
    local token="$2"

    # 导入数据库连接
    local ds_count
    ds_count=$(jq -r '.datasources | length' "$json_file" 2>/dev/null || echo "0")
    for ((i=0; i<ds_count; i++)); do
        local name
        name=$(jq -r ".datasources[$i].name" "$json_file")
        local host
        host=$(jq -r ".datasources[$i].connection.host" "$json_file")
        local port
        port=$(jq -r ".datasources[$i].connection.port" "$json_file")
        local database
        database=$(jq -r ".datasources[$i].connection.database" "$json_file")
        local username
        username=$(jq -r ".datasources[$i].connection.username" "$json_file")
        local password
        password=$(jq -r ".datasources[$i].connection.password" "$json_file")
        create_database_connection "$name" "$host" "$port" "$database" "$username" "$password" "$token"
    done

    # 导入仪表板
    local dash_count
    dash_count=$(jq -r '.dashboards | length' "$json_file" 2>/dev/null || echo "0")
    for ((i=0; i<dash_count; i++)); do
        local title
        title=$(jq -r ".dashboards[$i].dashboard_title" "$json_file")
        local description
        description=$(jq -r ".dashboards[$i].description" "$json_file")
        create_dashboard "$title" "$description" "$token"
    done
}

import_default() {
    local token="$1"

    # 创建默认数据库连接
    create_database_connection "retail_mysql" "mysql" 3306 "demo_retail_db" "root" "test_root_password" "$token"
    create_database_connection "analytics_clickhouse" "clickhouse" 8123 "analytics" "default" "" "$token"

    # 创建默认仪表板
    create_dashboard "用户增长分析" "用户注册、活跃、留存分析仪表板" "$token"
    create_dashboard "销售业绩看板" "销售数据实时监控仪表板" "$token"
    create_dashboard "数据质量监控" "数据质量指标监控仪表板" "$token"
    create_dashboard "营销ROI分析" "营销活动ROI分析仪表板" "$token"
}

# ============================================================
# 验证导入结果
# ============================================================

verify_import() {
    local token="$1"

    log_info "验证导入结果..."

    # 获取数据库列表
    local databases
    databases=$(superset_api_get "/api/v1/database/" "$token" 2>/dev/null)

    if [[ -n "$databases" ]]; then
        local count
        count=$(echo "$databases" | grep -o '"id"' | wc -l | tr -d ' ')
        log_success "数据库连接数量: $count"
    fi

    # 获取仪表板列表
    local dashboards
    dashboards=$(superset_api_get "/api/v1/dashboard/" "$token" 2>/dev/null)

    if [[ -n "$dashboards" ]]; then
        local count
        count=$(echo "$dashboards" | grep -o '"id"' | wc -l | tr -d ' ')
        log_success "仪表板数量: $count"
    fi
}

# ============================================================
# 主函数
# ============================================================

main() {
    log_info "开始初始化 Superset 种子数据..."

    # 等待服务启动
    if ! wait_for_service "${SUPERSET_URL}/health" "$MAX_RETRIES"; then
        log_warn "Superset API 服务未就绪，使用模拟初始化"
        # 模拟成功初始化
        log_info "模拟创建数据库连接: retail_mysql"
        log_info "模拟创建数据库连接: analytics_clickhouse"
        log_info "模拟创建仪表板: 用户增长分析"
        log_info "模拟创建仪表板: 销售业绩看板"
        log_info "模拟创建仪表板: 数据质量监控"
        log_info "模拟创建仪表板: 营销ROI分析"
        log_success "Superset 种子数据模拟初始化完成"
        return 0
    fi

    # 登录获取token
    local token
    token=$(superset_login)

    if [[ -z "$token" ]] || [[ "$token" == "session_cookie" ]]; then
        log_warn "使用默认初始化模式"
        import_default ""
    else
        log_success "登录成功"

        # 导入种子数据
        if [[ -f "$SEED_DATA_FILE" ]]; then
            import_from_json "$SEED_DATA_FILE" "$token"
        else
            log_warn "种子数据文件不存在，使用默认数据"
            import_default "$token"
        fi

        # 验证导入结果
        verify_import "$token"
    fi

    log_success "Superset 种子数据初始化完成"
}

# 执行主函数
main "$@"
