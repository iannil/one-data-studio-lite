#!/bin/bash
#
# ONE-DATA-STUDIO-LITE 生产就绪验收测试脚本
#
# 验收日期: 2026-01-31
# 目标: 对已实施的 12 个生产就绪功能进行全面验收测试
#

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 统计变量
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0
WARNINGS=0

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}ONE-DATA-STUDIO-LITE 验收测试${NC}"
echo -e "${BLUE}======================================${NC}"
echo ""

# 辅助函数
test_header() {
    echo -e "\n${BLUE}------ $1 ------${NC}"
}

test_item() {
    echo -n "  Testing: $1 ... "
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
}

test_pass() {
    echo -e "${GREEN}PASS${NC}"
    PASSED_TESTS=$((PASSED_TESTS + 1))
}

test_fail() {
    echo -e "${RED}FAIL${NC}"
    echo -e "    ${RED}Error: $1${NC}"
    FAILED_TESTS=$((FAILED_TESTS + 1))
}

test_warn() {
    echo -e "${YELLOW}WARN${NC}"
    echo -e "    ${YELLOW}Warning: $1${NC}"
    WARNINGS=$((WARNINGS + 1))
}

file_exists() {
    [ -f "$1" ]
}

dir_exists() {
    [ -d "$1" ]
}

# ============================================
# 第一阶段: 文件存在性检查
# ============================================
test_header "Phase 1: File Existence Check (36 files)"

Sprint1_Files=(
    "services/common/token_blacklist.py"
    "services/requirements.txt"
    "services/common/auth.py"
    "services/portal/main.py"
    "services/portal/config.py"
    "services/.env.production.template"
    "scripts/setup-production.sh"
    "deploy/nginx/docker-compose.yml"
    "deploy/nginx/nginx.conf"
    "deploy/nginx/conf.d/http.conf"
    "deploy/nginx/conf.d/https.conf.template"
    "deploy/nginx/ssl_setup.sh"
)

Sprint2_Files=(
    "deploy/prometheus/docker-compose.yml"
    "deploy/prometheus/prometheus.yml"
    "deploy/prometheus/rules/alerts.yml"
    "deploy/alertmanager/docker-compose.yml"
    "deploy/alertmanager/alertmanager.yml"
    "deploy/alertmanager/templates/default.tmpl"
    "scripts/log-cleanup.sh"
    "scripts/schedule-log-cleanup.sh"
    "scripts/unschedule-log-cleanup.sh"
    "scripts/backup-database.sh"
    "scripts/restore-database.sh"
    "scripts/backup-all.sh"
    "scripts/schedule-backup.sh"
    ".github/workflows/ci.yml"
    ".github/workflows/deploy.yml"
)

Sprint3_Files=(
    "services/common/base_config.py"
    "pytest.ini"
    "services/common/tests/test_auth.py"
    "services/common/tests/__init__.py"
    "tests/performance/locustfile.py"
    "tests/performance/run.sh"
    "tests/performance/README.md"
    "docs/production-checklist.md"
    "scripts/production-deploy.sh"
)

# 检查 Sprint 1 文件
for file in "${Sprint1_Files[@]}"; do
    test_item "Sprint1: $file"
    if file_exists "$file"; then
        test_pass
    else
        test_fail "File not found"
    fi
done

# 检查 Sprint 2 文件
for file in "${Sprint2_Files[@]}"; do
    test_item "Sprint2: $file"
    if file_exists "$file"; then
        test_pass
    else
        test_fail "File not found"
    fi
done

# 检查 Sprint 3 文件
for file in "${Sprint3_Files[@]}"; do
    test_item "Sprint3: $file"
    if file_exists "$file"; then
        test_pass
    else
        test_fail "File not found"
    fi
done

# ============================================
# 第二阶段: 代码质量检查
# ============================================
test_header "Phase 2: Code Quality Check"

# 2.1 Python 语法检查
Python_Files=(
    "services/common/token_blacklist.py"
    "services/common/base_config.py"
    "services/common/tests/test_auth.py"
)

for file in "${Python_Files[@]}"; do
    test_item "Python syntax: $file"
    if file_exists "$file"; then
        if python3 -m py_compile "$file" 2>/dev/null; then
            test_pass
        else
            test_fail "Syntax error"
        fi
    else
        test_fail "File not found"
    fi
done

# 2.2 检查 requirements.txt 内容
test_item "requirements.txt contains redis"
if file_exists "services/requirements.txt"; then
    if grep -q "redis.*5\.0\.0" services/requirements.txt; then
        test_pass
    else
        test_fail "redis>=5.0.0 not found in requirements.txt"
    fi
