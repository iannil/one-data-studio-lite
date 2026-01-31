#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "==================================="
echo "SSL 证书配置"
echo "==================================="

# 创建 SSL 目录
mkdir -p ssl
mkdir -p www

echo ""
echo "选择 SSL 证书配置方式:"
echo "1) 使用自签名证书（开发/测试）"
echo "2) 使用 Let's Encrypt（生产环境）"
echo "3) 使用已有证书"
echo ""
read -p "请选择 (1-3): " choice

case $choice in
    1)
        echo "生成自签名证书..."
        openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
            -keyout ssl/privkey.pem \
            -out ssl/fullchain.pem \
            -subj "/C=CN/ST=Beijing/L=Beijing/O=ONE-DATA-STUDIO/CN=localhost"

        echo ""
        echo "自签名证书已生成"
        echo "警告: 浏览器将显示安全警告，这是正常的"
        ;;
    2)
        echo "配置 Let's Encrypt..."
        read -p "输入域名: " domain
        read -p "输入邮箱: " email

        # 检查 certbot 是否可用
        if command -v certbot &> /dev/null; then
            sudo certbot certonly --standalone \
                -d "$domain" \
                --email "$email" \
                --agree-tos \
                --force-renewal

            # 链接证书
            sudo ln -sf "/etc/letsencrypt/live/$domain/fullchain.pem" ssl/fullchain.pem
            sudo ln -sf "/etc/letsencrypt/live/$domain/privkey.pem" ssl/privkey.pem
        else
            echo "错误: certbot 未安装"
            echo "请安装: apt-get install certbot (Ubuntu/Debian)"
            exit 1
        fi

        echo ""
        echo "Let's Encrypt 证书已获取"
        ;;
    3)
        echo "复制已有证书..."
        read -p "证书文件路径 (fullchain.pem): " cert_path
        read -p "私钥文件路径 (privkey.pem): " key_path

        if [ ! -f "$cert_path" ]; then
            echo "错误: 证书文件不存在: $cert_path"
            exit 1
        fi

        if [ ! -f "$key_path" ]; then
            echo "错误: 私钥文件不存在: $key_path"
            exit 1
        fi

        cp "$cert_path" ssl/fullchain.pem
        cp "$key_path" ssl/privkey.pem
        echo "证书已复制"
        ;;
    *)
        echo "无效选择"
        exit 1
        ;;
esac

# 设置权限
chmod 600 ssl/privkey.pem

# 复制 HTTPS 配置模板
if [ -f "conf.d/https.conf.template" ]; then
    cp conf.d/https.conf.template conf.d/https.conf
    echo "已启用 HTTPS 配置"
fi

echo ""
echo "==================================="
echo "SSL 配置完成"
echo "==================================="
echo ""
echo "下一步:"
echo "1. 启动 Nginx: docker compose up -d"
echo "2. 验证 HTTPS: curl -k https://localhost"
