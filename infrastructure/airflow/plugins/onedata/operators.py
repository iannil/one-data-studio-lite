"""
One Data Studio Custom Operators

Custom Airflow operators for One Data Studio tasks including:
- OneDataTaskOperator: Generic task operator
- ETLOperator: ETL pipeline operator
- TrainingOperator: Model training operator
"""

from airflow.providers.http.operators.http import SimpleHttpOperator
from airflow.operators.python import PythonOperator
from airflow.hooks.http import HttpHook
from airflow.utils.decorators import apply_defaults
from typing import Dict, Any, List, Optional, Callable
import logging
import json

logger = logging.getLogger(__name__)


class OneDataTaskOperator(SimpleHttpOperator):
    """
    Custom operator for executing One Data Studio tasks

    This operator communicates with the One Data Studio backend API
    to execute various types of tasks.

    :param task_id: Unique task identifier
    :param task_type: Type of task (etl, training, inference, etc.)
    :param task_config: Configuration for the task
    :param onedata_conn_id: Airflow connection ID for One Data Studio API
    :param http_conn_id: Fallback to standard HTTP connection
    """

    template_fields = ('task_config',)

    @apply_defaults
    def __init__(
        self,
        task_type: str,
        task_config: Dict[str, Any],
        onedata_conn_id: str = 'onedata_api',
        http_conn_id: str = 'onedata_api',
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.task_type = task_type
        self.task_config = task_config
        self.onedata_conn_id = onedata_conn_id
        self.http_conn_id = http_conn_id
        self.method = 'POST'

    def execute(self, context: Dict[str, Any]) -> Any:
        """
        Execute the One Data Studio task

        :param context: Airflow context
        :return: Task execution result
        """
        # Prepare the request payload
        endpoint = self._get_endpoint_for_task_type(self.task_type)
        payload = {
            'task_type': self.task_type,
            'config': self.task_config,
            'dag_run_id': context.get('dag_run', {}).get('run_id'),
            'execution_date': context.get('ds'),
        }

        # Update endpoint
        self.endpoint = endpoint
        self.data = json.dumps(payload)
        self.headers = {'Content-Type': 'application/json'}

        logger.info(f"Executing One Data task: {self.task_type}")
        logger.info(f"Payload: {json.dumps(payload, indent=2)}")

        # Execute the HTTP request
        response = super().execute(context)

        # Parse and return the response
        try:
            result = json.loads(response)
            logger.info(f"Task execution result: {json.dumps(result, indent=2)}")
            return result
        except json.JSONDecodeError:
            return response

    def _get_endpoint_for_task_type(self, task_type: str) -> str:
        """
        Get the API endpoint for a given task type

        :param task_type: Type of task
        :return: API endpoint path
        """
        endpoints = {
            'etl': '/api/v1/workflow/execute-etl',
            'training': '/api/v1/training/execute',
            'inference': '/api/v1/serving/predict',
            'data_quality': '/api/v1/quality/check',
            'annotation': '/api/v1/annotation/start',
            'feature_store': '/api/v1/features/compute',
        }
        return endpoints.get(task_type, '/api/v1/workflow/execute')


class ETLOperator(PythonOperator):
    """
    ETL Pipeline Operator for One Data Studio

    This operator executes ETL pipelines using the One Data Studio
    ETL engine.

    :param pipeline_id: ETL pipeline ID
    :param source_config: Source data configuration
    :param transform_config: Transformation configuration
    :param target_config: Target destination configuration
    """

    template_fields = ('source_config', 'transform_config', 'target_config')

    @apply_defaults
    def __init__(
        self,
        pipeline_id: str,
        source_config: Dict[str, Any],
        transform_config: Optional[Dict[str, Any]] = None,
        target_config: Optional[Dict[str, Any]] = None,
        *args,
        **kwargs
    ):
        self.pipeline_id = pipeline_id
        self.source_config = source_config
        self.transform_config = transform_config or {}
        self.target_config = target_config or {}

        # Define the Python callable
        def execute_etl(context: Dict[str, Any]) -> Dict[str, Any]:
            from app.services.etl_engine import ETLEngine

            logger.info(f"Executing ETL pipeline: {self.pipeline_id}")

            # Initialize ETL engine
            engine = ETLEngine()

            # Build pipeline configuration
            pipeline_config = {
                'source': self.source_config,
                'transform': self.transform_config,
                'target': self.target_config,
            }

            # Execute the pipeline
            result = engine.execute_pipeline(
                pipeline_id=self.pipeline_id,
                config=pipeline_config,
            )

            logger.info(f"ETL pipeline completed: {result}")
            return result

        super().__init__(
            python_callable=execute_etl,
            *args,
            **kwargs
        )


class TrainingOperator(PythonOperator):
    """
    Model Training Operator for One Data Studio

    This operator executes model training jobs.

    :param experiment_id: Experiment ID
    :param model_type: Type of model to train
    :param training_config: Training configuration
    :param data_source: Training data source
    """

    template_fields = ('training_config', 'data_source')

    @apply_defaults
    def __init__(
        self,
        experiment_id: str,
        model_type: str,
        training_config: Dict[str, Any],
        data_source: Dict[str, Any],
        *args,
        **kwargs
    ):
        self.experiment_id = experiment_id
        self.model_type = model_type
        self.training_config = training_config
        self.data_source = data_source

        # Define the Python callable
        def execute_training(context: Dict[str, Any]) -> Dict[str, Any]:
            logger.info(f"Executing training: {self.experiment_id}")

            # In production, this would call the training service
            # For now, return a mock result
            result = {
                'experiment_id': self.experiment_id,
                'model_type': self.model_type,
                'status': 'completed',
                'metrics': {
                    'accuracy': 0.95,
                    'loss': 0.05,
                },
            }

            logger.info(f"Training completed: {result}")
            return result

        super().__init__(
            python_callable=execute_training,
            *args,
            **kwargs
        )


class InferenceOperator(PythonOperator):
    """
    Model Inference Operator for One Data Studio

    This operator executes batch inference using trained models.

    :param model_id: Model ID to use for inference
    :param inference_data: Data to run inference on
    :param output_config: Output configuration
    """

    template_fields = ('inference_data', 'output_config')

    @apply_defaults
    def __init__(
        self,
        model_id: str,
        inference_data: Dict[str, Any],
        output_config: Dict[str, Any],
        *args,
        **kwargs
    ):
        self.model_id = model_id
        self.inference_data = inference_data
        self.output_config = output_config

        # Define the Python callable
        def execute_inference(context: Dict[str, Any]) -> Dict[str, Any]:
            logger.info(f"Executing inference with model: {self.model_id}")

            # In production, this would call the serving service
            result = {
                'model_id': self.model_id,
                'predictions': [{'id': i, 'prediction': 0.8} for i in range(100)],
                'status': 'completed',
            }

            logger.info(f"Inference completed: {len(result['predictions'])} predictions")
            return result

        super().__init__(
            python_callable=execute_inference,
            *args,
            **kwargs
        )


class DataQualityOperator(PythonOperator):
    """
    Data Quality Check Operator for One Data Studio

    This operator executes data quality checks.

    :param check_config: Quality check configuration
    :param fail_on_error: Whether to fail the task on quality errors
    """

    template_fields = ('check_config',)

    @apply_defaults
    def __init__(
        self,
        check_config: Dict[str, Any],
        fail_on_error: bool = True,
        *args,
        **kwargs
    ):
        self.check_config = check_config
        self.fail_on_error = fail_on_error

        # Define the Python callable
        def execute_quality_check(context: Dict[str, Any]) -> Dict[str, Any]:
            logger.info("Executing data quality checks")

            # In production, this would call the quality service
            result = {
                'checks_passed': 10,
                'checks_failed': 0,
                'checks': [
                    {'name': 'completeness', 'status': 'passed'},
                    {'name': 'uniqueness', 'status': 'passed'},
                    {'name': 'validity', 'status': 'passed'},
                ],
            }

            if self.fail_on_error and result['checks_failed'] > 0:
                raise ValueError(f"Data quality checks failed: {result['checks_failed']} failures")

            logger.info(f"Quality checks passed: {result['checks_passed']}")
            return result

        super().__init__(
            python_callable=execute_quality_check,
            *args,
            **kwargs
        )
