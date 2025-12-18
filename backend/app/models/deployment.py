from sqlalchemy import String, ForeignKey, DateTime, DECIMAL, Enum, BigInteger
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship, Mapped, mapped_column
import uuid
from datetime import datetime
from typing import Optional
import enum
from app.database import Base

class DeploymentStatus(str, enum.Enum):
    ACTIVE = "active"
    PROVISIONING = "provisioning"
    FAILED = "failed"
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

class Deployment(Base):
    __tablename__ = "deployments"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Core fields
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default=DeploymentStatus.PROVISIONING)
    deployment_type: Mapped[str] = mapped_column(String(50), nullable=False, default=DeploymentType.INFRASTRUCTURE)
    
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
    
    # Data
    inputs: Mapped[Optional[dict]] = mapped_column(JSONB)
    outputs: Mapped[Optional[dict]] = mapped_column(JSONB)
    
    # Ownership
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user: Mapped["User"] = relationship("User", backref="deployments")
