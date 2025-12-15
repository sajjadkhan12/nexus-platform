from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, DateTime, ForeignKey, Text, JSON, Enum as SQLEnum, Boolean, UniqueConstraint, TypeDecorator
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
import enum
import uuid

class Plugin(Base):
    __tablename__ = "plugins"

    id: Mapped[str] = mapped_column(String, primary_key=True)  # e.g., "gke-cluster"
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    author: Mapped[Optional[str]] = mapped_column(String)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    versions: Mapped[List["PluginVersion"]] = relationship(back_populates="plugin", cascade="all, delete-orphan")
    access_grants: Mapped[List["PluginAccess"]] = relationship(back_populates="plugin", cascade="all, delete-orphan")
    access_requests: Mapped[List["PluginAccessRequest"]] = relationship(back_populates="plugin", cascade="all, delete-orphan")

class PluginVersion(Base):
    __tablename__ = "plugin_versions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    plugin_id: Mapped[str] = mapped_column(ForeignKey("plugins.id"), nullable=False)
    version: Mapped[str] = mapped_column(String, nullable=False)  # e.g., "1.0.0"
    manifest: Mapped[dict] = mapped_column(JSON, nullable=False)
    storage_path: Mapped[str] = mapped_column(String, nullable=False)  # Path to zip file (legacy)
    git_repo_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # GitHub repository URL
    git_branch: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # Template branch (e.g., "gcp-bucket-001")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    plugin: Mapped["Plugin"] = relationship(back_populates="versions")
    jobs: Mapped[List["Job"]] = relationship(back_populates="plugin_version")

class CloudProvider(str, enum.Enum):
    AWS = "aws"
    GCP = "gcp"
    AZURE = "azure"
    KUBERNETES = "kubernetes"

class CloudCredential(Base):
    __tablename__ = "cloud_credentials"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    provider: Mapped[CloudProvider] = mapped_column(SQLEnum(CloudProvider), nullable=False)
    encrypted_data: Mapped[str] = mapped_column(Text, nullable=False)  # Encrypted JSON blob
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class JobStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"

class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String, primary_key=True)  # UUID
    plugin_version_id: Mapped[int] = mapped_column(ForeignKey("plugin_versions.id"), nullable=False)
    deployment_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("deployments.id"), nullable=True)
    status: Mapped[JobStatus] = mapped_column(SQLEnum(JobStatus), default=JobStatus.PENDING)
    triggered_by: Mapped[str] = mapped_column(String, nullable=False)  # User ID or email
    inputs: Mapped[dict] = mapped_column(JSON, default={})
    outputs: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    plugin_version: Mapped["PluginVersion"] = relationship(back_populates="jobs")
    logs: Mapped[List["JobLog"]] = relationship(back_populates="job", cascade="all, delete-orphan")

class JobLog(Base):
    __tablename__ = "job_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    level: Mapped[str] = mapped_column(String, default="INFO")
    message: Mapped[str] = mapped_column(Text, nullable=False)

    job: Mapped["Job"] = relationship(back_populates="logs")

class AccessRequestStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class AccessRequestStatusType(TypeDecorator):
    """TypeDecorator to ensure enum values (not names) are stored in database"""
    impl = String(20)
    cache_ok = True
    
    def process_bind_param(self, value, dialect):
        """Convert enum to its value (string) when storing"""
        if value is None:
            return None
        if isinstance(value, AccessRequestStatus):
            return value.value  # Return the enum value, not name
        if isinstance(value, str):
            return value  # Already a string
        return str(value)
    
    def process_result_value(self, value, dialect):
        """Convert string back to enum when reading"""
        if value is None:
            return None
        if isinstance(value, AccessRequestStatus):
            return value
        # Try to find enum member by value
        if isinstance(value, str):
            for status in AccessRequestStatus:
                if status.value == value:
                    return status
        return value

class PluginAccess(Base):
    __tablename__ = "plugin_access"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    plugin_id: Mapped[str] = mapped_column(ForeignKey("plugins.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    granted_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=False)
    granted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    plugin: Mapped["Plugin"] = relationship(back_populates="access_grants")
    
    __table_args__ = (
        UniqueConstraint('plugin_id', 'user_id', name='uq_plugin_access'),
    )

class PluginAccessRequest(Base):
    __tablename__ = "plugin_access_requests"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plugin_id: Mapped[str] = mapped_column(ForeignKey("plugins.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[AccessRequestStatus] = mapped_column(
        AccessRequestStatusType(),
        default=AccessRequestStatus.PENDING,
        nullable=False
    )
    requested_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    reviewed_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    plugin: Mapped["Plugin"] = relationship(back_populates="access_requests")
