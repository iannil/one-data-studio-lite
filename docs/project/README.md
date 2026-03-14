# Smart Data Platform (智能数据平台)

Enterprise-grade intelligent data management platform with integrated MLOps capabilities. A comprehensive solution combining DataOps, MLOps, and AI services into one unified platform.

[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-v1.24+-blue.svg)](https://kubernetes.io)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green.svg)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-14-black.svg)](https://nextjs.org)

## 🎯 Overview

Smart Data Platform is a full-stack data platform that provides:

- **Data Management**: Multi-source metadata management, data lineage, quality monitoring
- **Data Processing**: Visual ETL pipelines, SQL lab, data analysis
- **Data Services**: Data assets, API services, BI integration
- **AI/ML Platform**: Jupyter notebooks, experiment tracking, model management, serving
- **Annotation**: Label Studio integration for data labeling
- **AIHub**: 400+ pre-trained models marketplace
- **LLM Support**: Chat interface, private knowledge base with RAG
- **Enterprise**: SSO, multi-tenancy, billing, multi-cluster management

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (Next.js 14)                    │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐       │
│  │ Data Portal│ │ AI Studio │ │ Model Hub │ │  Admin   │       │
│  └───────────┘ └───────────┘ └───────────┘ └───────────┘       │
└─────────────────────────────────────────────────────────────────┘
                                  │
┌─────────────────────────────────────────────────────────────────┐
│                      API Gateway (FastAPI)                      │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐       │
│  │ Data APIs │ │ MLOps APIs│ │ Serving APIs││ Admin APIs │       │
│  └───────────┘ └───────────┘ └───────────┘ └───────────┘       │
└─────────────────────────────────────────────────────────────────┘
                                  │
┌─────────────────────────────────────────────────────────────────┐
│                         Microservices                           │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐       │
│  │ Metadata  │ │  ETL      │ │ Training  │ │ Inference │       │
│  │  Engine   │ │  Engine   │ │ Service   │ │  Service  │       │
│  ├───────────┤ ├───────────┤ ├───────────┤ ├───────────┤       │
│  │ Notebook  │ │ Label     │ │ Experiment│ │  AIHub    │       │
│  │  Service  │ │ Studio    │ │ Tracking  │ │  Service  │       │
│  └───────────┘ └───────────┘ └───────────┘ └───────────┘       │
└─────────────────────────────────────────────────────────────────┘
                                  │
┌─────────────────────────────────────────────────────────────────┐
│                       Infrastructure                            │
│  PostgreSQL • Redis • MinIO • RabbitMQ                         │
│  Kubernetes • MLflow • Jupyter Hub • Label Studio              │
│  Prometheus • Grafana • KServe                                  │
└─────────────────────────────────────────────────────────────────┘
```

## ✨ Features

### Data Management
- **Multi-source Support**: MySQL, PostgreSQL, ClickHouse, Hive, Presto, MongoDB
- **Metadata Browser**: Visual database schema explorer
- **Data Lineage**: Track data flow and dependencies
- **Data Quality**: Automated quality checks and monitoring
- **Data Standards**: Define and enforce data standards

### Data Processing
- **Visual ETL**: Drag-and-drop pipeline builder
- **SQL Lab**: Interactive SQL query editor
- **Data Analysis**: Built-in analysis tools
- **OCR**: Document recognition and extraction

### AI/ML Platform
- **Jupyter Hub**: Online notebook development
- **Experiment Tracking**: MLflow integration
- **Model Registry**: Version control for models
- **Model Serving**: One-click deployment with KServe
- **Hyperparameter Tuning**: NNI integration
- **Distributed Training**: Multi-GPU training support

### AIHub
- **400+ Models**: Pre-trained models for CV, NLP, Audio, Multimodal
- **One-click Deploy**: Deploy models as API services
- **Fine-tuning**: LoRA, QLoRA, full fine-tuning support
- **Model Formats**: PyTorch, TensorFlow, ONNX, SafeTensors

### LLM Support
- **Multi-model Chat**: Support for ChatGLM, Qwen, Llama, etc.
- **Private Knowledge Base**: RAG-powered Q&A
- **Vector Search**: Semantic search with embeddings
- **Prompt Management**: Template library

### Annotation
- **Label Studio**: Enterprise data labeling
- **Auto-annotation**: LLM-assisted labeling
- **Multi-modal**: Image, text, audio, video

### Enterprise
- **SSO**: OAuth2, SAML, LDAP support
- **Multi-tenancy**: Organization and resource isolation
- **Billing**: Usage-based pricing
- **Multi-cluster**: Workload distribution across clusters

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.11+
- Node.js 18+
- kubectl & Helm (for Kubernetes deployment)

### Local Development (Docker Compose)

```bash
# Clone repository
git clone https://github.com/one-data-studio/smart-data-platform.git
cd smart-data-platform

# Start all services
docker-compose up -d

# Wait for services to be ready
# Backend: http://localhost:8000
# Frontend: http://localhost:3000
# API Docs: http://localhost:8000/docs
```

### Kubernetes Deployment

```bash
# Add Helm repository
helm repo add one-data-studio https://charts.one-data-studio.io
helm repo update

# Create namespace
kubectl create namespace one-data-studio

# Install
helm install one-data-studio one-data-studio/one-data-studio \
  --namespace one-data-studio \
  --set frontend.ingress.host=platform.example.com \
  --set backend.secretKey=$(openssl rand -hex 32)
```

See [Kubernetes Deployment Guide](../deployment/kubernetes-guide.md) for details.

## 📁 Project Structure

```
one-data-studio-lite/
├── apps/
│   ├── backend/              # FastAPI backend
│   │   ├── app/
│   │   │   ├── api/v1/       # API endpoints
│   │   │   ├── core/         # Config, security, database
│   │   │   ├── models/       # SQLAlchemy models
│   │   │   ├── schemas/      # Pydantic schemas
│   │   │   └── services/     # Business logic
│   │   ├── tests/
│   │   └── requirements.txt
│   │
│   ├── frontend/             # Next.js frontend
│   │   ├── src/
│   │   │   ├── components/   # React components
│   │   │   ├── pages/        # Next.js pages
│   │   │   ├── stores/       # Zustand state
│   │   │   └── styles/       # CSS modules
│   │   ├── public/
│   │   └── package.json
│   │
│   └── jupyter-hub/          # Jupyter Hub service
│
├── infrastructure/           # K8s configurations
│   ├── kubernetes/
│   │   ├── base/
│   │   ├── overlays/
│   │   └── helm/
│   └── monitoring/           # Prometheus, Grafana
│
├── deployment/
│   ├── docker/
│   └── scripts/
│
├── docs/                     # Documentation
│   ├── api/
│   ├── deployment/
│   └── development/
│
└── docker-compose.yml
```

## 🔧 Configuration

### Backend Configuration

Create `apps/backend/.env`:

```bash
# Application
APP_NAME=Smart Data Platform
APP_URL=http://localhost:3000
API_URL=http://localhost:8000

# Security
SECRET_KEY=your-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Database
DATABASE_URL=postgresql://user:password@localhost/onedatastudio

# Redis
REDIS_URL=redis://localhost:6379/0

# MinIO
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin

# SSO (Optional)
GOOGLE_OAUTH_CLIENT_ID=
GOOGLE_OAUTH_CLIENT_SECRET=
```

### Frontend Configuration

Create `apps/frontend/.env.local`:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_APP_URL=http://localhost:3000
```

## 📖 API Documentation

Interactive API documentation available at `/docs` when backend is running.

See [API Reference](../api/api-reference.md) for complete documentation.

## 🧪 Testing

### Backend Tests

```bash
cd apps/backend
pytest tests/
pytest tests/ -v --cov=app
```

### Frontend Tests

```bash
cd apps/frontend
npm test
npm run test:e2e
```

## 📊 Monitoring

### Prometheus Metrics

Backend exposes metrics at `/metrics`:

- Request count and latency
- Database query performance
- Cache hit rates
- Resource utilization

### Health Checks

- `/health` - Overall health status
- `/health/ready` - Readiness probe
- `/health/live` - Liveness probe

## 🤝 Contributing

Contributions are welcome! Please read our contributing guidelines before submitting PRs.

## 📄 License

Apache License 2.0 - see [LICENSE](../../LICENSE) for details.

## 🙏 Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [Next.js](https://nextjs.org/) - React framework
- [Ant Design](https://ant.design/) - UI components
- [MLflow](https://mlflow.org/) - Experiment tracking
- [Label Studio](https://labelstud.io/) - Data labeling
- [KServe](https://kserve.github.io/) - Model serving

## 📞 Support

- Documentation: https://docs.one-data-studio.io
- Community: https://github.com/one-data-studio/community
- Issues: https://github.com/one-data-studio/smart-data-platform/issues
