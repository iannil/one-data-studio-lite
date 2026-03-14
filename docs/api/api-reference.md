# API Reference

Complete API documentation for the Smart Data Platform.

## Base URL

```
Production: https://api.example.com/api/v1
Development: http://localhost:8000/api/v1
```

## Authentication

All API requests require authentication using JWT tokens.

```bash
# Get token
curl -X POST https://api.example.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password"}'

# Use token
curl https://api.example.com/api/v1/users/me \
  -H "Authorization: Bearer <token>"
```

## Core APIs

### Authentication

#### POST /auth/login
Login with email and password.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**Response:**
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "full_name": "John Doe"
  }
}
```

#### POST /auth/register
Register a new user account.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "password123",
  "full_name": "John Doe"
}
```

#### POST /auth/refresh
Refresh access token.

**Request:**
```json
{
  "refresh_token": "eyJ..."
}
```

### SSO Authentication

#### GET /auth/sso/{provider}/authorize
Initiate OAuth2 flow with provider.

**Providers:** `google`, `github`, `microsoft`, `azure_ad`

**Response:**
```json
{
  "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth?...",
  "state": "uuid"
}
```

#### POST /auth/sso/{provider}/callback
OAuth2 callback handler.

**Request:**
```json
{
  "code": "authorization_code",
  "state": "state_value"
}
```

#### POST /auth/sso/ldap
LDAP authentication.

**Request:**
```json
{
  "username": "jdoe",
  "password": "password"
}
```

### User Management

#### GET /users/me
Get current user profile.

