# Scripts Reference

**Updated**: 2026-02-04
**Source**: package.json, Makefile, ods.sh

This document provides a complete reference of all available scripts in the ONE-DATA-STUDIO-LITE project.

---

## Table of Contents

1. [Unified Operations Entry (ods.sh)](#unified-operations-entry-odssh)
2. [Makefile Commands](#makefile-commands)
3. [npm Scripts (Frontend)](#npm-scripts-frontend)
4. [Module Commands](#module-commands)

---

## Unified Operations Entry (ods.sh)

The `ods.sh` script is the primary entry point for all operations.

### Usage

```bash
./ods.sh <command> [target] [options]
```

### Commands

| Command | Description | Example |
|---------|-------------|---------|
| `start [target]` | Start services | `./ods.sh start all` |
| `stop [target]` | Stop services | `./ods.sh stop all` |
| `status [target]` | Show service status | `./ods.sh status all` |
| `logs <service>` | View service logs | `./ods.sh logs portal` |
| `health [target]` | Health check | `./ods.sh health all` |
| `init-data [action]` | Initialize data | `./ods.sh init-data seed` |
| `test [type]` | Run tests | `./ods.sh test lifecycle` |
| `info` | Show access URLs | `./ods.sh info` |
| `version` | Show version | `./ods.sh version` |
| `help` | Show help | `./ods.sh help` |

### Targets

| Target | Description |
|--------|-------------|
| `all` | All services (default) |
| `infra` | Infrastructure (MySQL, Redis, MinIO, etcd) |
| `platforms` | Third-party platforms (OpenMetadata, Superset, DolphinScheduler, etc.) |
| `services` | Microservices (Portal, NL2SQL, etc.) |
| `web` | Frontend development server |

### Init-Data Actions

| Action | Description |
|--------|-------------|
| `seed` | Initialize seed data (default) |
| `verify` | Verify data integrity |
| `reset` | Reset data (dangerous) |
| `status` | Show data status |

### Test Types

| Type | Description |
|------|-------------|
| `all` | Run all tests |
| `lifecycle` | Test by lifecycle order |
| `foundation` | Test system foundation |
| `planning` | Test data planning |
| `collection` | Test data collection |
| `processing` | Test data processing |
| `analysis` | Test data analysis |
| `security` | Test data security |

### Options

| Option | Description |
|--------|-------------|
| `--skip-cube-studio` | Skip Cube-Studio (requires K8s) |
| `--no-wait` | Don't wait for services ready |
| `--build` | Force rebuild images |
| `-v, --volumes` | Delete volumes on stop |

---

## Makefile Commands

### Basic Commands

| Command | Description |
|---------|-------------|
| `make help` | Show all available commands |
| `make start` | Start all services |
| `make stop` | Stop all services |
| `make status` | Show service status |
| `make info` | Show access URLs |
| `make health` | Health check |
| `make network` | Create Docker network |

### Start Commands

| Command | Description |
|---------|-------------|
| `make start` | Start all services |
| `make start-infra` | Start infrastructure |
| `make start-platforms` | Start third-party platforms |
| `make start-services` | Start microservices |
| `make start-web` | Start frontend dev server |

### Stop Commands

| Command | Description |
|---------|-------------|
| `make stop` | Stop all services |
| `make stop-infra` | Stop infrastructure |
| `make stop-platforms` | Stop third-party platforms |
| `make stop-services` | Stop microservices |
| `make stop-web` | Stop frontend |

### Health Commands

| Command | Description |
|---------|-------------|
| `make health` | Health check all |
| `make health-infra` | Health check infrastructure |
| `make health-platforms` | Health check platforms |
| `make health-services` | Health check services |

### Services

| Command | Description |
|---------|-------------|
| `make services-up` | Start custom services |
| `make services-down` | Stop custom services |
| `make services-logs` | View service logs |

### Single Component Deployment

| Command | Description |
|---------|-------------|
| `make superset-up` | Start Superset |
| `make superset-down` | Stop Superset |
| `make openmetadata-up` | Start OpenMetadata |
| `make openmetadata-down` | Stop OpenMetadata |
| `make dolphinscheduler-up` | Start DolphinScheduler |
| `make dolphinscheduler-down` | Stop DolphinScheduler |
| `make seatunnel-up` | Start SeaTunnel |
| `make hop-up` | Start Apache Hop |
| `make shardingsphere-up` | Start ShardingSphere |
| `make cube-studio-up` | Start Cube-Studio |
| `make cube-studio-down` | Stop Cube-Studio |
| `make cube-studio-logs` | View Cube-Studio logs |

### Configuration Center (etcd)

| Command | Description |
|---------|-------------|
| `make etcd-up` | Start etcd config center |
| `make etcd-down` | Stop etcd |
| `make etcd-logs` | View etcd logs |
| `make etcd-ctl` | Enter etcdctl interactive mode |
| `make etcd-backup` | Backup etcd data |
| `make etcd-init` | Initialize etcd config |

### Security Tools

| Command | Description |
|---------|-------------|
| `make generate-secrets` | Generate production secrets |
| `make generate-secrets-env` | Generate and export secrets |
| `make generate-secrets-file` | Generate secrets to .env.production |
| `make security-check` | Check security configuration |

### Database Migration

| Command | Description |
|---------|-------------|
| `make db-migrate` | Run migration (no password migration) |
| `make db-migrate-dev` | Run migration (with dev passwords) |
| `make db-reset` | Reset database (WARNING: deletes data) |
| `make db-seed` | Initialize seed data (dev) |
| `make db-seed-prod` | Initialize seed data (production) |
| `make db-verify` | Verify data integrity |

### Backup & Restore

| Command | Description |
|---------|-------------|
| `make backup-db` | Backup database |
| `make backup-etcd` | Backup etcd |
| `make backup-all` | Full backup (db + etcd + config) |
| `make restore-db` | Restore database |
| `make restore-etcd` | Restore etcd |
| `make schedule-backup` | Schedule daily backup (1 AM) |
| `make unschedule-backup` | Cancel scheduled backup |

### Monitoring & Logging

| Command | Description |
|---------|-------------|
| `make loki-up` | Start Loki log aggregation |
| `make loki-down` | Stop Loki |
| `make loki-logs` | View Loki logs |
| `make promtail-logs` | View Promtail logs |
| `make grafana-up` | Start Grafana dashboard |
| `make grafana-down` | Stop Grafana |
| `make grafana-logs` | View Grafana logs |
| `make monitoring-up` | Start full monitoring (Loki + Promtail + Grafana) |
| `make monitoring-down` | Stop monitoring |
| `make monitoring-logs` | View monitoring logs |
| `make monitoring-status` | Check monitoring status |

### Local Development

| Command | Description |
|---------|-------------|
| `make dev-install` | Install Python dependencies |
| `make dev-portal` | Start Portal service locally (port 8010) |
| `make dev-nl2sql` | Start NL2SQL service locally (port 8011) |
| `make dev-cleaning` | Start AI Cleaning service locally (port 8012) |
| `make dev-metadata` | Start Metadata Sync service locally (port 8013) |
| `make dev-dataapi` | Start Data API service locally (port 8014) |
| `make dev-sensitive` | Start Sensitive Detect service locally (port 8015) |
| `make dev-audit` | Start Audit Log service locally (port 8016) |

### Cleanup

| Command | Description |
|---------|-------------|
| `make clean` | Stop and clean all containers and volumes |

### Frontend Development

| Command | Description |
|---------|-------------|
| `make web-install` | Install frontend dependencies |
| `make web-dev` | Start frontend dev server |
| `make web-build` | Build frontend for production |
| `make web-build-deploy` | Build and deploy to Portal static dir |
| `make web-preview` | Preview production build |

### Testing

| Command | Description |
|---------|-------------|
| `make test` | Run all tests |
| `make test-e2e` | Run E2E tests |
| `make test-unit` | Run Python unit tests |
| `make test-lifecycle` | Run lifecycle tests |
| `make test-foundation` | Run foundation tests |
| `make test-planning` | Run planning tests |
| `make test-collection` | Run collection tests |
| `make test-processing` | Run processing tests |
| `make test-analysis` | Run analysis tests |
| `make test-security` | Run security tests |
| `make test-report` | Generate HTML test report |
| `make test-report-json` | Generate JSON test report |
| `make test-clean` | Clean test results |
| `make test-ui` | Open test UI mode |
| `make test-debug` | Debug tests |
| `make test-codegen` | Generate test code |
| `make test-smoke` | Run smoke tests |
| `make test-p0` | Run P0 priority tests |
| `make test-p1` | Run P1 priority tests |
| `make test-coverage` | Generate coverage report |

---

## npm Scripts (Frontend)

Located in `/web/package.json`

### Development Commands

| Command | Description |
|---------|-------------|
| `npm run dev` | Start Vite dev server |
| `npm run build` | Build production version (tsc + vite build) |
| `npm run build:full` | Full build (tsc -b + vite build) |
| `npm run preview` | Preview production build |

### Linting

| Command | Description |
|---------|-------------|
| `npm run lint` | Run ESLint check |
| `npm run lint:fix` | Auto-fix ESLint issues |

### Unit Tests (Vitest)

| Command | Description |
|---------|-------------|
| `npm run test` | Run Vitest tests (watch mode) |
| `npm run test:ui` | Open Vitest UI |
| `npm run test:run` | Run tests once |
| `npm run test:coverage` | Generate coverage report |
| `npm run test:watch` | Watch mode |

### E2E Tests (Playwright)

| Command | Description |
|---------|-------------|
| `npm run e2e` | Run all E2E tests |
| `npm run e2e:ui` | Open Playwright UI mode |
| `npm run e2e:debug` | Debug mode |
| `npm run e2e:headed` | Run with headed browser |
| `npm run e2e:report` | Show test report |
| `npm run e2e:p0` | Run P0 priority tests |
| `npm run e2e:p1` | Run P1 priority tests |
| `npm run e2e:sup` | Run Superset tests |
| `npm run e2e:adm` | Run admin tests |
| `npm run e2e:sci` | Run data science tests |
| `npm run e2e:ana` | Run analysis tests |
| `npm run e2e:vw` | Run viewer tests |
| `npm run e2e:smoke` | Run smoke tests |
| `npm run e2e:auth` | Run authentication tests |

---

## Module Commands

Module-based operations for fine-grained control.

### Start Modules

| Command | Description |
|---------|-------------|
| `make mod-base` | Start base platform module |
| `make mod-metadata` | Start metadata management module |
| `make mod-integration` | Start data integration module |
| `make mod-processing` | Start data processing module |
| `make mod-bi` | Start BI analysis module |
| `make mod-security` | Start data security module |
| `make mod-all` | Start all modules |
| `make mod-stop-all` | Stop all modules |

### Generic Module Commands

| Command | Description |
|---------|-------------|
| `make module-start MODULE=<name>` | Start specific module |
| `make module-stop MODULE=<name>` | Stop specific module |
| `make module-restart MODULE=<name>` | Restart specific module |
| `make module-status` | Show module status |
| `make module-health MODULE=<name>` | Check module health |
| `make module-list` | List all modules |
| `make module-test MODULE=<name>` | Test module |
| `make module-verify MODULE=<name>` | Quick verify module |

### Available Modules

| Module | Name | Memory | Ports |
|--------|------|--------|-------|
| `base` | Base Platform | ~4 GB | 8010, 8016, 3306, 6379 |
| `metadata` | Metadata Management | ~6 GB | 8585, 8586, 9201 |
| `integration` | Data Integration | ~8 GB | 5802, 12345, 2181 |
| `processing` | Data Processing | ~6 GB | 8083, 8012 |
| `bi` | BI Analysis | ~8 GB | 8088, 8011 |
| `security` | Data Security | ~5 GB | 8015 |

---

## Service Access URLs

Run `./ods.sh info` to display all access URLs.

| Service | URL | Credentials |
|---------|-----|-------------|
| Cube-Studio | http://localhost:30080 | - |
| Superset | http://localhost:8088 | admin/admin123 |
| OpenMetadata | http://localhost:8585 | admin/admin |
| DolphinScheduler | http://localhost:12345 | admin/dolphinscheduler123 |
| Apache Hop | http://localhost:8083 | - |
| SeaTunnel API | http://localhost:5802 | - |
| Portal | http://localhost:8010 | admin/admin123 |
| NL2SQL | http://localhost:8011/docs | - |
| AI Cleaning | http://localhost:8012/docs | - |
| Metadata Sync | http://localhost:8013/docs | - |
| Data API | http://localhost:8014/docs | - |
| Sensitive Detect | http://localhost:8015/docs | - |
| Audit Log | http://localhost:8016/docs | - |
| Frontend Dev | http://localhost:3000 | - |
| MySQL | localhost:3306 | root/config_password |
| Redis | localhost:6379 | - |
| MinIO | http://localhost:9000 | minioadmin/minioadmin123 |
| etcd | localhost:2379 | - |

---

## Related Documentation

- [Deployment Guide](./deployment.md) - Basic deployment instructions
- [Contributing Guide](./CONTRIB.md) - Development workflow and scripts
- [Runbook](./RUNBOOK.md) - Operations and troubleshooting
- [Configuration Reference](./REFERENCE.md) - Complete configuration reference
- [Modules Guide](./modules/MODULES.md) - Detailed module documentation
