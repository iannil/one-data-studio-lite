"""
Notebook data models for One Data Studio Lite

Defines database models for notebook servers and configurations.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, DateTime, JSON, Float, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship

from app.core.database import Base


class Notebook(Base):
    """
    Notebook server model

    Represents a Jupyter notebook server managed by the platform.
    """

    __tablename__ = "notebooks"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, default="default")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)

    # Server configuration
    image_id = Column(String(100), nullable=False, default="pytorch")
    profile_id = Column(String(100), nullable=False, default="medium")

    # Resource allocation
    cpu_limit = Column(Float, nullable=False, default=2.0)
    cpu_guarantee = Column(Float, nullable=False, default=0.5)
    mem_limit = Column(String(20), nullable=False, default="4G")
    mem_guarantee = Column(String(20), nullable=False, default="1G")
    gpu_limit = Column(Integer, nullable=False, default=0)

    # Server state
    state = Column(String(50), nullable=False, default="stopped")  # running, stopped, pending, error
    pod_name = Column(String(255), nullable=True)
    url = Column(String(500), nullable=True)

    # Metadata
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    stopped_at = Column(DateTime, nullable=True)
    last_activity = Column(DateTime, nullable=True)

    # Configuration (for custom overrides)
    config = Column(JSON, nullable=True)

    # Relationships
    user = relationship("User", back_populates="notebooks")
    project = relationship("Project", back_populates="notebooks")
    sessions = relationship("NotebookSession", back_populates="notebook", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Notebook(id={self.id}, name='{self.name}', user_id={self.user_id}, state='{self.state}')>"


class NotebookSession(BaseModel):
    """
    Notebook session model

    Tracks active sessions on notebook servers.
    """

    __tablename__ = "notebook_sessions"

    id = Column(Integer, primary_key=True, index=True)
    notebook_id = Column(Integer, ForeignKey("notebooks.id"), nullable=False, index=True)

    # Session info
    kernel_id = Column(String(255), nullable=True)
    session_id = Column(String(255), nullable=False)
    connection_path = Column(String(500), nullable=True)

    # State
    state = Column(String(50), nullable=False, default="starting")  # starting, running, stopped, error

    # Timing
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    stopped_at = Column(DateTime, nullable=True)
    last_activity = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Resource usage
    cpu_percent = Column(Float, nullable=True)
    memory_mb = Column(Integer, nullable=True)
    gpu_memory_mb = Column(Integer, nullable=True)

    # Execution stats
    exec_count = Column(Integer, nullable=False, default=0)
    exec_total_seconds = Column(Float, nullable=False, default=0.0)

    # Relationships
    notebook = relationship("Notebook", back_populates="sessions")

    def __repr__(self):
        return f"<NotebookSession(id={self.id}, notebook_id={self.notebook_id}, state='{self.state}')>"


class NotebookImage(Base):
    """
    Notebook image template model

    Defines available notebook images.
    """

    __tablename__ = "notebook_images"

    id = Column(String(100), primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    image = Column(String(500), nullable=False)  # Full image name with tag
    icon = Column(String(100), nullable=False, default="python")
    packages = Column(JSON, nullable=False, default=list)  # List of package names
    default = Column(Boolean, nullable=False, default=False)
    gpu_required = Column(Boolean, nullable=False, default=False)
    gpu_recommended = Column(Boolean, nullable=False, default=False)
    enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f"<NotebookImage(id='{self.id}', name='{self.name}', image='{self.image}')>"


class ResourceProfile(Base):
    """
    Resource profile model

    Defines resource profiles available for notebook servers.
    """

    __tablename__ = "resource_profiles"

    id = Column(String(50), primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)

    # CPU resources
    cpu_limit = Column(Float, nullable=False)
    cpu_guarantee = Column(Float, nullable=False)

    # Memory resources
    mem_limit = Column(String(20), nullable=False)  # e.g., "4G"
    mem_guarantee = Column(String(20), nullable=False)

    # GPU resources
    gpu_limit = Column(Integer, nullable=False, default=0)

    # Metadata
    default = Column(Boolean, nullable=False, default=False)
    enabled = Column(Boolean, nullable=False, default=True)
    sort_order = Column(Integer, nullable=False, default=0)

    def __repr__(self):
        return f"<ResourceProfile(id='{self.id}', name='{self.name}', cpu_limit={self.cpu_limit})>"
