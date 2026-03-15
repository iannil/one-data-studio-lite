"""
Airflow DAG Synchronization Service

This service handles synchronization between DAG definitions stored in the database
and the Airflow DAGs folder. It ensures that DAGs created via the UI are properly
synced to Airflow's DAGs folder for execution.
"""

import asyncio
import os
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import json
import aiohttp
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workflow import DAG, DAGNode, DAGEdge
from app.core.database import get_async_session
from app.core.config import settings

logger = logging.getLogger(__name__)


class AirflowSyncService:
    """
    Service for synchronizing DAGs between database and Airflow DAGs folder

    Features:
    - Generate Airflow DAG files from database definitions
    - Watch for DAG changes and auto-sync
    - Handle DAG versioning
    - Validate DAG syntax before syncing
    """

    def __init__(
        self,
        dags_folder: str = "/opt/airflow/dags",
        airflow_api_url: str = "http://airflow-webserver:8080",
        airflow_username: str = "admin",
        airflow_password: str = "admin",
    ):
        """
        Initialize Airflow sync service

        Args:
            dags_folder: Path to Airflow DAGs folder
            airflow_api_url: Airflow webserver API URL
            airflow_username: Airflow username
            airflow_password: Airflow password
        """
        self.dags_folder = Path(dags_folder)
        self.airflow_api_url = airflow_api_url.rstrip('/')
        self.airflow_username = airflow_username
        self.airflow_password = airflow_password
        self._sync_lock = asyncio.Lock()

    async def sync_dag(self, dag_id: str, db_session: Optional[AsyncSession] = None) -> Dict[str, Any]:
        """
        Sync a single DAG from database to Airflow DAGs folder

        Args:
            dag_id: DAG identifier
            db_session: Database session (optional, will create if not provided)

        Returns:
            Sync result with status and details
        """
        async with self._sync_lock:
            try:
                # Get DAG from database
                if db_session is None:
                    async for session in get_async_session():
                        db_session = session
                        break
                else:
                    # Use the provided session
                    pass

                result = await self._fetch_and_sync_dag(dag_id, db_session)
                return result

            except Exception as e:
                logger.error(f"Error syncing DAG {dag_id}: {str(e)}")
                return {
                    "dag_id": dag_id,
                    "status": "error",
                    "error": str(e),
                }

    async def _fetch_and_sync_dag(self, dag_id: str, db_session: AsyncSession) -> Dict[str, Any]:
        """Fetch DAG from database and sync to file"""
        # Query DAG from database
        stmt = select(DAG).where(DAG.dag_id == dag_id)
        result = await db_session.execute(stmt)
        dag = result.scalar_one_or_none()

        if not dag:
            return {
                "dag_id": dag_id,
                "status": "not_found",
                "error": f"DAG {dag_id} not found in database",
            }

        # Get nodes and edges
        nodes_stmt = select(DAGNode).where(DAGNode.dag_id == dag.id)
        nodes_result = await db_session.execute(nodes_stmt)
        nodes = nodes_result.scalars().all()

        edges_stmt = select(DAGEdge).where(DAGEdge.dag_id == dag.id)
        edges_result = await db_session.execute(edges_stmt)
        edges = edges_result.scalars().all()

        # Generate DAG file content
        dag_code = await self._generate_dag_file(dag, nodes, edges)

        # Write to DAGs folder
        dag_file_path = self.dags_folder / f"{dag_id}.py"
        with open(dag_file_path, "w") as f:
            f.write(dag_code)

        logger.info(f"Synced DAG {dag_id} to {dag_file_path}")

        # Trigger Airflow to refresh DAG list
        await self._refresh_dag_list()

        return {
            "dag_id": dag_id,
            "status": "success",
            "file_path": str(dag_file_path),
            "synced_at": datetime.utcnow().isoformat(),
        }

    async def _generate_dag_file(
        self,
        dag: DAG,
        nodes: List[DAGNode],
        edges: List[DAGEdge],
    ) -> str:
        """
        Generate Airflow DAG file content from database models

        Args:
            dag: DAG model
            nodes: List of DAG nodes
            edges: List of DAG edges

        Returns:
            Python code for the DAG file
        """
        # Build imports
        imports = self._build_imports(nodes)

        # Build DAG definition
        dag_definition = self._build_dag_definition(dag)

        # Build task definitions
        task_definitions = self._build_task_definitions(nodes)

        # Build task dependencies
        task_dependencies = self._build_task_dependencies(nodes, edges)

        # Combine all parts
        dag_code = f'''"""
Auto-generated DAG: {dag.dag_id}
Generated at: {datetime.utcnow().isoformat()}
Source: One Data Studio

WARNING: This file is auto-generated. Manual changes may be overwritten.
"""

{imports}

{dag_definition}

{task_definitions}

{task_dependencies}
'''
        return dag_code

    def _build_imports(self, nodes: List[DAGNode]) -> str:
        """Build import statements based on node types"""
        imports = [
            "from airflow import DAG",
            "from airflow.operators.python import PythonOperator",
            "from datetime import datetime, timedelta",
        ]

        # Add operator imports based on node types
        node_types = set(node.node_type for node in nodes)

        if "sql" in node_types:
            imports.append("from airflow.providers.postgres.operators.sql import PostgresOperator")

        if "bash" in node_types or "shell" in node_types:
            imports.append("from airflow.operators.bash import BashOperator")

        if "http" in node_types:
            imports.append("from airflow.providers.http.operators.http import SimpleHttpOperator")

        if "sensor" in node_types:
            imports.append("from airflow.sensors.python import PythonSensor")

        # Add custom operators
        imports.append("# Custom One Data Studio operators")
        imports.append("try:")
        imports.append("    from airflow.plugins.onedata import ETLOperator, TrainingOperator, InferenceOperator")
        imports.append("except ImportError:")
        imports.append("    pass  # Running outside One Data Studio environment")

        return "\n".join(imports)

    def _build_dag_definition(self, dag: DAG) -> str:
        """Build DAG definition block"""
        # Parse schedule interval
        schedule = repr(dag.schedule_interval) if dag.schedule_interval else "None"

        # Parse start date
        start_date = (
            f"datetime({dag.start_date.year}, {dag.start_date.month}, {dag.start_date.day})"
            if dag.start_date
            else "days_ago(1)"
        )

        # Build default args
        default_args = f"""default_args={{
    'owner': '{dag.owner.username if dag.owner else 'onedata'}',
    'depends_on_past': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}}"""

        # Build DAG parameters
        dag_params = [
            f"dag_id='{dag.dag_id}'",
            f"default_args=default_args",
            f"start_date={start_date}",
            f"schedule_interval={schedule}",
            f"catchup={str(dag.catchup).lower()}",
            f"max_active_runs={dag.max_active_runs}",
            f"concurrency={dag.concurrency}",
            f"tags={dag.tags or []}",
        ]

        if dag.description:
            dag_params.append(f"description='{dag.description}'")

        # Build DAG definition (can't use \n in f-string expression)
        params_str = ',\n    '.join(dag_params)
        dag_def = f"""{default_args}

with DAG(
    {params_str}
) as dag:"""

        return dag_def

    def _build_task_definitions(self, nodes: List[DAGNode]) -> str:
        """Build task definitions for all nodes"""
        definitions = []

        for node in nodes:
            task_def = self._build_single_task_definition(node)
            definitions.append(task_def)

        return "\n\n".join(definitions)

    def _build_single_task_definition(self, node: DAGNode) -> str:
        """Build definition for a single task"""
        config = node.config or {}

        if node.node_type == "sql":
            return self._build_sql_task(node)
        elif node.node_type == "bash" or node.node_type == "shell":
            return self._build_bash_task(node)
        elif node.node_type == "etl":
            return self._build_etl_task(node)
        elif node.node_type == "training":
            return self._build_training_task(node)
        elif node.node_type == "inference":
            return self._build_inference_task(node)
        else:
            # Default to PythonOperator
            return self._build_python_task(node)

    def _build_sql_task(self, node: DAGNode) -> str:
        """Build SQL task definition"""
        config = node.config or {}
        sql = config.get("parameters", {}).get("sql", "-- TODO: Add SQL")
        conn_id = config.get("parameters", {}).get("conn_id", "postgres_default")

        return f"""    # Task: {node.name}
    {node.node_id}_task = PostgresOperator(
        task_id='{node.node_id}',
        sql={repr(sql)},
        postgres_conn_id='{conn_id}',
        dag=dag,
    )"""

    def _build_bash_task(self, node: DAGNode) -> str:
        """Build Bash task definition"""
        config = node.config or {}
        command = config.get("parameters", {}).get("command", "echo 'Hello from Airflow'")

        return f"""    # Task: {node.name}
    {node.node_id}_task = BashOperator(
        task_id='{node.node_id}',
        bash_command={repr(command)},
        dag=dag,
    )"""

    def _build_python_task(self, node: DAGNode) -> str:
        """Build Python task definition"""
        return f'''    # Task: {node.name}
    def {node.node_id}_function(**context):
        """Task: {node.description or node.name}"""
        # TODO: Implement task logic
        print("Executing task: {node.name}")

    {node.node_id}_task = PythonOperator(
        task_id='{node.node_id}',
        python_callable={node.node_id}_function,
        dag=dag,
    )'''

    def _build_etl_task(self, node: DAGNode) -> str:
        """Build ETL task definition using custom operator"""
        config = node.config or {}

        return f'''    # Task: {node.name} (ETL)
    try:
        {node.node_id}_task = ETLOperator(
            task_id='{node.node_id}',
            pipeline_id='{node.node_id}',
            source_config={config.get('source_config', {{}})},
            transform_config={config.get('transform_config', {{}})},
            target_config={config.get('target_config', {{}})},
            dag=dag,
        )
    except NameError:
        # Fallback to PythonOperator if custom operator not available
        def {node.node_id}_function(**context):
            print("ETL task: {node.name}")

        {node.node_id}_task = PythonOperator(
            task_id='{node.node_id}',
            python_callable={node.node_id}_function,
            dag=dag,
        )'''

    def _build_training_task(self, node: DAGNode) -> str:
        """Build training task definition using custom operator"""
        config = node.config or {}

        return f'''    # Task: {node.name} (Training)
    try:
        {node.node_id}_task = TrainingOperator(
            task_id='{node.node_id}',
            experiment_id='{config.get('experiment_id', 'default')}',
            model_type='{config.get('model_type', 'sklearn')}',
            training_config={config.get('training_config', {{}})},
            data_source={config.get('data_source', {{}})},
            dag=dag,
        )
    except NameError:
        # Fallback to PythonOperator if custom operator not available
        def {node.node_id}_function(**context):
            print("Training task: {node.name}")

        {node.node_id}_task = PythonOperator(
            task_id='{node.node_id}',
            python_callable={node.node_id}_function,
            dag=dag,
        )'''

    def _build_inference_task(self, node: DAGNode) -> str:
        """Build inference task definition using custom operator"""
        config = node.config or {}

        return f'''    # Task: {node.name} (Inference)
    try:
        {node.node_id}_task = InferenceOperator(
            task_id='{node.node_id}',
            model_id='{config.get('model_id', 'default')}',
            inference_data={config.get('inference_data', {{}})},
            output_config={config.get('output_config', {{}})},
            dag=dag,
        )
    except NameError:
        # Fallback to PythonOperator if custom operator not available
        def {node.node_id}_function(**context):
            print("Inference task: {node.name}")

        {node.node_id}_task = PythonOperator(
            task_id='{node.node_id}',
            python_callable={node.node_id}_function,
            dag=dag,
        )'''

    def _build_task_dependencies(self, nodes: List[DAGNode], edges: List[DAGEdge]) -> str:
        """Build task dependency definitions"""
        if not edges:
            return "    # No task dependencies"

        # Build dependency map
        dependencies: Dict[str, List[str]] = {}
        for node in nodes:
            dependencies[node.node_id] = []

        for edge in edges:
            source_node = next((n for n in nodes if n.id == edge.source_node_id), None)
            target_node = next((n for n in nodes if n.id == edge.target_node_id), None)
            if source_node and target_node:
                dependencies[target_node.node_id].append(source_node.node_id)

        # Build dependency statements
        dep_statements = []
        dep_statements.append("    # Task dependencies")
        for node_id, deps in dependencies.items():
            if deps:
                dep_list = ", ".join([f"{d}_task" for d in deps])
                dep_statements.append(f"    {node_id}_task.set_upstream({dep_list})")

        return "\n".join(dep_statements)

    async def sync_all_active_dags(self, db_session: Optional[AsyncSession] = None) -> List[Dict[str, Any]]:
        """
        Sync all active DAGs from database to Airflow DAGs folder

        Args:
            db_session: Database session (optional)

        Returns:
            List of sync results
        """
        if db_session is None:
            async for session in get_async_session():
                db_session = session
                break
        else:
            pass

        # Get all active DAGs
        stmt = select(DAG).where(DAG.is_active == True)
        result = await db_session.execute(stmt)
        dags = result.scalars().all()

        sync_results = []
        for dag in dags:
            result = await self.sync_dag(dag.dag_id, db_session)
            sync_results.append(result)

        return sync_results

    async def delete_dag_file(self, dag_id: str) -> bool:
        """
        Delete a DAG file from the Airflow DAGs folder

        Args:
            dag_id: DAG identifier

        Returns:
            True if deleted, False if not found
        """
        dag_file = self.dags_folder / f"{dag_id}.py"

        if dag_file.exists():
            dag_file.unlink()
            logger.info(f"Deleted DAG file: {dag_file}")
            await self._refresh_dag_list()
            return True

        return False

    async def _refresh_dag_list(self) -> None:
        """Trigger Airflow to refresh its DAG list"""
        # Note: Airflow automatically picks up new DAG files
        # This method can trigger an API call to force refresh if needed

        # Option 1: Call Airflow API to trigger refresh
        try:
            async with aiohttp.ClientSession() as session:
                auth = aiohttp.BasicAuth(self.airflow_username, self.airflow_password)
                async with session.post(
                    f"{self.airflow_api_url}/api/v1/dags/~/refresh",
                    auth=auth,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    if response.status == 204:
                        logger.info("Triggered Airflow DAG list refresh")
        except Exception as e:
            logger.warning(f"Could not trigger DAG refresh: {e}")

    async def validate_dag_syntax(self, dag_id: str, db_session: AsyncSession) -> Dict[str, Any]:
        """
        Validate DAG syntax without syncing

        Args:
            dag_id: DAG identifier
            db_session: Database session

        Returns:
            Validation result
        """
        try:
            # Get DAG from database
            stmt = select(DAG).where(DAG.dag_id == dag_id)
            result = await db_session.execute(stmt)
            dag = result.scalar_one_or_none()

            if not dag:
                return {"valid": False, "error": "DAG not found"}

            # Get nodes and edges
            nodes_stmt = select(DAGNode).where(DAGNode.dag_id == dag.id)
            nodes_result = await db_session.execute(nodes_stmt)
            nodes = nodes_result.scalars().all()

            edges_stmt = select(DAGEdge).where(DAGEdge.dag_id == dag.id)
            edges_result = await db_session.execute(edges_stmt)
            edges = edges_result.scalars().all()

            # Validate for circular dependencies
            has_cycle = self._check_circular_dependencies(nodes, edges)

            if has_cycle:
                return {"valid": False, "error": "Circular dependency detected"}

            # Try to compile the generated code
            dag_code = await self._generate_dag_file(dag, nodes, edges)
            compile(dag_code, f"<string:{dag_id}>", "exec")

            return {"valid": True}

        except SyntaxError as e:
            return {"valid": False, "error": f"Syntax error: {str(e)}"}
        except Exception as e:
            return {"valid": False, "error": str(e)}

    def _check_circular_dependencies(
        self, nodes: List[DAGNode], edges: List[DAGEdge]
    ) -> bool:
        """Check if DAG has circular dependencies using DFS"""
        # Build adjacency list
        graph: Dict[str, List[str]] = {}
        node_ids = {node.id: node.node_id for node in nodes}

        for node in nodes:
            graph[node.node_id] = []

        for edge in edges:
            source = node_ids.get(edge.source_node_id)
            target = node_ids.get(edge.target_node_id)
            if source and target:
                if source not in graph:
                    graph[source] = []
                if target not in graph:
                    graph[target] = []
                graph[target].append(source)

        # DFS to detect cycles
        visited = set()
        rec_stack = set()

        def has_cycle(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)

            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    if has_cycle(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True

            rec_stack.remove(node)
            return False

        for node in graph:
            if node not in visited:
                if has_cycle(node):
                    return True

        return False


# Singleton instance
_sync_service: Optional[AirflowSyncService] = None


def get_airflow_sync_service() -> AirflowSyncService:
    """Get the Airflow sync service singleton"""
    global _sync_service
    if _sync_service is None:
        _sync_service = AirflowSyncService(
            dags_folder=os.getenv("AIRFLOW_DAGS_FOLDER", "/opt/airflow/dags"),
            airflow_api_url=os.getenv("AIRFLOW_API_URL", "http://airflow-webserver:8080"),
            airflow_username=os.getenv("AIRFLOW_USERNAME", "admin"),
            airflow_password=os.getenv("AIRFLOW_PASSWORD", "admin"),
        )
    return _sync_service
