"""Deployment service for deployment operations"""
from uuid import UUID
from datetime import datetime, timezone
from typing import Optional, Dict
import uuid as uuid_lib

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload

from app.models.deployment import Deployment, DeploymentStatus, DeploymentHistory, DeploymentTag
from app.models.plugins import Job, JobStatus, JobLog, PluginVersion
from app.models.rbac import User
from app.schemas.deployment import DeploymentCreate, DeploymentUpdateRequest
from app.api.deps import OrgAwareEnforcer
from app.core.utils import get_or_404, raise_permission_denied
from app.logger import logger
from app.config import settings


class DeploymentService:
    """Service for deployment operations"""
    
    def __init__(self, db: AsyncSession, enforcer: OrgAwareEnforcer):
        self.db = db
        self.enforcer = enforcer
    
    async def check_permission(
        self, user: User, deployment: Deployment, action: str
    ) -> bool:
        """Check if user has permission for action on deployment"""
        user_id = str(user.id)
        
        # Check if user owns the deployment
        owns_deployment = deployment.user_id == user.id
        
        # Check permissions
        if action == "read":
            return (self.enforcer.enforce(user_id, "deployments", "list") or
                   (self.enforcer.enforce(user_id, "deployments", "list:own") and owns_deployment))
        elif action == "update":
            return (self.enforcer.enforce(user_id, "deployments", "update") or
                   (self.enforcer.enforce(user_id, "deployments", "update:own") and owns_deployment))
        elif action == "delete":
            return (self.enforcer.enforce(user_id, "deployments", "delete") or
                   (self.enforcer.enforce(user_id, "deployments", "delete:own") and owns_deployment))
        
        return False
    
    async def get_deployment(
        self, deployment_id: str, user: User, include_tags: bool = True
    ) -> Deployment:
        """Get a deployment by ID with permission check"""
        try:
            deployment_uuid = UUID(deployment_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid deployment ID format")
        
        query = select(Deployment)
        if include_tags:
            query = query.options(selectinload(Deployment.tags))
        
        result = await self.db.execute(
            query.where(Deployment.id == deployment_uuid)
        )
        deployment = result.scalar_one_or_none()
        
        if not deployment:
            raise HTTPException(status_code=404, detail="Deployment not found")
        
        if not await self.check_permission(user, deployment, "read"):
            raise_permission_denied("view this deployment")
        
        return deployment
    
    async def list_deployments(
        self, user: User, filters: Dict, pagination: Dict
    ) -> Dict:
        """List deployments with filters and pagination"""
        from sqlalchemy import or_
        
        user_id = str(user.id)
        skip = pagination.get("skip", 0)
        limit = pagination.get("limit", 50)
        
        # Base query based on permissions
        if self.enforcer.enforce(user_id, "deployments", "list"):
            base_query = select(Deployment).options(selectinload(Deployment.tags))
            base_count_query = select(func.count(Deployment.id))
        elif self.enforcer.enforce(user_id, "deployments", "list:own"):
            base_filter = Deployment.user_id == user.id
            base_query = select(Deployment).options(selectinload(Deployment.tags)).where(base_filter)
            base_count_query = select(func.count(Deployment.id)).where(base_filter)
        else:
            raise HTTPException(status_code=403, detail="Permission denied")
        
        # Apply search filter
        if filters.get("search"):
            search = filters["search"]
            if len(search) > 100:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Search query too long. Maximum 100 characters allowed."
                )
            search_pattern = f"%{search}%"
            search_filter = or_(
                Deployment.name.ilike(search_pattern),
                Deployment.plugin_id.ilike(search_pattern),
                Deployment.stack_name.ilike(search_pattern),
                Deployment.region.ilike(search_pattern)
            )
            base_query = base_query.where(search_filter)
            base_count_query = base_count_query.where(search_filter)
        
        # Apply status filter
        if filters.get("status"):
            base_query = base_query.where(Deployment.status == filters["status"])
            base_count_query = base_count_query.where(Deployment.status == filters["status"])
        
        # Apply cloud provider filter
        if filters.get("cloud_provider"):
            base_query = base_query.where(Deployment.cloud_provider.ilike(f"%{filters['cloud_provider']}%"))
            base_count_query = base_count_query.where(Deployment.cloud_provider.ilike(f"%{filters['cloud_provider']}%"))
        
        # Apply plugin_id filter
        if filters.get("plugin_id"):
            base_query = base_query.where(Deployment.plugin_id == filters["plugin_id"])
            base_count_query = base_count_query.where(Deployment.plugin_id == filters["plugin_id"])
        
        # Apply environment filter
        if filters.get("environment"):
            base_query = base_query.where(Deployment.environment == filters["environment"])
            base_count_query = base_count_query.where(Deployment.environment == filters["environment"])
        
        # Apply tags filter
        if filters.get("tags"):
            tags = filters["tags"]
            tag_filters = {}
            for tag_pair in tags.split(','):
                if ':' in tag_pair:
                    key, value = tag_pair.split(':', 1)
                    tag_filters[key.strip()] = value.strip()
            
            if tag_filters:
                from sqlalchemy import and_
                tag_conditions = [
                    and_(DeploymentTag.key == key, DeploymentTag.value == value)
                    for key, value in tag_filters.items()
                ]
                
                tag_match_subquery = (
                    select(DeploymentTag.deployment_id)
                    .where(or_(*tag_conditions))
                    .group_by(DeploymentTag.deployment_id)
                    .having(func.count(DeploymentTag.deployment_id) == len(tag_filters))
                )
                
                base_query = base_query.where(Deployment.id.in_(tag_match_subquery))
                base_count_query = base_count_query.where(Deployment.id.in_(tag_match_subquery))
        
        # Order by created_at descending
        base_query = base_query.order_by(Deployment.created_at.desc())
        
        # Get total count
        total_result = await self.db.execute(base_count_query)
        total = total_result.scalar() or 0
        
        # Apply pagination
        query = base_query.offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        deployments = result.scalars().all()
        
        # Serialize deployments
        from app.schemas.deployment import DeploymentResponse
        deployment_items = [DeploymentResponse.model_validate(d) for d in deployments]
        
        return {
            "items": deployment_items,
            "total": total,
            "skip": skip,
            "limit": limit
        }
    
    async def create_deployment(
        self, user: User, deployment_data: DeploymentCreate
    ) -> Deployment:
        """Create a new deployment"""
        user_id = str(user.id)
        if not self.enforcer.enforce(user_id, "deployments", "create"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
        
        new_deployment = Deployment(
            **deployment_data.dict(),
            user_id=user.id
        )
        self.db.add(new_deployment)
        await self.db.commit()
        await self.db.refresh(new_deployment)
        
        return new_deployment
    
    async def update_deployment(
        self, deployment_id: str, user: User, update_request: DeploymentUpdateRequest
    ) -> Dict:
        """Update an existing active deployment"""
        deployment = await get_or_404(self.db, Deployment, deployment_id, resource_name="Deployment")
        
        # Check permissions
        if not await self.check_permission(user, deployment, "update"):
            raise_permission_denied("update this deployment")
        
        # Only allow updates for active deployments
        if deployment.status != DeploymentStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot update deployment with status '{deployment.status}'. Only active deployments can be updated."
            )
        
        # Check if an update is already in progress
        if deployment.update_status == "updating":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An update is already in progress for this deployment. Please wait for it to complete."
            )
        
        # Get plugin version
        plugin_version_result = await self.db.execute(
            select(PluginVersion).where(
                PluginVersion.plugin_id == deployment.plugin_id,
                PluginVersion.version == deployment.version
            )
        )
        plugin_version = plugin_version_result.scalar_one_or_none()
        
        if not plugin_version:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plugin version not found"
            )
        
        # Only infrastructure deployments can be updated via this endpoint
        if deployment.deployment_type != "infrastructure":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only infrastructure deployments can be updated via this endpoint"
            )
        
        # Create a new job for the update
        update_job = Job(
            id=str(uuid_lib.uuid4()),
            plugin_version_id=plugin_version.id,
            deployment_id=deployment.id,
            status=JobStatus.PENDING,
            triggered_by=user.email,
            inputs=update_request.inputs,
            retry_count=0
        )
        self.db.add(update_job)
        
        # Update deployment tracking fields
        deployment.update_status = "updating"
        deployment.last_update_job_id = update_job.id
        deployment.last_update_error = None
        deployment.last_update_attempted_at = datetime.now(timezone.utc)
        
        # Update optional fields if provided
        if update_request.cost_center is not None:
            deployment.cost_center = update_request.cost_center
        if update_request.project_code is not None:
            deployment.project_code = update_request.project_code
        
        # Update tags if provided
        if update_request.tags is not None:
            # Delete existing tags
            existing_tags = await self.db.execute(
                select(DeploymentTag).where(DeploymentTag.deployment_id == deployment.id)
            )
            for tag in existing_tags.scalars().all():
                await self.db.delete(tag)
            
            # Add new tags
            for key, value in update_request.tags.items():
                tag = DeploymentTag(
                    deployment_id=deployment.id,
                    key=key,
                    value=value
                )
                self.db.add(tag)
        
        # Add log entry
        update_log = JobLog(
            job_id=update_job.id,
            level="INFO",
            message=f"Deployment update initiated by {user.email}"
        )
        self.db.add(update_log)
        
        await self.db.commit()
        await self.db.refresh(update_job)
        await self.db.refresh(deployment)
        
        # Auto-select credentials based on plugin's cloud provider
        credential_name = None
        cloud_provider = plugin_version.manifest.get("cloud_provider")
        
        if cloud_provider and cloud_provider != "unknown":
            from app.models import CloudProvider, CloudCredential
            try:
                provider_enum = CloudProvider(cloud_provider)
                cred_result = await self.db.execute(
                    select(CloudCredential).where(CloudCredential.provider == provider_enum)
                )
                credential = cred_result.scalar_one_or_none()
                if credential:
                    credential_name = credential.name
            except ValueError:
                pass
        
        # Queue update job to Celery worker
        from app.workers import celery_app
        
        try:
            task = celery_app.send_task(
                "provision_infrastructure",
                args=[update_job.id, deployment.plugin_id, deployment.version, 
                      update_request.inputs, credential_name, str(deployment.id)]
            )
            
            return {
                "message": "Deployment update initiated",
                "job_id": update_job.id,
                "deployment_id": str(deployment_id),
                "status": "accepted"
            }
        except Exception as e:
            logger.error(f"Error queuing update task for deployment {deployment_id}: {str(e)}")
            # Reset update status on error
            deployment.update_status = None
            deployment.last_update_job_id = None
            await self.db.commit()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to initiate deployment update: {str(e)}"
            )
    
    async def rollback_deployment(
        self, deployment_id: str, version_number: int, user: User
    ) -> Dict:
        """Rollback a deployment to a previous version"""
        deployment = await get_or_404(self.db, Deployment, deployment_id, resource_name="Deployment")
        
        # Check permissions
        if not await self.check_permission(user, deployment, "update"):
            raise_permission_denied("rollback this deployment")
        
        # Only allow rollback for active deployments
        if deployment.status != DeploymentStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot rollback deployment with status '{deployment.status}'. Only active deployments can be rolled back."
            )
        
        # Check if an update is already in progress
        if deployment.update_status == "updating":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An update is already in progress for this deployment. Please wait for it to complete."
            )
        
        # Get the history entry for the specified version
        history_result = await self.db.execute(
            select(DeploymentHistory)
            .where(
                DeploymentHistory.deployment_id == deployment.id,
                DeploymentHistory.version_number == version_number
            )
        )
        history_entry = history_result.scalar_one_or_none()
        
        if not history_entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Version {version_number} not found in deployment history"
            )
        
        # Get plugin version
        plugin_version_result = await self.db.execute(
            select(PluginVersion).where(
                PluginVersion.plugin_id == deployment.plugin_id,
                PluginVersion.version == deployment.version
            )
        )
        plugin_version = plugin_version_result.scalar_one_or_none()
        
        if not plugin_version:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plugin version not found"
            )
        
        # Only infrastructure deployments can be rolled back via this endpoint
        if deployment.deployment_type != "infrastructure":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only infrastructure deployments can be rolled back via this endpoint"
            )
        
        # Create a new job for the rollback
        rollback_job = Job(
            id=str(uuid_lib.uuid4()),
            plugin_version_id=plugin_version.id,
            deployment_id=deployment.id,
            status=JobStatus.PENDING,
            triggered_by=user.email,
            inputs=history_entry.inputs.copy(),
            retry_count=0
        )
        self.db.add(rollback_job)
        
        # Update deployment tracking fields
        deployment.update_status = "updating"
        deployment.last_update_job_id = rollback_job.id
        deployment.last_update_error = None
        deployment.last_update_attempted_at = datetime.now(timezone.utc)
        
        # Add log entry
        rollback_log = JobLog(
            job_id=rollback_job.id,
            level="INFO",
            message=f"Deployment rollback to version {version_number} initiated by {user.email}"
        )
        self.db.add(rollback_log)
        
        await self.db.commit()
        await self.db.refresh(rollback_job)
        await self.db.refresh(deployment)
        
        # Auto-select credentials
        credential_name = None
        cloud_provider = plugin_version.manifest.get("cloud_provider")
        
        if cloud_provider and cloud_provider != "unknown":
            from app.models import CloudProvider, CloudCredential
            try:
                provider_enum = CloudProvider(cloud_provider)
                cred_result = await self.db.execute(
                    select(CloudCredential).where(CloudCredential.provider == provider_enum)
                )
                credential = cred_result.scalar_one_or_none()
                if credential:
                    credential_name = credential.name
            except ValueError:
                pass
        
        # Queue rollback job
        from app.workers import celery_app
        try:
            celery_app.send_task(
                "provision_infrastructure",
                args=[rollback_job.id, deployment.plugin_id, deployment.version,
                      history_entry.inputs, credential_name, str(deployment.id)]
            )
            
            return {
                "message": f"Deployment rollback to version {version_number} initiated",
                "job_id": rollback_job.id,
                "deployment_id": str(deployment_id),
                "version_number": version_number,
                "status": "accepted"
            }
        except Exception as e:
            logger.error(f"Error queuing rollback task for deployment {deployment_id}: {str(e)}")
            deployment.update_status = None
            deployment.last_update_job_id = None
            await self.db.commit()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to initiate deployment rollback: {str(e)}"
            )
    
    async def delete_deployment(
        self, deployment_id: str, user: User
    ) -> Dict:
        """Delete a deployment"""
        deployment = await get_or_404(self.db, Deployment, deployment_id, resource_name="Deployment")
        
        # Check permissions
        if not await self.check_permission(user, deployment, "delete"):
            raise_permission_denied("delete this deployment")
        
        # Get plugin version to create a deletion job
        plugin_version_result = await self.db.execute(
            select(PluginVersion).where(
                PluginVersion.plugin_id == deployment.plugin_id,
                PluginVersion.version == deployment.version
            )
        )
        plugin_version = plugin_version_result.scalar_one_or_none()
        
        # Create a job for deletion tracking
        job_id = None
        if plugin_version:
            deletion_job = Job(
                id=str(uuid_lib.uuid4()),
                plugin_version_id=plugin_version.id,
                deployment_id=deployment.id,
                status=JobStatus.PENDING,
                triggered_by=user.email,
                inputs={"action": "destroy", "deployment_id": str(deployment_id), "deployment_name": deployment.name}
            )
            self.db.add(deletion_job)
            await self.db.commit()
            job_id = deletion_job.id
        
        # Route to appropriate destroy task based on deployment type
        deployment_type = deployment.deployment_type or "infrastructure"
        
        if deployment_type == "microservice":
            from app.workers import celery_app
            try:
                logger.info(f"Initiating microservice deletion for deployment {deployment_id}")
                task = celery_app.send_task("destroy_microservice", args=[str(deployment_id)])
                
                return {
                    "message": "Microservice deletion initiated",
                    "task_id": task.id,
                    "job_id": job_id,
                    "deployment_id": str(deployment_id),
                    "status": "accepted"
                }
            except Exception as e:
                logger.error(f"Error initiating microservice deletion: {e}", exc_info=True)
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to initiate deletion: {str(e)}"
                )
        else:
            from app.workers import celery_app
            try:
                logger.info(f"Initiating infrastructure deletion for deployment {deployment_id}, job_id: {job_id}")
                task = celery_app.send_task("destroy_infrastructure", args=[str(deployment_id)])
                logger.info(f"Celery task created successfully: task_id={task.id}, deployment_id={deployment_id}, job_id={job_id}")
                
                return {
                    "message": "Infrastructure deletion initiated",
                    "task_id": task.id,
                    "job_id": job_id,
                    "deployment_id": str(deployment_id),
                    "status": "accepted"
                }
            except Exception as e:
                logger.error(f"Error initiating infrastructure deletion: {e}", exc_info=True)
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to initiate deletion: {str(e)}"
                )
    
    async def get_deployment_history(
        self, deployment_id: str, user: User
    ) -> Dict:
        """Get deployment history"""
        deployment = await get_or_404(self.db, Deployment, deployment_id, resource_name="Deployment")
        
        # Check permissions
        if not await self.check_permission(user, deployment, "read"):
            raise_permission_denied("view deployment history")
        
        # Get history entries
        history_result = await self.db.execute(
            select(DeploymentHistory)
            .where(DeploymentHistory.deployment_id == deployment.id)
            .order_by(DeploymentHistory.version_number.desc())
        )
        history_entries = history_result.scalars().all()
        
        # Convert to response format
        history_list = []
        for entry in history_entries:
            history_list.append({
                "id": str(entry.id),
                "version_number": entry.version_number,
                "inputs": entry.inputs,
                "outputs": entry.outputs,
                "status": entry.status,
                "job_id": entry.job_id,
                "created_at": entry.created_at.isoformat() if entry.created_at else None,
                "created_by": entry.created_by,
                "description": entry.description
            })
        
        return {"history": history_list}

