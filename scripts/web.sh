#!/usr/bin/env bash
# ONE-DATA-STUDIO-LITE - 前端管理脚本
# 管理: Vite 开发服务器
# 用法: ./scripts/web.sh <start|stop|status|build>

# 加载公共库
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/lib/common.sh"

# 前端配置
WEB_PORT="${WEB_PORT:-3000}"
PID_FILE="${LOGS_DIR}/web-dev.pid"
LOG_FILE="${LOGS_DIR}/web-dev.log"

# ============================================================
# 启动前端
# ============================================================

start_web() {
    log_section "启动前端开发服务器"

    # 检查 web 目录
    if [[ ! -d "$WEB_DIR" ]]; then
        log_error "前端目录不存在: ${WEB_DIR}"
        return 1
    fi

    # 检查 Node.js
    if ! command -v node &>/dev/null; then
        log_error "Node.js 未安装"
        return 1
    fi

    # 检查端口
    if check_port_used "$WEB_PORT"; then
        log_warn "端口 ${WEB_PORT} 已被占用"
        # 检查是否是已存在的前端进程
        if [[ -f "$PID_FILE" ]]; then
            local pid
            pid=$(cat "$PID_FILE")
            if kill -0 "$pid" 2>/dev/null; then
                log_info "前端服务器已在运行 (PID: $pid)"
                return 0
            fi
        fi
        log_error "请先停止占用端口 ${WEB_PORT} 的进程"
        return 1
    fi

    cd "$WEB_DIR"

    # 检查 node_modules
    if [[ ! -d "node_modules" ]]; then
        log_step "安装前端依赖..."
        npm install
    fi

    # 启动开发服务器
    log_step "启动 Vite 开发服务器..."

    nohup npm run dev > "$LOG_FILE" 2>&1 &
    local web_pid=$!
    echo "$web_pid" > "$PID_FILE"

    # 等待服务启动
    sleep 2

    if kill -0 "$web_pid" 2>/dev/null; then
        log_success "前端开发服务器已启动"
        log_info "PID: $web_pid"
        log_info "日志: ${LOG_FILE}"
        log_info "访问: http://localhost:${WEB_PORT}"
    else
        log_error "前端服务器启动失败"
        cat "$LOG_FILE"
        return 1
    fi

    cd "$PROJECT_ROOT"
}

# ============================================================
# 停止前端
# ============================================================

stop_web() {
    log_section "停止前端开发服务器"

    if [[ -f "$PID_FILE" ]]; then
        local pid
        pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            log_step "停止进程 (PID: $pid)..."
            kill "$pid" 2>/dev/null || true
            sleep 1
            # 强制停止
            kill -9 "$pid" 2>/dev/null || true
            log_success "前端服务器已停止"
        else
            log_info "前端服务器未运行"
        fi
        rm -f "$PID_FILE"
    else
        log_info "前端服务器未运行"
    fi

    # 清理可能残留的 node 进程
    pkill -f "vite.*${WEB_DIR}" 2>/dev/null || true
}

# ============================================================
# 重启前端
# ============================================================

restart_web() {
    stop_web
    sleep 1
    start_web
}

# ============================================================
# 显示状态
# ============================================================

show_status() {
    log_section "前端服务器状态"

    if [[ -f "$PID_FILE" ]]; then
        local pid
        pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            echo -e "状态: ${GREEN}运行中${NC}"
            echo "PID: $pid"
            echo "端口: $WEB_PORT"
            echo "日志: $LOG_FILE"

            # 显示最近日志
            if [[ -f "$LOG_FILE" ]]; then
                echo ""
                echo "最近日志:"
                tail -5 "$LOG_FILE"
            fi
        else
            echo -e "状态: ${YELLOW}已停止${NC} (PID 文件存在但进程不存在)"
            rm -f "$PID_FILE"
        fi
    else
        echo -e "状态: ${WHITE}未启动${NC}"
    fi
}

# ============================================================
# 构建生产版本
# ============================================================

build_web() {
    log_section "构建前端生产版本"

    if [[ ! -d "$WEB_DIR" ]]; then
        log_error "前端目录不存在: ${WEB_DIR}"
        return 1
    fi

    cd "$WEB_DIR"

    # 检查 node_modules
    if [[ ! -d "node_modules" ]]; then
        log_step "安装前端依赖..."
        npm install
    fi

    log_step "构建生产版本..."
    npm run build

    log_success "构建完成"
    log_info "输出目录: ${WEB_DIR}/dist"

    # 复制到 Portal 静态目录
    local portal_static="${SERVICES_DIR}/portal/static"
    if [[ -d "$portal_static" ]]; then
        log_step "复制到 Portal 静态目录..."
        rm -rf "${portal_static}"/*
        cp -r dist/* "$portal_static/"
        log_success "已复制到: ${portal_static}"
    fi

    cd "$PROJECT_ROOT"
}

# ============================================================
# 查看日志
# ============================================================

show_logs() {
    local follow="${1:-false}"

    if [[ ! -f "$LOG_FILE" ]]; then
        log_info "日志文件不存在"
        return 0
    fi

    if [[ "$follow" == "true" ]]; then
        tail -f "$LOG_FILE"
    else
        tail -100 "$LOG_FILE"
    fi
}

# ============================================================
# 帮助信息
# ============================================================

show_help() {
    show_header "web.sh" "前端管理脚本"

    cat << 'EOF'
用法: ./scripts/web.sh <command> [options]

命令:
  start     启动开发服务器
  stop      停止开发服务器
  restart   重启开发服务器
  status    查看服务器状态
  build     构建生产版本
  logs      查看日志

选项:
  -f, --follow  持续跟踪日志

环境变量:
  WEB_PORT  开发服务器端口 (默认: 3000)

示例:
  ./scripts/web.sh start      # 启动开发服务器
  ./scripts/web.sh stop       # 停止开发服务器
  ./scripts/web.sh build      # 构建生产版本
  ./scripts/web.sh logs -f    # 跟踪日志

EOF
}

# ============================================================
# 主入口
# ============================================================

main() {
    local cmd="${1:-help}"
    shift || true

    case "$cmd" in
        start)
            start_web
            ;;
        stop)
            stop_web
            ;;
        restart)
            restart_web
            ;;
        status)
            show_status
            ;;
        build)
            build_web
            ;;
        logs)
            local follow="false"
            for arg in "$@"; do
                case "$arg" in
                    -f|--follow) follow="true" ;;
                esac
            done
            show_logs "$follow"
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
