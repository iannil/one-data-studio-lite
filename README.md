# ONE-DATA-STUDIO-LITE

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/Python-3.11+-green.svg)](https://www.python.org/)

[中文文档](README_zh.md)

**ONE-DATA-STUDIO-LITE** is an intelligent big data platform built on [Cube-Studio](https://github.com/tencentmusic/cube-studio) (open-sourced by Tencent Music), integrating best-in-class open source components to cover the entire data lifecycle management. It combines three core capabilities: intelligent metadata recognition, AI-enhanced processing, and BI visualization.

## Key Features

- **Intelligent Metadata Recognition** - DataHub-driven metadata management with data lineage tracking
- **AI-Enhanced Processing** - LLM-powered cleaning rule recommendations, NL2SQL natural language querying
- **BI Visualization** - Apache Superset interactive data analysis
- **End-to-End Data Pipeline** - From data ingestion to insights with Apache Hop, SeaTunnel, and DolphinScheduler
- **Data Security** - Transparent data masking with Apache ShardingSphere

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Unified Portal (Portal)                   │
├─────────────────────────────────────────────────────────────┤
│  Custom Services: NL2SQL · AI Cleaning · Metadata Sync ·    │
│                   Data API · Sensitive Detection · Audit     │
├─────────────────────────────────────────────────────────────┤
│  AI Engine: Cube-Studio (Ollama/vLLM) · PaddleOCR           │
├─────────────────────────────────────────────────────────────┤
│  ETL: Apache Hop + SeaTunnel  │  Scheduler: DolphinScheduler│
├─────────────────────────────────────────────────────────────┤
│  Metadata: DataHub  │  BI: Superset  │  Security: ShardingSphere
├─────────────────────────────────────────────────────────────┤
│  Infrastructure: K3s · MySQL/PostgreSQL · MinIO · Redis     │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- Docker 24.0+ and Docker Compose
- 8GB+ RAM (16GB recommended for full deployment)
- 50GB+ available disk space

### One-Click Deployment

```bash
# Clone the repository
git clone https://github.com/your-org/one-data-studio-lite.git
cd one-data-studio-lite

# Configure environment variables
cp .env.example .env
# Edit .env to set passwords and secrets

# Deploy all components
make deploy
```

### Local Development

```bash
# Install Python dependencies
make dev-install

# Start the portal service locally
make dev-portal

# Or start other services
make dev-nl2sql      # NL2SQL service
make dev-cleaning    # AI Cleaning service
make dev-dataapi     # Data API service
```

### Access URLs

| Service | URL | Credentials |
|---------|-----|-------------|
| Unified Portal | http://localhost:8010 | admin / admin123 |
| Cube-Studio | http://localhost:30080 | - |
| Apache Superset | http://localhost:8088 | admin / admin123 |
| DataHub | http://localhost:9002 | datahub / datahub |
| DolphinScheduler | http://localhost:12345 | admin / dolphinscheduler123 |
| Apache Hop | http://localhost:8083 | - |
| SeaTunnel API | http://localhost:5801 | - |

## Project Structure

```
├── deploy/                    # Deployment configurations
│   ├── k3s/                   # K3s installation scripts
│   ├── cube-studio/           # Cube-Studio Helm values
│   ├── superset/              # Apache Superset deployment
│   ├── datahub/               # DataHub deployment + ingestion
│   ├── hop/                   # Apache Hop ETL engine
│   ├── seatunnel/             # SeaTunnel data sync
│   ├── dolphinscheduler/      # DolphinScheduler
│   └── shardingsphere/        # ShardingSphere data masking
├── services/                  # Custom microservices (Python/FastAPI)
│   ├── common/                # Shared libraries (auth, db, http, middleware)
│   ├── portal/                # Unified portal (:8010)
│   ├── nl2sql/                # Natural language to SQL (:8011)
│   ├── ai_cleaning/           # AI cleaning rule recommendation (:8012)
│   ├── metadata_sync/         # Metadata-ETL synchronization (:8013)
│   ├── data_api/              # Data asset API gateway (:8014)
│   ├── sensitive_detect/      # Sensitive data detection (:8015)
│   └── audit_log/             # Unified audit logging (:8016)
├── docs/                      # Documentation
├── configs/                   # Configuration files
├── deploy.sh                  # One-click deployment script
└── Makefile                   # Common commands
```

## Six Subsystems

| Subsystem | Core Components | Capabilities |
|-----------|-----------------|--------------|
| **Data Planning & Metadata** | DataHub | Metadata recognition, tag management, data lineage |
| **Data Collection** | SeaTunnel + DolphinScheduler + Hop | Multi-source ingestion, batch-stream unified, CDC |
| **Data Processing** | SeaTunnel Transform + LLM | AI cleaning rules, data quality checks |
| **Data Analysis (AI+BI)** | Superset + NL2SQL | BI visualization, natural language queries |
| **Data Assets** | DataHub + Data API | Asset catalog, service gateway |
| **Data Security** | ShardingSphere + AI | Transparent masking, sensitive data detection |

## Tech Stack

| Category | Component | Purpose |
|----------|-----------|---------|
| Foundation Platform | Cube-Studio | AI/MLOps, Jupyter, Pipeline orchestration |
| ETL Engine | Apache Hop | Visual ETL design (Kettle successor) |
| Data Integration | Apache SeaTunnel | High-performance data sync, 200+ connectors |
| Scheduler | Apache DolphinScheduler | Workflow scheduling |
| Metadata | DataHub | Metadata management & lineage |
| BI | Apache Superset | Interactive visualization |
| AI/LLM | Ollama / vLLM | LLM inference via Cube-Studio |
| Data Security | Apache ShardingSphere | Transparent data masking |
| Custom Services | Python 3.11 + FastAPI | Microservices development |

## Common Commands

```bash
make help              # Show all available commands
make deploy            # Deploy all components
make stop              # Stop all services
make status            # Check service status
make info              # Show access URLs

# Component management
make superset-up       # Start Superset
make datahub-up        # Start DataHub
make services-up       # Start custom services

# Local development
make dev-install       # Install Python dependencies
make dev-portal        # Start portal locally
make dev-nl2sql        # Start NL2SQL locally
```

## API Documentation

Each custom service provides OpenAPI documentation:

- Portal: http://localhost:8010/docs
- NL2SQL: http://localhost:8011/docs
- AI Cleaning: http://localhost:8012/docs
- Metadata Sync: http://localhost:8013/docs
- Data API: http://localhost:8014/docs
- Sensitive Detection: http://localhost:8015/docs
- Audit Log: http://localhost:8016/docs

## Configuration

Copy `.env.example` to `.env` and configure the following:

```bash
# Database
DATABASE_URL=mysql+aiomysql://user:password@localhost:3306/one_data_studio

# JWT Authentication
JWT_SECRET=your-secure-secret-key

# LLM Configuration (Ollama)
LLM_BASE_URL=http://localhost:31434
LLM_MODEL=qwen2.5:7b
```

See [.env.example](.env.example) for all available configuration options.

## Documentation

- [Architecture Design](docs/architecture.md)
- [Technology Stack](docs/tech-stack.md)
- [Deployment Guide](docs/deployment.md)
- [Development Guide](docs/development.md)
- [API Reference](docs/api/services.md)

## Data Flow

```
Data Sources (MySQL/PostgreSQL/Files/APIs)
    │
    ▼
SeaTunnel (Data Sync/CDC)  ←→  DolphinScheduler (Scheduling)
    │
    ▼
Apache Hop (Complex ETL)  ←  AI Cleaning Rules (LLM)
    │
    ▼
Data Warehouse  ←→  DataHub (Metadata Management)
    │                    │
    ├──→ Superset (BI)   ├──→ Data Asset API
    ├──→ NL2SQL          └──→ Lineage Tracking
    └──→ ShardingSphere (Masking Proxy)
```

## Contributing

Contributions are welcome! Please read our contributing guidelines before submitting pull requests.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

This project integrates the following excellent open source projects:

- [Cube-Studio](https://github.com/tencentmusic/cube-studio) - Tencent Music
- [Apache Superset](https://superset.apache.org/) - Apache Software Foundation
- [DataHub](https://datahubproject.io/) - LinkedIn
- [Apache Hop](https://hop.apache.org/) - Apache Software Foundation
- [Apache SeaTunnel](https://seatunnel.apache.org/) - Apache Software Foundation
- [Apache DolphinScheduler](https://dolphinscheduler.apache.org/) - Apache Software Foundation
- [Apache ShardingSphere](https://shardingsphere.apache.org/) - Apache Software Foundation
