"""
DAG Engine for One Data Studio Lite

Wrapper around Apache Airflow for DAG management and execution.
"""

import logging
import tempfile
import os
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass

from .task_types import TaskConfig, TaskRegistry, TaskType

logger = logging.getLogger(__name__)


@dataclass
class DAGConfig:
    """DAG configuration"""

    dag_id: str
    description: Optional[str] = None
    schedule_interval: Optional[str] = None  # Cron expression or None for manual
    start_date: Optional[datetime] = None
    catchup: bool = False
    max_active_runs: int = 1
    tags: List[str] = None
    owner: str = "airflow"
    tasks: List[TaskConfig] = None

    def __post_init__(self):
        if self.tasks is None:
            self.tasks = []
        if self.tags is None:
            self.tags = []
        if self.start_date is None:
            self.start_date = datetime.utcnow()


class DAGEngine:
    """
    DAG Engine wrapper

    Manages Airflow DAGs including creation, scheduling, and execution.
    """

    def __init__(
        self,
        airflow_api_url: str = "http://airflow-webserver:8080",
        airflow_username: str = "admin",
        airflow_password: str = "admin",
        dags_folder: str = "/opt/airflow/dags",
    ):
        """
        Initialize DAG Engine

        Args:
            airflow_api_url: Airflow webserver API URL
            airflow_username: Airflow username
            airflow_password: Airflow password
            dags_folder: Path to DAGs folder
        """
        self.airflow_api_url = airflow_api_url
        self.airflow_username = airflow_username
        self.airflow_password = airflow_password
        self.dags_folder = dags_folder

    async def create_dag(self, config: DAGConfig) -> Dict[str, Any]:
        """
        Create a new DAG from configuration

        Args:
            config: DAG configuration

        Returns:
            Created DAG info
        """
        # Validate configuration
        self._validate_dag_config(config)

        # Generate Airflow Python DAG file
        dag_code = self._generate_dag_code(config)

        # Write DAG file to DAGs folder
        dag_file_path = os.path.join(self.dags_folder, f"{config.dag_id}.py")
        with open(dag_file_path, "w") as f:
            f.write(dag_code)

        # Sync with Airflow
        await self._sync_dag(config.dag_id)

        return {
            "dag_id": config.dag_id,
            "file_path": dag_file_path,
            "created_at": datetime.utcnow().isoformat(),
        }

    async def update_dag(self, dag_id: str, config: DAGConfig) -> Dict[str, Any]:
        """
        Update an existing DAG

        Args:
            dag_id: DAG ID
            config: New DAG configuration

        Returns:
            Updated DAG info
        """
        # Delete old DAG file
        dag_file_path = os.path.join(self.dags_folder, f"{dag_id}.py")
        if os.path.exists(dag_file_path):
            os.remove(dag_file_path)

        # Create new DAG file
        return await self.create_dag(config)

    async def delete_dag(self, dag_id: str) -> bool:
        """
        Delete a DAG

        Args:
            dag_id: DAG ID

        Returns:
            True if successful
        """
        dag_file_path = os.path.join(self.dags_folder, f"{dag_id}.py")

        if os.path.exists(dag_file_path):
            os.remove(dag_file_path)
            return True

        return False

    async def trigger_dag_run(
        self,
        dag_id: str,
        conf: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Trigger a manual DAG run

        Args:
            dag_id: DAG ID
            conf: Configuration for the DAG run

        Returns:
            DAG run info
        """
        # This would call Airflow API to trigger the DAG run
        # For now, return a mock response
        return {
            "dag_run_id": f"manual__{datetime.utcnow().timestamp()}",
            "dag_id": dag_id,
            "state": "running",
            "start_date": datetime.utcnow().isoformat(),
        }

    async def get_dag_status(self, dag_id: str) -> Dict[str, Any]:
        """
        Get DAG status

        Args:
            dag_id: DAG ID

        Returns:
            DAG status info
        """
        # This would query Airflow API for DAG status
        # For now, return a mock response
        return {
            "dag_id": dag_id,
            "is_active": True,
            "is_paused": False,
            "last_dagrun": None,
            "last_dagrun_status": None,
        }

    async def list_dags(self) -> List[Dict[str, Any]]:
        """
        List all DAGs

        Returns:
            List of DAG info
        """
        # This would query Airflow API for all DAGs
        # For now, return empty list
        return []

    async def get_dag_runs(
        self,
        dag_id: str,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Get DAG runs

        Args:
            dag_id: DAG ID
            limit: Max number of runs

        Returns:
            List of DAG runs
        """
        # This would query Airflow API for DAG runs
        return []

    def _validate_dag_config(self, config: DAGConfig) -> None:
        """Validate DAG configuration"""
        if not config.dag_id:
            raise ValueError("dag_id is required")

        # Validate task IDs are unique
        task_ids = [task.task_id for task in config.tasks]
        if len(task_ids) != len(set(task_ids)):
            raise ValueError("Task IDs must be unique")

        # Validate dependencies exist
        for task in config.tasks:
            if task.depends_on:
                for dep_id in task.depends_on:
                    if dep_id not in task_ids:
                        raise ValueError(f"Task {dep_id} not found in DAG")

    def _generate_dag_code(self, config: DAGConfig) -> str:
        """Generate Airflow Python DAG code from configuration"""

        # Build imports
        imports = [
            "from airflow import DAG",
            "from airflow.operators.python import PythonOperator",
            "from airflow.providers.postgres.operators.sql import PostgresOperator",
            "from airflow.providers.http.operators.http import SimpleHttpOperator",
            "from airflow.sensors.python import PythonSensor",
            "from datetime import datetime, timedelta",
            "",
        ]

        # Build DAG definition
        dag_params = [
            f"dag_id='{config.dag_id}'",
            f"start_date=datetime({config.start_date.year}, {config.start_date.month}, {config.start_date.day})",
            f"schedule_interval={repr(config.schedule_interval)}",
            f"catchup={str(config.catchup).lower()}",
            f"max_active_runs={config.max_active_runs}",
            f"tags={config.tags}",
        ]

        if config.description:
            dag_params.append(f"description='{config.description}'")

        dag_definition = [
            "default_args = {",
            "    'owner': '" + config.owner + "',",
            "    'depends_on_past': False,",
            "    'retries': 1,",
            "    'retry_delay': timedelta(minutes=5),",
            "}",
            "",
            f"dag = DAG({', '.join(dag_params)})",
            "",
        ]

        # Build tasks
        task_definitions = []
        task_builders = []

        for task in config.tasks:
            task_def = self._generate_task_definition(task)
            task_definitions.append(task_def)
            task_builders.append(self._generate_task_builder(task))

        # Combine all parts
        dag_code = "\n".join(imports) + "\n" + "\n".join(dag_definition) + "\n"

        # Add task definitions
        for task_def in task_definitions:
            dag_code += task_def + "\n"

        # Add task builders (with dependencies)
        dag_code += "\n".join(task_builders)

        return dag_code

    def _generate_task_definition(self, task: TaskConfig) -> str:
        """Generate Airflow task definition code"""
        handler = TaskRegistry.create_handler(task)

        if task.task_type == TaskType.SQL:
            return f"""
# Task: {task.task_id}
{task.task_id}_task = PostgresOperator(
    task_id='{task.task_id}',
    sql={repr(task.parameters.get('sql', ''))},
    postgres_conn_id={repr(task.parameters.get('conn_id', 'postgres_default'))},
    dag=dag,
)
"""

        elif task.task_type == TaskType.PYTHON:
            return f"""
# Task: {task.task_id}
def {task.task_id}_function(**context):
    # TODO: Implement Python logic
    pass

{task.task_id}_task = PythonOperator(
    task_id='{task.task_id}',
    python_callable={task.task_id}_function,
    dag=dag,
)
"""

        elif task.task_type == TaskType.SHELL:
            return f"""
# Task: {task.task_id}
{task.task_id}_task = BashOperator(
    task_id='{task.task_id}',
    bash_command={repr(task.parameters.get('command', ''))},
    dag=dag,
)
"""

        elif task.task_type == TaskType.ETL:
            return f"""
# Task: {task.task_id}
def {task.task_id}_function(**context):
    # TODO: Implement ETL logic
    pass

{task.task_id}_task = PythonOperator(
    task_id='{task.task_id}',
    python_callable={task.task_id}_function,
    dag=dag,
)
"""

        else:
            # Default to PythonOperator
            return f"""
# Task: {task.task_id}
def {task.task_id}_function(**context):
    # TODO: Implement {task.task_type} logic
    pass

{task.task_id}_task = PythonOperator(
    task_id='{task.task_id}',
    python_callable={task.task_id}_function,
    dag=dag,
)
"""

    def _generate_task_builder(self, task: TaskConfig) -> str:
        """Generate task dependency code"""
        if not task.depends_on:
            return f""

        deps = ", ".join([f"{dep}_task" for dep in task.depends_on])
        return f"{task.task_id}_task.set_upstream({deps})"

    async def _sync_dag(self, dag_id: str) -> None:
        """Sync DAG with Airflow"""
        # This would call Airflow API to sync the DAG
        # For now, just log
        logger.info(f"Synced DAG: {dag_id}")
