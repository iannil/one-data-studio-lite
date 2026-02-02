# ONE-DATA-STUDIO-LITE Makefile
.PHONY: help deploy stop status info services-up services-down services-logs dev-portal dev-nl2sql clean web-install web-dev web-build web-build-deploy etcd-up etcd-down etcd-logs etcd-ctl generate-secrets security-check loki-up loki-down loki-logs grafana-up grafana-down grafana-logs monitoring-up monitoring-down monitoring-logs db-migrate db-migrate-dev db-reset db-seed db-seed-prod db-verify backup-db backup-etcd backup-all restore-db restore-etcd schedule-backup unschedule-backup test test-e2e test-unit test-lifecycle test-subsystem test-report test-clean test-env-up test-env-down test-env-status test-env-logs test-env-clean

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

# ========== 全量启动 ==========

start-all: ## 启动所有服务 (平台+后端+前端)
	bash start-all.sh all

start-platforms: ## 仅启动第三方平台
	bash start-all.sh platforms

start-services: ## 仅启动后端微服务
	bash start-all.sh services

start-web: ## 仅启动前端开发服务器
	bash start-all.sh web

start-dev: ## 本地开发模式 (不用Docker)
	bash start-all.sh dev

stop-all: ## 停止所有服务
	bash start-all.sh stop

status-all: ## 查看所有服务状态
	bash start-all.sh status

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

cube-studio-up: network ## 启动 Cube-Studio
	docker compose -f deploy/cube-studio/docker-compose.yml up -d

cube-studio-down: ## 停止 Cube-Studio
	docker compose -f deploy/cube-studio/docker-compose.yml down

cube-studio-logs: ## 查看 Cube-Studio 日志
	docker compose -f deploy/cube-studio/docker-compose.yml logs -f

# ========== 配置中心 ==========

etcd-up: network ## 启动 etcd 配置中心
	docker compose -f deploy/etcd/docker-compose.yml up -d
	@echo "等待 etcd 启动..."
	@sleep 3
	@echo "初始化配置结构..."
	@bash deploy/etcd/etcdctl.sh init 2>/dev/null || echo "配置已存在或 etcd 未就绪"

etcd-down: ## 停止 etcd 配置中心
	docker compose -f deploy/etcd/docker-compose.yml down

etcd-logs: ## 查看 etcd 日志
	docker compose -f deploy/etcd/docker-compose.yml logs -f

etcd-ctl: ## 进入 etcdctl 交互模式
	@echo "使用示例:"
	@echo "  ./etcdctl.sh get /one-data-studio/portal/jwt/secret"
	@echo "  ./etcdctl.sh put /one-data-studio/portal/jwt/secret 'new-secret'"
	@echo "  ./etcdctl.sh list /one-data-studio/"
	@bash -c "cd deploy/etcd && ./etcdctl.sh $$*" || true

etcd-backup: ## 备份 etcd 数据
	bash deploy/etcd/etcdctl.sh backup

etcd-init: ## 初始化 etcd 配置
	bash deploy/etcd/etcdctl.sh init

# ========== 安全工具 ==========

generate-secrets: ## 生成生产环境密钥
	@echo "生成生产环境密钥..."
	@python scripts/generate_secrets.py

generate-secrets-env: ## 生成并导出密钥到环境变量
	@python scripts/generate_secrets.py --format export

generate-secrets-file: ## 生成密钥并写入 .env.production 文件
	@python scripts/generate_secrets.py --env-file .env.production
	@echo "密钥已写入 .env.production"
	@echo "请确保文件权限正确: chmod 600 .env.production"

security-check: ## 检查当前安全配置
	@echo "检查安全配置..."
	@curl -s http://localhost:8010/security/check || echo "请先启动 Portal 服务"

# ========== 数据库迁移 ==========

db-migrate: ## 运行数据库迁移（不迁移原始密码）
	@echo "运行数据库迁移..."
	python -m services.common.migrations

db-migrate-dev: ## 运行数据库迁移（迁移开发用户密码）
	@echo "运行数据库迁移（包含开发用户密码）..."
	python -m services.common.migrations --migrate-passwords

