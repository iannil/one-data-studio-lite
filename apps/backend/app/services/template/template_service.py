"""
Template Service for One Data Studio Lite

Manages workflow templates for quick start and best practices.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime

logger = logging.getLogger(__name__)


# Template directory
TEMPLATE_DIR = Path(__file__).parent.parent.parent.parent / "templates" / "workflows"


@dataclass
class TemplateVariable:
    """Variable definition for template parameterization"""

    name: str
    type: str  # string, number, boolean, select, multiline
    label: str
    default: Any = None
    required: bool = False
    options: Optional[List[str]] = None
    description: Optional[str] = None


@dataclass
class TemplateTask:
    """Task definition within a template"""

    task_id: str
    task_type: str
    name: str
    description: Optional[str] = None
    depends_on: Optional[List[str]] = None
    parameters: Optional[Dict[str, Any]] = None
    position: Optional[Dict[str, float]] = None


@dataclass
class WorkflowTemplate:
    """Workflow template definition"""

    id: str
    name: str
    description: str
    category: str
    icon: Optional[str] = None
    tags: Optional[List[str]] = None
    tasks: Optional[List[TemplateTask]] = None
    variables: Optional[List[TemplateVariable]] = None
    thumbnail: Optional[str] = None
    created_at: Optional[str] = None
    author: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        if self.tasks:
            data["tasks"] = [asdict(t) if isinstance(t, TemplateTask) else t for t in self.tasks]
        if self.variables:
            data["variables"] = [asdict(v) if isinstance(v, TemplateVariable) else v for v in self.variables]
        return data


class TemplateService:
    """
    Service for managing workflow templates

    Provides CRUD operations for workflow templates and
    handles template instantiation with variable substitution.
    """

    def __init__(self, template_dir: Optional[Path] = None):
        """
        Initialize template service

        Args:
            template_dir: Directory containing template files
        """
        self.template_dir = template_dir or TEMPLATE_DIR
        self.template_dir.mkdir(parents=True, exist_ok=True)

        # Load built-in templates
        self._builtin_templates = self._load_builtin_templates()

    def _load_builtin_templates(self) -> Dict[str, WorkflowTemplate]:
        """Load built-in templates"""
        templates = {}

        # Daily ETL Pipeline
        templates["daily_etl"] = WorkflowTemplate(
            id="daily_etl",
            name="Daily ETL Pipeline",
            description="Extract data from source, transform it, and load to target. Runs daily.",
            category="etl",
            icon="🔄",
            tags=["etl", "daily", "data"],
            tasks=[
                TemplateTask(
                    task_id="extract",
                    task_type="sql",
                    name="Extract Data",
                    description="Extract data from source table",
                    parameters={
                        "sql": "SELECT * FROM {{ source_table }} WHERE updated_at > '{{ last_run_date }}'",
                        "conn_id": "{{ source_conn }}",
                    },
                    position={"x": 100, "y": 100},
                ),
                TemplateTask(
                    task_id="validate",
                    task_type="python",
                    name="Validate Data",
                    description="Validate extracted data quality",
                    depends_on=["extract"],
                    parameters={
                        "code": "validate_schema(df, schema)",
                    },
                    position={"x": 350, "y": 100},
                ),
                TemplateTask(
                    task_id="transform",
                    task_type="etl",
                    name="Transform Data",
                    description="Apply transformation logic",
                    depends_on=["validate"],
                    parameters={
                        "pipeline_id": "{{ pipeline_id }}",
                    },
                    position={"x": 600, "y": 100},
                ),
                TemplateTask(
                    task_id="load",
                    task_type="sql",
                    name="Load Data",
                    description="Load transformed data to target",
                    depends_on=["transform"],
                    parameters={
                        "sql": "INSERT INTO {{ target_table }} SELECT * FROM temp_table",
                        "conn_id": "{{ target_conn }}",
                    },
                    position={"x": 850, "y": 100},
                ),
            ],
            variables=[
                TemplateVariable(
                    name="source_table",
                    type="string",
                    label="Source Table",
                    required=True,
                    description="Name of the source table to extract from",
                ),
                TemplateVariable(
                    name="target_table",
                    type="string",
                    label="Target Table",
                    required=True,
                    description="Name of the target table to load into",
                ),
                TemplateVariable(
                    name="source_conn",
                    type="select",
                    label="Source Connection",
                    default="postgres_default",
                    required=True,
                    options=["postgres_default", "mysql_default", "snowflake_default"],
                ),
                TemplateVariable(
                    name="target_conn",
                    type="select",
                    label="Target Connection",
                    default="postgres_default",
                    required=True,
                    options=["postgres_default", "mysql_default", "snowflake_default"],
                ),
                TemplateVariable(
                    name="pipeline_id",
                    type="select",
                    label="ETL Pipeline",
                    required=True,
                    description="ID of the ETL pipeline to use for transformation",
                ),
            ],
            author="System",
            created_at="2024-01-01T00:00:00Z",
        )

        # ML Training Pipeline
        templates["ml_training"] = WorkflowTemplate(
            id="ml_training",
            name="ML Training Pipeline",
            description="End-to-end machine learning training workflow with data prep, training, and evaluation.",
            category="ml",
            icon="🧠",
            tags=["ml", "training", "model"],
            tasks=[
                TemplateTask(
                    task_id="prepare_features",
                    task_type="python",
                    name="Prepare Features",
                    description="Prepare and split training data",
                    parameters={
                        "code": "# Load and preprocess data\nX, y = load_data()\nX_train, X_test, y_train, y_test = train_test_split(X, y)",
                    },
                    position={"x": 100, "y": 100},
                ),
                TemplateTask(
                    task_id="train_model",
                    task_type="training",
                    name="Train Model",
                    description="Train the machine learning model",
                    depends_on=["prepare_features"],
                    parameters={
                        "experiment_id": "{{ experiment_id }}",
                        "model_type": "{{ model_type }}",
                        "hyperparameters": "{{ hyperparameters }}",
                        "resources": {"gpu": 1, "memory": "8Gi"},
                    },
                    position={"x": 350, "y": 100},
                ),
                TemplateTask(
                    task_id="evaluate_model",
                    task_type="evaluation",
                    name="Evaluate Model",
                    description="Evaluate model performance on test set",
                    depends_on=["train_model"],
                    parameters={
                        "metrics": ["accuracy", "precision", "recall", "f1"],
                    },
                    position={"x": 600, "y": 100},
                ),
                TemplateTask(
                    task_id="register_model",
                    task_type="model_register",
                    name="Register Model",
                    description="Register model to model registry",
                    depends_on=["evaluate_model"],
                    parameters={
                        "model_name": "{{ model_name }}",
                        "stage": "staging",
                    },
                    position={"x": 850, "y": 100},
                ),
            ],
            variables=[
                TemplateVariable(
                    name="experiment_id",
                    type="string",
                    label="Experiment ID",
                    required=True,
                    description="ID of the MLflow experiment",
                ),
                TemplateVariable(
                    name="model_type",
                    type="select",
                    label="Model Type",
                    default="sklearn.ensemble.RandomForestClassifier",
                    options=[
                        "sklearn.ensemble.RandomForestClassifier",
                        "sklearn.ensemble.GradientBoostingClassifier",
                        "xgboost.XGBClassifier",
                        "lightgbm.LGBMClassifier",
                    ],
                ),
                TemplateVariable(
                    name="hyperparameters",
                    type="multiline",
                    label="Hyperparameters",
                    default='{"n_estimators": 100, "max_depth": 10}',
                    description="JSON string of hyperparameters",
                ),
                TemplateVariable(
                    name="model_name",
                    type="string",
                    label="Model Name",
                    required=True,
                    description="Name to register the model with",
                ),
            ],
            author="System",
            created_at="2024-01-01T00:00:00Z",
        )

        # Data Quality Monitoring
        templates["data_quality"] = WorkflowTemplate(
            id="data_quality",
            name="Data Quality Monitoring",
            description="Monitor data quality with alerts for anomalies and issues.",
            category="quality",
            icon="📊",
            tags=["quality", "monitoring", "alerting"],
            tasks=[
                TemplateTask(
                    task_id="check_schema",
                    task_type="python",
                    name="Check Schema",
                    description="Validate table schema matches expectations",
                    parameters={
                        "code": "check_schema_drift(table_name, expected_schema)",
                    },
                    position={"x": 100, "y": 100},
                ),
                TemplateTask(
                    task_id="check_nulls",
                    task_type="python",
                    name="Check Null Values",
                    description="Check for unexpected null values",
                    depends_on=["check_schema"],
                    parameters={
                        "max_null_pct": "{{ max_null_pct }}",
                    },
                    position={"x": 350, "y": 100},
                ),
                TemplateTask(
                    task_id="check_duplicates",
                    task_type="python",
                    name="Check Duplicates",
                    description="Check for duplicate records",
                    depends_on=["check_schema"],
                    parameters={
                        "key_columns": "{{ key_columns }}",
                    },
                    position={"x": 350, "y": 250},
                ),
                TemplateTask(
                    task_id="check_anomalies",
                    task_type="python",
                    name="Check Anomalies",
                    description="Detect anomalies using statistical methods",
                    depends_on=["check_nulls", "check_duplicates"],
                    parameters={
                        "method": "isolation_forest",
                        "contamination": 0.1,
                    },
                    position={"x": 600, "y": 175},
                ),
                TemplateTask(
                    task_id="send_alert",
                    task_type="email",
                    name="Send Alert",
                    description="Send alert if quality issues detected",
                    depends_on=["check_anomalies"],
                    parameters={
                        "to": "{{ alert_email }}",
                        "subject": "Data Quality Alert for {{ table_name }}",
                        "trigger_on_failure": True,
                    },
                    position={"x": 850, "y": 175},
                ),
            ],
            variables=[
                TemplateVariable(
                    name="table_name",
                    type="string",
                    label="Table Name",
                    required=True,
                ),
                TemplateVariable(
                    name="max_null_pct",
                    type="number",
                    label="Max Null %",
                    default=5.0,
                    description="Maximum allowed null percentage",
                ),
                TemplateVariable(
                    name="key_columns",
                    type="multiline",
                    label="Key Columns",
                    description="Comma-separated list of key columns for duplicate check",
                ),
                TemplateVariable(
                    name="alert_email",
                    type="string",
                    label="Alert Email",
                    required=True,
                    description="Email address to send alerts to",
                ),
            ],
            author="System",
            created_at="2024-01-01T00:00:00Z",
        )

        # Batch Inference Pipeline
        templates["batch_inference"] = WorkflowTemplate(
            id="batch_inference",
            name="Batch Inference Pipeline",
            description="Run batch inference on a dataset using a registered model.",
            category="inference",
            icon="🔮",
            tags=["inference", "batch", "prediction"],
            tasks=[
                TemplateTask(
                    task_id="load_model",
                    task_type="python",
                    name="Load Model",
                    description="Load model from registry",
                    parameters={
                        "model_name": "{{ model_name }}",
                        "model_stage": "{{ model_stage }}",
                    },
                    position={"x": 100, "y": 100},
                ),
                TemplateTask(
                    task_id="load_data",
                    task_type="sql",
                    name="Load Input Data",
                    description="Load data for inference",
                    parameters={
                        "sql": "SELECT * FROM {{ input_table }} WHERE processed = false",
                    },
                    position={"x": 100, "y": 250},
                ),
                TemplateTask(
                    task_id="run_inference",
                    task_type="inference",
                    name="Run Inference",
                    description="Run batch inference",
                    depends_on=["load_model", "load_data"],
                    parameters={
                        "batch_size": "{{ batch_size }}",
                        "resources": {"gpu": 1},
                    },
                    position={"x": 350, "y": 175},
                ),
                TemplateTask(
                    task_id="save_predictions",
                    task_type="sql",
                    name="Save Predictions",
                    description="Save predictions to output table",
                    depends_on=["run_inference"],
                    parameters={
                        "sql": "INSERT INTO {{ output_table }} (id, prediction) VALUES %s",
                    },
                    position={"x": 600, "y": 175},
                ),
            ],
            variables=[
                TemplateVariable(
                    name="model_name",
                    type="string",
                    label="Model Name",
                    required=True,
                ),
                TemplateVariable(
                    name="model_stage",
                    type="select",
                    label="Model Stage",
                    default="production",
                    options=["production", "staging", "development"],
                ),
                TemplateVariable(
                    name="input_table",
                    type="string",
                    label="Input Table",
                    required=True,
                ),
                TemplateVariable(
                    name="output_table",
                    type="string",
                    label="Output Table",
                    required=True,
                ),
                TemplateVariable(
                    name="batch_size",
                    type="number",
                    label="Batch Size",
                    default=1000,
                ),
            ],
            author="System",
            created_at="2024-01-01T00:00:00Z",
        )

        return templates

    async def list_templates(
        self,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        List all available templates

        Args:
            category: Filter by category
            tags: Filter by tags (any match)

        Returns:
            List of template summaries
        """
        templates = []

        # Add built-in templates
        for template in self._builtin_templates.values():
            if category and template.category != category:
                continue
            if tags and not any(tag in (template.tags or []) for tag in tags):
                continue

            templates.append({
                "id": template.id,
                "name": template.name,
                "description": template.description,
                "category": template.category,
                "icon": template.icon,
                "tags": template.tags,
                "task_count": len(template.tasks or []),
                "variable_count": len(template.variables or []),
                "is_builtin": True,
            })

        # Add custom templates from directory
        for template_file in self.template_dir.glob("*.json"):
            try:
                with open(template_file, "r") as f:
                    template_data = json.load(f)

                if category and template_data.get("category") != category:
                    continue
                if tags and not any(
                    tag in template_data.get("tags", []) for tag in tags
                ):
                    continue

                templates.append({
                    **template_data,
                    "is_builtin": False,
                    "task_count": len(template_data.get("tasks", [])),
                    "variable_count": len(template_data.get("variables", [])),
                })
            except Exception as e:
                logger.warning(f"Failed to load template from {template_file}: {e}")

        return templates

    async def get_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific template

        Args:
            template_id: Template identifier

        Returns:
            Template data or None if not found
        """
        # Check built-in templates
        if template_id in self._builtin_templates:
            return self._builtin_templates[template_id].to_dict()

        # Check custom templates
        template_file = self.template_dir / f"{template_id}.json"
        if template_file.exists():
            try:
                with open(template_file, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load template {template_id}: {e}")
                return None

        return None

    async def create_template(
        self,
        template_data: Dict[str, Any],
        author: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a new custom template

        Args:
            template_data: Template configuration
            author: Template author

        Returns:
            Created template data
        """
        template_id = template_data.get("id", f"custom_{datetime.utcnow().timestamp()}")

        # Add metadata
        template_data["id"] = template_id
        template_data["created_at"] = datetime.utcnow().isoformat() + "Z"
        if author:
            template_data["author"] = author

        # Save to file
        template_file = self.template_dir / f"{template_id}.json"
        with open(template_file, "w") as f:
            json.dump(template_data, f, indent=2)

        logger.info(f"Created template {template_id}")
        return template_data

    async def update_template(
        self,
        template_id: str,
        template_data: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        Update an existing template

        Args:
            template_id: Template identifier
            template_data: New template configuration

        Returns:
            Updated template data or None if not found
        """
        # Can't update built-in templates
        if template_id in self._builtin_templates:
            raise ValueError("Cannot update built-in template")

        template_file = self.template_dir / f"{template_id}.json"
        if not template_file.exists():
            return None

        # Preserve ID and created_at
        template_data["id"] = template_id
        with open(template_file, "r") as f:
            existing = json.load(f)
            template_data["created_at"] = existing.get("created_at")
            template_data["author"] = existing.get("author")

        template_data["updated_at"] = datetime.utcnow().isoformat() + "Z"

        # Save updated template
        with open(template_file, "w") as f:
            json.dump(template_data, f, indent=2)

        logger.info(f"Updated template {template_id}")
        return template_data

    async def delete_template(self, template_id: str) -> bool:
        """
        Delete a custom template

        Args:
            template_id: Template identifier

        Returns:
            True if deleted, False if not found
        """
        # Can't delete built-in templates
        if template_id in self._builtin_templates:
            raise ValueError("Cannot delete built-in template")

        template_file = self.template_dir / f"{template_id}.json"
        if template_file.exists():
            template_file.unlink()
            logger.info(f"Deleted template {template_id}")
            return True

        return False

    async def instantiate_template(
        self,
        template_id: str,
        variables: Dict[str, Any],
        dag_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Instantiate a template with variable values

        Args:
            template_id: Template identifier
            variables: Variable values to substitute
            dag_name: Name for the instantiated DAG

        Returns:
            DAG configuration ready for creation
        """
        template = await self.get_template(template_id)
        if not template:
            raise ValueError(f"Template {template_id} not found")

        # Substitute variables in template parameters
        def substitute_value(value: Any) -> Any:
            if isinstance(value, str):
                # Replace {{ variable }} placeholders
                for var_name, var_value in variables.items():
                    placeholder = f"{{{{ {var_name} }}}}"
                    if placeholder in value:
                        value = value.replace(placeholder, str(var_value))
                return value
            elif isinstance(value, dict):
                return {k: substitute_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [substitute_value(v) for v in value]
            return value

        # Process tasks
        tasks = []
        for task in template.get("tasks", []):
            task_data = {
                "task_id": task["task_id"],
                "task_type": task["task_type"],
                "name": task["name"],
                "description": task.get("description"),
                "depends_on": task.get("depends_on", []),
                "parameters": substitute_value(task.get("parameters", {})),
                "position": task.get("position"),
            }
            tasks.append(task_data)

        return {
            "dag_id": f"{template_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            "name": dag_name or template["name"],
            "description": template.get("description"),
            "schedule_interval": None,
            "tags": template.get("tags", []),
            "tasks": tasks,
            "template_id": template_id,
        }

    async def export_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """
        Export a template for sharing

        Args:
            template_id: Template identifier

        Returns:
            Export data with version info
        """
        template = await self.get_template(template_id)
        if not template:
            return None

        return {
            "version": "1.0",
            "exported_at": datetime.utcnow().isoformat() + "Z",
            "template": template,
        }

    async def import_template(
        self,
        import_data: Dict[str, Any],
        author: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Import a template from export data

        Args:
            import_data: Export data from export_template
            author: Importing user

        Returns:
            Imported template data
        """
        template = import_data.get("template")
        if not template:
            raise ValueError("Invalid import data: missing template")

        # Generate new ID if conflicts
        template_id = template.get("id", "imported")
        if await self.get_template(template_id):
            template_id = f"{template_id}_{datetime.utcnow().timestamp()}"

        template["id"] = template_id
        return await self.create_template(template, author)


# Singleton instance
_template_service: Optional[TemplateService] = None


def get_template_service() -> TemplateService:
    """Get the template service singleton instance"""
    global _template_service
    if _template_service is None:
        _template_service = TemplateService()
    return _template_service
