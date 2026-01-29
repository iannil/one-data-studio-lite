#!/usr/bin/env bash
# ONE-DATA-STUDIO-LITE - Cube-Studio 部署脚本
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
CUBE_STUDIO_REPO="https://github.com/tencentmusic/cube-studio.git"
CUBE_STUDIO_DIR="${PROJECT_ROOT}/.vendor/cube-studio"
NAMESPACE="one-data"

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

# ========== 克隆 Cube-Studio ==========
clone_repo() {
    if [[ -d "$CUBE_STUDIO_DIR" ]]; then
        log_info "Cube-Studio 仓库已存在，拉取最新代码..."
        cd "$CUBE_STUDIO_DIR" && git pull --ff-only || true
    else
        log_info "克隆 Cube-Studio 仓库..."
        mkdir -p "$(dirname "$CUBE_STUDIO_DIR")"
        git clone --depth 1 "$CUBE_STUDIO_REPO" "$CUBE_STUDIO_DIR"
    fi
}

# ========== 部署到 k3s ==========
deploy() {
    log_info "部署 Cube-Studio 到命名空间: $NAMESPACE"

    # 确保命名空间存在
    kubectl get namespace "$NAMESPACE" &>/dev/null || kubectl create namespace "$NAMESPACE"

    # 使用 Cube-Studio 自带的安装脚本 (k3s 模式)
    if [[ -f "$CUBE_STUDIO_DIR/install/kubernetes/install.sh" ]]; then
        log_info "使用 Cube-Studio 官方安装脚本..."
        cd "$CUBE_STUDIO_DIR/install/kubernetes"
        bash install.sh
    else
        log_info "使用 Helm 安装..."
        # 查找 helm chart 路径
        local chart_path="$CUBE_STUDIO_DIR/install/kubernetes/helm"
        if [[ -d "$chart_path" ]]; then
            helm upgrade --install cube-studio "$chart_path" \
                --namespace "$NAMESPACE" \
                -f "$SCRIPT_DIR/values.yaml" \
                --wait --timeout 600s
        else
            log_error "未找到 Helm chart，请参考 Cube-Studio 官方文档手动部署"
            log_error "文档: https://github.com/tencentmusic/cube-studio/wiki"
            exit 1
        fi
    fi
}

# ========== 等待就绪 ==========
wait_ready() {
    log_info "等待 Cube-Studio Pod 就绪..."
    kubectl wait --for=condition=ready pod \
        -l app=cube-studio \
        -n "$NAMESPACE" \
        --timeout=300s 2>/dev/null || {
        log_info "等待所有 Pod 就绪..."
        sleep 30
        kubectl get pods -n "$NAMESPACE"
    }
}

# ========== 打印访问信息 ==========
print_info() {
    local node_ip
    node_ip=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}' 2>/dev/null || echo "localhost")

    echo ""
    log_info "=========================================="
    log_info " Cube-Studio 部署完成！"
    log_info "=========================================="
    log_info "Dashboard:   http://${node_ip}:30080"
    log_info "MinIO:       http://${node_ip}:30900"
    log_info "Grafana:     http://${node_ip}:30300"
    log_info "Prometheus:  http://${node_ip}:30090"
    log_info "Ollama API:  http://${node_ip}:31434"
    log_info "=========================================="
    log_info "默认账号: admin / admin123"
    echo ""
    log_info "查看 Pod 状态: kubectl get pods -n $NAMESPACE"
}

# ========== 主流程 ==========
main() {
    log_info "开始部署 Cube-Studio..."
    clone_repo
    deploy
    wait_ready
    print_info
}

main "$@"
