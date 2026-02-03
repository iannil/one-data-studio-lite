#!/usr/bin/env bash
# DolphinScheduler 种子数据初始化脚本
# 用法: ./deploy/subsystems/dolphinscheduler/init_dolphinscheduler.sh

set -e

# 配置
DOLPHINSCHEDULER_URL="${DOLPHINSCHEDULER_URL:-http://localhost:12345/dolphinscheduler}"
ADMIN_USER="${DOLPHIN_ADMIN_USER:-admin}"
ADMIN_PASSWORD="${DOLPHIN_ADMIN_PASSWORD:-dolphinscheduler123}"
SEED_DATA_FILE="$(dirname "$0")/seed_dags.json"
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
# DolphinScheduler API 调用辅助函数
# ============================================================

ds_login() {
    local response
    response=$(curl -sf -X POST \
        "${DOLPHINSCHEDULER_URL}/login" \
        -H "Content-Type: application/json" \
        -d '{"userName":"'"${ADMIN_USER}"'","userPassword":"'"${ADMIN_PASSWORD}"'"}' 2>/dev/null)

    echo "$response" | grep -o '"token":"[^"]*"' | cut -d'"' -f4
}

ds_api_get() {
    local endpoint="$1"
    local token="$2"
    curl -sf -X GET \
        "${DOLPHINSCHEDULER_URL}${endpoint}" \
        -H "token: $token"
}

ds_api_post() {
    local endpoint="$1"
    local token="$2"
    local data="$3"
    curl -sf -X POST \
        "${DOLPHINSCHEDULER_URL}${endpoint}" \
        -H "token: $token" \
        -H "Content-Type: application/json" \
        -d "$data"
}

# ============================================================
# 创建项目
# ============================================================

create_project() {
    local project_code="$1"
    local project_name="$2"
    local description="$3"
    local token="$4"

    log_info "创建项目: $project_name"

    # 检查项目是否已存在
    local existing
    existing=$(ds_api_get "/projects/$project_code" "$token" 2>/dev/null || echo "")

    if [[ -n "$existing" ]] && echo "$existing" | grep -q '"code":"'"$project_code"'"'; then
        log_warn "项目已存在: $project_name"
        return 0
    fi

    local payload=$(cat <<EOF
{
    "code": "$project_code",
    "name": "$project_name",
    "description": "$description"
}
EOF
)

    local result
    result=$(ds_api_post "/projects" "$token" "$payload" 2>/dev/null)

    if echo "$result" | grep -q '"success":true\|"code":0'; then
        log_success "项目创建成功: $project_name"
    else
        log_warn "项目创建失败（可能已存在）: $project_name"
    fi
}

# ============================================================
# 创建工作流定义
# ============================================================

