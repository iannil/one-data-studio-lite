#!/usr/bin/env bash
# ONE-DATA-STUDIO-LITE 快速启动脚本
# 根据场景选择启动的模块

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "$0") && pwd")"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "         ONE-DATA-STUDIO-LITE 快速启动"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 显示场景菜单
show_scenarios() {
    echo "请选择启动场景:"
    echo ""
    echo "  1) 前端开发      (~6 GB)  - 基础平台 + 前端"
    echo "  2) 后端开发      (~4 GB)  - 基础平台（本地模式）"
    echo "  3) 元数据开发    (~10 GB) - 基础平台 + 元数据管理"
    echo "  4) 数据工程师    (~14 GB) - 基础平台 + 数据集成 + 加工"
    echo "  5) BI 开发       (~12 GB) - 基础平台 + BI 分析"
    echo "  6) 安全开发      (~10 GB) - 基础平台 + 数据安全"
    echo "  7) 全栈开发      (~32 GB) - 所有模块"
    echo "  8) 自定义        - 手动选择模块"
    echo "  9) 仅查看状态"
    echo "  0) 退出"
    echo ""
    echo -n "请输入选项 [1-9]: "
}

# 启动前端开发场景
scenario_frontend() {
    echo -e "${BLUE}启动前端开发场景...${NC}"
    "${SCRIPT_DIR}/modules.sh" start base --local
    echo ""
    echo -e "${GREEN}前端开发环境已准备就绪！${NC}"
    echo ""
    echo "下一步:"
    echo "  make web-dev     # 启动前端开发服务器"
    echo ""
    echo "访问地址:"
    echo "  Portal:  http://localhost:8010"
    echo "  前端:    http://localhost:5173 (启动后)"
}

# 启动后端开发场景
scenario_backend() {
    echo -e "${BLUE}启动后端开发场景...${NC}"
    "${SCRIPT_DIR}/modules.sh" start base --local
    echo ""
    echo -e "${GREEN}后端开发环境已准备就绪！${NC}"
    echo ""
    echo "可用的开发命令:"
    echo "  make dev-portal      # 本地运行 Portal"
    echo "  make dev-nl2sql      # 本地运行 NL2SQL"
    echo "  make dev-cleaning    # 本地运行 AI 清洗"
    echo "  make dev-metadata    # 本地运行元数据同步"
    echo ""
    echo "访问地址:"
    echo "  Portal:   http://localhost:8010"
    echo "  NL2SQL:   http://localhost:8011"
    echo "  Cleaning: http://localhost:8012"
}

# 启动元数据开发场景
scenario_metadata() {
    echo -e "${BLUE}启动元数据开发场景...${NC}"
    "${SCRIPT_DIR}/modules.sh" start metadata
    echo ""
    echo -e "${GREEN}元数据开发环境已准备就绪！${NC}"
    echo ""
    echo "访问地址:"
    echo "  Portal:          http://localhost:8010"
    echo "  OpenMetadata:    http://localhost:8585 (admin/admin)"
    echo "  Metadata Sync:   http://localhost:8013"
    echo ""
    echo "运行测试:"
    echo "  ./scripts/test-modules.sh test metadata"
}

# 启动数据工程师场景
scenario_data_engineer() {
    echo -e "${BLUE}启动数据工程师场景...${NC}"
    "${SCRIPT_DIR}/modules.sh" start integration
    "${SCRIPT_DIR}/modules.sh" start processing
    echo ""
    echo -e "${GREEN}数据开发环境已准备就绪！${NC}"
    echo ""
    echo "访问地址:"
    echo "  Portal:            http://localhost:8010"
    echo "  SeaTunnel:         http://localhost:5802"
    echo "  DolphinScheduler:  http://localhost:12345 (admin/dolphinscheduler123)"
    echo "  Hop:               http://localhost:8083"
    echo "  AI Cleaning:       http://localhost:8012"
}

