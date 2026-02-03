#!/usr/bin/env bash
# OpenMetadata 种子数据初始化脚本
# 用法: ./deploy/subsystems/openmetadata/init_openmetadata.sh

set -e

# 配置
OPENMETADATA_URL="${OPENMETADATA_URL:-http://localhost:8585}"
ADMIN_USER="${OPENMETADATA_ADMIN_USER:-admin}"
ADMIN_PASSWORD="${OPENMETADATA_ADMIN_PASSWORD:-admin}"
SEED_DATA_FILE="$(dirname "$0")/seed_metadata.json"
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
# OpenMetadata API 调用辅助函数
# ============================================================

om_api_get() {
    local endpoint="$1"
    curl -sf -X GET \
        "${OPENMETADATA_URL}${endpoint}" \
        -u "${ADMIN_USER}:${ADMIN_PASSWORD}" \
        -H "Content-Type: application/json"
}

om_api_post() {
    local endpoint="$1"
    local data="$2"
    curl -sf -X POST \
        "${OPENMETADATA_URL}${endpoint}" \
        -u "${ADMIN_USER}:${ADMIN_PASSWORD}" \
        -H "Content-Type: application/json" \
        -d "$data"
}

om_api_put() {
    local endpoint="$1"
    local data="$2"
    curl -sf -X PUT \
        "${OPENMETADATA_URL}${endpoint}" \
        -u "${ADMIN_USER}:${ADMIN_PASSWORD}" \
        -H "Content-Type: application/json" \
        -d "$data"
}

# ============================================================
# 数据库服务创建
# ============================================================

create_database_service() {
    local name="$1"
    local service_type="$2"
    local description="$3"

    log_info "创建数据库服务: $name"

    # 检查服务是否已存在
    local existing
    existing=$(om_api_get "/api/v1/services/databaseServices/name/$name" 2>/dev/null || echo "")

    if [[ -n "$existing" ]] && echo "$existing" | grep -q '"name"'; then
        log_warn "数据库服务已存在: $name"
        return 0
    fi

    # 根据服务类型创建不同的配置
    local config_json
    case "$service_type" in
        mysql)
            config_json='{
                "username": "root",
                "password": "test_root_password",
                "hostPort": "mysql:3306",
                "connectionTimeout": 30000,
                "database": "demo_retail_db"
            }'
            ;;
        clickhouse)
            config_json='{
                "username": "default",
                "password": "",
                "hostPort": "clickhouse:8123",
                "database": "analytics"
            }'
            ;;
        *)
            config_json='{}'
            ;;
    esac

    local payload=$(cat <<EOF
{
    "name": "$name",
    "serviceType": "$service_type",
    "description": "$description",
    "connection": {
        "config": $config_json,
        "scheme": "${service_type}+jdbc"
    }
}
EOF
)

    local result
    result=$(om_api_post "/api/v1/services/databaseServices" "$payload" 2>/dev/null)

    if [[ $? -eq 0 ]]; then
        log_success "数据库服务创建成功: $name"
    else
        log_error "数据库服务创建失败: $name"
    fi
}

# ============================================================
# 标签分类创建
# ============================================================

create_classification() {
    local name="$1"
    local description="$2"
    local category="$3"

    log_info "创建标签分类: $name"

    # 检查分类是否已存在
    local existing
    existing=$(om_api_get "/api/v1/classifications/name/$name" 2>/dev/null || echo "")

    if [[ -n "$existing" ]] && echo "$existing" | grep -q '"name"'; then
        log_warn "标签分类已存在: $name"
        return 0
    fi

    local payload=$(cat <<EOF
{
    "name": "$name",
    "description": "$description",
    "category": "$category",
    "mutability": "MUTABLE"
}
EOF
)

    local result
    result=$(om_api_post "/api/v1/classifications" "$payload" 2>/dev/null)

    if [[ $? -eq 0 ]]; then
        log_success "标签分类创建成功: $name"
    else
        log_warn "标签分类创建失败（可能已存在）: $name"
    fi
}

# ============================================================
# 标签创建
# ============================================================

