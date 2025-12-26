"""Microservice provisioning and destruction tasks"""
import traceback
from datetime import datetime, timezone
from uuid import UUID
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.workers.db import get_sync_db_session
from app.logger import logger
from app.config import settings

from app.models import (
    Job, JobLog, JobStatus, PluginVersion, Plugin, Deployment,
    DeploymentStatus, Notification, NotificationType, User
)
from app.services.microservice_service import microservice_service
from app.services.github_actions_service import github_actions_service


class MicroserviceProvisionTask:
    """Task for provisioning microservices"""
    
    def __init__(self, job_id: str):
        self.job_id = job_id
        self.db: Optional[Session] = None
    
    def log_message(self, level: str, message: str):
        """Log message to both JobLog and server log"""
        if self.db:
            try:
                log = JobLog(job_id=self.job_id, level=level, message=message)
                self.db.add(log)
                self.db.commit()
            except Exception as e:
                logger.warning(f"Failed to write job log: {e}")
        
        log_func = getattr(logger, level.lower(), logger.info)
        log_func(f"[Microservice Job {self.job_id}] {message}")
    
    def execute(self, plugin_id: str, version: str, deployment_name: str,
                user_id: str, deployment_id: str = None):
        """Execute microservice provisioning"""
        self.db = get_sync_db_session()
        try:
            self._provision(plugin_id, version, deployment_name, user_id, deployment_id)
        except Exception as e:
            self._handle_error(e, deployment_id, deployment_name, user_id)
        finally:
            if self.db:
                self.db.close()
    
    def _provision(self, plugin_id: str, version: str, deployment_name: str,
                   user_id: str, deployment_id: str):
        """Main provisioning logic"""
        # Update job status
        job = self.db.execute(select(Job).where(Job.id == self.job_id)).scalar_one()
        job.status = JobStatus.RUNNING
        self.db.commit()
        
        self.log_message("INFO", f"Starting microservice provisioning: {deployment_name}")
        
        # Get plugin version
        plugin_version = self.db.execute(
            select(PluginVersion).where(
                PluginVersion.plugin_id == plugin_id,
                PluginVersion.version == version
            )
        ).scalar_one()
        
        # Verify this is a microservice plugin
        plugin = self.db.execute(
            select(Plugin).where(Plugin.id == plugin_id)
        ).scalar_one()
        
        if plugin.deployment_type != "microservice":
            raise Exception(f"Plugin {plugin_id} is not a microservice plugin")
        
        # Get template information
        template_repo_url = plugin_version.template_repo_url
        template_path = plugin_version.template_path
        
        if not template_repo_url or not template_path:
            raise Exception(f"Template repository URL or path not configured for plugin {plugin_id}")
        
        self.log_message("INFO", f"Template: {template_repo_url}/{template_path}")
        
        # Get or create deployment
        deployment = self._setup_deployment(deployment_id, plugin_id, version,
                                           deployment_name, user_id)
        
        # Get GitHub token
        user_github_token = settings.GITHUB_TOKEN if hasattr(settings, 'GITHUB_TOKEN') else ""
        if not user_github_token:
            raise Exception("GitHub token not configured. Cannot create repository.")
        
        self.log_message("INFO", f"Creating GitHub repository: {deployment_name}")
        
        # Get organization from settings
        organization = getattr(settings, 'MICROSERVICE_REPO_ORG', '') or None
        if organization:
            self.log_message("INFO", f"Creating repository in organization: {organization}")
        
        # Create repository from template
        try:
            repo_url, repo_full_name = microservice_service.create_repository_from_template(
                template_repo_url=template_repo_url,
                template_path=template_path,
                repo_name=deployment_name,
                user_github_token=user_github_token,
                description=f"Microservice: {deployment_name} (provisioned via IDP)",
                organization=organization
            )
            
            self.log_message("INFO", f"Successfully created repository: {repo_full_name}")
            self.log_message("INFO", f"Repository URL: {repo_url}")
        except Exception as e:
            error_msg = f"Failed to create repository: {str(e)}"
            self.log_message("ERROR", error_msg)
            raise Exception(error_msg)
        
        # Update deployment with repository information
        deployment.github_repo_url = repo_url
        deployment.github_repo_name = repo_full_name
        deployment.status = DeploymentStatus.ACTIVE
        deployment.ci_cd_status = "pending"
        self.db.add(deployment)
        
        # Update job status
        job.status = JobStatus.SUCCESS
        job.finished_at = datetime.now(timezone.utc)
        job.outputs = {
            "repository_url": repo_url,
            "repository_name": repo_full_name,
            "deployment_id": str(deployment.id)
        }
        self.db.add(job)
        
        # Get initial CI/CD status
        self._get_initial_cicd_status(deployment, repo_full_name, user_github_token)
        
        self.db.commit()
        
        # Create success notification
        user = self.db.execute(select(User).where(User.id == user_id)).scalar_one()
        notification = Notification(
            user_id=user.id,
            title="Microservice Created",
            message=f"Microservice '{deployment_name}' has been created. Repository: {repo_full_name}",
            type=NotificationType.SUCCESS,
            link=f"/deployments/{deployment.id}"
        )
        self.db.add(notification)
        self.db.commit()
        
        self.log_message("INFO", "Microservice provisioning completed successfully")
    
    def _setup_deployment(self, deployment_id: str, plugin_id: str, version: str,
                         deployment_name: str, user_id: str) -> Deployment:
        """Setup or get deployment record"""
        deployment = None
        if deployment_id:
            deployment_uuid = UUID(deployment_id) if isinstance(deployment_id, str) else deployment_id
            deployment = self.db.execute(
                select(Deployment).where(Deployment.id == deployment_uuid)
            ).scalar_one_or_none()
        
        if not deployment:
            user = self.db.execute(
                select(User).where(User.id == user_id)
            ).scalar_one_or_none()
            
            if not user:
                raise Exception(f"User {user_id} not found")
            
            deployment = Deployment(
                name=deployment_name,
                plugin_id=plugin_id,
                version=version,
                status=DeploymentStatus.PROVISIONING,
                deployment_type="microservice",
                user_id=user_id,
                inputs={"deployment_name": deployment_name},
            )
            self.db.add(deployment)
            self.db.commit()
            self.db.refresh(deployment)
            self.log_message("INFO", f"Created deployment record: {deployment.id}")
        else:
            deployment.status = DeploymentStatus.PROVISIONING
            deployment.deployment_type = "microservice"
            self.db.add(deployment)
            self.db.commit()
        
        return deployment
    
    def _get_initial_cicd_status(self, deployment: Deployment, repo_full_name: str,
                                user_github_token: str):
        """Get initial CI/CD status from GitHub Actions"""
        try:
            ci_cd_status = github_actions_service.get_latest_workflow_status(
                repo_full_name=repo_full_name,
                user_github_token=user_github_token,
                branch="main"
            )
            
            if ci_cd_status:
                deployment.ci_cd_status = ci_cd_status.get("ci_cd_status", "pending")
                deployment.ci_cd_run_id = ci_cd_status.get("ci_cd_run_id")
                deployment.ci_cd_run_url = ci_cd_status.get("ci_cd_run_url")
                deployment.ci_cd_updated_at = datetime.now(timezone.utc)
                self.log_message("INFO", f"Initial CI/CD status: {deployment.ci_cd_status}")
        except Exception as e:
            self.log_message("WARNING", f"Could not fetch initial CI/CD status: {str(e)}")
    
    def _handle_error(self, error: Exception, deployment_id: str,
                     deployment_name: str, user_id: str):
        """Handle errors during provisioning"""
        error_details = traceback.format_exc()
        logger.error(f"[CELERY ERROR] Microservice job {self.job_id} failed: {error_details}")
        
        try:
            job = self.db.execute(select(Job).where(Job.id == self.job_id)).scalar_one()
            job.status = JobStatus.FAILED
            job.error_message = str(error)
            job.finished_at = datetime.now(timezone.utc)
            self.db.add(job)  # Explicitly add job to ensure it's saved
            self.log_message("ERROR", f"Internal Error: {str(error)}")
            
            # Update deployment status
            deployment = None
            if deployment_id:
                deployment_uuid = UUID(deployment_id) if isinstance(deployment_id, str) else deployment_id
                deployment = self.db.execute(
                    select(Deployment).where(Deployment.id == deployment_uuid)
                ).scalar_one_or_none()
            
            if deployment:
                # Always set to FAILED if deployment exists and is in PROVISIONING or other non-final state
                if deployment.status in [DeploymentStatus.PROVISIONING, DeploymentStatus.ACTIVE]:
                    deployment.status = DeploymentStatus.FAILED
                    self.db.add(deployment)
                    self.log_message("ERROR", f"Deployment status set to FAILED due to error: {str(error)}")
                else:
                    self.log_message("WARNING", f"Deployment {deployment.id} is in status {deployment.status}, not updating to FAILED")
            
            # Create failure notification
            try:
                user = self.db.execute(select(User).where(User.id == user_id)).scalar_one()
                notification = Notification(
                    user_id=user.id,
                    title="Microservice Creation Failed",
                    message=f"Failed to create microservice '{deployment_name}': {str(error)}",
                    type=NotificationType.ERROR,
                    link=f"/jobs/{self.job_id}" if self.job_id else None
                )
                self.db.add(notification)
            except Exception as notif_error:
                logger.error(f"Failed to create notification for user {user_id} on microservice failure: {notif_error}", exc_info=True)
            
            self.db.commit()
        except Exception as db_error:
            logger.error(f"[CELERY ERROR] Failed to update job status for {self.job_id}: {db_error}")


