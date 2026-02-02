#!/bin/bash
# ONE-DATA-STUDIO-LITE - 测试环境一键停止脚本
# 用途: 快速停止并清理测试环境

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 获取脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
TEST_ENV_DIR="$PROJECT_DIR/deploy/test-env"

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 停止服务
stop_services() {
    log_info "停止测试环境服务..."

    if [ ! -f "$TEST_ENV_DIR/docker-compose.yml" ]; then
        log_error "docker-compose.yml 文件不存在"
        exit 1
    fi

    cd "$TEST_ENV_DIR"

    docker compose down

    log_success "服务已停止"
}

# 询问是否删除卷
remove_volumes() {
    echo ""
    read -p "是否删除数据卷? (将删除所有数据) [y/N] " -n 1 -r
    echo ""

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "删除数据卷..."

        cd "$TEST_ENV_DIR"
        docker compose down -v

        log_success "数据卷已删除"
    else
        log_info "保留数据卷"
    fi
}

# 显示信息
show_info() {
    echo ""
    echo "=========================================="
    log_success "测试环境已停止"
    echo "=========================================="
    echo ""
    echo "重新启动: ./deploy/test-env.sh"
    echo ""
}

# 主函数
main() {
    local clean_volumes=false

    # 解析参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            --clean|-c)
                clean_volumes=true
                shift
                ;;
            --help|-h)
                echo "用法: $0 [选项]"
                echo ""
                echo "选项:"
                echo "  --clean, -c    删除数据卷 (清除所有数据)"
                echo "  --help, -h     显示帮助"
                exit 0
                ;;
            *)
                log_error "未知参数: $1"
                exit 1
                ;;
        esac
    done

    echo ""
    echo "=========================================="
    echo "  ONE-DATA-STUDIO-LITE 测试环境停止"
    echo "=========================================="
    echo ""

    stop_services

    if [ "$clean_volumes" = true ]; then
        remove_volumes
    fi

    show_info
}

# 执行主函数
main "$@"
