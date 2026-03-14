# MLOps Services

This directory contains configuration and initialization scripts for the MLOps services in the Smart Data Platform.

## Services

### MLflow (Model Lifecycle Management)

**Port:** 5000
**UI:** http://localhost:5000

MLflow is an open-source platform for the machine learning lifecycle. It provides:

- **Experiment Tracking:** Log and query experiments (code, data, config, results)
- **Model Registry:** Centralized model store, model metadata, and stage transitions
- **Projects:** Packaging reproducible data science code
- **Model Serving:** Deploy models for inference (REST API)

#### Usage

Start MLflow:
```bash
docker-compose up -d mlflow
```

Initialize MLflow database and buckets:
```bash
docker-compose exec mlflow python /mlflow/config/init_mlflow.py
```

#### Python Client Usage

```python
from app.services.model.mlflow_client import get_mlflow_client

mlflow = get_mlflow_client()

# Create experiment
exp_id = await mlflow.create_experiment("my-experiment")

# Log parameters and metrics
run_id = await mlflow.create_run(exp_id, "my-run")
await mlflow.log_param(run_id, "learning_rate", 0.001)
await mlflow.log_metric(run_id, "accuracy", 0.95)

# Log model
await mlflow.log_model(run_id, "model_path", model_type="sklearn")
```

### TensorFlow Serving

**Ports:**
- 8501: REST API
- 9000: gRPC API

#### Usage (GPU)
```bash
docker-compose --profile gpu up -d tf-serving
```

#### Usage (CPU)
```bash
docker-compose -f docker-compose.yml -f docker-compose.mlops.yml --profile mlops-cpu up -d tf-serving-cpu
```

#### REST API Example

```bash
# Predict
curl -d '{"instances": [[1.0, 2.0, 3.0]]}' \
  -X POST http://localhost:8501/v1/models/sample_model:predict
```

### TorchServe

**Ports:**
- 8080: Inference API
- 8081: Management API
- 8082: Metrics API

#### Usage (GPU)
```bash
docker-compose --profile gpu up -d torchserve
```

#### Usage (CPU)
```bash
docker-compose -f docker-compose.yml -f docker-compose.mlops.yml --profile mlops-cpu up -d torchserve-cpu
```

#### API Examples

```bash
# List models
curl http://localhost:8081/models

# Get model info
curl http://localhost:8081/models/my-model

# Predict
curl -X POST http://localhost:8080/predictions/my-model \
  -H "Content-Type: application/json" \
  -d '{"data": [[1.0, 2.0, 3.0]]}'
```

### Triton Inference Server

**Ports:**
- 8001: HTTP/REST
- 8002: gRPC
- 8003: Metrics

Triton supports multiple frameworks:
- TensorFlow
- PyTorch
- ONNX
- TensorRT
- OpenVINO

#### Usage
```bash
docker-compose --profile gpu up -d triton
```

### Optuna (Hyperparameter Optimization)

**Port:** 8083
**UI:** http://localhost:8083

#### Usage
```bash
docker-compose -f docker-compose.yml -f docker-compose.mlops.yml --profile mlops-optuna up -d optuna
```

#### Python Client

```python
import optuna

# Create study
study = optuna.create_study(
    study_name="my-study",
    storage="postgresql://postgres:postgres@localhost:5432/optuna",
    direction="maximize"
)

# Define objective
def objective(trial):
    x = trial.suggest_float("x", -10, 10)
    return (x - 2) ** 2

# Run optimization
study.optimize(objective, n_trials=100)
```

### Ray (Distributed Computing)

**Ports:**
- 8265: Dashboard
- 10001: Client
- 8000: Ray Serve

#### Usage
```bash
docker-compose -f docker-compose.yml -f docker-compose.mlops.yml --profile mlops-ray up -d ray-head
```

### Evidently AI (Model Monitoring)

**Port:** 8084

#### Usage
```bash
docker-compose -f docker-compose.yml -f docker-compose.mlops.yml --profile mlops-monitoring up -d evidently
```

### Feast (Feature Store)

**Port:** 6566

#### Usage
```bash
docker-compose -f docker-compose.yml -f docker-compose.mlops.yml --profile mlops-feast up -d feast
```

## Model Storage

Models are stored in MinIO under the following buckets:
- `mlflow/` - MLflow artifacts
- `models/` - Trained models
- `datasets/` - Training datasets
- `artifacts/` - Other artifacts

## Profiles Summary

| Profile | Services | Description |
|---------|----------|-------------|
| `mlops-cpu` | tf-serving-cpu, torchserve-cpu, onnxruntime, xgboost-server | CPU-based model serving |
| `mlops-optuna` | optuna | Hyperparameter optimization dashboard |
| `mlops-ray` | ray-head | Distributed computing |
| `mlops-monitoring` | evidently | Model monitoring |
| `mlops-feast` | feast | Feature store |
| `gpu` | tf-serving, torchserve, triton | GPU-accelerated serving |

## Quick Start

1. Start core services:
```bash
docker-compose up -d
```

2. Start MLflow:
```bash
docker-compose up -d mlflow
docker-compose exec mlflow python /mlflow/config/init_mlflow.py
```

3. Start model serving (choose one):
```bash
# CPU version
docker-compose -f docker-compose.yml -f docker-compose.mlops.yml --profile mlops-cpu up -d

# GPU version (requires NVIDIA runtime)
docker-compose --profile gpu up -d
```

4. Access dashboards:
- MLflow: http://localhost:5000
- Optuna: http://localhost:8083
- Ray: http://localhost:8265