class MicroserviceDestroyTask:
    """Task for destroying microservices"""
    
    def __init__(self, deployment_id: str):
        self.deployment_id = deployment_id
        self.db: Optional[Session] = None
        self.deletion_job_id: Optional[str] = None
    
    def log_message(self, level: str, message: str):
        """Log message to both JobLog and server log"""
        if self.deletion_job_id and self.db:
            try:
                log = JobLog(job_id=self.deletion_job_id, level=level, message=message)
                self.db.add(log)
                self.db.commit()
            except Exception as e:
                logger.warning(f"Failed to write job log: {e}")
        
        log_func = getattr(logger, level.lower(), logger.info)
        log_func(f"[Microservice Deletion {self.deletion_job_id or 'N/A'}] {message}")
    
    def execute(self):
        """Execute microservice destruction"""
        self.db = get_sync_db_session()
        try:
            return self._destroy()
        except Exception as e:
            error_details = traceback.format_exc()
            logger.error(f"[CELERY ERROR] Microservice deletion {self.deployment_id} failed: {error_details}")
            
            try:
                if self.deletion_job_id:
                    deletion_job = self.db.execute(
                        select(Job).where(Job.id == self.deletion_job_id)
                    ).scalar_one_or_none()
                    if deletion_job:
                        deletion_job.status = JobStatus.FAILED
                        deletion_job.finished_at = datetime.now(timezone.utc)
                        self.db.add(deletion_job)
                
                deployment_uuid = UUID(self.deployment_id) if isinstance(self.deployment_id, str) else self.deployment_id
                deployment = self.db.execute(
                    select(Deployment).where(Deployment.id == deployment_uuid)
                ).scalar_one_or_none()
                
                if deployment:
                    deployment.status = DeploymentStatus.FAILED
                    self.db.add(deployment)
                    
                    # Create failure notification
                    try:
                        user = self.db.execute(
                            select(User).where(User.id == deployment.user_id)
                        ).scalar_one()
                        notification = Notification(
                            user_id=user.id,
                            title="Deletion Failed",
                            message=f"Failed to delete microservice '{deployment.name}': {str(e)}",
                            type=NotificationType.ERROR,
                            link=f"/deployments/{deployment.id}" if deployment else None
                        )
                        self.db.add(notification)
                    except Exception:
                        pass
                
                self.db.commit()
            except Exception as db_error:
                logger.error(f"[CELERY ERROR] Failed to update job status for {self.deployment_id}: {db_error}")
            
            return {"status": "error", "message": str(e)}
        finally:
            if self.db:
                self.db.close()
    
    def _destroy(self):
        """Main destruction logic"""
        logger.info(f"Starting microservice deletion for deployment {self.deployment_id}")
        
        # Get deployment
        deployment_uuid = UUID(self.deployment_id) if isinstance(self.deployment_id, str) else self.deployment_id
        deployment = self.db.execute(
            select(Deployment).where(Deployment.id == deployment_uuid)
        ).scalar_one_or_none()
        
        if not deployment:
            logger.error(f"Deployment {self.deployment_id} not found")
            return {"status": "error", "message": "Deployment not found"}
        
        # Verify this is a microservice
        if deployment.deployment_type != "microservice":
            logger.warning(f"Deployment {self.deployment_id} is not a microservice, but destroy_microservice was called")
            self.log_message("WARNING", "This deployment is not a microservice")
        
        # Find deletion job
        deletion_job = self._find_deletion_job(deployment)
        if deletion_job:
            self.deletion_job_id = deletion_job.id
            if deletion_job.status == JobStatus.PENDING:
                deletion_job.status = JobStatus.RUNNING
                self.db.commit()
            self.log_message("INFO", f"Starting microservice deletion for deployment {self.deployment_id}")
        
        # Update status
        deployment.status = DeploymentStatus.DELETED  # Mark as deleted to prevent provisioning logic
        self.db.commit()
        self.log_message("INFO", "Updated deployment status to deleting")
        
        # Delete GitHub repository
        self._delete_github_repository(deployment)
        
        # Create notification
        notification = Notification(
            user_id=deployment.user_id,
            title="Deletion Successful",
            message=f"Microservice '{deployment.name}' has been deleted successfully.",
            type=NotificationType.SUCCESS,
            link="/catalog"
        )
        self.db.add(notification)
        self.db.commit()
        self.log_message("INFO", "Notification created for successful deletion")
        
        # Update deletion job
        if deletion_job:
            deletion_job.status = JobStatus.SUCCESS
            deletion_job.finished_at = datetime.now(timezone.utc)
            self.db.add(deletion_job)
            self.db.commit()
            self.log_message("INFO", "Deletion job completed successfully")
        
        # Mark deployment as deleted ONLY after successful destruction
        # This preserves history and allows users to see deleted deployments
        # Store as string value to ensure proper comparison in queries
        from app.models.deployment import DeploymentStatus
        deployment.status = DeploymentStatus.DELETED.value
        deployment.updated_at = datetime.now(timezone.utc)
        self.db.add(deployment)
        self.db.commit()
        self.log_message("INFO", f"Microservice deployment {deployment.id} ({deployment.name}) marked as DELETED after successful destruction")
        logger.info(f"Microservice deployment {self.deployment_id} marked as DELETED after successful destruction")
        
        return {"status": "success", "message": "Microservice deleted successfully"}
    
    def _find_deletion_job(self, deployment: Deployment):
        """Find deletion job for deployment"""
        from app.models import Job, JobStatus
        
        deletion_job_result = self.db.execute(
            select(Job).where(
                Job.deployment_id == deployment.id,
                Job.status == JobStatus.PENDING
            ).order_by(Job.created_at.desc())
        )
        deletion_job_row = deletion_job_result.first()
        return deletion_job_row[0] if deletion_job_row else None
    
    def _delete_github_repository(self, deployment: Deployment):
        """Delete GitHub repository if it exists"""
        if deployment.github_repo_name:
            try:
                user_github_token = settings.GITHUB_TOKEN if hasattr(settings, 'GITHUB_TOKEN') else ""
                if user_github_token:
                    self.log_message("INFO", f"Deleting GitHub repository: {deployment.github_repo_name}")
                    logger.info(f"Deleting GitHub repository: {deployment.github_repo_name}")
                    microservice_service.delete_github_repository(deployment.github_repo_name, user_github_token)
                    self.log_message("INFO", f"Successfully deleted GitHub repository: {deployment.github_repo_name}")
                    logger.info(f"Successfully deleted GitHub repository: {deployment.github_repo_name}")
                else:
                    self.log_message("WARNING", "GITHUB_TOKEN not configured, cannot delete repository")
                    logger.warning("GITHUB_TOKEN not configured, skipping repository deletion")
            except Exception as e:
                error_msg = f"Could not delete GitHub repository: {str(e)}"
                self.log_message("WARNING", error_msg)
                logger.warning(error_msg, exc_info=True)
        else:
            self.log_message("INFO", "No GitHub repository associated with this deployment")

