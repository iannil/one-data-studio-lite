#!/bin/bash
# ONE-DATA-STUDIO-LITE - 测试环境一键启动脚本
# 用途: 快速启动精简测试环境

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

# 检查 Docker 是否安装
check_docker() {
    log_info "检查 Docker 环境..."

    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安装，请先安装 Docker"
        exit 1
    fi

    if ! docker info &> /dev/null; then
        log_error "Docker 未运行，请启动 Docker"
        exit 1
    fi

    # 检查 docker compose
    if ! docker compose version &> /dev/null; then
        log_error "Docker Compose 未安装或版本过低"
        exit 1
    fi

    log_success "Docker 环境检查通过"
}

# 检查环境配置
check_env() {
    log_info "检查环境配置..."

    if [ ! -f "$TEST_ENV_DIR/.env" ]; then
        log_warning ".env 文件不存在，将使用默认配置"
    else
        log_success "找到 .env 配置文件"
    fi

    # 检查 LLM API 配置
    if grep -q "^LLM_API_KEY=" "$TEST_ENV_DIR/.env" 2>/dev/null; then
        LLM_API_KEY=$(grep "^LLM_API_KEY=" "$TEST_ENV_DIR/.env" | cut -d'=' -f2)
        if [ -n "$LLM_API_KEY" ] && [ "$LLM_API_KEY" != "your-api-key-here" ]; then
            log_success "LLM API 已配置"
        else
            log_warning "LLM_API_KEY 未设置，AI 相关功能可能无法使用"
        fi
    else
        log_warning "未配置 LLM_API_KEY，AI 相关功能可能无法使用"
    fi
}

# 创建网络
create_network() {
    log_info "创建 Docker 网络..."

    if ! docker network ls | grep -q "test-env-network"; then
        docker network create test-env-network
        log_success "网络 test-env-network 创建成功"
    else
        log_success "网络 test-env-network 已存在"
    fi
}

# 创建必要的目录
create_directories() {
    log_info "创建必要的目录..."

    mkdir -p "$TEST_ENV_DIR/cube-studio-lite"
    mkdir -p "$TEST_ENV_DIR/init-sql"

    log_success "目录创建完成"
}

