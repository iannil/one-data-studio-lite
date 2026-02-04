#!/usr/bin/env python3
"""
ONE-DATA-STUDIO-LITE 生产环境密钥生成脚本

用于生成生产环境所需的各种密钥和凭据。

使用方法:
    python scripts/generate_secrets.py
    python scripts/generate_secrets.py --env-file .env.production
    python scripts/generate_secrets.py --format json
"""

import argparse
import json
import secrets
import sys
from pathlib import Path

# 添加项目根目录到路径
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root))

from services.common.security import (
    generate_api_key,
    generate_internal_token,
    generate_jwt_secret,
    generate_password,
    generate_webhook_secret,
)


def generate_all_secrets() -> dict:
    """生成所有密钥"""
    return {
        "JWT_SECRET": generate_jwt_secret(),
        "JWT_EXPIRE_HOURS": "24",
        "INTERNAL_TOKEN": generate_internal_token(),
        "SEA_TUNNEL_API_KEY": generate_api_key("st", 32),
        "META_SYNC_DATAHUB_WEBHOOK_SECRET": generate_webhook_secret(),
        "CONFIG_ENCRYPTION_KEY": secrets.token_urlsafe(32),
        # Superset
        "SUPERSET_ADMIN_USER": "admin",
        "SUPERSET_ADMIN_PASSWORD": generate_password(20, use_special=False),
        "SUPERSET_SECRET_KEY": secrets.token_hex(32),
        "SUPERSET_DB_PASSWORD": generate_password(24),
        # 数据库（如果使用）
        "DATABASE_PASSWORD": generate_password(24),
    }


def print_export_format(secrets: dict):
    """打印为 export 格式"""
    print("# ONE-DATA-STUDIO-LITE 生产环境密钥")
    print("# 生成时间:", __import__("datetime").datetime.now().isoformat())
    print()
    print("# ============================================================")
    print("# 安全配置（必须设置）")
    print("# ============================================================")
    print(f"export JWT_SECRET={secrets['JWT_SECRET']}")
    print(f"export INTERNAL_TOKEN={secrets['INTERNAL_TOKEN']}")
    print(f"export SEA_TUNNEL_API_KEY={secrets['SEA_TUNNEL_API_KEY']}")
    print(f"export META_SYNC_DATAHUB_WEBHOOK_SECRET={secrets['META_SYNC_DATAHUB_WEBHOOK_SECRET']}")
    print(f"export CONFIG_ENCRYPTION_KEY={secrets['CONFIG_ENCRYPTION_KEY']}")
    print()
    print("# ============================================================")
    print("# Superset 配置")
    print("# ============================================================")
    print(f"export SUPERSET_ADMIN_USER={secrets['SUPERSET_ADMIN_USER']}")
    print(f"export SUPERSET_ADMIN_PASSWORD={secrets['SUPERSET_ADMIN_PASSWORD']}")
    print(f"export SUPERSET_SECRET_KEY={secrets['SUPERSET_SECRET_KEY']}")
    print(f"export SUPERSET_DB_PASSWORD={secrets['SUPERSET_DB_PASSWORD']}")
    print()
    print("# ============================================================")
    print("# 子系统 Token（需要从各系统获取后填入）")
    print("# ============================================================")
    print("# 请在 DataHub 中生成 Personal Access Token 并设置:")
    print("export PORTAL_DATAHUB_TOKEN=<your-datahub-token>")
    print()
    print("# 请在 DolphinScheduler 中创建 Token 并设置:")
    print("export PORTAL_DOLPHINSCHEDULER_TOKEN=<your-ds-token>")
    print()
    print("# ============================================================")
    print("# 使用说明")
    print("# ============================================================")
    print("# 1. 将上述密钥保存到安全的地方（如密码管理器）")
    print("# 2. 设置环境变量或保存到 .env 文件（确保 .env 不提交到版本控制）")
    print("# 3. 更新 docker-compose.yml 中的环境变量")
    print("# 4. 重新部署服务")


def print_env_file_format(secrets: dict):
    """打印为 .env 文件格式"""
    print("# ONE-DATA-STUDIO-LITE 生产环境配置")
    print("# 生成时间:", __import__("datetime").datetime.now().isoformat())
    print()
    print("# ============================================================")
    print("# 安全配置（必须设置）")
    print("# ============================================================")
    print(f"JWT_SECRET={secrets['JWT_SECRET']}")
    print(f"INTERNAL_TOKEN={secrets['INTERNAL_TOKEN']}")
    print(f"SEA_TUNNEL_API_KEY={secrets['SEA_TUNNEL_API_KEY']}")
    print(f"META_SYNC_DATAHUB_WEBHOOK_SECRET={secrets['META_SYNC_DATAHUB_WEBHOOK_SECRET']}")
    print(f"CONFIG_ENCRYPTION_KEY={secrets['CONFIG_ENCRYPTION_KEY']}")
    print()
    print("# ============================================================")
    print("# Superset 配置")
    print("# ============================================================")
    print(f"SUPERSET_ADMIN_USER={secrets['SUPERSET_ADMIN_USER']}")
    print(f"SUPERSET_ADMIN_PASSWORD={secrets['SUPERSET_ADMIN_PASSWORD']}")
    print(f"SUPERSET_SECRET_KEY={secrets['SUPERSET_SECRET_KEY']}")
    print(f"SUPERSET_DB_PASSWORD={secrets['SUPERSET_DB_PASSWORD']}")
    print()
    print("# ============================================================")
    print("# 子系统 Token（需要手动获取）")
    print("# ============================================================")
    print("PORTAL_DATAHUB_TOKEN=")
    print("PORTAL_DOLPHINSCHEDULER_TOKEN=")


def print_json_format(secrets: dict):
    """打印为 JSON 格式"""
    print(json.dumps(secrets, indent=2))


def print_copy_commands(secrets: dict):
    """打印为直接复制命令"""
    print("复制以下命令到终端执行：")
    print()
    for key, value in secrets.items():
        print(f'export {key}="{value}"')


def main():
    parser = argparse.ArgumentParser(
        description="生成 ONE-DATA-STUDIO-LITE 生产环境密钥"
    )
    parser.add_argument(
        "--format",
        choices=["export", "env", "json", "copy"],
        default="export",
        help="输出格式",
    )
    parser.add_argument(
        "--env-file",
        type=str,
        help="直接写入到指定的 .env 文件",
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="在终端显示敏感信息（默认会隐藏部分内容）",
    )

    args = parser.parse_args()
    secrets = generate_all_secrets()

    if args.env_file:
        # 写入文件
        env_file = Path(args.env_file)
        import io
        from contextlib import redirect_stdout

        content = io.StringIO()
        with redirect_stdout(content):
            print_env_file_format(secrets)

        env_file.write_text(content.getvalue())
        print(f"密钥已写入 {args.env_file}")
        print(f"请确保文件权限正确: chmod 600 {args.env_file}")
    else:
        # 输出到终端
        if args.format == "export":
            print_export_format(secrets)
        elif args.format == "env":
            print_env_file_format(secrets)
        elif args.format == "json":
            print_json_format(secrets)
        elif args.format == "copy":
            print_copy_commands(secrets)


if __name__ == "__main__":
    main()