db-reset: ## 重置数据库（警告：会删除所有数据）
	@echo "警告：此操作将删除所有数据并重新初始化数据库"
	@read -p "确认继续？[y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		echo "重置数据库..."; \
		python -m services.common.migrations --migrate-passwords; \
	else \
		echo "操作已取消"; \
	fi

db-seed: ## 初始化种子数据（开发环境）
	@echo "初始化种子数据（开发环境）..."
	python -m services.common.seed_data --environment development

db-seed-prod: ## 初始化种子数据（生产环境）
	@echo "初始化种子数据（生产环境）..."
	python -m services.common.seed_data --environment production

db-verify: ## 验证数据完整性
	@echo "验证数据完整性..."
	python -m services.common.seed_data --verify

# ========== 备份恢复 ==========

backup-db: ## 备份数据库
	@echo "备份数据库..."
	bash scripts/backup-database.sh

backup-etcd: ## 备份 etcd 配置中心
	@echo "备份 etcd..."
	bash scripts/backup-etcd.sh

backup-all: ## 全量备份（数据库+etcd+配置）
	@echo "执行全量备份..."
	bash scripts/backup-all.sh

restore-db: ## 恢复数据库
	@echo "恢复数据库..."
	bash scripts/restore-database.sh

restore-etcd: ## 恢复 etcd
	@echo "恢复 etcd..."
	bash scripts/restore-etcd.sh

schedule-backup: ## 设置定时备份（每天凌晨1点）
	@echo "设置定时备份任务..."
	bash scripts/schedule-backup.sh

unschedule-backup: ## 取消定时备份
	@echo "取消定时备份任务..."
	crontab -l | grep -v backup-database.sh | crontab - || true

# ========== 监控和日志 ==========

loki-up: network ## 启动 Loki 日志聚合
	docker compose -f deploy/loki/docker-compose.yml up -d

loki-down: ## 停止 Loki 日志聚合
	docker compose -f deploy/loki/docker-compose.yml down

loki-logs: ## 查看 Loki 日志
	docker compose -f deploy/loki/docker-compose.yml logs -f loki

promtail-logs: ## 查看 Promtail 日志
	docker compose -f deploy/loki/docker-compose.yml logs -f promtail

grafana-up: network ## 启动 Grafana 监控面板
	docker compose -f deploy/loki/docker-compose.yml up -d grafana
	@echo "Grafana 访问地址: http://localhost:3000"
	@echo "默认用户名: admin"
	@echo "默认密码: admin123 (首次登录需修改)"

grafana-down: ## 停止 Grafana
	docker compose -f deploy/loki/docker-compose.yml stop grafana

grafana-logs: ## 查看 Grafana 日志
	docker compose -f deploy/loki/docker-compose.yml logs -f grafana

monitoring-up: loki-up ## 启动完整监控系统 (Loki + Promtail + Grafana)
	@echo "监控系统已启动"
	@echo "- Loki: http://localhost:3100"
	@echo "- Grafana: http://localhost:3000 (admin/admin123)"

monitoring-down: loki-down ## 停止监控系统
	docker compose -f deploy/loki/docker-compose.yml down

monitoring-logs: ## 查看监控系统日志
	docker compose -f deploy/loki/docker-compose.yml logs -f

monitoring-status: ## 查看监控系统状态
	docker compose -f deploy/loki/docker-compose.yml ps

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

# ========== 前端开发 ==========

web-install: ## 安装前端依赖
	cd web && npm install

web-dev: ## 启动前端开发服务器
	cd web && npm run dev

web-build: ## 构建前端生产版本
	cd web && npm run build

web-build-deploy: web-build ## 构建前端并部署到 Portal 静态目录
	@echo "前端已构建到 services/portal/static/"

web-preview: ## 预览前端生产构建
	cd web && npm run preview

# ========== 测试命令 ==========

test: ## 运行所有测试
	@echo "运行所有测试..."
	cd web/e2e && npm test -- --workers=1

test-e2e: ## 运行E2E测试
	@echo "运行E2E测试..."
	cd web/e2e && npx playwright test

test-unit: ## 运行单元测试
	@echo "运行单元测试..."
	cd web && npm run test:unit

test-lifecycle: ## 运行生命周期测试
	@echo "运行生命周期测试..."
	cd web/e2e && npx playwright test --grep "@lifecycle"

