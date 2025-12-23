"""Infrastructure provisioning and destruction tasks"""
from pathlib import Path
import tempfile
import shutil
import traceback
import asyncio
import re
from datetime import datetime, timezone
from uuid import UUID
from typing import Optional, Dict, Tuple

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.workers.db import get_sync_db_session
from app.workers.utils import categorize_error
from app.logger import logger
from app.config import settings

from app.models import (
    Job, JobLog, JobStatus, PluginVersion, CloudCredential, Deployment,
    DeploymentStatus, Notification, NotificationType, User, Plugin, DeploymentHistory
)
from app.services.storage import storage_service
from app.services.pulumi_service import pulumi_service
from app.services.crypto import crypto_service
from app.services.cloud_integrations import CloudIntegrationService
from app.services.git_service import git_service


class InfrastructureProvisionTask:
    """Task for provisioning infrastructure using Pulumi"""
    
    def __init__(self, job_id: str):
        self.job_id = job_id
        self.db: Optional[Session] = None
        self.temp_dir: Optional[Path] = None
    
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
        log_func(f"[Job {self.job_id}] {message}")
    
    def execute(self, plugin_id: str, version: str, inputs: dict,
                credential_name: str = None, deployment_id: str = None):
        """Execute infrastructure provisioning"""
        self.db = get_sync_db_session()
        try:
            self._provision(plugin_id, version, inputs, credential_name, deployment_id)
        except Exception as e:
            self._handle_error(e, deployment_id)
        finally:
            if self.temp_dir and self.temp_dir.exists():
                shutil.rmtree(self.temp_dir, ignore_errors=True)
            if self.db:
                self.db.close()
    
    def _provision(self, plugin_id: str, version: str, inputs: dict,
                   credential_name: str, deployment_id: str):
        """Main provisioning logic"""
        # Update job status
        job = self.db.execute(select(Job).where(Job.id == self.job_id)).scalar_one()
        job.status = JobStatus.RUNNING
        self.db.commit()
        
        self.log_message("INFO", "Starting provisioning job")
        
        # Get plugin version
        plugin_version = self._get_plugin_version(plugin_id, version)
        
        # Determine stack name and resource name
        # For updates/rollbacks, we need to preserve the existing stack_name and resource name
        # to avoid creating new resources
        temp_stack_name = f"{plugin_id}-{self.job_id[:8]}"
        temp_resource_name = inputs.get("bucket_name") or inputs.get("name") or f"{plugin_id}-{self.job_id[:8]}"
        
        # Setup deployment - this will return existing deployment if deployment_id is provided
        deployment, is_update, user_id = self._setup_deployment(
            job, plugin_id, version, inputs, deployment_id, plugin_version, temp_stack_name, temp_resource_name
        )
        
        # For updates/rollbacks, preserve existing stack_name and resource name
        if is_update and deployment:
            # Use existing stack_name (critical for Pulumi to update the same stack)
            stack_name = deployment.stack_name or temp_stack_name
            self.log_message("INFO", f"Update/rollback detected - using existing stack: {stack_name}")
            
            # Preserve the existing resource name from current deployment to avoid creating new resources
            # The resource name (bucket_name/name) must match the existing deployment
            existing_inputs = deployment.inputs or {}
            resource_name_key = "bucket_name" if "bucket_name" in existing_inputs else "name"
            
            if resource_name_key in existing_inputs:
                existing_resource_name = existing_inputs[resource_name_key]
                resource_name = existing_resource_name
                # Update inputs to use existing resource name - this ensures Pulumi updates the same resource
                inputs = inputs.copy()
                inputs[resource_name_key] = existing_resource_name
                self.log_message("INFO", f"Preserving existing resource name '{resource_name}' for update/rollback (key: {resource_name_key})")
            else:
                # Fallback to deployment name if no resource name in inputs
                resource_name = deployment.name or temp_resource_name
                self.log_message("INFO", f"Using deployment name '{resource_name}' as resource name")
        else:
            # New deployment - use generated names
            stack_name = temp_stack_name
            resource_name = temp_resource_name
        
        # Ensure stack_name is valid
        if not stack_name or stack_name.strip() == "":
            stack_name = f"{plugin_id}-{self.job_id[:8]}"
            self.log_message("WARNING", f"stack_name was empty/None, using generated name: {stack_name}")
        
        # Setup plugin source (GitOps or ZIP)
        extract_path = self._setup_plugin_source(
            plugin_version, deployment, inputs, stack_name, resource_name, plugin_id, version
        )
        
        # Get credentials via OIDC
        credentials = self._get_credentials(deployment, plugin_version, user_id)
        
        # Run Pulumi
        self.log_message("INFO", f"Executing Pulumi program with credentials: {bool(credentials)}")
        result = asyncio.run(pulumi_service.run_pulumi(
            plugin_path=extract_path,
            stack_name=stack_name,
            config=inputs,
            credentials=credentials,
            manifest=plugin_version.manifest
        ))
        
        # Handle result
        self._handle_provision_result(result, job, deployment, inputs, is_update, resource_name)
    
    def _get_plugin_version(self, plugin_id: str, version: str):
        """Get plugin version from database"""
        return self.db.execute(
            select(PluginVersion).where(
                PluginVersion.plugin_id == plugin_id,
                PluginVersion.version == version
            )
        ).scalar_one()
    
    def _setup_deployment(self, job, plugin_id: str, version: str, inputs: dict,
                         deployment_id: str, plugin_version, stack_name: str,
                         resource_name: str) -> Tuple[Optional[Deployment], bool, Optional[str]]:
        """Setup or get deployment record"""
        deployment = None
        is_update = False
        user_id = None
        
        if deployment_id:
            deployment_uuid = UUID(deployment_id) if isinstance(deployment_id, str) else deployment_id
            deployment = self.db.execute(
                select(Deployment).where(Deployment.id == deployment_uuid)
            ).scalar_one_or_none()
            
            if deployment:
                if deployment.stack_name:
                    stack_name = deployment.stack_name
                user_id = deployment.user_id
                
                if deployment.status == DeploymentStatus.ACTIVE:
                    is_update = True
                    self.log_message("INFO", f"Detected update job for active deployment: {deployment.name}")
            else:
                self.log_message("WARNING", f"Deployment {deployment_id} not found")
        
        # Create deployment if it doesn't exist
        if not deployment:
            user = self.db.execute(
                select(User).where(User.email == job.triggered_by)
            ).scalar_one_or_none()
            
            if user:
                user_id = user.id
                deployment = Deployment(
                    name=resource_name,
                    plugin_id=plugin_id,
                    version=version,
                    status=DeploymentStatus.PROVISIONING,
                    user_id=user_id,
                    inputs=inputs,
                    stack_name=stack_name,
                    cloud_provider=plugin_version.manifest.get("cloud_provider", "unknown"),
                    region=inputs.get("location", "unknown")
                )
                self.db.add(deployment)
                self.db.commit()
                self.db.refresh(deployment)
                self.log_message("INFO", f"Created deployment record: {deployment.name} (ID: {deployment.id})")
            else:
                self.log_message("WARNING", f"User not found for email: {job.triggered_by}")
        
        # Fallback: get user from job if not found
        if not user_id:
            user = self.db.execute(
                select(User).where(User.email == job.triggered_by)
            ).scalar_one_or_none()
            if user:
                user_id = user.id
        
        return deployment, is_update, user_id
    
    def _setup_plugin_source(self, plugin_version, deployment, inputs: dict,
                            stack_name: str, resource_name: str, plugin_id: str,
                            version: str) -> Path:
        """Setup GitOps or ZIP extraction"""
        self.temp_dir = Path(tempfile.mkdtemp())
        
        if plugin_version.git_repo_url and plugin_version.git_branch:
            # GitOps flow
            self.log_message("INFO", f"Using GitOps: {plugin_version.git_repo_url} branch {plugin_version.git_branch}")
            try:
                # Check if deployment already has a git branch
                if deployment and deployment.git_branch:
                    deployment_branch = deployment.git_branch
                    self.log_message("INFO", f"Using existing deployment branch: {deployment_branch}")
                    repo_path = git_service.clone_repository(
                        plugin_version.git_repo_url,
                        deployment_branch,
                        self.temp_dir / "repo"
                    )
                    git_service.inject_user_values(repo_path, inputs, plugin_version.manifest, stack_name)
                    git_service.commit_changes(
                        repo_path,
                        f"Update deployment {deployment.name if deployment else resource_name}",
                        "IDP System",
                        "idp@system"
                    )
                else:
                    # First deployment - create new branch
                    repo_path = git_service.clone_repository(
                        plugin_version.git_repo_url,
                        plugin_version.git_branch,
                        self.temp_dir / "repo"
                    )
                    
                    # Create deployment branch name
                    deployment_name = deployment.name if deployment else resource_name
                    deployment_branch = re.sub(r'[^a-z0-9\-]', '-', deployment_name.lower())
                    deployment_branch = re.sub(r'-+', '-', deployment_branch)
                    deployment_branch = deployment_branch.strip('-')
                    
                    if not deployment_branch or len(deployment_branch) == 0:
                        deployment_branch = f"deploy-{deployment.id if deployment else self.job_id[:8]}"
                    if len(deployment_branch) > 255:
                        deployment_branch = deployment_branch[:255]
                    
                    self.log_message("INFO", f"Creating new deployment branch '{deployment_branch}' from template branch '{plugin_version.git_branch}'")
                    git_service.create_deployment_branch(repo_path, plugin_version.git_branch, deployment_branch)
                    git_service.inject_user_values(repo_path, inputs, plugin_version.manifest, stack_name)
                    git_service.commit_changes(
                        repo_path,
                        f"Deploy {deployment_name} - Initial deployment with user values",
                        "IDP System",
                        "idp@system"
                    )
                    
                    # Push branch to GitHub
                    try:
                        git_service.push_branch(repo_path, deployment_branch)
                        self.log_message("INFO", f"Pushed deployment branch '{deployment_branch}' to GitHub")
                    except Exception as push_error:
                        self.log_message("WARNING", f"Failed to push branch to GitHub (will use local): {push_error}")
                    
                    # Update deployment with git branch
                    if deployment:
                        deployment.git_branch = deployment_branch
                        self.db.commit()
                        self.log_message("INFO", f"Updated deployment record with git branch: {deployment_branch}")
                
                self.log_message("INFO", f"GitOps setup complete: branch {deployment_branch}")
                return repo_path
                
            except Exception as e:
                error_msg = f"GitOps setup failed: {str(e)}"
                self.log_message("ERROR", error_msg)
                logger.error(error_msg, exc_info=True)
                self.log_message("INFO", "Falling back to ZIP extraction")
                return storage_service.extract_plugin(plugin_id, version, self.temp_dir)
        else:
            # Legacy ZIP flow
            extract_path = storage_service.extract_plugin(plugin_id, version, self.temp_dir)
            self.log_message("INFO", f"Extracted plugin ZIP to {extract_path}")
            return extract_path
    
    def _get_credentials(self, deployment: Optional[Deployment],
                        plugin_version, user_id: Optional[str]) -> Optional[Dict]:
        """Get cloud credentials via OIDC"""
        cloud_provider = plugin_version.manifest.get("cloud_provider", "").lower()
        
        if user_id and cloud_provider:
            try:
                if cloud_provider == "aws":
                    self.log_message("INFO", f"Exchanging OIDC token for AWS credentials for user_id: {user_id}...")
                    credentials = asyncio.run(CloudIntegrationService.get_aws_credentials(
                        user_id=str(user_id),
                        duration_seconds=3600
                    ))
                    self.log_message("INFO", f"Successfully obtained AWS credentials via OIDC. Has access_key: {'aws_access_key_id' in credentials}, Has session_token: {'aws_session_token' in credentials}")
                    self.log_message("DEBUG", f"Credential keys: {list(credentials.keys())}")
                    return credentials
                
                elif cloud_provider == "gcp":
                    self.log_message("INFO", "Exchanging OIDC token for GCP credentials...")
                    credentials = asyncio.run(CloudIntegrationService.get_gcp_access_token(
                        user_id=str(user_id)
                    ))
                    self.log_message("INFO", "Successfully obtained GCP credentials via OIDC")
                    return credentials
                
                elif cloud_provider == "azure":
                    self.log_message("INFO", "Exchanging OIDC token for Azure credentials...")
                    credentials = asyncio.run(CloudIntegrationService.get_azure_token(
                        user_id=str(user_id)
                    ))
                    self.log_message("INFO", "Successfully obtained Azure credentials via OIDC")
                    return credentials
                    
            except Exception as e:
                self.log_message("ERROR", f"Failed to auto-exchange OIDC credentials: {str(e)}")
                self.log_message("ERROR", f"Error details: {type(e).__name__}: {str(e)}")
                self.log_message("ERROR", f"Traceback: {traceback.format_exc()}")
                
                if deployment:
                    try:
                        deployment.status = DeploymentStatus.FAILED
                        self.db.add(deployment)
                        self.db.commit()
                    except Exception as deploy_error:
                        logger.warning(f"Failed to update deployment status: {deploy_error}")
                
                raise Exception(f"Failed to obtain credentials via OIDC: {str(e)}")
        
        elif cloud_provider and not user_id:
            self.log_message("ERROR", f"Cloud provider '{cloud_provider}' detected but unable to determine user_id for OIDC exchange")
            if deployment:
                try:
                    deployment.status = DeploymentStatus.FAILED
                    self.db.add(deployment)
                    self.db.commit()
                except Exception as deploy_error:
                    logger.warning(f"Failed to update deployment status: {deploy_error}")
            raise Exception(f"Cannot provision {cloud_provider} resources without user_id for OIDC token exchange")
        
        return None
    
    def _handle_provision_result(self, result: Dict, job: Job, deployment: Optional[Deployment],
                                inputs: dict, is_update: bool, resource_name: str):
        """Handle provisioning result"""
        # Re-fetch job and deployment
        job = self.db.execute(select(Job).where(Job.id == self.job_id)).scalar_one()
        if deployment:
            deployment = self.db.execute(select(Deployment).where(Deployment.id == deployment.id)).scalar_one()
        
        if result["status"] == "success":
            job.status = JobStatus.SUCCESS
            job.outputs = result["outputs"]
            
            if deployment:
                if is_update:
                    deployment.update_status = "update_succeeded"
                    deployment.last_update_error = None
                    deployment.inputs = inputs
                    deployment.outputs = result["outputs"]
                    self.log_message("INFO", "Deployment update completed successfully")
                    
                    # Save history entry
                    self._save_deployment_history(deployment, inputs, result["outputs"], job, is_update=True)
                else:
                    deployment.status = DeploymentStatus.ACTIVE
                    deployment.outputs = result["outputs"]
                    self.log_message("INFO", "Provisioning completed successfully")
                    
                    # Save initial history entry
                    self._save_deployment_history(deployment, inputs, result["outputs"], job, is_update=False)
                
                self.db.add(deployment)
            
            # Create success notification
            self._create_notification(deployment, resource_name, is_update, success=True)
            self.db.commit()
        else:
            # Provisioning failed
            error_msg = result.get('error', 'Unknown error')
            error_state = categorize_error(error_msg)
            
            job.error_state = error_state
            job.error_message = error_msg
            job.status = JobStatus.FAILED
            job.finished_at = datetime.now(timezone.utc)
            
            if is_update and deployment:
                deployment.update_status = "update_failed"
                deployment.last_update_error = error_msg
                self.db.add(deployment)
                self.db.commit()
                
                self.log_message("ERROR", f"Deployment update failed: {error_msg}")
                self.log_message("INFO", "Deployment remains active with previous configuration")
                
                self._create_notification(deployment, resource_name, is_update=True, success=False, error_state=error_state)
                logger.error(f"[UPDATE FAILED] Deployment {deployment.id} update failed. Deployment remains active. Error: {error_state} - {error_msg}")
            else:
                if deployment:
                    deployment.status = DeploymentStatus.FAILED
                    self.db.add(deployment)
                
                self.log_message("ERROR", f"Provisioning failed: {error_msg}")
                self.log_message("ERROR", f"Error category: {error_state}")
                
                self._create_notification(deployment, resource_name, is_update=False, success=False, error_state=error_state)
                self.db.commit()
                logger.error(f"[FAILED] Job {self.job_id} failed. Error: {error_state} - {error_msg}")
    
    def _save_deployment_history(self, deployment: Deployment, inputs: dict,
                                outputs: dict, job: Job, is_update: bool):
        """Save deployment history entry"""
        try:
            if is_update:
                max_version_result = self.db.execute(
                    select(func.max(DeploymentHistory.version_number))
                    .where(DeploymentHistory.deployment_id == deployment.id)
                )
                max_version = max_version_result.scalar() or 0
                next_version = max_version + 1
                
                history_entry = DeploymentHistory(
                    deployment_id=deployment.id,
                    version_number=next_version,
                    inputs=inputs.copy(),
                    outputs=outputs.copy() if outputs else None,
                    status=DeploymentStatus.ACTIVE,
                    job_id=self.job_id,
                    created_by=job.triggered_by,
                    description=f"Update to version {next_version}"
                )
            else:
                history_entry = DeploymentHistory(
                    deployment_id=deployment.id,
                    version_number=1,
                    inputs=inputs.copy(),
                    outputs=outputs.copy() if outputs else None,
                    status=DeploymentStatus.ACTIVE,
                    job_id=self.job_id,
                    created_by=job.triggered_by,
                    description="Initial deployment"
                )
            
            self.db.add(history_entry)
            version_num = history_entry.version_number
            self.log_message("INFO", f"Saved deployment history entry (version {version_num})")
        except Exception as hist_error:
            self.log_message("WARNING", f"Failed to save deployment history: {hist_error}")
    
    def _create_notification(self, deployment: Optional[Deployment], resource_name: str,
                           is_update: bool, success: bool, error_state: str = None):
        """Create notification for user"""
        job = self.db.execute(select(Job).where(Job.id == self.job_id)).scalar_one()
        user_email = job.triggered_by
        user = self.db.execute(select(User).where(User.email == user_email)).scalar_one_or_none()
        
        if not user:
            return
        
        if success:
            if is_update:
                notification = Notification(
                    user_id=user.id,
                    title="Deployment Updated",
                    message=f"Resource '{resource_name}' has been updated successfully.",
                    type=NotificationType.SUCCESS,
                    link=f"/deployments/{deployment.id}" if deployment else f"/jobs/{self.job_id}"
                )
            else:
                notification = Notification(
                    user_id=user.id,
                    title="Provisioning Successful",
                    message=f"Resource '{resource_name}' has been provisioned successfully.",
                    type=NotificationType.SUCCESS,
                    link=f"/deployments/{deployment.id}" if deployment else f"/jobs/{self.job_id}"
                )
        else:
            if is_update:
                notification = Notification(
                    user_id=user.id,
                    title="Deployment Update Failed",
                    message=f"Update for '{resource_name}' failed. Deployment remains active with previous configuration. Error: {error_state}",
                    type=NotificationType.ERROR,
                    link=f"/deployments/{deployment.id}" if deployment else f"/jobs/{self.job_id}"
                )
            else:
                notification = Notification(
                    user_id=user.id,
                    title="Provisioning Failed",
                    message=f"Job '{resource_name}' failed. Error: {error_state}. Please review and retry manually if needed.",
                    type=NotificationType.ERROR,
                    link=f"/jobs/{self.job_id}"
                )
        
        self.db.add(notification)
    
    def _handle_error(self, error: Exception, deployment_id: str):
        """Handle errors during provisioning"""
        error_details = traceback.format_exc()
        error_msg = str(error)
        logger.error(f"[CELERY ERROR] Job {self.job_id} failed: {error_details}")
        
        try:
            job = self.db.execute(select(Job).where(Job.id == self.job_id)).scalar_one()
            error_state = categorize_error(error_msg)
            job.error_state = error_state
            job.error_message = error_msg
            job.status = JobStatus.FAILED
            job.finished_at = datetime.now(timezone.utc)
            
            self.log_message("ERROR", f"Internal Error: {error_msg}")
            self.log_message("ERROR", f"Exception occurred: {error_msg}")
            self.log_message("ERROR", f"Error category: {error_state}")
            
            # Get deployment
            deployment = None
            if deployment_id:
                deployment_uuid = UUID(deployment_id) if isinstance(deployment_id, str) else deployment_id
                deployment = self.db.execute(
                    select(Deployment).where(Deployment.id == deployment_uuid)
                ).scalar_one_or_none()
            elif job.deployment_id:
                deployment = self.db.execute(
                    select(Deployment).where(Deployment.id == job.deployment_id)
                ).scalar_one_or_none()
            
            # Check if this is an update
            is_update_exception = deployment and deployment.status == DeploymentStatus.ACTIVE
            
            if is_update_exception:
                deployment.update_status = "update_failed"
                deployment.last_update_error = error_msg
                self.db.add(deployment)
                self.db.commit()
                
                self.log_message("ERROR", f"Deployment update failed with exception: {error_msg}")
                self.log_message("INFO", "Deployment remains active with previous configuration")
                
                self._create_notification(deployment, deployment.name if deployment else "resource", is_update=True, success=False, error_state=error_state)
            elif deployment:
                deployment.status = DeploymentStatus.FAILED
                self.db.add(deployment)
                self.db.commit()
                
                self._create_notification(deployment, deployment.name if deployment else "resource", is_update=False, success=False, error_state=error_state)
            
            logger.error(f"[FAILED] Job {self.job_id} failed with exception. Error: {error_state} - {error_msg}")
        except Exception as db_error:
            logger.error(f"[CELERY ERROR] Failed to update job status for {self.job_id}: {db_error}")


