from sqlalchemy import String, ForeignKey, DateTime, DECIMAL, Enum, BigInteger, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship, Mapped, mapped_column
import uuid
from datetime import datetime
from typing import Optional, List
import enum
from app.database import Base

class DeploymentStatus(str, enum.Enum):
    ACTIVE = "active"
    PROVISIONING = "provisioning"
    FAILED = "failed"
    DELETING = "deleting"  # Status while deletion is in progress
    DELETED = "deleted"

class DeploymentType(str, enum.Enum):
    INFRASTRUCTURE = "infrastructure"
    MICROSERVICE = "microservice"

class CICDStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"

class Environment(str, enum.Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"

class DeploymentTag(Base):
    """Tags for deployments - flexible key-value pairs"""
    __tablename__ = "deployment_tags"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    deployment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("deployments.id", ondelete="CASCADE"), nullable=False)
    key: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        UniqueConstraint('deployment_id', 'key', name='uix_deployment_tag_key'),
    )
    
    # Relationship
    deployment: Mapped["Deployment"] = relationship("Deployment", back_populates="tags")

class Deployment(Base):
    __tablename__ = "deployments"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Core fields
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default=DeploymentStatus.PROVISIONING)
    deployment_type: Mapped[str] = mapped_column(String(50), nullable=False, default=DeploymentType.INFRASTRUCTURE)
    
    # Environment & Cost Tracking
    environment: Mapped[str] = mapped_column(String(50), nullable=False, default=Environment.DEVELOPMENT, index=True)
    cost_center: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    project_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Plugin reference
    plugin_id: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # Infrastructure details
    stack_name: Mapped[str] = mapped_column(String(255), nullable=True)
    cloud_provider: Mapped[str] = mapped_column(String(50), nullable=True)
    region: Mapped[str] = mapped_column(String(100), nullable=True)
    git_branch: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Deployment branch (e.g., "deploy-{deployment-id}")
    
    # Microservice details
    github_repo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # Full URL to created microservice repository
    github_repo_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Repository name for easy reference
    
    # CI/CD status tracking
    ci_cd_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # pending, running, success, failed, cancelled
    ci_cd_run_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)  # GitHub Actions run ID (BIGINT for large IDs)
    ci_cd_run_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # Direct link to Actions run
    ci_cd_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)  # Last CI/CD status update
    
    # Update tracking (for updating existing deployments)
    update_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # null, updating, update_succeeded, update_failed
    last_update_job_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Job ID of the most recent update attempt
    last_update_error: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # Error message from last failed update
    last_update_attempted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)  # Timestamp of last update attempt
    
    # Data
    inputs: Mapped[Optional[dict]] = mapped_column(JSONB)
    outputs: Mapped[Optional[dict]] = mapped_column(JSONB)
    
    # Ownership
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Business Unit
    business_unit_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("business_units.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user: Mapped["User"] = relationship("User", backref="deployments")
    business_unit: Mapped[Optional["BusinessUnit"]] = relationship("BusinessUnit", back_populates="deployments")
    tags: Mapped[List["DeploymentTag"]] = relationship("DeploymentTag", back_populates="deployment", cascade="all, delete-orphan")
    history: Mapped[List["DeploymentHistory"]] = relationship("DeploymentHistory", back_populates="deployment", cascade="all, delete-orphan", order_by="DeploymentHistory.version_number.desc()")

class DeploymentHistory(Base):
    """Tracks all versions/changes to deployments for history and rollback capability"""
    __tablename__ = "deployment_history"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    deployment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("deployments.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number: Mapped[int] = mapped_column(BigInteger, nullable=False)  # Sequential version number (1, 2, 3, ...)
    inputs: Mapped[dict] = mapped_column(JSONB, nullable=False)
    outputs: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False)  # Status at time of this version
    job_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # User email who created this version
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # Optional description of what changed
    
    __table_args__ = (
        UniqueConstraint('deployment_id', 'version_number', name='uix_deployment_version'),
    )
    
    # Relationships
    deployment: Mapped["Deployment"] = relationship("Deployment", back_populates="history")
