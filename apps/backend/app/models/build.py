"""
Build models for image build records
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import String, DateTime, Integer, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class BuildStatus(str):
    """Build status enumeration"""
    PENDING = "pending"
    BUILDING = "building"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BuildRecord(Base):
    """Image build record"""
    __tablename__ = "build_records"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    image_name: Mapped[str] = mapped_column(String(500), nullable=False)
    image_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    build_config: Mapped[str] = mapped_column(Text, nullable=False)
    build_key: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=BuildStatus.PENDING, index=True
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    build_time_ms: Mapped[int] = mapped_column(Integer, default=0)
    size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    layers: Mapped[list["BuildLayer"]] = relationship(
        "BuildLayer", back_populates="build", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<BuildRecord {self.name}:{self.status}>"


class BuildLayer(Base):
    """Individual build layer"""
    __tablename__ = "build_layers"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    build_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("build_records.id"),
        nullable=False,
        index=True,
    )
    layer_type: Mapped[str] = mapped_column(String(50), nullable=False)
    layer_order: Mapped[int] = mapped_column(Integer, nullable=False)
    cache_key: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    build: Mapped["BuildRecord"] = relationship("BuildRecord", back_populates="layers")

    def __repr__(self) -> str:
        return f"<BuildLayer {self.layer_type}:{self.layer_order}>"


class RepositoryRecord(Base):
    """Image repository record"""
    __tablename__ = "repository_records"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    registry: Mapped[str] = mapped_column(String(255), nullable=False)
    registry_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="docker"
    )  # docker, harbor, gitlab, aws_ecr, gcp_gcr, azure_acr
    endpoint: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    # Password should be encrypted
    password: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_public: Mapped[bool] = mapped_column(default=False)
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return f"<RepositoryRecord {self.registry}/{self.name}>"


class ImageTag(Base):
    """Image tag record"""
    __tablename__ = "image_tags"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    repository_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("repository_records.id"),
        nullable=False,
        index=True,
    )
    image_name: Mapped[str] = mapped_column(String(255), nullable=False)
    tag: Mapped[str] = mapped_column(String(100), nullable=False)
    digest: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    manifest: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    last_pulled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_pushed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return f"<ImageTag {self.image_name}:{self.tag}>"


# Import JSON type
from sqlalchemy.dialects.postgresql import JSON