create_tag() {
    local tag_name="$1"
    local description="$2"
    local tag_type="${3:-descriptor}"

    log_info "创建标签: $tag_name"

    local payload=$(cat <<EOF
{
    "name": "$tag_name",
    "description": "$description",
    "tagType": "$tag_type"
}
EOF
)

    local result
    result=$(om_api_post "/api/v1/tags" "$payload" 2>/dev/null)

    if [[ $? -eq 0 ]]; then
        log_success "标签创建成功: $tag_name"
    else
        log_warn "标签创建失败（可能已存在）: $tag_name"
    fi
}

# ============================================================
# 术语表术语创建
# ============================================================

create_glossary_term() {
    local term_name="$1"
    local description="$2"
    local synonyms="$3"

    log_info "创建术语表术语: $term_name"

    # 首先获取或创建默认术语表
    local glossary_name="default_glossary"
    local glossary_id

    # 检查术语表是否存在
    local existing_glossary
    existing_glossary=$(om_api_get "/api/v1/glossaries/name/$glossary_name" 2>/dev/null || echo "")

    if [[ -z "$existing_glossary" ]] || ! echo "$existing_glossary" | grep -q '"id"'; then
        # 创建默认术语表
        local glossary_payload='{"name": "'"$glossary_name"'", "description": "Default glossary"}'
        existing_glossary=$(om_api_post "/api/v1/glossaries" "$glossary_payload" 2>/dev/null)
    fi

    glossary_id=$(echo "$existing_glossary" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)

    if [[ -z "$glossary_id" ]]; then
        log_warn "无法获取术语表ID，跳过术语创建"
        return 1
    fi

    # 检查术语是否已存在
    local existing_term
    existing_term=$(om_api_get "/api/v1/glossaries/$glossary_id/terms/$term_name" 2>/dev/null || echo "")

    if [[ -n "$existing_term" ]] && echo "$existing_term" | grep -q '"name"'; then
        log_warn "术语已存在: $term_name"
        return 0
    fi

    local synonyms_json="[]"
    if [[ -n "$synonyms" ]]; then
        # 简单的同义词处理
        synonyms_json="[\"$(echo "$synonyms" | sed 's/,/","/g')\"]"
    fi

    local term_payload=$(cat <<EOF
{
    "name": "$term_name",
    "description": "$description",
    "synonyms": $synonyms_json
}
EOF
)

    local result
    result=$(om_api_post "/api/v1/glossaries/$glossary_id/terms" "$term_payload" 2>/dev/null)

    if [[ $? -eq 0 ]]; then
        log_success "术语创建成功: $term_name"
    else
        log_warn "术语创建失败（可能已存在）: $term_name"
    fi
}

# ============================================================
# 从 JSON 文件导入数据
# ============================================================

import_from_json() {
    local json_file="$1"

    if [[ ! -f "$json_file" ]]; then
        log_error "种子数据文件不存在: $json_file"
        return 1
    fi

    log_info "从 JSON 文件导入元数据: $json_file"

    # 检查 jq 是否安装
    if ! command -v jq &>/dev/null; then
        log_warn "jq 未安装，使用简单 JSON 解析"
        import_simple "$json_file"
    else
        import_with_jq "$json_file"
    fi
}