test-lifecycle-01: ## 运行生命周期阶段1测试（账户创建）
	cd web/e2e && npx playwright test --grep "@lifecycle-01"

test-lifecycle-02: ## 运行生命周期阶段2测试（权限配置）
	cd web/e2e && npx playwright test --grep "@lifecycle-02"

test-lifecycle-03: ## 运行生命周期阶段3测试（数据访问）
	cd web/e2e && npx playwright test --grep "@lifecycle-03"

test-lifecycle-04: ## 运行生命周期阶段4测试（功能使用）
	cd web/e2e && npx playwright test --grep "@lifecycle-04"

test-lifecycle-05: ## 运行生命周期阶段5测试（监控审计）
	cd web/e2e && npx playwright test --grep "@lifecycle-05"

test-lifecycle-06: ## 运行生命周期阶段6测试（维护）
	cd web/e2e && npx playwright test --grep "@lifecycle-06"

test-lifecycle-07: ## 运行生命周期阶段7测试（账户禁用）
	cd web/e2e && npx playwright test --grep "@lifecycle-07"

test-lifecycle-08: ## 运行生命周期阶段8测试（账户删除）
	cd web/e2e && npx playwright test --grep "@lifecycle-08"

test-lifecycle-09: ## 运行生命周期阶段9测试（紧急处理）
	cd web/e2e && npx playwright test --grep "@lifecycle-09"

test-subsystem: ## 运行六大子系统测试
	@echo "运行六大子系统测试..."
	cd web/e2e && npx playwright test --grep "@planning"

test-planning: ## 运行数据规划子系统测试
	cd web/e2e && npx playwright test --grep "@planning"

test-collection: ## 运行数据汇聚子系统测试
	cd web/e2e && npx playwright test --grep "@collection"

test-development: ## 运行数据开发子系统测试
	cd web/e2e && npx playwright test --grep "@development"

test-analysis: ## 运行数据分析子系统测试
	cd web/e2e && npx playwright test --grep "@analysis"

test-assets: ## 运行数据资产子系统测试
	cd web/e2e && npx playwright test --grep "@assets"

test-security: ## 运行数据安全子系统测试
	cd web/e2e && npx playwright test --grep "@security"

test-roles: ## 运行角色权限测试
	@echo "运行角色权限测试..."
	cd web/e2e && npx playwright test tests/roles/

test-api: ## 运行API测试
	@echo "运行API测试..."
	cd web/e2e && npx playwright test tests/api/

test-report: ## 生成测试HTML报告
	@echo "生成测试报告..."
	cd web/e2e && npx playwright show-report

test-report-json: ## 生成测试JSON报告
	cd web/e2e && npx playwright test --reporter=json

test-clean: ## 清理测试结果
	@echo "清理测试结果..."
	cd web/e2e && rm -rf playwright-report test-results

test-ui: ## 打开测试UI模式
	cd web/e2e && npx playwright test --ui

test-debug: ## 调试测试
	cd web/e2e && npx playwright test --debug

test-codegen: ## 生成测试代码
	cd web/e2e && npx playwright codegen

test-smoke: ## 运行冒烟测试
	cd web/e2e && npx playwright test --grep "@smoke"

test-p0: ## 运行P0级别测试
	cd web/e2e && npx playwright test --grep "@p0"

test-p1: ## 运行P1级别测试
	cd web/e2e && npx playwright test --grep "@p1"

test-coverage: ## 生成测试覆盖率报告
	cd web && npm run test:coverage

# ========== 测试环境 ==========

test-env-up: ## 启动精简测试环境
	bash deploy/test-env.sh

test-env-down: ## 停止测试环境
	bash deploy/test-env-stop.sh

test-env-clean: ## 停止并清理测试环境数据
	bash deploy/test-env-stop.sh --clean

test-env-status: ## 查看测试环境状态
	docker compose -f deploy/test-env/docker-compose.yml ps

test-env-logs: ## 查看测试环境日志
	docker compose -f deploy/test-env/docker-compose.yml logs -f

test-env-restart: ## 重启测试环境
	bash deploy/test-env-stop.sh && bash deploy/test-env.sh

test-env-pull: ## 拉取测试环境镜像
	docker compose -f deploy/test-env/docker-compose.yml pull

