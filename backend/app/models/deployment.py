from sqlalchemy import String, ForeignKey, DateTime, DECIMAL, Enum
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

class Deployment(Base):
    __tablename__ = "deployments"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Core fields
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default=DeploymentStatus.PROVISIONING)
    
    # Plugin reference
    plugin_id: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # Infrastructure details
    stack_name: Mapped[str] = mapped_column(String(255), nullable=True)
    cloud_provider: Mapped[str] = mapped_column(String(50), nullable=True)
    region: Mapped[str] = mapped_column(String(100), nullable=True)
    git_branch: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Deployment branch (e.g., "deploy-{deployment-id}")
    
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
