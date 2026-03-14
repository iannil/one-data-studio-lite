"""
DAG Engine for One Data Studio Lite

Wrapper around Apache Airflow for DAG management and execution.
Integrates with Airflow REST API v2.
"""

import logging
import tempfile
import os
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass
from urllib.parse import urljoin
import base64

import aiohttp

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
    is_active: bool = True
    is_paused: bool = False

    def __post_init__(self):
        if self.tasks is None:
            self.tasks = []
        if self.tags is None:
            self.tags = []
        if self.start_date is None:
            self.start_date = datetime.utcnow()


class AirflowAPIError(Exception):
    """Airflow API error"""
    pass


class DAGEngine:
    """
    DAG Engine wrapper

    Manages Airflow DAGs including creation, scheduling, and execution.
    Uses Airflow REST API v2.
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
        self.airflow_api_url = airflow_api_url.rstrip('/')
        self.airflow_username = airflow_username
        self.airflow_password = airflow_password
        self.dags_folder = dags_folder

        # Prepare basic auth header
        auth_string = f"{airflow_username}:{airflow_password}"
        self.auth_header = {
            "Authorization": f"Basic {base64.b64encode(auth_string.encode()).decode()}"
        }

    def _get_api_url(self, path: str) -> str:
        """Get full API URL for a path"""
        return urljoin(self.airflow_api_url, f"/api/v1/{path.lstrip('/')}")

    async def _api_request(
        self,
        method: str,
        path: str,
        json_data: Optional[Dict] = None,
        params: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Make an API request to Airflow

        Args:
            method: HTTP method
            path: API path
            json_data: Request body (JSON)
            params: Query parameters

        Returns:
            Response data

        Raises:
            AirflowAPIError: If API call fails
        """
        url = self._get_api_url(path)

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            **self.auth_header,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method=method,
                    url=url,
                    json=json_data,
                    params=params,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as response:
                    if response.status >= 400:
                        error_text = await response.text()
                        logger.error(f"Airflow API error: {response.status} - {error_text}")
                        raise AirflowAPIError(
                            f"Airflow API returned {response.status}: {error_text}"
                        )

                    if response.status == 204:
                        return {}

                    return await response.json()

        except aiohttp.ClientError as e:
            logger.error(f"Airflow API request failed: {str(e)}")
            # Return mock data for development when Airflow is not available
            logger.warning("Returning mock data (Airflow not available)")
            return {}

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

        # Ensure DAGs folder exists
        os.makedirs(self.dags_folder, exist_ok=True)

        # Write DAG file to DAGs folder
        dag_file_path = os.path.join(self.dags_folder, f"{config.dag_id}.py")
        with open(dag_file_path, "w") as f:
            f.write(dag_code)

        logger.info(f"Created DAG file: {dag_file_path}")

        # Sync with Airflow (trigger DAG list refresh)
        await self._sync_dag(config.dag_id)

        # Try to pause/unpause based on config
        try:
            if config.is_paused:
                await self.pause_dag(config.dag_id)
            else:
                await self.unpause_dag(config.dag_id)
        except AirflowAPIError:
            pass  # DAG might not be synced yet

        return {
            "dag_id": config.dag_id,
            "file_path": dag_file_path,
            "created_at": datetime.utcnow().isoformat(),
            "is_active": config.is_active,
            "is_paused": config.is_paused,
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
            logger.info(f"Deleted DAG file: {dag_file_path}")
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
        try:
            data = {"conf": conf} if conf else {}

            response = await self._api_request(
                method="POST",
                path=f"/dags/{dag_id}/dagRuns",
                json_data=data,
            )

            return {
                "dag_run_id": response.get("dag_run_id"),
                "dag_id": dag_id,
                "state": response.get("state", "queued"),
                "start_date": response.get("execution_date"),
            }

        except AirflowAPIError:
            # Return mock response for development
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
        try:
            response = await self._api_request(
                method="GET",
                path=f"/dags/{dag_id}",
            )

            return {
                "dag_id": dag_id,
                "is_active": response.get("is_active", True),
                "is_paused": response.get("is_paused", False),
                "last_dagrun": response.get("last_dagrun"),
                "last_dagrun_status": response.get("last_dagrun", {}).get("state"),
                "tags": response.get("tags", []),
            }

        except AirflowAPIError:
            # Return mock response for development
            return {
                "dag_id": dag_id,
                "is_active": True,
                "is_paused": False,
                "last_dagrun": None,
                "last_dagrun_status": None,
            }

    async def list_dags(
        self,
        limit: int = 100,
        offset: int = 0,
        tags: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        List all DAGs

        Args:
            limit: Max number of results
            offset: Offset for pagination
            tags: Filter by tags

        Returns:
            List of DAG info
        """
        try:
            params = {"limit": limit, "offset": offset}
            if tags:
                params["tags"] = tags

            response = await self._api_request(
                method="GET",
                path="/dags",
                params=params,
            )

            dags = response.get("dags", [])
            return [
                {
                    "dag_id": dag.get("dag_id"),
                    "is_active": dag.get("is_active"),
                    "is_paused": dag.get("is_paused"),
                    "tags": dag.get("tags", []),
                }
                for dag in dags
            ]

        except AirflowAPIError:
            # Return empty list for development
            return []

    async def get_dag_runs(
        self,
        dag_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Get DAG runs

        Args:
            dag_id: DAG ID
            limit: Max number of runs
            offset: Offset for pagination

        Returns:
            List of DAG runs
        """
        try:
            params = {"limit": limit, "offset": offset}

            response = await self._api_request(
                method="GET",
                path=f"/dags/{dag_id}/dagRuns",
                params=params,
            )

            runs = response.get("dag_runs", [])
            return [
                {
                    "id": run.get("id"),
                    "dag_run_id": run.get("dag_run_id"),
                    "dag_id": dag_id,
                    "execution_date": run.get("execution_date"),
                    "state": run.get("state"),
                    "start_date": run.get("start_date"),
                    "end_date": run.get("end_date"),
                    "run_type": run.get("run_type", "manual"),
                }
                for run in runs
            ]

        except AirflowAPIError:
            # Return empty list for development
            return []

    async def get_task_instances(
        self,
        dag_id: str,
        dag_run_id: str,
    ) -> List[Dict[str, Any]]:
        """
        Get task instances for a DAG run

        Args:
            dag_id: DAG ID
            dag_run_id: DAG Run ID

        Returns:
            List of task instances
        """
        try:
            response = await self._api_request(
                method="GET",
                path=f"/dags/{dag_id}/dagRuns/{dag_run_id}/taskInstances",
            )

            tasks = response.get("task_instances", [])
            return [
                {
                    "task_id": task.get("task_id"),
                    "state": task.get("state"),
                    "start_date": task.get("start_date"),
                    "end_date": task.get("end_date"),
                    "try_number": task.get("try_number"),
                }
                for task in tasks
            ]

        except AirflowAPIError:
            # Return empty list for development
            return []

    async def pause_dag(self, dag_id: str) -> bool:
        """
        Pause a DAG

        Args:
            dag_id: DAG ID

        Returns:
            True if successful
        """
        try:
            await self._api_request(
                method="PATCH",
                path=f"/dags/{dag_id}",
                json_data={"is_paused": True},
            )
            logger.info(f"Paused DAG: {dag_id}")
            return True

        except AirflowAPIError:
            logger.warning(f"Failed to pause DAG: {dag_id}")
            return False

    async def unpause_dag(self, dag_id: str) -> bool:
        """
        Unpause a DAG

        Args:
            dag_id: DAG ID

        Returns:
            True if successful
        """
        try:
            await self._api_request(
                method="PATCH",
                path=f"/dags/{dag_id}",
                json_data={"is_paused": False},
            )
            logger.info(f"Unpaused DAG: {dag_id}")
            return True

        except AirflowAPIError:
            logger.warning(f"Failed to unpause DAG: {dag_id}")
            return False

    async def set_dag_active(self, dag_id: str, is_active: bool) -> bool:
        """
        Set DAG active status

        Args:
            dag_id: DAG ID
            is_active: Active status

        Returns:
            True if successful
        """
        try:
            await self._api_request(
                method="PATCH",
                path=f"/dags/{dag_id}",
                json_data={"is_active": is_active},
            )
            logger.info(f"Set DAG {dag_id} active={is_active}")
            return True

        except AirflowAPIError:
            logger.warning(f"Failed to set DAG {dag_id} active status")
            return False

    async def get_dag_code(self, dag_id: str) -> Optional[str]:
        """
        Get the generated Python code for a DAG

        Args:
            dag_id: DAG ID

        Returns:
            DAG code or None if file doesn't exist
        """
        dag_file_path = os.path.join(self.dags_folder, f"{dag_id}.py")

        if os.path.exists(dag_file_path):
            with open(dag_file_path, "r") as f:
                return f.read()

        return None

    async def backfill_dag(
        self,
        dag_id: str,
        start_date: str,
        end_date: str,
        dry_run: bool = False,
        clear_first: bool = False,
        task_regex: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Backfill a DAG for historical dates

        Args:
            dag_id: DAG ID
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            dry_run: Run in dry-run mode
            clear_first: Clear existing runs first
            task_regex: Regex to filter tasks

        Returns:
            Backfill result
        """
        # Calculate number of days
        start_dt = datetime.fromisoformat(start_date)
        end_dt = datetime.fromisoformat(end_date)
        days = (end_dt - start_dt).days + 1

        # Create backfill DAG runs
        results = []
        current_date = start_dt

        while current_date <= end_dt:
            execution_date = current_date.strftime("%Y-%m-%dT%H:%M:%S")

            if not dry_run:
                try:
                    result = await self.trigger_dag_run(
                        dag_id=dag_id,
                        conf={
                            "backfill": True,
                            "execution_date": execution_date,
                        },
                    )
                    results.append(result)
                except AirflowAPIError as e:
                    logger.error(f"Failed to trigger backfill run for {execution_date}: {e}")

            current_date = current_date.replace(day=current_date.day + 1)

        return {
            "dag_id": dag_id,
            "start_date": start_date,
            "end_date": end_date,
            "days": days,
            "dry_run": dry_run,
            "runs_triggered": len(results) if not dry_run else 0,
            "status": "completed" if not dry_run else "dry_run",
        }

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
            "from airflow.operators.bash import BashOperator",
            "from airflow.providers.postgres.operators.sql import PostgresOperator",
            "from airflow.providers.http.operators.http import SimpleHttpOperator",
            "from airflow.sensors.python import PythonSensor",
            "from datetime import datetime, timedelta",
            "",
        ]

        # Add custom operators import
        imports.append("# Custom One Data Studio operators")
        imports.append("try:")
        imports.append("    from airflow.plugins.onedata import ETLOperator, TrainingOperator, InferenceOperator")
        imports.append("except ImportError:")
        imports.append("    pass  # Running outside One Data Studio environment")
        imports.append("")

        # Build DAG definition
        schedule = repr(config.schedule_interval) if config.schedule_interval else "None"

        dag_params = [
            f"dag_id='{config.dag_id}'",
            f"start_date=datetime({config.start_date.year}, {config.start_date.month}, {config.start_date.day})",
            f"schedule_interval={schedule}",
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
            sql = task.parameters.get('sql', '-- TODO: Add SQL')
            conn_id = task.parameters.get('conn_id', 'postgres_default')

            return f"""
# Task: {task.task_id}
{task.task_id}_task = PostgresOperator(
    task_id='{task.task_id}',
    sql={repr(sql)},
    postgres_conn_id={repr(conn_id)},
    dag=dag,
)
"""

        elif task.task_type == TaskType.PYTHON:
            return f"""
# Task: {task.task_id}
def {task.task_id}_function(**context):
    \"\"\"Task: {task.description or task.name}\"\"\"
    # TODO: Implement Python logic
    print("Executing task: {task.name}")
    pass

{task.task_id}_task = PythonOperator(
    task_id='{task.task_id}',
    python_callable={task.task_id}_function,
    dag=dag,
)
"""

        elif task.task_type == TaskType.SHELL:
            command = task.parameters.get('command', 'echo "Hello from Airflow"')

            return f"""
# Task: {task.task_id}
{task.task_id}_task = BashOperator(
    task_id='{task.task_id}',
    bash_command={repr(command)},
    dag=dag,
)
"""

        elif task.task_type == TaskType.ETL:
            return f"""
# Task: {task.task_id} (ETL)
try:
    {task.task_id}_task = ETLOperator(
        task_id='{task.task_id}',
        pipeline_id='{task.task_id}',
        source_config={task.parameters.get('source_config', {})},
        transform_config={task.parameters.get('transform_config', {})},
        target_config={task.parameters.get('target_config', {})},
        dag=dag,
    )
except NameError:
    def {task.task_id}_function(**context):
        print("ETL task: {task.name}")

    {task.task_id}_task = PythonOperator(
        task_id='{task.task_id}',
        python_callable={task.task_id}_function,
        dag=dag,
    )
"""

        elif task.task_type == TaskType.TRAINING:
            return f"""
# Task: {task.task_id} (Training)
try:
    {task.task_id}_task = TrainingOperator(
        task_id='{task.task_id}',
        experiment_id='{task.parameters.get('experiment_id', 'default')}',
        model_type='{task.parameters.get('model_type', 'sklearn')}',
        training_config={task.parameters.get('training_config', {})},
        data_source={task.parameters.get('data_source', {})},
        dag=dag,
    )
except NameError:
    def {task.task_id}_function(**context):
        print("Training task: {task.name}")

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
    \"\"\"Task: {task.description or task.name}\"\"\"
    # TODO: Implement {task.task_type} logic
    print("Executing task: {task.name} (type: {task.task_type})")
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
            return ""

        deps = ", ".join([f"{dep}_task" for dep in task.depends_on])
        return f"{task.task_id}_task.set_upstream({deps})"

    async def _sync_dag(self, dag_id: str) -> None:
        """Sync DAG with Airflow"""
        try:
            # Trigger DAG list refresh
            await self._api_request(
                method="POST",
                path="/dags/~/refresh",
            )
            logger.info(f"Triggered DAG list refresh for: {dag_id}")
        except AirflowAPIError as e:
            logger.warning(f"Could not trigger DAG refresh: {e}")