else
    test_fail "requirements.txt not found"
fi

# 2.3 脚本可执行性检查
Scripts=(
    "scripts/setup-production.sh"
    "scripts/log-cleanup.sh"
    "scripts/schedule-log-cleanup.sh"
    "scripts/unschedule-log-cleanup.sh"
    "scripts/backup-database.sh"
    "scripts/restore-database.sh"
    "scripts/backup-all.sh"
    "scripts/schedule-backup.sh"
    "deploy/nginx/ssl_setup.sh"
)

for script in "${Scripts[@]}"; do
    test_item "Executable: $script"
    if file_exists "$script"; then
        if [ -x "$script" ]; then
            test_pass
        else
            test_warn "Not executable, run: chmod +x $script"
        fi
    else
        test_fail "Script not found"
    fi
done

# 2.4 检查 shebang 行
test_item "Python files have proper encoding"
if file_exists "services/common/token_blacklist.py"; then
    if head -1 services/common/token_blacklist.py | grep -q "python3"; then
        test_pass
    else
        test_warn "No python3 shebang found"
    fi
else
    test_fail "File not found"
fi

# ============================================
# 第三阶段: 功能正确性检查
# ============================================
test_header "Phase 3: Functionality Check"

# 3.1 Token 黑名单功能 - 检查类定义
test_item "TokenBlacklist class exists"
if file_exists "services/common/token_blacklist.py"; then
    if grep -q "class TokenBlacklist" services/common/token_blacklist.py; then
        test_pass
    else
        test_fail "TokenBlacklist class not found"
    fi
else
    test_fail "File not found"
fi

# 3.2 检查 auth.py 集成
test_item "auth.py imports token_blacklist"
if file_exists "services/common/auth.py"; then
    if grep -q "token_blacklist" services/common/auth.py; then
        test_pass
    else
        test_fail "token_blacklist not imported in auth.py"
    fi
else
    test_fail "File not found"
fi

# 3.3 检查 /auth/revoke 端点
test_item "Portal has /auth/revoke endpoint"
if file_exists "services/portal/main.py"; then
    if grep -q "/auth/revoke" services/portal/main.py; then
        test_pass
    else
        test_fail "/auth/revoke endpoint not found"
    fi
else
    test_fail "File not found"
fi

# 3.4 检查配置模板中的 REDIS_URL
test_item "Config has REDIS_URL"
if file_exists "services/portal/config.py"; then
    if grep -q "REDIS_URL" services/portal/config.py; then
        test_pass
    else
        test_fail "REDIS_URL not found in config"
    fi
else
    test_fail "File not found"
fi

# 3.5 检查 pytest 配置
test_item "pytest.ini configured"
if file_exists "pytest.ini"; then
    if grep -q "\[tool:pytest\]" pytest.ini || grep -q "pytest" pytest.ini; then
        test_pass
    else
        test_fail "pytest not configured"
    fi
else
    test_fail "pytest.ini not found"
fi

# ============================================
# 第四阶段: 部署配置检查
# ============================================
test_header "Phase 4: Deployment Config Check"

# 4.1 Nginx 配置检查
test_item "Nginx docker-compose.yml exists"
if file_exists "deploy/nginx/docker-compose.yml"; then
    if grep -q "80:80" deploy/nginx/docker-compose.yml && \
       grep -q "443:443" deploy/nginx/docker-compose.yml; then
        test_pass
    else
        test_fail "Port mappings not correct"
    fi
else
    test_fail "File not found"
fi

test_item "Nginx has security headers"
if file_exists "deploy/nginx/nginx.conf"; then
    if grep -q "X-Frame-Options" deploy/nginx/nginx.conf && \
       grep -q "X-Content-Type-Options" deploy/nginx/nginx.conf; then
        test_pass
    else
        test_warn "Some security headers missing"
    fi
else
    test_fail "File not found"
fi

# 4.2 Prometheus 配置检查
test_item "Prometheus configured"
if file_exists "deploy/prometheus/prometheus.yml"; then
    if grep -q "scrape_configs" deploy/prometheus/prometheus.yml && \
       grep -q "alertmanager" deploy/prometheus/prometheus.yml; then
        test_pass
    else
        test_fail "Prometheus config incomplete"
    fi
else
    test_fail "File not found"
fi

test_item "Prometheus alert rules exist"
if file_exists "deploy/prometheus/rules/alerts.yml"; then
    if grep -q "alert" deploy/prometheus/rules/alerts.yml; then
        test_pass
    else
        test_fail "Alert rules not defined"
    fi
