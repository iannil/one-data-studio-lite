# ONE-DATA-STUDIO-LITE Makefile
.PHONY: help deploy stop status info services-up services-down services-logs dev-portal dev-nl2sql clean

help: ## 显示帮助
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ========== 部署命令 ==========

deploy: ## 一键部署所有组件
	bash deploy.sh deploy

stop: ## 停止所有服务
	bash deploy.sh stop

status: ## 查看服务状态
	bash deploy.sh status

info: ## 显示访问地址
	bash deploy.sh info

network: ## 创建 Docker 网络
	docker network create ods-network 2>/dev/null || true

# ========== 二开服务 ==========

services-up: network ## 启动二开服务
	docker compose -f services/docker-compose.yml up -d --build

services-down: ## 停止二开服务
	docker compose -f services/docker-compose.yml down

services-logs: ## 查看二开服务日志
	docker compose -f services/docker-compose.yml logs -f

# ========== 单组件部署 ==========

superset-up: network ## 启动 Superset
	docker compose -f deploy/superset/docker-compose.yml up -d

superset-down: ## 停止 Superset
	docker compose -f deploy/superset/docker-compose.yml down

datahub-up: network ## 启动 DataHub
	docker compose -f deploy/datahub/docker-compose.yml up -d

datahub-down: ## 停止 DataHub
	docker compose -f deploy/datahub/docker-compose.yml down

dolphinscheduler-up: network ## 启动 DolphinScheduler
	docker compose -f deploy/dolphinscheduler/docker-compose.yml up -d

dolphinscheduler-down: ## 停止 DolphinScheduler
	docker compose -f deploy/dolphinscheduler/docker-compose.yml down

seatunnel-up: network ## 启动 SeaTunnel
	docker compose -f deploy/seatunnel/docker-compose.yml up -d

hop-up: network ## 启动 Apache Hop
	docker compose -f deploy/hop/docker-compose.yml up -d --build

shardingsphere-up: network ## 启动 ShardingSphere
	docker compose -f deploy/shardingsphere/docker-compose.yml up -d

# ========== 本地开发 ==========

dev-install: ## 安装 Python 开发依赖
	pip install -r services/requirements.txt

dev-portal: ## 本地启动门户服务
	uvicorn services.portal.main:app --reload --host 0.0.0.0 --port 8010

dev-nl2sql: ## 本地启动 NL2SQL 服务
	uvicorn services.nl2sql.main:app --reload --host 0.0.0.0 --port 8011

dev-cleaning: ## 本地启动 AI 清洗服务
	uvicorn services.ai_cleaning.main:app --reload --host 0.0.0.0 --port 8012

dev-metadata: ## 本地启动元数据同步服务
	uvicorn services.metadata_sync.main:app --reload --host 0.0.0.0 --port 8013

dev-dataapi: ## 本地启动数据 API 服务
	uvicorn services.data_api.main:app --reload --host 0.0.0.0 --port 8014

dev-sensitive: ## 本地启动敏感检测服务
	uvicorn services.sensitive_detect.main:app --reload --host 0.0.0.0 --port 8015

dev-audit: ## 本地启动审计日志服务
	uvicorn services.audit_log.main:app --reload --host 0.0.0.0 --port 8016

# ========== 清理 ==========

clean: ## 停止并清理所有容器和卷
	bash deploy.sh stop
	docker volume prune -f