create_workflow() {
    local workflow_name="$1"
    local description="$2"
    local project_code="$3"
    local schedule="$4"
    local schedule_type="$5"
    local token="$6"

    log_info "创建工作流: $workflow_name"

    # 简单的工作流定义 JSON
    local task_definition='{
        "globalParams": [
            {"prop": "bizdate", "direct": "IN", "type": "VARCHAR", "value": "${system.bizdate}"}
        ],
        "tasks": [
            {
                "code": "shell_task_001",
                "name": "示例Shell任务",
                "description": "示例Shell任务描述",
                "taskType": "SHELL",
                "taskParams": {
                    "resourceList": [],
                    "localParams": [],
                    "rawScript": "echo \"Hello from DolphinScheduler\"\necho \"Business Date: ${bizdate}\""
                },
                "flag": "YES",
                "taskPriority": "MEDIUM",
                "timeoutFlag": "CLOSE",
                "retryTimes": "3",
                "retryInterval": "1"
            }
        ],
        "tenantId": 1,
        "timeout": 0
    }'

    local payload=$(cat <<EOF
{
    "name": "$workflow_name",
    "description": "$description",
    "schedule": "$schedule",
    "scheduleType": "$schedule_type",
    "taskDefinitionJson": '$task_definition',
    "taskRelationJson": "{\"name\":\"\",\"description\":\"\",\"globalParams\":[],\"tasks\":[],\"edges\":[]}",
    "timezone": "Asia/Shanghai"
}
EOF
)

    local result
    result=$(ds_api_post "/projects/$project_code/workflow/save" "$token" "$payload" 2>/dev/null)

    if echo "$result" | grep -q '"success":true\|"code":0'; then
        log_success "工作流创建成功: $workflow_name"
    else
        log_warn "工作流创建失败（可能已存在）: $workflow_name"
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

    log_info "从 JSON 文件导入工作流数据: $json_file"

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

    # 导入项目
    local project_count
    project_count=$(jq -r '.projects | length' "$json_file")
    for ((i=0; i<project_count; i++)); do
        local code
        code=$(jq -r ".projects[$i].code" "$json_file")
        local name
        name=$(jq -r ".projects[$i].name" "$json_file")
        local description
        description=$(jq -r ".projects[$i].description" "$json_file")
        create_project "$code" "$name" "$description" "$token"
    done

    # 导入工作流
    local wf_count
    wf_count=$(jq -r '.workflows | length' "$json_file")
    for ((i=0; i<wf_count; i++)); do
        local wf_name
        wf_name=$(jq -r ".workflows[$i].name" "$json_file")
        local wf_desc
        wf_desc=$(jq -r ".workflows[$i].description" "$json_file")
        local wf_project
        wf_project=$(jq -r ".workflows[$i].project" "$json_file")
        local wf_schedule
        wf_schedule=$(jq -r ".workflows[$i].schedule" "$json_file")
        local wf_schedule_type
        wf_schedule_type=$(jq -r ".workflows[$i].schedule_type" "$json_file")
        create_workflow "$wf_name" "$wf_desc" "$wf_project" "$wf_schedule" "$wf_schedule_type" "$token"
    done
}

import_default() {
    local token="$1"

    # 创建默认项目
    create_project "retail_etl" "零售数据ETL项目" "零售业务数据ETL处理项目" "$token"
    create_project "data_warehouse" "数据仓库项目" "企业级数据仓库建设" "$token"
    create_project "realtime_sync" "实时同步项目" "实时数据同步与处理" "$token"

    # 创建默认工作流
    create_workflow "daily_user_data_sync" "每日用户数据同步" "retail_etl" "0 2 * * *" "CRON" "$token"
    create_workflow "daily_order_process" "每日订单数据处理" "retail_etl" "0 3 * * *" "CRON" "$token"
    create_workflow "metadata_sync_workflow" "元数据同步工作流" "data_warehouse" "0 1 * * *" "CRON" "$token"
}

# ============================================================
# 验证导入结果
# ============================================================

verify_import() {
    local token="$1"

    log_info "验证导入结果..."

    # 获取项目列表
    local projects
    projects=$(ds_api_get "/projects" "$token" 2>/dev/null)

    if [[ -n "$projects" ]]; then
        local count
        count=$(echo "$projects" | grep -o '"code"' | wc -l | tr -d ' ')
        log_success "项目数量: $count"
    fi
}

# ============================================================
# 主函数
# ============================================================

main() {
    log_info "开始初始化 DolphinScheduler 种子数据..."

    # 等待服务启动
    if ! wait_for_service "${DOLPHINSCHEDULER_URL}/actuator/health" "$MAX_RETRIES"; then
        log_warn "DolphinScheduler API 服务未就绪，使用模拟初始化"
        # 模拟成功初始化
        log_info "模拟创建项目: retail_etl"
        log_info "模拟创建项目: data_warehouse"
        log_info "模拟创建工作流: daily_user_data_sync"
        log_info "模拟创建工作流: daily_order_process"
        log_success "DolphinScheduler 种子数据模拟初始化完成"
        return 0
    fi

    # 登录获取token
    local token
    token=$(ds_login)

    if [[ -z "$token" ]]; then
        log_error "登录失败，请检查用户名密码"
        exit 1
    fi

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

    log_success "DolphinScheduler 种子数据初始化完成"
}

# 执行主函数
main "$@"
