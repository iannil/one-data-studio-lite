"""
Example ETL Pipeline DAG for Smart Data Platform

This example demonstrates a typical ETL pipeline with:
1. Data extraction from source
2. Data transformation
3. Data loading to destination
4. Data quality checks
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.sql import SQLExecuteQueryOperator
from datetime import datetime, timedelta
import pandas as pd
import logging

# Default arguments for the DAG
default_args = {
    'owner': 'onedata',
    'depends_on_past': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'execution_timeout': timedelta(hours=2),
}

# Create the DAG
with DAG(
    'etl_pipeline_example',
    default_args=default_args,
    description='Example ETL Pipeline - Extract, Transform, Load',
    schedule_interval='0 2 * * *',  # Run daily at 2 AM
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['etl', 'example', 'pipeline'],
    max_active_runs=1,
    concurrency=4,
) as dag:

    def extract_data(**context):
        """
        Extract data from source system
        """
        logging.info("Starting data extraction...")

        # Get parameters from DAG run configuration
        params = context.get('params', {})
        source_table = params.get('source_table', 'source_data')
        date = context['ds']

        # Simulate data extraction
        # In production, this would connect to actual data sources
        data = {
            'id': range(1, 101),
            'name': [f'Item_{i}' for i in range(1, 101)],
            'value': [i * 10 for i in range(1, 101)],
            'category': ['A', 'B', 'C', 'D'] * 25,
            'date': [date] * 100,
        }

        df = pd.DataFrame(data)
        logging.info(f"Extracted {len(df)} rows")

        # Push data to XCom for next task
        return df.to_json()

    def transform_data(**context):
        """
        Transform extracted data
        """
        logging.info("Starting data transformation...")

        # Get data from previous task
        ti = context['ti']
        data_json = ti.xcom_pull(task_ids='extract')
        df = pd.read_json(data_json)

        # Apply transformations
        df['value_doubled'] = df['value'] * 2
        df['category_upper'] = df['category'].str.upper()

        # Filter data
        df_filtered = df[df['value'] > 50]

        logging.info(f"Transformed and filtered to {len(df_filtered)} rows")

        return df_filtered.to_json()

    def load_data(**context):
        """
        Load transformed data to destination
        """
        logging.info("Starting data load...")

        # Get data from previous task
        ti = context['ti']
        data_json = ti.xcom_pull(task_ids='transform')
        df = pd.read_json(data_json)

        # Simulate loading data
        # In production, this would write to database or data warehouse
        logging.info(f"Loaded {len(df)} rows to destination")
        logging.info(f"Summary statistics:\n{df.describe()}")

        return len(df)

    def check_data_quality(**context):
        """
        Perform data quality checks
        """
        logging.info("Starting data quality checks...")

        # Get data from previous task
        ti = context['ti']
        row_count = ti.xcom_pull(task_ids='load')

        # Define quality checks
        checks = {
            'row_count': row_count > 0,
            'has_data': row_count is not None,
        }

        all_passed = all(checks.values())

        if not all_passed:
            failed_checks = [k for k, v in checks.items() if not v]
            raise ValueError(f"Data quality checks failed: {failed_checks}")

        logging.info(f"All data quality checks passed! Rows loaded: {row_count}")
        return all_passed

    # Define tasks
    extract_task = PythonOperator(
        task_id='extract',
        python_callable=extract_data,
    )

    transform_task = PythonOperator(
        task_id='transform',
        python_callable=transform_data,
    )

    load_task = PythonOperator(
        task_id='load',
        python_callable=load_data,
    )

    quality_check_task = PythonOperator(
        task_id='quality_check',
        python_callable=check_data_quality,
    )

    # Example SQL task (requires database connection)
    # verify_data_task = SQLExecuteQueryOperator(
    #     task_id='verify_data',
    #     conn_id='postgres_default',
    #     sql="""
    #         SELECT COUNT(*) as row_count
    #         FROM destination_table
    #         WHERE date = '{{ ds }}'
    #     """,
    # )

    # Define task dependencies
    extract_task >> transform_task >> load_task >> quality_check_task
    # quality_check_task >> verify_data_task