# 启动 BI 开发场景
scenario_bi() {
    echo -e "${BLUE}启动 BI 开发场景...${NC}"
    "${SCRIPT_DIR}/modules.sh" start bi
    echo ""
    echo -e "${GREEN}BI 开发环境已准备就绪！${NC}"
    echo ""
    echo "访问地址:"
    echo "  Portal:    http://localhost:8010"
    echo "  Superset:  http://localhost:8088 (admin/admin123)"
    echo "  NL2SQL:    http://localhost:8011"
    echo ""
    echo "运行测试:"
    echo "  ./scripts/test-modules.sh test bi"
}

# 启动安全开发场景
scenario_security() {
    echo -e "${BLUE}启动数据安全开发场景...${NC}"
    "${SCRIPT_DIR}/modules.sh" start security
    echo ""
    echo -e "${GREEN}安全开发环境已准备就绪！${NC}"
    echo ""
    echo "访问地址:"
    echo "  Portal:        http://localhost:8010"
    echo "  Sensitive Det: http://localhost:8015"
    echo ""
    echo "运行测试:"
    echo "  ./scripts/test-modules.sh test security"
}

# 启动全栈开发场景
scenario_fullstack() {
    echo -e "${BLUE}启动全栈开发场景...${NC}"
    echo -e "${YELLOW}警告: 这将消耗约 32GB 内存${NC}"
    echo -n "确认继续? [y/N] "
    read -r confirm

    if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
        echo "已取消"
        return
    fi

    "${SCRIPT_DIR}/modules.sh" start all
    echo ""
    echo -e "${GREEN}全栈开发环境已准备就绪！${NC}"
    echo ""
    echo "所有服务访问地址:"
    echo "  Portal:            http://localhost:8010"
    echo "  OpenMetadata:      http://localhost:8585"
    echo "  Superset:          http://localhost:8088"
    echo "  DolphinScheduler:  http://localhost:12345"
    echo "  SeaTunnel:         http://localhost:5802"
    echo "  Hop:               http://localhost:8083"
}

# 自定义场景
scenario_custom() {
    echo ""
    echo "可用模块:"
    echo "  1) base       - 基础平台"
    echo "  2) metadata   - 元数据管理"
    echo "  3) integration- 数据集成"
    echo "  4) processing - 数据加工"
    echo "  5) bi         - BI 分析"
    echo "  6) security   - 数据安全"
    echo ""
    echo -n "请输入要启动的模块编号 (多个用空格分隔): "
    read -r choices

    local modules=""
    for choice in $choices; do
        case $choice in
            1) modules="$modules base " ;;
            2) modules="$modules metadata " ;;
            3) modules="$modules integration " ;;
            4) modules="$modules processing " ;;
            5) modules="$modules bi " ;;
            6) modules="$modules security " ;;
        esac
    done

    if [[ -n "$modules" ]]; then
        for module in $modules; do
            "${SCRIPT_DIR}/modules.sh" start "$module"
        done
    fi
}

# 查看状态
show_status() {
    echo ""
    "${SCRIPT_DIR}/modules.sh" status
}

# 主循环
while true; do
    show_scenarios
    read -r choice

    case $choice in
        1) scenario_frontend; break ;;
        2) scenario_backend; break ;;
        3) scenario_metadata; break ;;
        4) scenario_data_engineer; break ;;
        5) scenario_bi; break ;;
        6) scenario_security; break ;;
        7) scenario_fullstack; break ;;
        8) scenario_custom; break ;;
        9) show_status ;;
        0) echo "退出"; exit 0 ;;
        *) echo -e "${RED}无效选项${NC}" ;;
    esac

    if [[ "$choice" != "9" ]]; then
        break
    fi
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "使用以下命令管理模块:"
echo "  ./scripts/modules.sh start <module>   # 启动模块"
echo "  ./scripts/modules.sh stop <module>    # 停止模块"
echo "  ./scripts/modules.sh status           # 查看状态"
echo ""
echo "查看完整文档: docs/modules/MODULES.md"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
