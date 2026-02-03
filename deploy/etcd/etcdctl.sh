#!/bin/bash
# etcdctl 快捷操作脚本
#
# 使用方法:
#   ./etcdctl.sh get /one-data-studio/portal/jwt/secret
#   ./etcdctl.sh put /one-data-studio/portal/jwt/secret "my-secret"
#   ./etcdctl.sh watch /one-data-studio/
#   ./etcdctl.sh list /one-data-studio/

set -e

# etcd 连接配置
ETCD_ENDPOINTS="${ETCD_ENDPOINTS:-http://localhost:2379}"
ETCDCTL_DIAL_TIMEOUT="${ETCDCTL_DIAL_TIMEOUT:-3s}"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 帮助信息
show_help() {
    cat << EOF
etcdctl 快捷操作脚本

用法:
  $0 <command> [arguments]

命令:
  get <key>              获取配置值
  put <key> <value>      设置配置值
  del <key>              删除配置值
  list [prefix]          列出所有键（支持前缀过滤）
  watch <prefix>         监控配置变更
  history <key>          查看配置历史版本
  backup <file>          备份 etcd 数据
  restore <file>         恢复 etcd 数据
  init                   初始化 ONE-DATA-STUDIO-LITE 配置

示例:
  $0 get /one-data-studio/portal/jwt/secret
  $0 put /one-data-studio/portal/jwt/secret "my-secret"
  $0 list /one-data-studio/
  $0 watch /one-data-studio/portal/
  $0 history /one-data-studio/portal/jwt/secret
  $0 init

环境变量:
  ETCD_ENDPOINTS         etcd 服务地址 (默认: http://localhost:2379)
  ETCDCTL_DIAL_TIMEOUT   连接超时时间 (默认: 3s)

EOF
}

# 检查 etcd 连接
check_etcd() {
    if ! docker run --rm --network ods-network \
        quay.io/coreos/etcd:v3.5.12 \
        etcdctl --endpoints=$ETCD_ENDPOINTS endpoint health >/dev/null 2>&1; then
        echo -e "${RED}错误: 无法连接到 etcd 服务${NC}"
        echo "请确认 etcd 服务正在运行: make etcd-up"
        exit 1
    fi
}

# 执行 etcdctl 命令
etcdctl_cmd() {
    docker run --rm --network ods-network \
        -v "$(pwd)/workspace:/workspace" \
        quay.io/coreos/etcd:v3.5.12 \
        etcdctl \
        --endpoints=$ETCD_ENDPOINTS \
        --dial-timeout=$ETCDCTL_DIAL_TIMEOUT \
        "$@"
}

# 获取配置
cmd_get() {
    if [ -z "$1" ]; then
        echo -e "${RED}错误: 请指定键名${NC}"
        exit 1
    fi
    check_etcd
    etcdctl_cmd get "$1" --print-value-only
}

# 设置配置
cmd_put() {
    if [ -z "$1" ] || [ -z "$2" ]; then
        echo -e "${RED}错误: 请指定键名和值${NC}"
        exit 1
    fi
    check_etcd
    etcdctl_cmd put "$1" "$2"
    echo -e "${GREEN}✓ 配置已设置: $1${NC}"
}

# 删除配置
cmd_del() {
    if [ -z "$1" ]; then
        echo -e "${RED}错误: 请指定键名${NC}"
        exit 1
    fi
    check_etcd
    etcdctl_cmd del "$1"
    echo -e "${GREEN}✓ 配置已删除: $1${NC}"
}

# 列出键
cmd_list() {
    local prefix="${1:-/one-data-studio/}"
    check_etcd
    echo -e "${GREEN}列出配置键: $prefix${NC}"
    etcdctl_cmd get "$prefix" --prefix --keys-only
}

# 监控配置变更
cmd_watch() {
    local prefix="${1:-/one-data-studio/}"
    check_etcd
    echo -e "${GREEN}监控配置变更: $prefix (按 Ctrl+C 退出)${NC}"
    etcdctl_cmd watch "$prefix" --prefix
}

# 查看配置历史
cmd_history() {
    if [ -z "$1" ]; then
        echo -e "${RED}错误: 请指定键名${NC}"
        exit 1
    fi
    check_etcd
    echo -e "${GREEN}配置历史: $1${NC}"
    etcdctl_cmd get "$1" --rev=1 --prefix
    # 获取当前版本号
    local rev=$(etcdctl_cmd endpoint status --write-out=fields | grep Revision | awk '{print $2}')
    echo "当前版本: $rev"
}

# 备份数据
cmd_backup() {
    local file="${1:-etcd-backup-$(date +%Y%m%d-%H%M%S).db}"
    check_etcd
    echo -e "${GREEN}备份 etcd 数据到: $file${NC}"
    etcdctl_cmd snapshot save /workspace/$file
    echo -e "${GREEN}✓ 备份完成${NC}"
}

# 恢复数据
cmd_restore() {
    if [ -z "$1" ]; then
        echo -e "${RED}错误: 请指定备份文件路径${NC}"
        exit 1
    fi
    if [ ! -f "$1" ]; then
        echo -e "${RED}错误: 备份文件不存在: $1${NC}"
        exit 1
    fi
    echo -e "${YELLOW}警告: 恢复操作需要停止 etcd 服务${NC}"
    echo "请执行以下步骤:"
    echo "  1. make etcd-down"
    echo "  2. docker run --rm -v \$(pwd)/workspace:/workspace -v one-data-studio-etcd-data:/etcd-data \\"
    echo "      quay.io/coreos/etcd:v3.5.12 etcdctl snapshot restore /workspace/$1 --data-dir /etcd-data"
    echo "  3. make etcd-up"
}

# 初始化配置
cmd_init() {
    check_etcd
    echo -e "${GREEN}初始化 ONE-DATA-STUDIO-LITE 配置...${NC}"

    # 创建配置结构
    echo "创建配置目录结构..."
    etcdctl_cmd put /one-data-studio/.initialized "true" >/dev/null 2>&1
    etcdctl_cmd put /one-data-studio/.version "1.0.0" >/dev/null 2>&1

    # Portal 配置模板
    etcdctl_cmd put /one-data-studio/portal/database/url "" >/dev/null 2>&1
    etcdctl_cmd put /one-data-studio/portal/database/pool_size "10" >/dev/null 2>&1
    etcdctl_cmd put /one-data-studio/portal/jwt/secret "" >/dev/null 2>&1
    etcdctl_cmd put /one-data-studio/portal/jwt/expire_hours "24" >/dev/null 2>&1

    # SeaTunnel 配置模板
    etcdctl_cmd put /one-data-studio/seatunnel/api/token "" >/dev/null 2>&1

    # Superset 配置模板
    etcdctl_cmd put /one-data-studio/superset/auth/username "admin" >/dev/null 2>&1
    etcdctl_cmd put /one-data-studio/superset/auth/password "admin" >/dev/null 2>&1

    # 全局配置
    etcdctl_cmd put /one-data-studio/global/log/level "INFO" >/dev/null 2>&1
    etcdctl_cmd put /one-data-studio/global/llm/base_url "http://localhost:31434" >/dev/null 2>&1
    etcdctl_cmd put /one-data-studio/global/llm/model "qwen2.5:7b" >/dev/null 2>&1

    echo -e "${GREEN}✓ 配置初始化完成${NC}"
    echo ""
    echo "使用以下命令查看配置:"
    echo "  $0 list /one-data-studio/"
}

# 主函数
main() {
    if [ $# -eq 0 ]; then
        show_help
        exit 0
    fi

    local command=$1
    shift

    case $command in
        get) cmd_get "$@" ;;
        put) cmd_put "$@" ;;
        del) cmd_del "$@" ;;
        list) cmd_list "$@" ;;
        watch) cmd_watch "$@" ;;
        history) cmd_history "$@" ;;
        backup) cmd_backup "$@" ;;
        restore) cmd_restore "$@" ;;
        init) cmd_init ;;
        help|--help|-h) show_help ;;
        *)
            echo -e "${RED}错误: 未知命令 '$command'${NC}"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

main "$@"
