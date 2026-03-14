#!/bin/bash
#
# Airflow Initialization Script
# This script initializes the Airflow database and creates the admin user
#
# Usage: ./init_airflow.sh

set -e

echo "======================================"
echo "Initializing Apache Airflow for Smart Data Platform"
echo "======================================"

# Airflow configuration
export AIRFLOW_HOME=${AIRFLOW_HOME:-/opt/airflow}
export AIRFLOW__CORE__DAGS_FOLDER=${AIRFLOW__CORE__DAGS_FOLDER:-$AIRFLOW_HOME/dags}
export AIRFLOW__CORE__EXECUTOR=${AIRFLOW__CORE__EXECUTOR:-CeleryExecutor}
export AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=${AIRFLOW__DATABASE__SQL_ALCHEMY_CONN:-postgresql+psycopg2://airflow:airflow@airflow-postgres:5432/airflow}
export AIRFLOW__CELERY__BROKER_URL=${AIRFLOW__CELERY__BROKER_URL:-redis://:@airflow-redis:6379/0}
export AIRFLOW__CELERY__RESULT_BACKEND=${AIRFLOW__CELERY__RESULT_BACKEND:-db+postgresql://airflow:airflow@airflow-postgres:5432/airflow}
export AIRFLOW__CORE__LOAD_EXAMPLES=${AIRFLOW__CORE__LOAD_EXAMPLES:-False}
export AIRFLOW__WEBSERVER__SECRET_KEY=${AIRFLOW__WEBSERVER__SECRET_KEY:-temporary_secret_key_change_in_production}
export AIRFLOW__WEBSERVER__BASE_URL=${AIRFLOW__WEBSERVER__BASE_URL:-http://localhost:3108}
export AIRFLOW__CORE__UNIT_TEST_MODE=${AIRFLOW__CORE__UNIT_TEST_MODE:-False}
export AIRFLOW__CORE__DAG_DISCOVERY_SAFE_MODE=${AIRFLOW__CORE__DAG_DISCOVERY_SAFE_MODE:-False}

# User configuration
export _AIRFLOW_WWW_USER_CREATE=${_AIRFLOW_WWW_USER_CREATE:-true}
export _AIRFLOW_WWW_USER_USERNAME=${_AIRFLOW_WWW_USER_USERNAME:-admin}
export _AIRFLOW_WWW_USER_PASSWORD=${_AIRFLOW_WWW_USER_PASSWORD:-admin}
export _AIRFLOW_WWW_USER_EMAIL=${_AIRFLOW_WWW_USER_EMAIL:-admin@onedatastudio.io}
export _AIRFLOW_WWW_USER_FIRSTNAME=${_AIRFLOW_WWW_USER_FIRSTNAME:-Admin}
export _AIRFLOW_WWW_USER_LASTNAME=${_AIRFLOW_WWW_USER_LASTNAME:-User}

# Upgrade flag
export _AIRFLOW_DB_UPGRADE=${_AIRFLOW_DB_UPGRADE:-true}

# Create necessary directories
echo "Creating Airflow directories..."
mkdir -p "$AIRFLOW_HOME/dags"
mkdir -p "$AIRFLOW_HOME/logs"
mkdir -p "$AIRFLOW_HOME/plugins"

echo ""
echo "Waiting for PostgreSQL to be ready..."
until PGPASSWORD=airflow psql -h airflow-postgres -U airflow -c '\q'; do
  echo "PostgreSQL is unavailable - sleeping"
  sleep 2
done

echo "PostgreSQL is ready!"
echo ""
echo "Waiting for Redis to be ready..."
until redis-cli -h airflow-redis ping; do
  echo "Redis is unavailable - sleeping"
  sleep 2
done

echo "Redis is ready!"
echo ""

# Initialize the database
if [ "$_AIRFLOW_DB_UPGRADE" = "true" ]; then
    echo "Initializing Airflow database..."
    airflow db init
    echo "Database initialized!"
fi

# Create admin user
if [ "$_AIRFLOW_WWW_USER_CREATE" = "true" ]; then
    echo "Creating admin user..."
    airflow users create \
        --username "$_AIRFLOW_WWW_USER_USERNAME" \
        --password "$_AIRFLOW_WWW_USER_PASSWORD" \
        --email "$_AIRFLOW_WWW_USER_EMAIL" \
        --firstname "$_AIRFLOW_WWW_USER_FIRSTNAME" \
        --lastname "$_AIRFLOW_WWW_USER_LASTNAME" \
        --role Admin || echo "User may already exist, skipping..."
    echo "Admin user created!"
fi

echo ""
echo "======================================"
echo "Airflow initialization complete!"
echo "======================================"
echo ""
echo "Airflow Webserver: http://localhost:3108"
echo "Username: $_AIRFLOW_WWW_USER_USERNAME"
echo "Password: $_AIRFLOW_WWW_USER_PASSWORD"
echo ""
echo "Airflow Flower (Celery Monitor): http://localhost:3109"
echo ""
