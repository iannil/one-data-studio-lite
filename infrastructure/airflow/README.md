# Apache Airflow Integration

This folder contains the Apache Airflow configuration and integration files for the Smart Data Platform.

## Overview

Apache Airflow is used as the workflow orchestration engine for the platform. It provides:

- **DAG Scheduling**: Schedule and execute data pipelines
- **Task Management**: Execute ETL, training, and data quality tasks
- **Backfill Support**: Re-run historical data pipelines
- **Monitoring**: Track task execution via Airflow UI and Flower
- **Scalability**: CeleryExecutor for distributed task execution

## Quick Start

### 1. Start Airflow Services

```bash
# From the project root
docker-compose -f docker-compose.yml -f infrastructure/airflow/docker-compose-airflow.yml up -d

# Or just start Airflow services
docker-compose -f infrastructure/airflow/docker-compose-airflow.yml up -d
```

### 2. Access Airflow

- **Airflow Web UI**: http://localhost:3108
  - Default username: `admin`
  - Default password: `admin`
- **Flower (Celery Monitor)**: http://localhost:3109

### 3. Configuration

Edit `.env` file to customize:

```bash
# Airflow Configuration
AIRFLOW_SECRET_KEY=your-secret-key-here
AIRFLOW_USERNAME=admin
AIRFLOW_PASSWORD=admin
```

## Directory Structure

```
infrastructure/airflow/
├── docker-compose-airflow.yml    # Airflow services compose file
├── config/
│   └── airflow.cfg               # Airflow configuration
├── dags/                          # DAG files folder
│   └── examples/                  # Example DAGs
├── plugins/                       # Custom Airflow plugins
│   └── onedata/                   # One Data custom plugins
├── logs/                          # Airflow logs
└── init_airflow.sh                # Initialization script
```

## Services

### airflow-postgres
PostgreSQL database for Airflow metadata.

- Port: 5432 (internal)
- Database: `airflow`
- User: `airflow`

### airflow-redis
Redis broker for Celery.

- Port: 6379 (internal)

### airflow-webserver
Airflow web server and API.

- Port: 3108
- Health: http://localhost:3108/health

### airflow-scheduler
Airflow scheduler for DAG execution.

### airflow-worker
Celery workers for task execution.

- Concurrency: 16 (configurable)

### airflow-flower
Flower for Celery monitoring.

- Port: 3109

## DAG Management

### Creating DAGs

Place Python files in `dags/` folder:

```python
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'onedata',
    'depends_on_past': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'my_dag',
    default_args=default_args,
    start_date=datetime(2024, 1, 1),
    schedule_interval='0 0 * * *',
    catchup=False,
    tags=['etl', 'daily'],
) as dag:
    def my_task():
        print("Hello from Airflow!")

    task1 = PythonOperator(
        task_id='task1',
        python_callable=my_task,
    )
```

### DAG Synchronization

The platform automatically syncs DAG definitions from the database to the Airflow DAGs folder.

## Integration with One Data Studio

### Backend Integration

The backend integrates with Airflow through:

1. **DAG Engine Service** (`apps/backend/app/services/workflow/dag_engine.py`)
   - Creates/updates DAGs in Airflow
   - Triggers DAG runs
   - Queries DAG status

2. **Task Handlers** (`apps/backend/app/services/workflow/task_handlers.py`)
   - Executes tasks within Airflow
   - Handles task retries and failures

3. **Scheduler Service** (`apps/backend/app/scheduler_service.py`)
   - Schedules DAGs from the database
   - Manages backfill operations

### API Endpoints

- `POST /api/v1/workflows/{dag_id}/trigger` - Trigger a DAG run
- `GET /api/v1/workflows/{dag_id}/runs` - Get DAG runs
- `GET /api/v1/workflows/{dag_id}/status` - Get DAG status
- `POST /api/v1/workflows/{dag_id}/backfill` - Trigger backfill

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `AIRFLOW_SECRET_KEY` | Secret key for session encryption | temporary_secret_key |
| `AIRFLOW_USERNAME` | Admin username | admin |
| `AIRFLOW_PASSWORD` | Admin password | admin |

## Troubleshooting

### Reset Airflow Database

```bash
# Stop Airflow
docker-compose -f infrastructure/airflow/docker-compose-airflow.yml down -v

# Start Airflow (will reinitialize)
docker-compose -f infrastructure/airflow/docker-compose-airflow.yml up -d
```

### View Logs

```bash
# View webserver logs
docker logs onedata-airflow-webserver -f

# View scheduler logs
docker logs onedata-airflow-scheduler -f

# View worker logs
docker logs onedata-airflow-worker -f
```

### DAG Not Appearing

1. Check DAG file syntax: `python dags/your_dag.py`
2. Check scheduler logs for errors
3. Wait for DAG folder refresh (30 seconds)
4. Verify DAG has no import errors in Airflow UI

## Production Considerations

1. **Secret Key**: Change `AIRFLOW_SECRET_KEY` in production
2. **Database**: Consider using external PostgreSQL
3. **Redis**: Consider using external Redis
4. **Persistence**: Ensure volumes are properly mounted
5. **HTTPS**: Use reverse proxy (nginx) for HTTPS
6. **Authentication**: Configure LDAP/OAuth for production

## References

- [Apache Airflow Documentation](https://airflow.apache.org/docs/)
- [Airflow Providers](https://airflow.apache.org/docs/apache-airflow-providers/)
- [Celery Documentation](https://docs.celeryproject.org/)
