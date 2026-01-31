#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "==================================="
echo "ONE-DATA-STUDIO-LITE 生产环境配置"
echo "==================================="

# 检查 .env.production 是否存在
ENV_FILE="$PROJECT_ROOT/services/.env.production"
TEMPLATE_FILE="$PROJECT_ROOT/services/.env.production.template"

if [ -f "$ENV_FILE" ]; then
    echo "警告: .env.production 已存在"
    read -p "是否覆盖? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "取消操作"
        exit 1
    fi
fi

# 复制模板
if [ -f "$TEMPLATE_FILE" ]; then
    cp "$TEMPLATE_FILE" "$ENV_FILE"
    echo "已从模板创建 .env.production"
else
    # 创建基本配置
    cat > "$ENV_FILE" << 'EOF'
# ONE-DATA-STUDIO-LITE 生产环境配置
ENVIRONMENT=production
DEBUG=false
EOF
fi

# 生成密钥
echo ""
echo "生成生产密钥..."
echo ""

# JWT Secret
JWT_SECRET=$(openssl rand -hex 32)
sed -i.bak "s|JWT_SECRET=__CHANGE_ME_GENERATE_WITH_openssl_rand_hex_32__|JWT_SECRET=$JWT_SECRET|g" "$ENV_FILE"
rm -f "${ENV_FILE}.bak"
echo "JWT_SECRET=***已生成***"

# Service Secret
SERVICE_SECRET=$(openssl rand -hex 32)
sed -i.bak "s|SERVICE_SECRET=__CHANGE_ME_GENERATE_WITH_openssl_rand_hex_32__|SERVICE_SECRET=$SERVICE_SECRET|g" "$ENV_FILE"
rm -f "${ENV_FILE}.bak"
echo "SERVICE_SECRET=***已生成***"

# Internal Token
INTERNAL_TOKEN=$(openssl rand -hex 32)
sed -i.bak "s|INTERNAL_TOKEN=__CHANGE_ME_GENERATE_WITH_openssl_rand_hex_32__|INTERNAL_TOKEN=$INTERNAL_TOKEN|g" "$ENV_FILE"
rm -f "${ENV_FILE}.bak"
echo "INTERNAL_TOKEN=***已生成***"

# Config Encryption Key
CONFIG_ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" 2>/dev/null || echo "")
if [[ $CONFIG_ENCRYPTION_KEY != "" ]]; then
    sed -i.bak "s|CONFIG_ENCRYPTION_KEY=__CHANGE_ME_GENERATE_WITH_python_cryptography_fernet__|CONFIG_ENCRYPTION_KEY=$CONFIG_ENCRYPTION_KEY|g" "$ENV_FILE"
    rm -f "${ENV_FILE}.bak"
    echo "CONFIG_ENCRYPTION_KEY=***已生成***"
else
    echo "警告: 无法生成 CONFIG_ENCRYPTION_KEY（需要 cryptography 包）"
fi

# Webhook Secret
WEBHOOK_SECRET=$(openssl rand -hex 32)
sed -i.bak "s|META_SYNC_DATAHUB_WEBHOOK_SECRET=__CHANGE_ME_GENERATE_WITH_openssl_rand_hex_32__|META_SYNC_DATAHUB_WEBHOOK_SECRET=$WEBHOOK_SECRET|g" "$ENV_FILE"
rm -f "${ENV_FILE}.bak"
echo "META_SYNC_DATAHUB_WEBHOOK_SECRET=***已生成***"

# 设置权限
chmod 600 "$ENV_FILE"

echo ""
echo "==================================="
echo "配置文件已创建: $ENV_FILE"
echo "==================================="
echo ""
echo "下一步:"
echo "1. 编辑 .env.production，修改所有 __CHANGE_ME__ 占位符"
echo "2. 配置数据库密码和外部服务 Token"
echo "3. 运行: make services-up"
echo ""
echo "安全提示:"
echo " - 请勿将 .env.production 提交到版本控制系统"
echo " - 定期轮换密钥和密码"