**Response:**
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "full_name": "John Doe",
  "is_active": true,
  "created_at": "2024-01-01T00:00:00Z"
}
```

#### PUT /users/me
Update user profile.

**Request:**
```json
{
  "full_name": "John Smith",
  "avatar_url": "https://example.com/avatar.jpg"
}
```

#### GET /users
List users (admin only).

**Query Parameters:**
- `page`: Page number (default: 1)
- `limit`: Items per page (default: 50)
- `search`: Search by email or name

**Response:**
```json
{
  "items": [...],
  "total": 100,
  "page": 1,
  "pages": 2
}
```

### Data Source Management

#### GET /sources
List all data sources.

**Response:**
```json
[
  {
    "id": "uuid",
    "name": "Production DB",
    "type": "postgresql",
    "host": "db.example.com",
    "port": 5432,
    "database": "production",
    "status": "connected"
  }
]
```

#### POST /sources
Create a new data source.

**Request:**
```json
{
  "name": "Production DB",
  "type": "postgresql",
  "host": "db.example.com",
  "port": 5432,
  "database": "production",
  "username": "user",
  "password": "password"
}
```

#### GET /sources/{id}/test
Test data source connection.

**Response:**
```json
{
  "status": "success",
  "latency_ms": 45
}
```

#### POST /sources/{id}/sync
Sync metadata from data source.

**Response:**
```json
{
  "job_id": "uuid",
  "status": "running"
}
```

### ETL Pipelines

#### GET /etl/pipelines
List ETL pipelines.

**Response:**
```json
[
  {
    "id": "uuid",
    "name": "Daily Data Sync",
    "status": "running",
    "schedule": "0 2 * * *",
    "last_run": "2024-03-14T02:00:00Z",
    "next_run": "2024-03-15T02:00:00Z"
  }
]
```

#### POST /etl/pipelines
Create a new pipeline.

**Request:**
```json
{
  "name": "Data Sync",
  "description": "Sync data daily",
  "source_id": "uuid",
  "target_id": "uuid",
  "schedule": "0 2 * * *",
  "config": {
    "mode": "incremental",
    "key_column": "id"
  }
}
```

#### POST /etl/pipelines/{id}/run
Manually trigger pipeline execution.

**Response:**
```json
{
  "run_id": "uuid",
  "status": "started"
}
```

#### GET /etl/pipelines/{id}/runs
List pipeline runs.

**Query Parameters:**
- `status`: Filter by status
- `limit`: Max results

### Workflow / DAG

#### GET /workflows
List all workflows.

**Response:**
```json
[
  {
    "id": "uuid",
    "name": "ML Training Pipeline",
    "status": "active",
    "nodes": 5,
    "edges": 4
  }
]
```

#### POST /workflows
Create a workflow.

**Request:**
```json
{
  "name": "ML Pipeline",
  "description": "Training workflow",
  "nodes": [
    {
      "id": "node1",
      "type": "data_load",
      "config": {"source_id": "uuid"}
    },
    {
      "id": "node2",
      "type": "training",
      "config": {"model": "xgboost"}
    }
  ],
  "edges": [
    {"from": "node1", "to": "node2"}
  ]
}
```

#### POST /workflows/{id}/execute
Execute a workflow.

**Request:**
```json
{
  "parameters": {
    "learning_rate": 0.001,
    "epochs": 100
  }
}
```

#### GET /workflows/{id}/runs
List workflow executions.

### Experiments

#### GET /experiments
List experiments.

**Response:**
```json
[
  {
    "id": "uuid",
    "name": "Churn Prediction",
    "project_id": "uuid",
    "mlflow_exp_id": "1",
    "created_at": "2024-03-01T00:00:00Z"
  }
]
```

#### POST /experiments
Create a new experiment.

**Request:**
```json
{
  "name": "Churn Prediction",
  "description": "Customer churn ML experiment",
  "project_id": "uuid"
}
```

#### GET /experiments/{id}/runs
List runs in experiment.

**Query Parameters:**
- `status`: Filter by status
- `order`: Order by metric

**Response:**
```json
[
  {
    "run_id": "uuid",
    "mlflow_run_id": "abc123",
    "status": "completed",
    "params": {"learning_rate": 0.001},
    "metrics": {"accuracy": 0.95, "f1": 0.93},
    "start_time": "2024-03-14T10:00:00Z",
    "end_time": "2024-03-14T10:30:00Z"
  }
]
```

#### POST /experiments/{id}/runs
Create a new run.

**Request:**
```json
{
  "params": {
    "learning_rate": 0.001,
    "batch_size": 32
  },
  "tags": ["baseline"]
}
```

#### POST /experiments/runs/{run_id}/log
Log metrics to a run.

**Request:**
```json
{
  "metrics": {
    "accuracy": 0.95,
    "loss": 0.05
  },
  "step": 100
}
```

### Model Management

#### GET /models
List registered models.

**Response:**
```json
[
  {
    "id": "uuid",
    "name": "churn-predictor",
    "framework": "xgboost",
    "version_count": 5,
    "latest_version": {
      "version": "v5",
      "stage": "production",
      "metrics": {"accuracy": 0.95}
    }
  }
]
```

#### POST /models
Register a new model.

**Request:**
```json
{
  "name": "churn-predictor",
  "description": "Customer churn prediction",
  "framework": "xgboost",
  "task_type": "classification"
}
```

#### POST /models/{id}/versions
Create a new model version.

**Request:**
```json
{
  "run_id": "uuid",
  "model_uri": "s3://models/churn/v5",
  "metrics": {"accuracy": 0.95}
}
```

#### PUT /models/{id}/stage
Transition model stage.

**Request:**
```json
{
  "version": "v5",
  "stage": "production"
}
```

### Model Serving

#### GET /serving/deployments
List model deployments.

**Response:**
```json
[
  {
    "id": "uuid",
    "name": "churn-api",
    "model_version_id": "uuid",
    "endpoint": "https://churn-api.example.com",
    "status": "healthy",
    "replicas": 3,
    "traffic_ratio": 1.0
  }
]
```

#### POST /serving/deployments
Deploy a model.

**Request:**
```json
{
  "name": "churn-api",
  "model_version_id": "uuid",
  "replicas": 3,
  "gpu_enabled": false,
  "resources": {
    "cpu": "1000m",
    "memory": "2Gi"
  }
}
```

#### POST /serving/deployments/{id}/scale
Scale deployment.

**Request:**
```json
{
  "replicas": 5
}
```

#### POST /serving/deployments/{id}/traffic
Update traffic routing (for canary).

**Request:**
```json
{
  "version_traffic": {
    "v5": 0.9,
    "v6": 0.1
  }
}
```

### LLM / Chat

#### POST /llm/chat
Send a chat message.

**Request:**
```json
{
  "model": "chatglm3-6b",
  "messages": [
    {"role": "user", "content": "Hello!"}
  ],
  "stream": false,
  "temperature": 0.7
}
```

**Response:**
```json
{
  "message": {
    "role": "assistant",
    "content": "Hello! How can I help you today?"
  },
  "usage": {
    "prompt_tokens": 10,
    "completion_tokens": 20,
    "total_tokens": 30
  }
}
```

#### POST /llm/completions
Text completion (compatible with OpenAI format).

**Request:**
```json
{
  "model": "qwen-14b",
  "prompt": "Write a poem about data.",
  "max_tokens": 100,
  "temperature": 0.8
}
```

### Knowledge Base

#### GET /knowledge/bases
List knowledge bases.

**Response:**
```json
[
  {
    "id": "uuid",
    "name": "Company Docs",
    "embedding_model": "bge-large-zh",
    "document_count": 150,
    "chunk_count": 15000
  }
]
```

#### POST /knowledge/bases
Create a knowledge base.

**Request:**
```json
{
  "name": "Company Docs",
  "description": "Internal documentation",
  "embedding_model": "bge-large-zh",
  "chunk_size": 500,
  "chunk_overlap": 50
}
```

#### POST /knowledge/bases/{id}/documents
Add a document.

**Request:**
```json
{
  "title": "Employee Handbook",
  "content": "...",
  "source_uri": "https://docs.example.com/handbook.pdf"
}
```

#### POST /knowledge/bases/{id}/search
Semantic search.

**Request:**
```json
{
  "query": "What is the vacation policy?",
  "top_k": 5
}
```

**Response:**
```json
{
  "results": [
    {
      "chunk_id": "uuid",
      "content": "...",
      "score": 0.89,
      "metadata": {"document_id": "uuid"}
    }
  ]
}
```

#### POST /knowledge/bases/{id}/ask
RAG-powered Q&A.

**Request:**
```json
{
  "question": "What is the vacation policy?"
}
```

**Response:**
```json
{
  "answer": "According to the employee handbook...",
  "sources": [
    {
      "document_id": "uuid",
      "chunk_id": "uuid",
      "score": 0.89
    }
  ]
}
```

### Billing

#### GET /billing/subscription
Get current subscription.

**Response:**
```json
{
  "id": "uuid",
  "plan": "professional",
  "status": "active",
  "current_period_end": "2024-04-01T00:00:00Z"
}
```

#### PUT /billing/subscription
Update subscription plan.

**Request:**
```json
{
  "plan": "professional"
}
```

#### GET /billing/invoices
List invoices.

**Response:**
```json
[
  {
    "id": "uuid",
    "invoice_number": "INV-202603-001001",
    "period_start": "2024-03-01T00:00:00Z",
    "period_end": "2024-03-31T23:59:59Z",
    "total": 99.00,
    "status": "paid"
  }
]
```

#### GET /billing/usage
Get usage summary.

**Query Parameters:**
- `start_date`: Period start
- `end_date`: Period end

**Response:**
```json
{
  "usage": {
    "cpu_hour": 45.5,
    "api_request": 5000
  },
  "total_cost": 12.50,
  "free_tier_remaining": {
    "cpu_hour": 54.5,
    "api_request": 5000
  }
}
```

### Cluster Management

#### GET /cluster/clusters
List clusters.

**Response:**
```json
[
  {
    "id": "uuid",
    "name": "production-us-west",
    "type": "managed",
    "status": "active",
    "region": "us-west-2",
    "node_count": 12,
    "cpu_capacity": 192,
    "utilization": {
      "cpu_percent": 65
    }
  }
]
```

#### POST /cluster/clusters
Register a cluster.

**Request:**
```json
{
  "name": "production-cluster",
  "type": "managed",
  "api_endpoint": "https://cluster.example.com",
  "region": "us-west-2"
}
```

#### GET /cluster/clusters/{id}/metrics
Get cluster metrics.

**Response:**
```json
{
  "cpu_usage_percent": 65,
  "memory_usage_percent": 72,
  "pods_running": 150,
  "nodes_ready": 12
}
```

#### POST /cluster/jobs/schedule
Schedule a job on a cluster.

**Request:**
```json
{
  "name": "training-job",
  "cpu_request": 8,
  "memory_request_gb": 32,
  "gpu_request": 2,
  "preferred_regions": ["us-west-2"]
}
```

## Error Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 409 | Conflict |
| 422 | Validation Error |
| 429 | Rate Limit Exceeded |
| 500 | Internal Server Error |

## Rate Limits

| Plan | Requests/Minute |
|------|-----------------|
| Free | 10 |
| Basic | 60 |
| Professional | 300 |
| Enterprise | 1000 |

Rate limit headers are included in responses:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1647225600
```
