#!/usr/bin/env bash
# ONE-DATA-STUDIO-LITE - k3s 单机部署脚本
# 用途：在开发机上安装轻量级 Kubernetes (k3s) 环境

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

# ========== 系统需求检查 ==========
check_requirements() {
    log_info "检查系统需求..."

    # 检查内存 (最低 16GB)
    local mem_kb
    if [[ "$(uname)" == "Darwin" ]]; then
        mem_kb=$(sysctl -n hw.memsize | awk '{print int($1/1024)}')
    else
        mem_kb=$(grep MemTotal /proc/meminfo | awk '{print $2}')
    fi
    local mem_gb=$((mem_kb / 1024 / 1024))
    if [[ $mem_gb -lt 14 ]]; then
        log_error "内存不足: ${mem_gb}GB (需要 16GB+)"
        exit 1
    fi
    log_info "内存: ${mem_gb}GB ✓"

    # 检查 CPU 核心 (最低 4 核)
    local cpu_cores
    if [[ "$(uname)" == "Darwin" ]]; then
        cpu_cores=$(sysctl -n hw.ncpu)
    else
        cpu_cores=$(nproc)
    fi
    if [[ $cpu_cores -lt 4 ]]; then
        log_error "CPU 核心不足: ${cpu_cores} (需要 4+)"
        exit 1
    fi
    log_info "CPU: ${cpu_cores} 核 ✓"

    # 检查磁盘空间 (最低 100GB)
    local disk_avail
    if [[ "$(uname)" == "Darwin" ]]; then
        disk_avail=$(df -g / | tail -1 | awk '{print $4}')
    else
        disk_avail=$(df -BG / | tail -1 | awk '{print $4}' | tr -d 'G')
    fi
    if [[ $disk_avail -lt 80 ]]; then
        log_warn "磁盘可用空间: ${disk_avail}GB (建议 100GB+)"
    else
        log_info "磁盘可用空间: ${disk_avail}GB ✓"
    fi
}

# ========== 安装 k3s ==========
install_k3s() {
    log_info "安装 k3s..."

    if command -v k3s &>/dev/null; then
        log_warn "k3s 已安装，跳过安装步骤"
    else
        curl -sfL https://get.k3s.io | INSTALL_K3S_EXEC="server \
            --disable=traefik \
            --write-kubeconfig-mode=644 \
            --kube-apiserver-arg=service-node-port-range=1-65535 \
            --kubelet-arg=max-pods=200" sh -
    fi

    # 等待 k3s 就绪
    log_info "等待 k3s 启动..."
    sleep 5
    until k3s kubectl get nodes &>/dev/null; do
        sleep 2
    done
    log_info "k3s 已就绪 ✓"
}

# ========== 配置 kubectl ==========
configure_kubectl() {
    log_info "配置 kubectl..."

    # 设置 KUBECONFIG
    export KUBECONFIG=/etc/rancher/k3s/k3s.yaml

    # 写入 shell 配置
    local shell_rc="$HOME/.bashrc"
    [[ -f "$HOME/.zshrc" ]] && shell_rc="$HOME/.zshrc"

    if ! grep -q "KUBECONFIG=/etc/rancher/k3s/k3s.yaml" "$shell_rc" 2>/dev/null; then
        cat >> "$shell_rc" <<'EOF'

# ONE-DATA-STUDIO-LITE: k3s kubectl 配置
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml
alias kubectl='k3s kubectl'
EOF
        log_info "kubectl 别名已添加到 $shell_rc"
    fi
}

# ========== 创建命名空间 ==========
create_namespaces() {
    log_info "创建 Kubernetes 命名空间..."

    local namespaces=("one-data" "monitoring" "datahub")
    for ns in "${namespaces[@]}"; do
        if k3s kubectl get namespace "$ns" &>/dev/null; then
            log_info "命名空间 $ns 已存在"
        else
            k3s kubectl create namespace "$ns"
            log_info "命名空间 $ns 已创建 ✓"
        fi
    done
}

# ========== 主流程 ==========
main() {
    log_info "=========================================="
    log_info " ONE-DATA-STUDIO-LITE - k3s 环境部署"
    log_info "=========================================="

    check_requirements
    install_k3s
    configure_kubectl
    create_namespaces

    log_info "=========================================="
    log_info " k3s 部署完成！"
    log_info "=========================================="
    log_info "KUBECONFIG: /etc/rancher/k3s/k3s.yaml"
    log_info "查看节点: kubectl get nodes"
    log_info "查看命名空间: kubectl get namespaces"
}

main "$@"
