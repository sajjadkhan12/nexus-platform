from sqlalchemy import String, ForeignKey, DateTime, Boolean, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func
import uuid
from datetime import datetime
from typing import List, Optional
from app.database import Base

class BusinessUnit(Base):
    __tablename__ = "business_units"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(String(1000))
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    members: Mapped[List["BusinessUnitMember"]] = relationship("BusinessUnitMember", back_populates="business_unit", cascade="all, delete-orphan")
    groups: Mapped[List["BusinessUnitGroup"]] = relationship("BusinessUnitGroup", back_populates="business_unit", cascade="all, delete-orphan")
    deployments: Mapped[List["Deployment"]] = relationship("Deployment", back_populates="business_unit")

class BusinessUnitMember(Base):
    __tablename__ = "business_unit_members"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_unit_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("business_units.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("roles.id", ondelete="RESTRICT"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    business_unit: Mapped["BusinessUnit"] = relationship("BusinessUnit", back_populates="members")
    user: Mapped["User"] = relationship("User", back_populates="business_unit_memberships")
    role: Mapped["Role"] = relationship("Role")
    
    __table_args__ = (
        UniqueConstraint('business_unit_id', 'user_id', name='uix_business_unit_member'),
    )

class BusinessUnitGroup(Base):
    __tablename__ = "business_unit_groups"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_unit_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("business_units.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(String(500))
    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("roles.id", ondelete="RESTRICT"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    business_unit: Mapped["BusinessUnit"] = relationship("BusinessUnit", back_populates="groups")
    role: Mapped["Role"] = relationship("Role")
    members: Mapped[List["BusinessUnitGroupMember"]] = relationship("BusinessUnitGroupMember", back_populates="group", cascade="all, delete-orphan")
    
    __table_args__ = (
        UniqueConstraint('business_unit_id', 'name', name='uix_bu_group_name'),
    )

class BusinessUnitGroupMember(Base):
    __tablename__ = "business_unit_group_members"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("business_unit_groups.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    group: Mapped["BusinessUnitGroup"] = relationship("BusinessUnitGroup", back_populates="members")
    user: Mapped["User"] = relationship("User", back_populates="business_unit_group_memberships")
    
    __table_args__ = (
        UniqueConstraint('group_id', 'user_id', name='uix_bu_group_member'),
    )