# 创建 Cube-Studio Lite 静态页面
create_cube_studio_lite() {
    log_info "创建 Cube-Studio Lite 精简页面..."

    cat > "$TEST_ENV_DIR/cube-studio-lite/index.html" << 'EOF'
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cube-Studio Lite - AI工作流</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .container {
            background: white;
            border-radius: 12px;
            padding: 40px;
            max-width: 600px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }
        h1 { color: #333; margin-bottom: 10px; }
        .subtitle { color: #666; margin-bottom: 30px; }
        .badge {
            display: inline-block;
            background: #667eea;
            color: white;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            margin-bottom: 20px;
        }
        .features { margin: 30px 0; }
        .feature {
            display: flex;
            align-items: center;
            padding: 12px 0;
            border-bottom: 1px solid #eee;
        }
        .feature:last-child { border-bottom: none; }
        .feature-icon {
            width: 32px;
            height: 32px;
            background: #f0f0f0;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-right: 12px;
            font-size: 16px;
        }
        .note {
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 12px;
            margin-top: 20px;
            border-radius: 4px;
            font-size: 14px;
            color: #856404;
        }
        .btn {
            display: inline-block;
            background: #667eea;
            color: white;
            padding: 12px 30px;
            border-radius: 6px;
            text-decoration: none;
            margin-top: 20px;
            transition: background 0.3s;
        }
        .btn:hover { background: #5568d3; }
    </style>
</head>
<body>
    <div class="container">
        <span class="badge">测试环境</span>
        <h1>Cube-Studio Lite</h1>
        <p class="subtitle">AI 工作流编排与模型训练平台 (精简版)</p>

        <div class="features">
            <div class="feature">
                <div class="feature-icon">🧠</div>
                <div>
                    <strong>模型训练</strong>
                    <div style="font-size: 13px; color: #666;">可视化模型训练流程</div>
                </div>
            </div>
            <div class="feature">
                <div class="feature-icon">📊</div>
                <div>
                    <strong>数据标注</strong>
                    <div style="font-size: 13px; color: #666;">智能数据标注工具</div>
                </div>
            </div>
            <div class="feature">
                <div class="feature-icon">⚡</div>
                <div>
                    <strong>工作流编排</strong>
                    <div style="font-size: 13px; color: #666;">拖拽式工作流设计器</div>
                </div>
            </div>
        </div>

        <div class="note">
            <strong>注意:</strong> 这是测试环境的精简版本，仅包含前端演示。
            完整功能请使用完整版 Cube-Studio。
        </div>

        <a href="http://localhost:8010" class="btn">返回统一门户</a>
    </div>
</body>
</html>
EOF

    log_success "Cube-Studio Lite 页面创建完成"
}

# 拉取镜像
pull_images() {
    log_info "拉取 Docker 镜像 (首次运行可能需要几分钟)..."

    cd "$TEST_ENV_DIR"

    docker compose pull

    log_success "镜像拉取完成"
}

# 启动服务
start_services() {
    log_info "启动测试环境服务..."

    cd "$TEST_ENV_DIR"

    # 构建并启动
    docker compose up -d --build

    log_success "服务启动完成"
}

# 等待服务就绪
wait_for_services() {
    log_info "等待服务就绪..."

    local max_wait=120
    local waited=0

    while [ $waited -lt $max_wait ]; do
        # 检查关键服务是否健康
        local healthy=0
        local total=$(docker compose -f "$TEST_ENV_DIR/docker-compose.yml" ps --services | wc -l)

        # 统计运行中的容器
        local running=$(docker compose -f "$TEST_ENV_DIR/docker-compose.yml" ps -q | wc -l)

        echo -ne "\r等待中... ($running/$total 服务运行中) [$waited/$max_wait 秒]"

        if [ "$running" -ge "$((total / 2))" ]; then
            echo ""
            log_success "主要服务已启动"
            break
        fi

        sleep 2
        ((waited += 2))
    done

    echo ""
}

# 显示访问信息
show_access_info() {
    echo ""
    echo "=========================================="
    log_success "测试环境启动完成！"
    echo "=========================================="
    echo ""
    echo "服务访问地址:"
    echo ""
    echo -e "${GREEN}统一门户:${NC}         http://localhost:8010"
    echo -e "${GREEN}NL2SQL API:${NC}       http://localhost:8011/docs"
    echo -e "${GREEN}AI清洗服务:${NC}       http://localhost:8012/docs"
    echo -e "${GREEN}元数据同步:${NC}       http://localhost:8013/docs"
    echo -e "${GREEN}数据API:${NC}          http://localhost:8014/docs"
    echo -e "${GREEN}敏感检测:${NC}         http://localhost:8015/docs"
    echo -e "${GREEN}审计日志:${NC}         http://localhost:8016/docs"
    echo ""
    echo "开源组件:"
    echo ""
    echo -e "${GREEN}Superset BI:${NC}      http://localhost:8088 (admin/admin123)"
    echo -e "${GREEN}DataHub 元数据:${NC}   http://localhost:9002 (datahub/datahub)"
    echo -e "${GREEN}Cube-Studio Lite:${NC} http://localhost:30100"
    echo -e "${GREEN}MinIO:${NC}            http://localhost:9001 (minioadmin/minioadmin123)"
    echo ""
    echo "=========================================="
    echo ""
    echo "常用命令:"
    echo "  查看状态: docker compose -f deploy/test-env/docker-compose.yml ps"
    echo "  查看日志: docker compose -f deploy/test-env/docker-compose.yml logs -f [服务名]"
    echo "  停止服务: ./deploy/test-env-stop.sh"
    echo ""
}

# 主函数
main() {
    echo ""
    echo "=========================================="
    echo "  ONE-DATA-STUDIO-LITE 测试环境启动"
    echo "=========================================="
    echo ""

    check_docker
    check_env
    create_network
    create_directories
    create_cube_studio_lite
    pull_images
    start_services
    wait_for_services
    show_access_info
}

# 执行主函数
main
