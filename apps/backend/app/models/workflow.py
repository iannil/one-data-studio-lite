"""
Workflow data models for One Data Studio Lite

Defines database models for DAGs, nodes, edges, and executions.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    JSON,
    ForeignKey,
    Enum as SQLEnum,
    Boolean,
    Float,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class DAG(Base):
    """
    DAG (Directed Acyclic Graph) model

    Represents a workflow with nodes and edges.
    """

    __tablename__ = "dags"

    id = Column(Integer, primary_key=True, index=True)
    dag_id = Column(String(250), unique=True, nullable=False, index=True)
    name = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)

    # Scheduling
    schedule_interval = Column(String(100), nullable=True)  # Cron expression or None
    start_date = Column(DateTime, nullable=True)
    catchup = Column(Boolean, nullable=False, default=False)
    max_active_runs = Column(Integer, nullable=False, default=1)
    concurrency = Column(Integer, nullable=False, default=16)

    # State
    is_active = Column(Boolean, nullable=False, default=True)
    is_paused = Column(Boolean, nullable=False, default=False)

    # Metadata
    tags = Column(JSON, nullable=True, default=list)  # List of tag strings
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_parsed = Column(DateTime, nullable=True)

    # File info (for DAGs created from files)
    fileloc = Column(String(500), nullable=True)
    filepath = Column(String(500), nullable=True)

    # Relationships
    owner = relationship("User", back_populates="dags")
    project = relationship("Project", back_populates="dags")
    nodes = relationship("DAGNode", back_populates="dag", cascade="all, delete-orphan")
    edges = relationship("DAGEdge", back_populates="dag", cascade="all, delete-orphan")
    runs = relationship("DAGRun", back_populates="dag", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<DAG(id={self.id}, dag_id='{self.dag_id}', schedule='{self.schedule_interval}')>"


class DAGNode(Base):
    """
    DAG Node model

    Represents a single task/node in a DAG.
    """

    __tablename__ = "dag_nodes"

    id = Column(Integer, primary_key=True, index=True)
    dag_id = Column(Integer, ForeignKey("dags.id"), nullable=False, index=True)
    node_id = Column(String(250), nullable=False, index=True)
    name = Column(String(500), nullable=False)
    node_type = Column(String(50), nullable=False)  # sql, python, etl, training, etc.

    # Task configuration
    config = Column(JSON, nullable=True, default=dict)

    # Execution settings
    retry_count = Column(Integer, nullable=False, default=0)
    retry_delay_seconds = Column(Integer, nullable=False, default=300)
    timeout_seconds = Column(Integer, nullable=True)
    execution_timeout_seconds = Column(Integer, nullable=True)

    # Dependencies (calculated from edges)
    depends_on_ids = Column(JSON, nullable=True, default=list)  # List of node IDs

    # Position for visualization
    x_position = Column(Float, nullable=True)
    y_position = Column(Float, nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    dag = relationship("DAG", back_populates="nodes")
    outgoing_edges = relationship("DAGEdge", foreign_keys="[DAGEdge.source_node_id]", back_populates="source_node")
    incoming_edges = relationship("DAGEdge", foreign_keys="[DAGEdge.target_node_id]", back_populates="target_node")

    def __repr__(self):
        return f"<DAGNode(id={self.id}, node_id='{self.node_id}', type='{self.node_type}')>"


class DAGEdge(Base):
    """
    DAG Edge model

    Represents a dependency relationship between two nodes.
    """

    __tablename__ = "dag_edges"

    id = Column(Integer, primary_key=True, index=True)
    dag_id = Column(Integer, ForeignKey("dags.id"), nullable=False, index=True)
    source_node_id = Column(Integer, ForeignKey("dag_nodes.id"), nullable=False, index=True)
    target_node_id = Column(Integer, ForeignKey("dag_nodes.id"), nullable=False, index=True)

    # Edge condition (optional - for conditional dependencies)
    condition = Column(String(500), nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    dag = relationship("DAG", back_populates="edges")
    source_node = relationship("DAGNode", foreign_keys=[source_node_id], back_populates="outgoing_edges")
    target_node = relationship("DAGNode", foreign_keys=[target_node_id], back_populates="incoming_edges")

    def __repr__(self):
        return f"<DAGEdge(id={self.id}, source={self.source_node_id}, target={self.target_node_id})>"


class DAGRun(Base):
    """
    DAG Run model

    Represents a single execution of a DAG.
    """

    __tablename__ = "dag_runs"

    id = Column(Integer, primary_key=True, index=True)
    dag_id = Column(Integer, ForeignKey("dags.id"), nullable=False, index=True)
    run_id = Column(String(250), unique=True, nullable=False, index=True)

    # Execution info
    execution_date = Column(DateTime, nullable=False, index=True)
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)

    # State
    state = Column(
        SQLEnum("queued", "running", "success", "failed", "cancelled", "paused", name="dag_run_state"),
        nullable=False,
        default="queued",
        index=True,
    )

    # Run configuration
    conf = Column(JSON, nullable=True, default=dict)
    run_type = Column(String(50), nullable=False, default="manual")  # manual, scheduled, backfill

    # Execution stats
    duration = Column(Float, nullable=True)  # Duration in seconds
    max_tries = Column(Integer, nullable=False, default=0)

    # User info
    triggered_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    dag = relationship("DAG", back_populates="runs")
    trigger = relationship("User", foreign_keys=[triggered_by])
    task_instances = relationship("TaskInstance", back_populates="dag_run", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<DAGRun(id={self.id}, run_id='{self.run_id}', state='{self.state}')>"


class TaskInstance(Base):
    """
    Task Instance model

    Represents a single task execution within a DAG run.
    """

    __tablename__ = "task_instances"

    id = Column(Integer, primary_key=True, index=True)
    dag_run_id = Column(Integer, ForeignKey("dag_runs.id"), nullable=False, index=True)
    node_id = Column(Integer, ForeignKey("dag_nodes.id"), nullable=False, index=True)
    task_id = Column(String(250), nullable=False, index=True)  # Unique identifier for this task instance

    # Execution info
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    duration = Column(Float, nullable=True)  # Duration in seconds

    # State
    state = Column(
        SQLEnum(
            "pending",
            "queued",
            "running",
            "success",
            "failed",
            "skipped",
            "upstream_failed",
            "retried",
            name="task_instance_state",
        ),
        nullable=False,
        default="pending",
        index=True,
    )

    # Retry info
    try_number = Column(Integer, nullable=False, default=1)
    max_tries = Column(Integer, nullable=False, default=0)
    previous_try_task_id = Column(Integer, ForeignKey("task_instances.id"), nullable=True)

    # Result
    result = Column(JSON, nullable=True)  # Task output
    error = Column(Text, nullable=True)  # Error message if failed

    # Host/Executor info
    hostname = Column(String(500), nullable=True)
    executor = Column(String(50), nullable=True)  # e.g., "LocalExecutor", "KubernetesExecutor"

    # Logs
    log_url = Column(String(1000), nullable=True)
    log_filepath = Column(String(1000), nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    dag_run = relationship("DAGRun", back_populates="task_instances")
    node = relationship("DAGNode")
    previous_try = relationship("TaskInstance", foreign_keys=[previous_try_task_id])

    def __repr__(self):
        return f"<TaskInstance(id={self.id}, task_id='{self.task_id}', state='{self.state}')>"