class InfrastructureDestroyTask:
    """Task for destroying infrastructure"""
    
    def __init__(self, deployment_id: str):
        self.deployment_id = deployment_id
        self.db: Optional[Session] = None
        self.deletion_job_id: Optional[str] = None
        self.temp_dir: Optional[Path] = None
    
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
        log_func(f"[Deletion Job {self.deletion_job_id or 'N/A'}] {message}")
    
    def execute(self):
        """Execute infrastructure destruction"""
        self.db = get_sync_db_session()
        try:
            return self._destroy()
        except Exception as e:
            error_details = traceback.format_exc()
            logger.error(f"[CELERY ERROR] Destroy task failed for deployment {self.deployment_id}: {error_details}")
            
            try:
                deployment_uuid = UUID(self.deployment_id) if isinstance(self.deployment_id, str) else self.deployment_id
                deployment = self.db.execute(
                    select(Deployment).where(Deployment.id == deployment_uuid)
                ).scalar_one_or_none()
                
                if deployment:
                    deployment.status = DeploymentStatus.FAILED
                    self.db.commit()
            except Exception as db_error:
                logger.error(f"[CELERY ERROR] Failed to update deployment status: {db_error}")
            
            return {"status": "error", "message": str(e)}
        finally:
            if self.temp_dir and self.temp_dir.exists():
                shutil.rmtree(self.temp_dir, ignore_errors=True)
            if self.db:
                self.db.close()
    
    def _destroy(self):
        """Main destruction logic"""
        logger.info(f"[destroy_infrastructure] Starting infrastructure destruction for deployment {self.deployment_id}")
        
        # Get deployment
        deployment_uuid = UUID(self.deployment_id) if isinstance(self.deployment_id, str) else self.deployment_id
        deployment = self.db.execute(
            select(Deployment).where(Deployment.id == deployment_uuid)
        ).scalar_one_or_none()
        
        if not deployment:
            logger.error(f"Deployment {self.deployment_id} not found")
            return {"status": "error", "message": "Deployment not found"}
        
        # Find deletion job
        deletion_job = self._find_deletion_job(deployment)
        if deletion_job:
            self.deletion_job_id = deletion_job.id
            if deletion_job.status == JobStatus.PENDING:
                deletion_job.status = JobStatus.RUNNING
                self.db.commit()
            self.log_message("INFO", f"Starting infrastructure destruction for deployment {self.deployment_id}")
        
        # Update deployment status
        deployment.status = DeploymentStatus.PROVISIONING  # Using provisioning as "deleting" status
        self.db.commit()
        self.log_message("INFO", "Updated deployment status to deleting")
        
        # Refresh deployment
        self.db.refresh(deployment)
        
        # Get plugin version
        plugin_version = self.db.execute(
            select(PluginVersion).where(
                PluginVersion.plugin_id == deployment.plugin_id,
                PluginVersion.version == deployment.version
            )
        ).scalar_one()
        
        # Setup plugin source
        extract_path = self._setup_plugin_source(deployment, plugin_version)
        
        # Get credentials
        credentials = self._get_credentials(deployment)
        
        # Run Pulumi destroy
        if not deployment.stack_name:
            self.log_message("WARNING", "No stack_name found - this may be a microservice deployment")
            result = {
                "status": "success",
                "summary": {},
                "message": "No stack to destroy (microservice deployment)"
            }
        else:
            self.log_message("INFO", f"Executing Pulumi destroy for stack: {deployment.stack_name}")
            result = asyncio.run(pulumi_service.destroy_stack(
                plugin_path=extract_path,
                stack_name=deployment.stack_name,
                credentials=credentials
            ))
        
        self.log_message("INFO", f"Pulumi destroy completed with status: {result.get('status', 'unknown')}")
        
        # Handle result
        error_msg = result.get('error', '')
        is_stack_not_found = 'no stack named' in str(error_msg).lower() or 'not found' in str(error_msg).lower()
        
        if result["status"] == "success" or is_stack_not_found:
            if is_stack_not_found:
                self.log_message("WARNING", "Stack not found in Pulumi, deleting deployment record anyway")
            
            # Create notification
            self._create_success_notification(deployment)
            
            # Unlink jobs
            self._unlink_jobs(deployment)
            
            # Update deletion job
            if deletion_job:
                deletion_job.status = JobStatus.SUCCESS
                deletion_job.finished_at = datetime.now(timezone.utc)
                self.db.add(deletion_job)
                self.db.commit()
                self.log_message("INFO", "Deletion job completed successfully")
            
            # Delete GitOps branch
            self._delete_gitops_branch(deployment, plugin_version)
            
            # Delete deployment
            self.db.delete(deployment)
            self.db.commit()
            logger.info(f"Deployment record deleted")
            return {"status": "success", "message": "Infrastructure destroyed, branch deleted, and deployment removed"}
        else:
            # Destroy failed
            logger.error(f"Destroy failed: {error_msg}")
            self.log_message("ERROR", f"Destroy failed: {error_msg}")
            deployment.status = DeploymentStatus.FAILED
            
            if deletion_job:
                deletion_job.status = JobStatus.FAILED
                deletion_job.finished_at = datetime.now(timezone.utc)
                self.db.add(deletion_job)
                self.db.commit()
            
            # Create failure notification
            notification = Notification(
                user_id=deployment.user_id,
                title="Deletion Failed",
                message=f"Failed to delete '{deployment.name}': {error_msg}",
                type=NotificationType.ERROR,
                link=f"/deployments/{deployment.id}"
            )
            self.db.add(notification)
            self.db.commit()
            return {"status": "error", "message": error_msg}
    
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
        deletion_job = deletion_job_row[0] if deletion_job_row else None
        
        if not deletion_job:
            deletion_job_result = self.db.execute(
                select(Job).where(Job.deployment_id == deployment.id)
                .order_by(Job.created_at.desc())
            )
            deletion_job_row = deletion_job_result.first()
            deletion_job = deletion_job_row[0] if deletion_job_row else None
        
        if not deletion_job:
            logger.warning(f"Deletion job not found for deployment {self.deployment_id}, continuing without job tracking")
            self.log_message("WARNING", f"Deletion job not found for deployment {self.deployment_id}")
        
        return deletion_job
    
    def _setup_plugin_source(self, deployment: Deployment, plugin_version) -> Path:
        """Setup plugin source for destruction"""
        self.temp_dir = Path(tempfile.mkdtemp(prefix="pulumi_destroy_"))
        
        if deployment.git_branch and plugin_version.git_repo_url:
            try:
                repo_path = git_service.clone_repository(
                    plugin_version.git_repo_url,
                    deployment.git_branch,
                    self.temp_dir / "repo"
                )
                self.log_message("INFO", f"Cloned deployment branch {deployment.git_branch}")
                return repo_path
            except Exception as e:
                error_msg = f"GitOps clone failed: {str(e)}"
                self.log_message("ERROR", error_msg)
                logger.error(error_msg, exc_info=True)
                self.log_message("INFO", "Falling back to ZIP extraction")
                return storage_service.extract_plugin(deployment.plugin_id, deployment.version, self.temp_dir)
        elif plugin_version.git_repo_url and plugin_version.git_branch:
            try:
                repo_path = git_service.clone_repository(
                    plugin_version.git_repo_url,
                    plugin_version.git_branch,
                    self.temp_dir / "repo"
                )
                self.log_message("INFO", f"Cloned template branch {plugin_version.git_branch}")
                return repo_path
            except Exception as e:
                error_msg = f"GitOps clone failed: {str(e)}"
                self.log_message("ERROR", error_msg)
                logger.error(error_msg, exc_info=True)
                self.log_message("INFO", "Falling back to ZIP extraction")
                return storage_service.extract_plugin(deployment.plugin_id, deployment.version, self.temp_dir)
        else:
            self.log_message("INFO", "Extracting plugin ZIP to temporary directory")
            extract_path = storage_service.extract_plugin(deployment.plugin_id, deployment.version, self.temp_dir)
            self.log_message("INFO", "Plugin extracted successfully")
            return extract_path
    
    def _get_credentials(self, deployment: Deployment) -> Optional[Dict]:
        """Get credentials via OIDC"""
        if deployment.cloud_provider and deployment.user_id:
            try:
                cloud_provider = deployment.cloud_provider.lower()
                
                if cloud_provider == "aws":
                    self.log_message("INFO", "Exchanging OIDC token for AWS credentials")
                    credentials = asyncio.run(CloudIntegrationService.get_aws_credentials(
                        user_id=str(deployment.user_id),
                        duration_seconds=3600
                    ))
                    self.log_message("INFO", "Successfully obtained AWS credentials via OIDC")
                    return credentials
                
                elif cloud_provider == "gcp":
                    self.log_message("INFO", "Exchanging OIDC token for GCP credentials")
                    credentials = asyncio.run(CloudIntegrationService.get_gcp_access_token(
                        user_id=str(deployment.user_id)
                    ))
                    self.log_message("INFO", "Successfully obtained GCP credentials via OIDC")
                    return credentials
                
                elif cloud_provider == "azure":
                    self.log_message("INFO", "Exchanging OIDC token for Azure credentials")
                    credentials = asyncio.run(CloudIntegrationService.get_azure_token(
                        user_id=str(deployment.user_id)
                    ))
                    self.log_message("INFO", "Successfully obtained Azure credentials via OIDC")
                    return credentials
                    
            except Exception as e:
                logger.error(f"Failed to exchange OIDC credentials: {str(e)}")
                self.log_message("ERROR", f"Failed to exchange OIDC credentials: {str(e)}")
                raise Exception(f"Failed to obtain credentials via OIDC: {str(e)}")
        
        return None
    
    def _create_success_notification(self, deployment: Deployment):
        """Create success notification"""
        notification = Notification(
            user_id=deployment.user_id,
            title="Deletion Successful",
            message=f"Resource '{deployment.name}' has been deleted successfully.",
            type=NotificationType.SUCCESS,
            link="/catalog"
        )
        self.db.add(notification)
        self.db.commit()
        self.log_message("INFO", "Notification created for successful deletion")
    
    def _unlink_jobs(self, deployment: Deployment):
        """Unlink jobs from deployment"""
        from app.models import Job
        jobs = self.db.execute(
            select(Job).where(Job.deployment_id == deployment.id)
        ).scalars().all()
        
        for job in jobs:
            job.deployment_id = None
            self.db.add(job)
        self.db.commit()
        self.log_message("INFO", "Unlinked jobs from deployment to preserve history")
    
    def _delete_gitops_branch(self, deployment: Deployment, plugin_version):
        """Delete GitOps branch from GitHub"""
        if deployment.git_branch and plugin_version.git_repo_url:
            try:
                github_token = settings.GITHUB_TOKEN if hasattr(settings, 'GITHUB_TOKEN') else ""
                if not github_token:
                    self.log_message("WARNING", "GITHUB_TOKEN not configured, cannot delete branch via API")
                    logger.warning("GITHUB_TOKEN not configured, skipping branch deletion")
                else:
                    self.log_message("INFO", f"Deleting deployment branch '{deployment.git_branch}' from GitHub repository '{plugin_version.git_repo_url}' (after infrastructure removal)")
                    logger.info(f"Attempting to delete branch '{deployment.git_branch}' from {plugin_version.git_repo_url} (after infrastructure removal)")
                    git_service.delete_branch(plugin_version.git_repo_url, deployment.git_branch, github_token)
                    self.log_message("INFO", f"Successfully deleted deployment branch '{deployment.git_branch}' from GitHub")
                    logger.info(f"Successfully deleted branch '{deployment.git_branch}' from GitHub")
            except Exception as branch_error:
                error_msg = f"Failed to delete branch '{deployment.git_branch}': {str(branch_error)}"
                self.log_message("WARNING", error_msg)
                logger.warning(error_msg, exc_info=True)