import_with_jq() {
    local json_file="$1"

    # 导入数据库服务
    local db_count
    db_count=$(jq -r '.databases | length' "$json_file")
    for ((i=0; i<db_count; i++)); do
        local name
        name=$(jq -r ".databases[$i].name" "$json_file")
        local service_type
        service_type=$(jq -r ".databases[$i].serviceType" "$json_file")
        local description
        description=$(jq -r ".databases[$i].description" "$json_file")
        create_database_service "$name" "$service_type" "$description"
    done

    # 导入标签分类
    local cls_count
    cls_count=$(jq -r '.classifications | length' "$json_file")
    for ((i=0; i<cls_count; i++)); do
        local name
        name=$(jq -r ".classifications[$i].name" "$json_file")
        local description
        description=$(jq -r ".classifications[$i].description" "$json_file")
        local category
        category=$(jq -r ".classifications[$i].category" "$json_file")
        create_classification "$name" "$description" "$category"
    done

    # 导入标签
    local tag_count
    tag_count=$(jq -r '.tags | length' "$json_file" 2>/dev/null || echo "0")
    for ((i=0; i<tag_count; i++)); do
        local tag_name
        tag_name=$(jq -r ".tags[$i].name" "$json_file")
        local description
        description=$(jq -r ".tags[$i].description" "$json_file")
        local tag_type
        tag_type=$(jq -r ".tags[$i].tagType" "$json_file")
        create_tag "$tag_name" "$description" "$tag_type"
    done

    # 导入术语表术语
    local term_count
    term_count=$(jq -r '.glossary_terms | length' "$json_file" 2>/dev/null || echo "0")
    for ((i=0; i<term_count; i++)); do
        local term_name
        term_name=$(jq -r ".glossary_terms[$i].name" "$json_file")
        local description
        description=$(jq -r ".glossary_terms[$i].description" "$json_file")
        local synonyms
        synonyms=$(jq -r ".glossary_terms[$i].synonyms | join(\",\")" "$json_file")
        create_glossary_term "$term_name" "$description" "$synonyms"
    done
}

import_simple() {
    local json_file="$1"

    # 使用 grep 和 sed 进行简单的 JSON 解析
    # 创建默认标签分类
    create_classification "PII" "Personal Identifiable Information" "SECURITY"
    create_classification "SENSITIVE" "Sensitive Data" "SECURITY"
    create_classification "ODS" "Operational Data Store" "DATA_LAYER"
    create_classification "DWD" "Data Warehouse Detail" "DATA_LAYER"
    create_classification "DWS" "Data Warehouse Service" "DATA_LAYER"
    create_classification "ADS" "Application Data Service" "DATA_LAYER"

    # 创建默认标签
    create_tag "核心业务表" "Core Business Table"
    create_tag "用户域" "User Domain"
    create_tag "订单域" "Order Domain"

    # 创建默认数据库服务
    create_database_service "retail_mysql" "mysql" "零售业务MySQL数据库"

    # 创建默认术语
    create_glossary_term "DAU" "Daily Active Users" "日活,每日活跃用户"
    create_glossary_term "GMV" "Gross Merchandise Value" "交易总额,成交金额"
}

# ============================================================
# 验证导入结果
# ============================================================

verify_import() {
    log_info "验证导入结果..."

    # 检查服务健康
    local health
    health=$(om_api_get "/api/v1/system/version" 2>/dev/null)
    if echo "$health" | grep -q '"version"'; then
        local version
        version=$(echo "$health" | grep -o '"version":"[^"]*"' | cut -d'"' -f4)
        log_success "OpenMetadata 版本: $version"
    fi

    # 统计数据库服务
    local services
    services=$(om_api_get "/api/v1/services/databaseServices" 2>/dev/null)
    if [[ -n "$services" ]]; then
        local count
        count=$(echo "$services" | grep -o '"id"' | wc -l | tr -d ' ')
        log_success "数据库服务数量: $count"
    fi

    # 统计标签分类
    local classifications
    classifications=$(om_api_get "/api/v1/classifications" 2>/dev/null)
    if [[ -n "$classifications" ]]; then
        local count
        count=$(echo "$classifications" | grep -o '"name"' | wc -l | tr -d ' ')
        log_success "标签分类数量: $count"
    fi
}

# ============================================================
# 主函数
# ============================================================

main() {
    log_info "开始初始化 OpenMetadata 种子数据..."

    # 等待服务启动
    if ! wait_for_service "${OPENMETADATA_URL}/api/v1/system/version" "$MAX_RETRIES"; then
        log_error "OpenMetadata 服务未就绪"
        exit 1
    fi

    # 导入种子数据
    if [[ -f "$SEED_DATA_FILE" ]]; then
        import_from_json "$SEED_DATA_FILE"
    else
        log_warn "种子数据文件不存在，使用默认数据"
        import_simple ""
    fi

    # 验证导入结果
    verify_import

    log_success "OpenMetadata 种子数据初始化完成"
}

# 执行主函数
main "$@"