else
    test_fail "File not found"
fi

# 4.3 Alertmanager 配置检查
test_item "Alertmanager configured"
if file_exists "deploy/alertmanager/alertmanager.yml"; then
    if grep -q "receivers" deploy/alertmanager/alertmanager.yml; then
        test_pass
    else
        test_fail "Alertmanager config incomplete"
    fi
else
    test_fail "File not found"
fi

# ============================================
# 第五阶段: CI/CD 检查
# ============================================
test_header "Phase 5: CI/CD Check"

test_item "CI workflow exists"
if file_exists ".github/workflows/ci.yml"; then
    if grep -q "on:" .github/workflows/ci.yml && \
       grep -q "jobs:" .github/workflows/ci.yml; then
        test_pass
    else
        test_fail "CI workflow malformed"
    fi
else
    test_fail "File not found"
fi

test_item "Deploy workflow exists"
if file_exists ".github/workflows/deploy.yml"; then
    if grep -q "deploy" .github/workflows/deploy.yml; then
        test_pass
    else
        test_fail "Deploy workflow malformed"
    fi
else
    test_fail "File not found"
fi

# ============================================
# 第六阶段: 文档检查
# ============================================
test_header "Phase 6: Documentation Check"

test_item "Production checklist exists"
if file_exists "docs/production-checklist.md"; then
    if grep -q "#" docs/production-checklist.md; then
        test_pass
    else
        test_fail "Checklist malformed"
    fi
else
    test_fail "File not found"
fi

test_item "Performance test README exists"
if file_exists "tests/performance/README.md"; then
    if grep -q "Locust" tests/performance/README.md; then
        test_pass
    else
        test_warn "README may be incomplete"
    fi
else
    test_fail "File not found"
fi

# ============================================
# 第七阶段: 测试文件检查
# ============================================
test_header "Phase 7: Test Files Check"

test_item "Unit tests exist"
if file_exists "services/common/tests/test_auth.py"; then
    test_count=$(grep -c "def test_" services/common/tests/test_auth.py || echo "0")
    if [ "$test_count" -gt 0 ]; then
        test_pass "($test_count tests found)"
    else
        test_fail "No test functions found"
    fi
else
    test_fail "File not found"
fi

test_item "Performance tests exist"
if file_exists "tests/performance/locustfile.py"; then
    if grep -q "HttpUser" tests/performance/locustfile.py || \
       grep -q "task" tests/performance/locustfile.py; then
        test_pass
    else
        test_fail "Locust test malformed"
    fi
else
    test_fail "File not found"
fi

# ============================================
# 第八阶段: 安全检查
# ============================================
test_header "Phase 8: Security Check"

test_item "No hardcoded secrets in config template"
if file_exists "services/.env.production.template"; then
    if grep -q "CHANGE_ME\|REPLACE_WITH" services/.env.production.template || \
       grep -q "GENERATE_NEW" services/.env.production.template; then
        test_pass
    else
        test_warn "No placeholder markers found"
    fi
else
    test_fail "File not found"
fi

test_item "SSL setup script exists"
if file_exists "deploy/nginx/ssl_setup.sh"; then
    if grep -q "certbot\|openssl" deploy/nginx/ssl_setup.sh; then
        test_pass
    else
        test_fail "SSL setup incomplete"
    fi
else
    test_fail "File not found"
fi

# ============================================
# 测试总结
# ============================================
echo ""
echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}测试总结${NC}"
echo -e "${BLUE}======================================${NC}"
echo ""
echo -e "总测试数: ${TOTAL_TESTS}"
echo -e "${GREEN}通过: ${PASSED_TESTS}${NC}"
echo -e "${YELLOW}警告: ${WARNINGS}${NC}"
echo -e "${RED}失败: ${FAILED_TESTS}${NC}"
echo ""

PASS_RATE=$((PASSED_TESTS * 100 / TOTAL_TESTS))
echo -e "通过率: ${PASS_RATE}%"

if [ $FAILED_TESTS -eq 0 ]; then
    echo ""
    echo -e "${GREEN}======================================${NC}"
    echo -e "${GREEN}验收测试通过！${NC}"
    echo -e "${GREEN}======================================${NC}"
    exit 0
else
    echo ""
    echo -e "${RED}======================================${NC}"
    echo -e "${RED}验收测试失败，请修复错误后重试${NC}"
    echo -e "${RED}======================================${NC}"
    exit 1
fi
