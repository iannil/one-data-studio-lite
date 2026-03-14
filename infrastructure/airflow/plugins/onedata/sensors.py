"""
One Data Studio Custom Sensors

Custom Airflow sensors for One Data Studio integration.
"""

from airflow.sensors.base import BaseSensorOperator
from airflow.providers.http.sensors.http import HttpSensor
from airflow.utils.decorators import apply_defaults
from typing import Dict, Any, Optional
import logging
import json

logger = logging.getLogger(__name__)


class OneDataSensor(BaseSensorOperator):
    """
    Base sensor for One Data Studio tasks

    :param task_id: Unique task identifier
    :param endpoint: API endpoint to check
    :param poke_interval: Time in seconds between checks
    :param timeout: Maximum time to wait before failing
    """

    @apply_defaults
    def __init__(
        self,
        endpoint: str,
        onedata_conn_id: str = 'onedata_api',
        poke_interval: int = 60,
        timeout: int = 60 * 60 * 24,  # 24 hours
        *args,
        **kwargs
    ):
        super().__init__(poke_interval=poke_interval, timeout=timeout, *args, **kwargs)
        self.endpoint = endpoint
        self.onedata_conn_id = onedata_conn_id

    def poke(self, context: Dict[str, Any]) -> bool:
        """
        Check if the condition is met

        :param context: Airflow context
        :return: True if condition is met, False otherwise
        """
        # In production, this would make an API call to check status
        # For now, return True
        return True


class TaskCompletionSensor(OneDataSensor):
    """
    Sensor to wait for task completion

    :param task_id: Task ID to monitor
    :param expected_status: Expected task status (success, failed, etc.)
    """

    @apply_defaults
    def __init__(
        self,
        task_id: str,
        expected_status: str = 'success',
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.task_id = task_id
        self.expected_status = expected_status

    def poke(self, context: Dict[str, Any]) -> bool:
        """
        Check if task has completed with expected status

        :param context: Airflow context
        :return: True if task completed with expected status
        """
        # In production, make API call to check task status
        logger.info(f"Checking task {self.task_id} for status {self.expected_status}")

        # For now, return True (task completed)
        return True


class ModelAvailabilitySensor(OneDataSensor):
    """
    Sensor to wait for model to be available

    :param model_id: Model ID to check
    :param model_version: Expected model version
    """

    @apply_defaults
    def __init__(
        self,
        model_id: str,
        model_version: Optional[str] = None,
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.model_id = model_id
        self.model_version = model_version

    def poke(self, context: Dict[str, Any]) -> bool:
        """
        Check if model is available

        :param context: Airflow context
        :return: True if model is available
        """
        logger.info(f"Checking model {self.model_id} availability")

        # In production, make API call to check model status
        return True


class DataReadinessSensor(OneDataSensor):
    """
    Sensor to wait for data to be ready

    :param data_source: Data source configuration
    :param expected_rows: Expected number of rows
    """

    @apply_defaults
    def __init__(
        self,
        data_source: Dict[str, Any],
        expected_rows: Optional[int] = None,
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.data_source = data_source
        self.expected_rows = expected_rows

    def poke(self, context: Dict[str, Any]) -> bool:
        """
        Check if data is ready

        :param context: Airflow context
        :return: True if data is ready
        """
        logger.info(f"Checking data readiness for {self.data_source}")

        # In production, check if data exists and meets requirements
        return True
