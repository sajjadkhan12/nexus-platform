"""Celery worker for background job processing"""
from celery import Celery
from app.config import settings
import os
import asyncio
import json
from datetime import datetime, timezone
from dotenv import load_dotenv
from app.logger import logger  # Use centralized logger

# Load environment variables from .env file
load_dotenv()

# Create a shared synchronous database engine for all Celery tasks
# This avoids creating a new engine for each task, improving connection pooling
_sync_db_url = settings.DATABASE_URL.replace("+asyncpg", "")
if "postgresql://" not in _sync_db_url and "postgresql+psycopg2://" not in _sync_db_url:
    _sync_db_url = _sync_db_url.replace("postgresql:", "postgresql+psycopg2:")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Shared engine with connection pooling for Celery tasks
_shared_sync_engine = create_engine(
    _sync_db_url,
    echo=False,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True  # Verify connections before using
)
_shared_SessionLocal = sessionmaker(bind=_shared_sync_engine)

def get_sync_db_session():
    """Get a synchronous database session using the shared engine"""
    return _shared_SessionLocal()

# Create Celery app
celery_app = Celery(
    "idp_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Retry configuration - disabled (no automatic retries)
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_max_retries=0,  # No automatic retries - jobs fail immediately
    # Periodic task schedule (Celery Beat)
    beat_schedule={
        'cleanup-stuck-deployments': {
            'task': 'cleanup_stuck_deployments',
            'schedule': 300.0,  # Run every 5 minutes
        },
        'poll-github-actions-status': {
            'task': 'poll_github_actions_status',
            'schedule': 60.0,  # Run every 60 seconds
        },
        'cleanup-expired-refresh-tokens': {
            'task': 'cleanup_expired_refresh_tokens',
            'schedule': 3600.0,  # Run every hour
        },
    },
)

@celery_app.task(name="provision_infrastructure")
def provision_infrastructure(job_id: str, plugin_id: str, version: str, inputs: dict, credential_name: str = None, deployment_id: str = None):
    """
    Celery task to provision infrastructure using Pulumi
    Uses synchronous DB operations to avoid asyncio loop conflicts
    """
    from pathlib import Path
    import tempfile
    import shutil
    import traceback
    
    from sqlalchemy import select
    from sqlalchemy.orm import Session
    
    from app.models import Job, JobLog, JobStatus, PluginVersion, CloudCredential, Deployment, DeploymentStatus, Notification, NotificationType, User, Plugin, DeploymentHistory
    from app.services.storage import storage_service
    from app.services.pulumi_service import pulumi_service
    from app.services.crypto import crypto_service
    
    # Use shared sync engine for better connection pooling
    SessionLocal = _shared_SessionLocal
    
    # Helper to log messages
    def log_message(db: Session, level: str, message: str):
        log = JobLog(job_id=job_id, level=level, message=message)
        db.add(log)
        db.commit()
        # Log to server.log using appropriate level
        log_func = getattr(logger, level.lower(), logger.info)
        log_func(f"[Job {job_id}] {message}")

    # Retry logic disabled - jobs fail immediately without automatic retries
    # Users can manually retry failed jobs if needed
    
    with SessionLocal() as db:
        try:
            # Update job status to running
            job = db.execute(select(Job).where(Job.id == job_id)).scalar_one()
            job.status = JobStatus.RUNNING
            db.commit()
            
            log_message(db, "INFO", f"Starting provisioning job")
            
            # Get plugin version
            plugin_version = db.execute(
                select(PluginVersion).where(
                    PluginVersion.plugin_id == plugin_id,
                    PluginVersion.version == version
                )
            ).scalar_one()
            
            # Determine stack_name early (needed for GitOps setup)
            stack_name = f"{plugin_id}-{job_id[:8]}"
            resource_name = inputs.get("bucket_name") or inputs.get("name") or f"{plugin_id}-{job_id[:8]}"
            user_id = None  # Will be used for OIDC credential exchange
            
            # Get deployment info if deployment_id is provided, or create it if it doesn't exist
            deployment = None
            is_update = False
            if deployment_id:
                # Handle UUID conversion for deployment_id
                from uuid import UUID
                deployment_uuid = UUID(deployment_id) if isinstance(deployment_id, str) else deployment_id
                deployment = db.execute(select(Deployment).where(Deployment.id == deployment_uuid)).scalar_one_or_none()
                if deployment:
                    # Use stack name from record if it exists and is not None, otherwise keep the generated one
                    if deployment.stack_name:
                        stack_name = deployment.stack_name
                    # If stack_name is None or empty, keep the generated one from line 85
                    user_id = deployment.user_id  # Get user_id for OIDC exchange
                    
                    # Check if this is an update (deployment is active)
                    if deployment.status == DeploymentStatus.ACTIVE:
                        is_update = True
                        log_message(db, "INFO", f"Detected update job for active deployment: {deployment.name}")
                else:
                    log_message(db, "WARNING", f"Deployment {deployment_id} not found")
            
            # Create deployment record if it doesn't exist (needed before GitOps setup)
            if not deployment:
                from app.models import User
                user = db.execute(select(User).where(User.email == job.triggered_by)).scalar_one_or_none()
                
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
                    db.add(deployment)
                    db.commit()
                    db.refresh(deployment)
                    log_message(db, "INFO", f"Created deployment record: {deployment.name} (ID: {deployment.id})")
                else:
                    log_message(db, "WARNING", f"User not found for email: {job.triggered_by}")
            
            # Ensure stack_name is always defined and not None/empty (defensive check)
            if not stack_name or stack_name.strip() == "":
                stack_name = f"{plugin_id}-{job_id[:8]}"
                log_message(db, "WARNING", f"stack_name was empty/None, using generated name: {stack_name}")
            
            # Check if plugin uses GitOps (Git repository) or legacy ZIP
            extract_path = None
            temp_dir = Path(tempfile.mkdtemp())
            
            if plugin_version.git_repo_url and plugin_version.git_branch:
                # GitOps flow: Clone from Git repository
                log_message(db, "INFO", f"Using GitOps: {plugin_version.git_repo_url} branch {plugin_version.git_branch}")
                try:
                    from app.services.git_service import git_service
                    import re
                    
                    # Check if deployment already has a git branch (for re-deployments)
                    if deployment and deployment.git_branch:
                        # Use existing deployment branch
                        deployment_branch = deployment.git_branch
                        log_message(db, "INFO", f"Using existing deployment branch: {deployment_branch}")
                        repo_path = git_service.clone_repository(
                            plugin_version.git_repo_url,
                            deployment_branch,
                            temp_dir / "repo"
                        )
                        # Update user values in existing branch
                        git_service.inject_user_values(repo_path, inputs, plugin_version.manifest, stack_name)
                        git_service.commit_changes(
                            repo_path,
                            f"Update deployment {deployment.name if deployment else resource_name}",
                            "IDP System",
                            "idp@system"
                        )
                    else:
                        # First deployment - create new branch from template
                        # Clone template branch first
                        repo_path = git_service.clone_repository(
                            plugin_version.git_repo_url,
                            plugin_version.git_branch,
                            temp_dir / "repo"
                        )
                        
                        # Create deployment branch name from deployment name (sanitized for Git)
                        # Format: {deployment-name} (e.g., "user-a-gcp-bucket-name")
                        deployment_name = deployment.name if deployment else resource_name
                        # Sanitize branch name: lowercase, replace spaces/special chars with hyphens
                        deployment_branch = re.sub(r'[^a-z0-9\-]', '-', deployment_name.lower())
                        deployment_branch = re.sub(r'-+', '-', deployment_branch)  # Remove multiple hyphens
                        deployment_branch = deployment_branch.strip('-')  # Remove leading/trailing hyphens
                        
                        # Ensure branch name is valid (not empty, max 255 chars)
                        if not deployment_branch or len(deployment_branch) == 0:
                            deployment_branch = f"deploy-{deployment.id if deployment else job_id[:8]}"
                        if len(deployment_branch) > 255:
                            deployment_branch = deployment_branch[:255]
                        
                        log_message(db, "INFO", f"Creating new deployment branch '{deployment_branch}' from template branch '{plugin_version.git_branch}'")
                        git_service.create_deployment_branch(repo_path, plugin_version.git_branch, deployment_branch)
                        
                        # Inject user values into Pulumi config
                        git_service.inject_user_values(repo_path, inputs, plugin_version.manifest, stack_name)
                        
                        # Commit changes
                        git_service.commit_changes(
                            repo_path,
                            f"Deploy {deployment_name} - Initial deployment with user values",
                            "IDP System",
                            "idp@system"
                        )
                        
                        # Push branch to GitHub for history (so it persists)
                        try:
                            git_service.push_branch(repo_path, deployment_branch)
                            log_message(db, "INFO", f"Pushed deployment branch '{deployment_branch}' to GitHub")
                        except Exception as push_error:
                            log_message(db, "WARNING", f"Failed to push branch to GitHub (will use local): {push_error}")
                        
                        # Update deployment with git branch
                        if deployment:
                            deployment.git_branch = deployment_branch
                            db.commit()
                            log_message(db, "INFO", f"Updated deployment record with git branch: {deployment_branch}")
                    
                    extract_path = repo_path
                    log_message(db, "INFO", f"GitOps setup complete: branch {deployment_branch}")
                    
                except Exception as e:
                    error_msg = f"GitOps setup failed: {str(e)}"
                    log_message(db, "ERROR", error_msg)
                    logger.error(error_msg, exc_info=True)
                    # Fallback to ZIP extraction if Git fails
                    log_message(db, "INFO", "Falling back to ZIP extraction")
                    extract_path = storage_service.extract_plugin(plugin_id, version, temp_dir)
            else:
                # Legacy ZIP flow
                extract_path = storage_service.extract_plugin(plugin_id, version, temp_dir)
                log_message(db, "INFO", f"Extracted plugin ZIP to {extract_path}")
            
            # Deployment record should already exist (created above before GitOps setup)
            # This block is now redundant but kept for safety
            if not deployment:
                log_message(db, "ERROR", "Deployment record should have been created before GitOps setup!")
                # This should not happen, but create it as fallback
                from app.models import User
                user = db.execute(select(User).where(User.email == job.triggered_by)).scalar_one_or_none()
                
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
                    db.add(deployment)
                    db.commit()
                    db.refresh(deployment)
                    log_message(db, "INFO", f"Created deployment record (fallback): {deployment.name}")
            
            # Fallback: get user from job.triggered_by if not found in deployment
            if not user_id:
                from app.models import User
                user = db.execute(select(User).where(User.email == job.triggered_by)).scalar_one_or_none()
                if user:
                    user_id = user.id
            
            # Load credentials
            credentials = None
            if credential_name:
                cred_record = db.execute(
                    select(CloudCredential).where(CloudCredential.name == credential_name)
                ).scalar_one_or_none()
                
                if cred_record:
                    try:
                        credentials = crypto_service.decrypt(cred_record.encrypted_data)
                        log_message(db, "INFO", f"Loaded credentials: {credential_name}")
                    except Exception as e:
                        log_message(db, "ERROR", f"Failed to decrypt credentials: {str(e)}")
                        raise e
            
            # Always use OIDC token exchange for cloud credentials
            # This enables automatic credential provisioning for AWS, GCP, and Azure
            credentials = None
            cloud_provider = plugin_version.manifest.get("cloud_provider", "").lower()
            
            if user_id and cloud_provider:
                try:
                    from app.services.cloud_integrations import CloudIntegrationService
                    
                    if cloud_provider == "aws":
                        log_message(db, "INFO", f"Exchanging OIDC token for AWS credentials for user_id: {user_id}...")
                        credentials = asyncio.run(CloudIntegrationService.get_aws_credentials(
                            user_id=str(user_id),
                            duration_seconds=3600  # 1 hour
                        ))
                        log_message(db, "INFO", f"Successfully obtained AWS credentials via OIDC. Has access_key: {'aws_access_key_id' in credentials}, Has session_token: {'aws_session_token' in credentials}")
                        # Log credential keys for debugging
                        log_message(db, "DEBUG", f"Credential keys: {list(credentials.keys())}")
                    
                    elif cloud_provider == "gcp":
                        log_message(db, "INFO", "Exchanging OIDC token for GCP credentials...")
                        credentials = asyncio.run(CloudIntegrationService.get_gcp_access_token(
                            user_id=str(user_id)
                        ))
                        log_message(db, "INFO", "Successfully obtained GCP credentials via OIDC")
                    
                    elif cloud_provider == "azure":
                        log_message(db, "INFO", "Exchanging OIDC token for Azure credentials...")
                        credentials = asyncio.run(CloudIntegrationService.get_azure_token(
                            user_id=str(user_id)
                        ))
                        log_message(db, "INFO", "Successfully obtained Azure credentials via OIDC")
                        
                except Exception as e:
                    log_message(db, "ERROR", f"Failed to auto-exchange OIDC credentials: {str(e)}")
                    log_message(db, "ERROR", f"Error details: {type(e).__name__}: {str(e)}")
                    import traceback
                    log_message(db, "ERROR", f"Traceback: {traceback.format_exc()}")
                    
                    # Update deployment status to FAILED before raising
                    if deployment:
                        try:
                            deployment.status = DeploymentStatus.FAILED
                            db.add(deployment)
                            db.commit()
                        except Exception as deploy_error:
                            logger.warning(f"Failed to update deployment status: {deploy_error}")
                    
                    # Raise the error - we need credentials for cloud deployments
                    raise Exception(f"Failed to obtain credentials via OIDC: {str(e)}")
            elif cloud_provider and not user_id:
                log_message(db, "ERROR", f"Cloud provider '{cloud_provider}' detected but unable to determine user_id for OIDC exchange")
                # Update deployment status to FAILED
                if deployment:
                    try:
                        deployment.status = DeploymentStatus.FAILED
                        db.add(deployment)
                        db.commit()
                    except Exception as deploy_error:
                        logger.warning(f"Failed to update deployment status: {deploy_error}")
                raise Exception(f"Cannot provision {cloud_provider} resources without user_id for OIDC token exchange")
            elif cloud_provider and not credentials:
                log_message(db, "ERROR", f"Cloud provider '{cloud_provider}' requires credentials but none were obtained")
                # Update deployment status to FAILED
                if deployment:
                    try:
                        deployment.status = DeploymentStatus.FAILED
                        db.add(deployment)
                        db.commit()
                    except Exception as deploy_error:
                        logger.warning(f"Failed to update deployment status: {deploy_error}")
                raise Exception(f"Failed to obtain credentials for {cloud_provider}")

            # Verify credentials were obtained
            if cloud_provider and not credentials:
                log_message(db, "ERROR", f"No credentials obtained for cloud provider: {cloud_provider}")
                # Update deployment status to FAILED
                if deployment:
                    try:
                        deployment.status = DeploymentStatus.FAILED
                        db.add(deployment)
                        db.commit()
                    except Exception as deploy_error:
                        logger.warning(f"Failed to update deployment status: {deploy_error}")
                raise Exception(f"Credentials required for {cloud_provider} but none were obtained")

            # Run Pulumi (Async)
            log_message(db, "INFO", f"Executing Pulumi program with credentials: {bool(credentials)}")
            
            # Run the async Pulumi code in a fresh loop
            result = asyncio.run(pulumi_service.run_pulumi(
                plugin_path=extract_path,
                stack_name=stack_name,
                config=inputs,
                credentials=credentials,
                manifest=plugin_version.manifest
            ))
            
            # Update job with results
            # Re-fetch job and deployment to ensure attached to session
            job = db.execute(select(Job).where(Job.id == job_id)).scalar_one()
            if deployment:
                deployment = db.execute(select(Deployment).where(Deployment.id == deployment.id)).scalar_one()
            
            if result["status"] == "success":
                job.status = JobStatus.SUCCESS
                job.outputs = result["outputs"]
                
                if deployment:
                    if is_update:
                        # This is an update - keep status as ACTIVE, update update_status
                        deployment.update_status = "update_succeeded"
                        deployment.last_update_error = None
                        deployment.inputs = inputs  # Update stored inputs with new values
                        deployment.outputs = result["outputs"]
                        log_message(db, "INFO", "Deployment update completed successfully")
                        
                        # Save history entry for this update
                        try:
                            # Get the next version number
                            from sqlalchemy import func
                            max_version_result = db.execute(
                                select(func.max(DeploymentHistory.version_number))
                                .where(DeploymentHistory.deployment_id == deployment.id)
                            )
                            max_version = max_version_result.scalar() or 0
                            next_version = max_version + 1
                            
                            history_entry = DeploymentHistory(
                                deployment_id=deployment.id,
                                version_number=next_version,
                                inputs=inputs.copy(),
                                outputs=result["outputs"].copy() if result["outputs"] else None,
                                status=DeploymentStatus.ACTIVE,
                                job_id=job_id,
                                created_by=job.triggered_by,
                                description=f"Update to version {next_version}"
                            )
                            db.add(history_entry)
                            log_message(db, "INFO", f"Saved deployment history entry (version {next_version})")
                        except Exception as hist_error:
                            log_message(db, "WARNING", f"Failed to save deployment history: {hist_error}")
                            # Don't fail the update if history save fails
                    else:
                        # This is a new deployment - create initial history entry
                        deployment.status = DeploymentStatus.ACTIVE
                        deployment.outputs = result["outputs"]
                        log_message(db, "INFO", "Provisioning completed successfully")
                        
                        # Save initial history entry (version 1)
                        try:
                            history_entry = DeploymentHistory(
                                deployment_id=deployment.id,
                                version_number=1,
                                inputs=inputs.copy(),
                                outputs=result["outputs"].copy() if result["outputs"] else None,
                                status=DeploymentStatus.ACTIVE,
                                job_id=job_id,
                                created_by=job.triggered_by,
                                description="Initial deployment"
                            )
                            db.add(history_entry)
                            log_message(db, "INFO", "Saved initial deployment history entry (version 1)")
                        except Exception as hist_error:
                            log_message(db, "WARNING", f"Failed to save initial deployment history: {hist_error}")
                            # Don't fail the deployment if history save fails
                    db.add(deployment)
                
                # Create notification
                user_id = db.execute(select(Job.triggered_by).where(Job.id == job_id)).scalar_one()
                from app.models import User
                user = db.execute(select(User).where(User.email == user_id)).scalar_one_or_none()
                
                if user:
                    if is_update:
                        notification = Notification(
                            user_id=user.id,
                            title="Deployment Updated",
                            message=f"Resource '{resource_name}' has been updated successfully.",
                            type=NotificationType.SUCCESS,
                            link=f"/deployments/{deployment.id}" if deployment else f"/jobs/{job_id}"
                        )
                    else:
                        notification = Notification(
                            user_id=user.id,
                            title="Provisioning Successful",
                            message=f"Resource '{resource_name}' has been provisioned successfully.",
                            type=NotificationType.SUCCESS,
                            link=f"/deployments/{deployment.id}" if deployment else f"/jobs/{job_id}"
                        )
                    db.add(notification)
                
                db.commit()
                
            else:
                # Provisioning failed - mark as failed immediately (no automatic retries)
                error_msg = result.get('error', 'Unknown error')
                job = db.execute(select(Job).where(Job.id == job_id)).scalar_one()
                
                # Categorize error
                error_state = _categorize_error(error_msg)
                job.error_state = error_state
                job.error_message = error_msg
                
                # Mark job as FAILED immediately when error occurs
                job.status = JobStatus.FAILED
                job.finished_at = datetime.now(timezone.utc)
                
                # Handle updates differently from new deployments
                if is_update and deployment:
                    # For updates, mark update as failed but keep deployment active
                    deployment.update_status = "update_failed"
                    deployment.last_update_error = error_msg
                    # Keep deployment.status as ACTIVE - don't change it
                    db.add(deployment)
                    db.commit()
                    
                    log_message(db, "ERROR", f"Deployment update failed: {error_msg}")
                    log_message(db, "INFO", "Deployment remains active with previous configuration")
                    
                    # Create notification for update failure
                    user_email = job.triggered_by
                    user = db.execute(select(User).where(User.email == user_email)).scalar_one_or_none()
                    
                    if user:
                        notification = Notification(
                            user_id=user.id,
                            title="Deployment Update Failed",
                            message=f"Update for '{resource_name}' failed. Deployment remains active with previous configuration. Error: {error_state}",
                            type=NotificationType.ERROR,
                            link=f"/deployments/{deployment.id}"
                        )
                        db.add(notification)
                        db.commit()
                    
                    logger.error(f"[UPDATE FAILED] Deployment {deployment.id} update failed. Deployment remains active. Error: {error_state} - {error_msg}")
                else:
                    # For new deployments, mark as failed immediately (no automatic retries)
                    if deployment:
                        deployment.status = DeploymentStatus.FAILED
                        db.add(deployment)
                    
                    log_message(db, "ERROR", f"Provisioning failed: {error_msg}")
                    log_message(db, "ERROR", f"Error category: {error_state}")
                    
                    # Create failure notification
                    user_email = job.triggered_by
                    user = db.execute(select(User).where(User.email == user_email)).scalar_one_or_none()
                    
                    if user:
                        notification = Notification(
                            user_id=user.id,
                            title="Provisioning Failed",
                            message=f"Job '{resource_name}' failed. Error: {error_state}. Please review and retry manually if needed.",
                            type=NotificationType.ERROR,
                            link=f"/jobs/{job_id}"
                        )
                        db.add(notification)
                    
                    db.commit()
                    logger.error(f"[FAILED] Job {job_id} failed. Error: {error_state} - {error_msg}")
            
            # Clean up
            shutil.rmtree(temp_dir, ignore_errors=True)
            
        except Exception as e:
            error_details = traceback.format_exc()
            error_msg = str(e)
            logger.error(f"[CELERY ERROR] Job {job_id} failed: {error_details}")
            
            # Re-fetch job and deployment to ensure attached to session
            try:
                job = db.execute(select(Job).where(Job.id == job_id)).scalar_one()
                
                # Categorize error
                error_state = _categorize_error(error_msg)
                job.error_state = error_state
                job.error_message = error_msg
                
                log_message(db, "ERROR", f"Internal Error: {error_msg}")
                
                # Mark job as FAILED immediately when exception occurs
                job.status = JobStatus.FAILED
                job.finished_at = datetime.now(timezone.utc)
                
                # Mark job as failed immediately (no automatic retries)
                log_message(db, "ERROR", f"Exception occurred: {error_msg}")
                log_message(db, "ERROR", f"Error category: {error_state}")
                
                # Update deployment status if it exists
                deployment = None
                if deployment_id:
                    # Handle UUID conversion for deployment_id
                    from uuid import UUID
                    deployment_uuid = UUID(deployment_id) if isinstance(deployment_id, str) else deployment_id
                    deployment = db.execute(select(Deployment).where(Deployment.id == deployment_uuid)).scalar_one_or_none()
                elif job.deployment_id:
                    deployment = db.execute(select(Deployment).where(Deployment.id == job.deployment_id)).scalar_one_or_none()
                
                # Check if this is an update
                is_update_exception = deployment and deployment.status == DeploymentStatus.ACTIVE
                
                if is_update_exception:
                    # For updates, mark update as failed but keep deployment active
                    deployment.update_status = "update_failed"
                    deployment.last_update_error = error_msg
                    # Keep deployment.status as ACTIVE
                    db.add(deployment)
                    db.commit()
                    
                    log_message(db, "ERROR", f"Deployment update failed with exception: {error_msg}")
                    log_message(db, "INFO", "Deployment remains active with previous configuration")
                    
                    # Create notification for update failure
                    user_email = job.triggered_by
                    user = db.execute(select(User).where(User.email == user_email)).scalar_one_or_none()
                    
                    if user:
                        notification = Notification(
                            user_id=user.id,
                            title="Deployment Update Failed",
                            message=f"Update failed with an exception. Deployment remains active with previous configuration.",
                            type=NotificationType.ERROR,
                            link=f"/deployments/{deployment.id}" if deployment else f"/jobs/{job_id}"
                        )
                        db.add(notification)
                        db.commit()
                elif deployment:
                    # For new deployments, mark as failed
                    deployment.status = DeploymentStatus.FAILED
                    db.add(deployment)
                    db.commit()
                    
                    # Create failure notification
                    user_email = job.triggered_by
                    user = db.execute(select(User).where(User.email == user_email)).scalar_one_or_none()
                    
                    if user:
                        notification = Notification(
                            user_id=user.id,
                            title="Provisioning Failed",
                            message=f"Job failed with an exception. Error: {error_state}. Please review and retry manually if needed.",
                            type=NotificationType.ERROR,
                            link=f"/jobs/{job_id}"
                        )
                        db.add(notification)
                        db.commit()
                
                logger.error(f"[FAILED] Job {job_id} failed with exception. Error: {error_state} - {error_msg}")
                    
            except Exception as db_error:
                # Log but don't fail if we can't update the job status
                logger.error(f"[CELERY ERROR] Failed to update job status for {job_id}: {db_error}")


def _categorize_error(error_msg: str) -> str:
    """
    Categorize error messages into error states for better tracking and debugging.
    """
    error_lower = error_msg.lower()
    
    if "credential" in error_lower or "authentication" in error_lower or "oidc" in error_lower or "token" in error_lower:
        return "credential_error"
    elif "pulumi" in error_lower or "stack" in error_lower or "preview" in error_lower:
        return "pulumi_error"
    elif "network" in error_lower or "connection" in error_lower or "timeout" in error_lower:
        return "network_error"
    elif "git" in error_lower or "repository" in error_lower or "branch" in error_lower:
        return "git_error"
    elif "validation" in error_lower or "invalid" in error_lower or "missing" in error_lower:
        return "validation_error"
    elif "permission" in error_lower or "forbidden" in error_lower or "access" in error_lower:
        return "permission_error"
    elif "quota" in error_lower or "limit" in error_lower or "rate" in error_lower:
        return "quota_error"
    else:
        return "unknown_error"

@celery_app.task(name="destroy_infrastructure")
def destroy_infrastructure(deployment_id: str):
    """
    Celery task to destroy infrastructure using Pulumi and delete deployment record
    """
    from pathlib import Path
    import tempfile
    import shutil
    import traceback
    
    from sqlalchemy import select
    from sqlalchemy.orm import Session
    
    from app.models import Deployment, DeploymentStatus, PluginVersion, CloudCredential, Job, JobStatus, JobLog
    from app.services.storage import storage_service
    from app.services.pulumi_service import pulumi_service
    from app.services.crypto import crypto_service
    
    # Use shared sync engine for better connection pooling
    SessionLocal = _shared_SessionLocal
    
    with SessionLocal() as db:
        deletion_job = None
        deletion_job_id = None
        
        # Helper to log messages
        def log_message(db: Session, level: str, message: str):
            if deletion_job_id:
                log = JobLog(job_id=deletion_job_id, level=level, message=message)
                db.add(log)
                db.commit()
            # Log to server.log using appropriate level
            log_func = getattr(logger, level.lower(), logger.info)
            log_func(f"[Deletion Job {deletion_job_id or 'N/A'}] {message}")
        
        try:
            logger.info(f"[destroy_infrastructure] Starting infrastructure destruction for deployment {deployment_id}")
            
            # Get deployment - handle both UUID string and UUID object
            from uuid import UUID
            deployment_uuid = UUID(deployment_id) if isinstance(deployment_id, str) else deployment_id
            deployment = db.execute(select(Deployment).where(Deployment.id == deployment_uuid)).scalar_one_or_none()
            logger.info(f"[destroy_infrastructure] Deployment found: {deployment is not None}, ID: {deployment_id} (UUID: {deployment_uuid})")
            
            if not deployment:
                logger.error(f"Deployment {deployment_id} not found")
                return {"status": "error", "message": "Deployment not found"}
            
            # Find the deletion job for this deployment
            from app.models import JobStatus
            # First try to find a PENDING job - use deployment.id (UUID) for matching
            # Use first() instead of scalar_one_or_none() to handle multiple jobs (get the most recent)
            deletion_job_result = db.execute(
                select(Job).where(
                    Job.deployment_id == deployment.id,  # deployment.id is UUID, should match
                    Job.status == JobStatus.PENDING
                ).order_by(Job.created_at.desc())
            )
            deletion_job_row = deletion_job_result.first()
            deletion_job = deletion_job_row[0] if deletion_job_row else None
            
            # If not found, try to find any job for this deployment (might already be RUNNING or created differently)
            if not deletion_job:
                deletion_job_result = db.execute(
                    select(Job).where(
                        Job.deployment_id == deployment.id
                    ).order_by(Job.created_at.desc())
                )
                deletion_job_row = deletion_job_result.first()
                deletion_job = deletion_job_row[0] if deletion_job_row else None
            
            if deletion_job:
                deletion_job_id = deletion_job.id
                if deletion_job.status == JobStatus.PENDING:
                    deletion_job.status = JobStatus.RUNNING
                    db.commit()
                log_message(db, "INFO", f"Starting infrastructure destruction for deployment {deployment_id}")
                logger.info(f"Found deletion job {deletion_job.id} with status {deletion_job.status}")
            else:
                # Job not found - log warning but continue (might have been created differently)
                logger.warning(f"Deletion job not found for deployment {deployment_id}, continuing without job tracking")
                log_message(db, "WARNING", f"Deletion job not found for deployment {deployment_id}")
            
            # Update status to deleting
            deployment.status = DeploymentStatus.PROVISIONING  # Using provisioning as "deleting" status
            db.commit()
            log_message(db, "INFO", f"Updated deployment status to deleting")
            
            # Refresh deployment to ensure we have latest git_branch value
            db.refresh(deployment)
            
            # Get plugin version
            plugin_version = db.execute(
                select(PluginVersion).where(
                    PluginVersion.plugin_id == deployment.plugin_id,
                    PluginVersion.version == deployment.version
                )
            ).scalar_one()
            log_message(db, "INFO", f"Found plugin version: {deployment.plugin_id} v{deployment.version}")
            log_message(db, "INFO", f"Deployment git_branch: {deployment.git_branch}, Plugin git_repo_url: {plugin_version.git_repo_url}")
            
            # Check if deployment uses GitOps (Git branch) or legacy ZIP
            temp_dir = tempfile.mkdtemp(prefix="pulumi_destroy_")
            extract_path = Path(temp_dir)
            
            if deployment.git_branch and plugin_version.git_repo_url:
                # GitOps flow: Clone deployment branch
                log_message(db, "INFO", f"Using GitOps: {plugin_version.git_repo_url} branch {deployment.git_branch}")
                try:
                    from app.services.git_service import git_service
                    
                    repo_path = git_service.clone_repository(
                        plugin_version.git_repo_url,
                        deployment.git_branch,
                        extract_path / "repo"
                    )
                    extract_path = repo_path
                    log_message(db, "INFO", f"Cloned deployment branch {deployment.git_branch}")
                except Exception as e:
                    error_msg = f"GitOps clone failed: {str(e)}"
                    log_message(db, "ERROR", error_msg)
                    logger.error(error_msg, exc_info=True)
                    # Fallback to ZIP extraction
                    log_message(db, "INFO", "Falling back to ZIP extraction")
                    extract_path = storage_service.extract_plugin(deployment.plugin_id, deployment.version, extract_path)
            elif plugin_version.git_repo_url and plugin_version.git_branch:
                # GitOps but no deployment branch - use template branch
                log_message(db, "INFO", f"Using GitOps template: {plugin_version.git_repo_url} branch {plugin_version.git_branch}")
                try:
                    from app.services.git_service import git_service
                    
                    repo_path = git_service.clone_repository(
                        plugin_version.git_repo_url,
                        plugin_version.git_branch,
                        extract_path / "repo"
                    )
                    extract_path = repo_path
                    log_message(db, "INFO", f"Cloned template branch {plugin_version.git_branch}")
                except Exception as e:
                    error_msg = f"GitOps clone failed: {str(e)}"
                    log_message(db, "ERROR", error_msg)
                    logger.error(error_msg, exc_info=True)
                    # Fallback to ZIP extraction
                    log_message(db, "INFO", "Falling back to ZIP extraction")
                    extract_path = storage_service.extract_plugin(deployment.plugin_id, deployment.version, extract_path)
            else:
                # Legacy ZIP flow
                logger.info(f"Extracting plugin to {extract_path}")
                log_message(db, "INFO", f"Extracting plugin ZIP to temporary directory")
                extract_path = storage_service.extract_plugin(deployment.plugin_id, deployment.version, extract_path)
                log_message(db, "INFO", f"Plugin extracted successfully")
            
            # Always use OIDC token exchange for credentials
            credentials = None
            if deployment.cloud_provider and deployment.user_id:
                try:
                    from app.services.cloud_integrations import CloudIntegrationService
                    cloud_provider = deployment.cloud_provider.lower()
                    
                    if cloud_provider == "aws":
                        logger.info(f"Exchanging OIDC token for AWS credentials...")
                        log_message(db, "INFO", "Exchanging OIDC token for AWS credentials")
                        credentials = asyncio.run(CloudIntegrationService.get_aws_credentials(
                            user_id=str(deployment.user_id),
                            duration_seconds=3600
                        ))
                        logger.info(f"Successfully obtained AWS credentials via OIDC")
                        log_message(db, "INFO", "Successfully obtained AWS credentials via OIDC")
                    
                    elif cloud_provider == "gcp":
                        logger.info(f"Exchanging OIDC token for GCP credentials...")
                        log_message(db, "INFO", "Exchanging OIDC token for GCP credentials")
                        credentials = asyncio.run(CloudIntegrationService.get_gcp_access_token(
                            user_id=str(deployment.user_id)
                        ))
                        logger.info(f"Successfully obtained GCP credentials via OIDC")
                        logger.info(f"GCP credentials type: {credentials.get('type')}, has access_token: {'access_token' in credentials}")
                        log_message(db, "INFO", "Successfully obtained GCP credentials via OIDC")
                    
                    elif cloud_provider == "azure":
                        logger.info(f"Exchanging OIDC token for Azure credentials...")
                        log_message(db, "INFO", "Exchanging OIDC token for Azure credentials")
                        credentials = asyncio.run(CloudIntegrationService.get_azure_token(
                            user_id=str(deployment.user_id)
                        ))
                        logger.info(f"Successfully obtained Azure credentials via OIDC")
                        log_message(db, "INFO", "Successfully obtained Azure credentials via OIDC")
                        
                except Exception as e:
                    logger.error(f"Failed to exchange OIDC credentials: {str(e)}")
                    log_message(db, "ERROR", f"Failed to exchange OIDC credentials: {str(e)}")
                    raise Exception(f"Failed to obtain credentials via OIDC: {str(e)}")
            
            # Run Pulumi destroy
            # Check if stack_name exists (microservices don't have stacks)
            if not deployment.stack_name:
                log_message(db, "WARNING", "No stack_name found - this may be a microservice deployment")
                logger.warning(f"Deployment {deployment_id} has no stack_name - skipping Pulumi destroy")
                result = {
                    "status": "success",
                    "summary": {},
                    "message": "No stack to destroy (microservice deployment)"
                }
            else:
                logger.info(f"Executing Pulumi destroy for stack: {deployment.stack_name}")
                log_message(db, "INFO", f"Executing Pulumi destroy for stack: {deployment.stack_name}")
                
                result = asyncio.run(pulumi_service.destroy_stack(
                    plugin_path=extract_path,
                    stack_name=deployment.stack_name,
                    credentials=credentials
                ))
            
            log_message(db, "INFO", f"Pulumi destroy completed with status: {result.get('status', 'unknown')}")
            
            # Clean up temp directory
            shutil.rmtree(temp_dir, ignore_errors=True)
            
            # Check if error is "stack not found" - if so, still delete the deployment
            error_msg = result.get('error', '')
            is_stack_not_found = 'no stack named' in str(error_msg).lower() or 'not found' in str(error_msg).lower()
            
            if result["status"] == "success" or is_stack_not_found:
                if is_stack_not_found:
                    logger.info(f"Stack not found in Pulumi, deleting deployment record anyway")
                    log_message(db, "WARNING", "Stack not found in Pulumi, deleting deployment record anyway")
                else:
                    logger.info(f"Infrastructure destroyed successfully")
                    log_message(db, "INFO", "Infrastructure destroyed successfully")
                    
                # Create notification BEFORE deleting deployment
                from app.models import Notification, NotificationType
                notification = Notification(
                    user_id=deployment.user_id,
                    title="Deletion Successful",
                    message=f"Resource '{deployment.name}' has been deleted successfully.",
                    type=NotificationType.SUCCESS, # Green notification as requested
                    link="/catalog" # Redirect to catalog since deployment is gone
                )
                db.add(notification)
                db.commit() # Commit notification first so it persists even if delete fails (though we fix delete below)
                log_message(db, "INFO", "Notification created for successful deletion")
                    
                # Unlink jobs from this deployment to avoid ForeignKeyViolation
                # We want to keep the job history, just remove the link to the deleted deployment
                jobs = db.execute(select(Job).where(Job.deployment_id == deployment.id)).scalars().all()
                for job in jobs:
                    job.deployment_id = None
                    db.add(job)
                db.commit()
                log_message(db, "INFO", "Unlinked jobs from deployment to preserve history")

                # Update deletion job status to success
                if deletion_job:
                    deletion_job.status = JobStatus.SUCCESS
                    deletion_job.finished_at = datetime.now(timezone.utc)
                    db.add(deletion_job)
                    db.commit()
                    log_message(db, "INFO", "Deletion job completed successfully")
                    logger.info(f"Updated deletion job {deletion_job.id} status to SUCCESS")
                
                # Delete deployment branch from GitHub AFTER infrastructure is removed (GitOps cleanup)
                # This happens AFTER infrastructure destruction is confirmed successful
                # We delete the branch as the final cleanup step, before removing the deployment record
                log_message(db, "INFO", f"Checking GitOps branch deletion: deployment.git_branch={deployment.git_branch}, plugin_version.git_repo_url={plugin_version.git_repo_url}")
                if deployment.git_branch and plugin_version.git_repo_url:
                    try:
                        from app.services.git_service import git_service
                        # Get GitHub token from settings
                        github_token = settings.GITHUB_TOKEN if hasattr(settings, 'GITHUB_TOKEN') else ""
                        if not github_token:
                            log_message(db, "WARNING", "GITHUB_TOKEN not configured, cannot delete branch via API")
                            logger.warning("GITHUB_TOKEN not configured, skipping branch deletion")
                        else:
                            log_message(db, "INFO", f"Deleting deployment branch '{deployment.git_branch}' from GitHub repository '{plugin_version.git_repo_url}' (after infrastructure removal)")
                            logger.info(f"Attempting to delete branch '{deployment.git_branch}' from {plugin_version.git_repo_url} (after infrastructure removal)")
                            git_service.delete_branch(plugin_version.git_repo_url, deployment.git_branch, github_token)
                            log_message(db, "INFO", f"Successfully deleted deployment branch '{deployment.git_branch}' from GitHub")
                            logger.info(f"Successfully deleted branch '{deployment.git_branch}' from GitHub")
                    except Exception as branch_error:
                        # Log error but don't fail the deletion - branch might not exist or already deleted
                        error_msg = f"Failed to delete branch '{deployment.git_branch}': {str(branch_error)}"
                        log_message(db, "WARNING", error_msg)
                        logger.warning(error_msg, exc_info=True)
                else:
                    log_message(db, "INFO", f"Skipping branch deletion: git_branch={deployment.git_branch}, git_repo_url={plugin_version.git_repo_url}")
                    logger.info(f"Skipping branch deletion - deployment.git_branch={deployment.git_branch}, plugin_version.git_repo_url={plugin_version.git_repo_url}")
                
                # Delete deployment from database (final step - after branch deletion)
                db.delete(deployment)
                db.commit()
                logger.info(f"Deployment record deleted")
                return {"status": "success", "message": "Infrastructure destroyed, branch deleted, and deployment removed"}
            else:
                logger.error(f"Destroy failed: {error_msg}")
                log_message(db, "ERROR", f"Destroy failed: {error_msg}")
                deployment.status = DeploymentStatus.FAILED
                
                # Update deletion job status to failed
                if deletion_job:
                    deletion_job.status = JobStatus.FAILED
                    deletion_job.finished_at = datetime.now(timezone.utc)
                    db.add(deletion_job)
                    db.commit()
                    log_message(db, "ERROR", "Deletion job marked as FAILED")
                    logger.info(f"Updated deletion job {deletion_job.id} status to FAILED")
                
                # Create notification
                from app.models import Notification, NotificationType
                notification = Notification(
                    user_id=deployment.user_id,
                    title="Deletion Failed",
                    message=f"Failed to delete '{deployment.name}': {error_msg}",
                    type=NotificationType.ERROR,
                    link=f"/deployments/{deployment.id}"
                )
                db.add(notification)
                
                db.commit()
                return {"status": "error", "message": error_msg}
                
        except Exception as e:
            error_details = traceback.format_exc()
            logger.error(f"[CELERY ERROR] Destroy task failed for deployment {deployment_id}: {error_details}")
            
            try:
                if 'deployment' in locals() and deployment:
                    deployment.status = DeploymentStatus.FAILED
                    db.commit()
            except Exception as db_error:
                # Log but don't fail if we can't update the deployment status
                logger.error(f"[CELERY ERROR] Failed to update deployment status: {db_error}")
            
            return {"status": "error", "message": str(e)}


@celery_app.task(name="provision_microservice")
def provision_microservice(job_id: str, plugin_id: str, version: str, deployment_name: str, user_id: str, deployment_id: str = None):
    """
    Celery task to provision a microservice by creating a new GitHub repository from a template.
    Uses synchronous DB operations to avoid asyncio loop conflicts.
    """
    import tempfile
    import shutil
    import traceback
    from datetime import datetime
    
    from sqlalchemy import select
    from sqlalchemy.orm import Session
    
    from app.models import Job, JobLog, JobStatus, PluginVersion, Plugin, Deployment, DeploymentStatus, Notification, NotificationType, User
    from app.services.microservice_service import microservice_service
    from app.services.github_actions_service import github_actions_service
    
    # Use shared sync engine for better connection pooling
    SessionLocal = _shared_SessionLocal
    
    # Helper to log messages
    def log_message(db: Session, level: str, message: str):
        log = JobLog(job_id=job_id, level=level, message=message)
        db.add(log)
        db.commit()
        log_func = getattr(logger, level.lower(), logger.info)
        log_func(f"[Microservice Job {job_id}] {message}")
    
    with SessionLocal() as db:
        try:
            # Update job status
            job = db.execute(select(Job).where(Job.id == job_id)).scalar_one()
            job.status = JobStatus.RUNNING
            db.commit()
            
            log_message(db, "INFO", f"Starting microservice provisioning: {deployment_name}")
            
            # Get plugin version
            plugin_version = db.execute(
                select(PluginVersion).where(
                    PluginVersion.plugin_id == plugin_id,
                    PluginVersion.version == version
                )
            ).scalar_one()
            
            # Verify this is a microservice plugin
            plugin = db.execute(
                select(Plugin).where(Plugin.id == plugin_id)
            ).scalar_one()
            
            if plugin.deployment_type != "microservice":
                raise Exception(f"Plugin {plugin_id} is not a microservice plugin")
            
            # Get template information
            template_repo_url = plugin_version.template_repo_url
            template_path = plugin_version.template_path
            
            if not template_repo_url or not template_path:
                raise Exception(f"Template repository URL or path not configured for plugin {plugin_id}")
            
            log_message(db, "INFO", f"Template: {template_repo_url}/{template_path}")
            
            # Get or create deployment
            deployment = None
            if deployment_id:
                # Handle UUID conversion for deployment_id
                from uuid import UUID
                deployment_uuid = UUID(deployment_id) if isinstance(deployment_id, str) else deployment_id
                deployment = db.execute(select(Deployment).where(Deployment.id == deployment_uuid)).scalar_one_or_none()
            
            if not deployment:
                # Create new deployment record
                user = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
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
                db.add(deployment)
                db.commit()
                db.refresh(deployment)
                log_message(db, "INFO", f"Created deployment record: {deployment.id}")
            else:
                deployment.status = DeploymentStatus.PROVISIONING
                deployment.deployment_type = "microservice"
                db.add(deployment)
                db.commit()
            
            # Get user's GitHub token (for now, use platform token - TODO: get from user's OIDC or stored credentials)
            # In the future, we should get this from user's GitHub OAuth token or stored credentials
            user_github_token = settings.GITHUB_TOKEN if hasattr(settings, 'GITHUB_TOKEN') else ""
            
            if not user_github_token:
                raise Exception("GitHub token not configured. Cannot create repository.")
            
            log_message(db, "INFO", f"Creating GitHub repository: {deployment_name}")
            
            # Get organization from settings (if configured)
            organization = getattr(settings, 'MICROSERVICE_REPO_ORG', '') or None
            if organization:
                log_message(db, "INFO", f"Creating repository in organization: {organization}")
            
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
                
                log_message(db, "INFO", f"Successfully created repository: {repo_full_name}")
                log_message(db, "INFO", f"Repository URL: {repo_url}")
                
            except Exception as e:
                error_msg = f"Failed to create repository: {str(e)}"
                log_message(db, "ERROR", error_msg)
                raise Exception(error_msg)
            
            # Update deployment with repository information
            deployment.github_repo_url = repo_url
            deployment.github_repo_name = repo_full_name
            deployment.status = DeploymentStatus.ACTIVE
            deployment.ci_cd_status = "pending"  # Initial status, will be updated by webhook
            db.add(deployment)
            
            # Update job status
            job.status = JobStatus.SUCCESS
            job.finished_at = datetime.now(timezone.utc)
            job.outputs = {
                "repository_url": repo_url,
                "repository_name": repo_full_name,
                "deployment_id": str(deployment.id)
            }
            db.add(job)
            
            # Get initial CI/CD status (GitHub Actions might have already started)
            try:
                ci_cd_status = github_actions_service.get_latest_workflow_status(
                    repo_full_name=repo_full_name,
                    user_github_token=user_github_token,
                    branch="main"  # Default branch
                )
                
                if ci_cd_status:
                    deployment.ci_cd_status = ci_cd_status.get("ci_cd_status", "pending")
                    deployment.ci_cd_run_id = ci_cd_status.get("ci_cd_run_id")
                    deployment.ci_cd_run_url = ci_cd_status.get("ci_cd_run_url")
                    deployment.ci_cd_updated_at = datetime.now(timezone.utc)
                    log_message(db, "INFO", f"Initial CI/CD status: {deployment.ci_cd_status}")
            except Exception as e:
                log_message(db, "WARNING", f"Could not fetch initial CI/CD status: {str(e)}")
                # Continue anyway, webhook will update it
            
            db.commit()
            
            # Create success notification
            user = db.execute(select(User).where(User.id == user_id)).scalar_one()
            notification = Notification(
                user_id=user.id,
                title="Microservice Created",
                message=f"Microservice '{deployment_name}' has been created. Repository: {repo_full_name}",
                type=NotificationType.SUCCESS,
                link=f"/deployments/{deployment.id}"
            )
            db.add(notification)
            db.commit()
            
            log_message(db, "INFO", "Microservice provisioning completed successfully")
            
        except Exception as e:
            error_details = traceback.format_exc()
            logger.error(f"[CELERY ERROR] Microservice job {job_id} failed: {error_details}")
            
            try:
                job = db.execute(select(Job).where(Job.id == job_id)).scalar_one()
                job.status = JobStatus.FAILED
                job.finished_at = datetime.now(timezone.utc)
                log_message(db, "ERROR", f"Internal Error: {str(e)}")
                
                # Update deployment status if exists
                if deployment_id:
                    # Handle UUID conversion for deployment_id
                    from uuid import UUID
                    deployment_uuid = UUID(deployment_id) if isinstance(deployment_id, str) else deployment_id
                    deployment = db.execute(select(Deployment).where(Deployment.id == deployment_uuid)).scalar_one_or_none()
                    if deployment:
                        deployment.status = DeploymentStatus.FAILED
                        db.add(deployment)
                elif 'deployment' in locals() and deployment:
                    deployment.status = DeploymentStatus.FAILED
                    db.add(deployment)
                
                # Create failure notification
                try:
                    user = db.execute(select(User).where(User.id == user_id)).scalar_one()
                    notification = Notification(
                        user_id=user.id,
                        title="Microservice Creation Failed",
                        message=f"Failed to create microservice '{deployment_name}': {str(e)}",
                        type=NotificationType.ERROR,
                        link=f"/jobs/{job_id}" if job_id else None
                    )
                    db.add(notification)
                except Exception as notif_error:
                    logger.error(f"Failed to create notification for user {user_id} on microservice failure: {notif_error}", exc_info=True)
                    # Continue without notification rather than failing the entire job update
                
                db.commit()
            except Exception as db_error:
                logger.error(f"[CELERY ERROR] Failed to update job status for {job_id}: {db_error}")


@celery_app.task(name="destroy_microservice")
def destroy_microservice(deployment_id: str):
    """
    Celery task to destroy microservice deployment
    """
    from uuid import UUID
    """
    Celery task to delete a microservice deployment.
    For microservices, we just delete the deployment record and optionally the GitHub repository.
    Uses synchronous DB operations to avoid asyncio loop conflicts.
    """
    import traceback
    from datetime import datetime
    
    from sqlalchemy import select
    from sqlalchemy.orm import Session
    
    from app.models import Deployment, DeploymentStatus, Job, JobStatus, JobLog, Notification, NotificationType, User
    
    # Use shared sync engine for better connection pooling
    SessionLocal = _shared_SessionLocal
    
    with SessionLocal() as db:
        deletion_job = None
        deletion_job_id = None
        
        # Helper to log messages
        def log_message(db: Session, level: str, message: str):
            if deletion_job_id:
                log = JobLog(job_id=deletion_job_id, level=level, message=message)
                db.add(log)
                db.commit()
            log_func = getattr(logger, level.lower(), logger.info)
            log_func(f"[Microservice Deletion {deletion_job_id or 'N/A'}] {message}")
        
        try:
            logger.info(f"Starting microservice deletion for deployment {deployment_id}")
            
            # Get deployment
            # Handle UUID conversion for deployment_id
            from uuid import UUID
            deployment_uuid = UUID(deployment_id) if isinstance(deployment_id, str) else deployment_id
            deployment = db.execute(select(Deployment).where(Deployment.id == deployment_uuid)).scalar_one_or_none()
            
            if not deployment:
                logger.error(f"Deployment {deployment_id} not found")
                return {"status": "error", "message": "Deployment not found"}
            
            # Verify this is a microservice
            if deployment.deployment_type != "microservice":
                logger.warning(f"Deployment {deployment_id} is not a microservice, but destroy_microservice was called")
                log_message(db, "WARNING", "This deployment is not a microservice")
            
            # Find the deletion job for this deployment
            # Use first() instead of scalar_one_or_none() to handle multiple jobs (get the most recent)
            deletion_job_result = db.execute(
                select(Job).where(
                    Job.deployment_id == deployment.id,
                    Job.status == JobStatus.PENDING
                ).order_by(Job.created_at.desc())
            )
            deletion_job_row = deletion_job_result.first()
            deletion_job = deletion_job_row[0] if deletion_job_row else None
            
            if deletion_job:
                deletion_job_id = deletion_job.id
                if deletion_job.status == JobStatus.PENDING:
                    deletion_job.status = JobStatus.RUNNING
                    db.commit()
                log_message(db, "INFO", f"Starting microservice deletion for deployment {deployment_id}")
            else:
                logger.warning(f"Deletion job not found for deployment {deployment_id}")
            
            # Update status to deleting
            deployment.status = DeploymentStatus.PROVISIONING  # Using provisioning as "deleting" status
            db.commit()
            log_message(db, "INFO", f"Updated deployment status to deleting")
            
            # Delete GitHub repository if it exists
            if deployment.github_repo_name:
                try:
                    from app.services.microservice_service import microservice_service
                    user_github_token = settings.GITHUB_TOKEN if hasattr(settings, 'GITHUB_TOKEN') else ""
                    if user_github_token:
                        log_message(db, "INFO", f"Deleting GitHub repository: {deployment.github_repo_name}")
                        logger.info(f"Deleting GitHub repository: {deployment.github_repo_name}")
                        microservice_service.delete_github_repository(deployment.github_repo_name, user_github_token)
                        log_message(db, "INFO", f"Successfully deleted GitHub repository: {deployment.github_repo_name}")
                        logger.info(f"Successfully deleted GitHub repository: {deployment.github_repo_name}")
                    else:
                        log_message(db, "WARNING", "GITHUB_TOKEN not configured, cannot delete repository")
                        logger.warning("GITHUB_TOKEN not configured, skipping repository deletion")
                except Exception as e:
                    # Log error but don't fail the deletion - repository might not exist or already deleted
                    error_msg = f"Could not delete GitHub repository: {str(e)}"
                    log_message(db, "WARNING", error_msg)
                    logger.warning(error_msg, exc_info=True)
                    # Continue with deployment deletion even if repo deletion fails
            else:
                log_message(db, "INFO", "No GitHub repository associated with this deployment")
            
            # Create notification BEFORE deleting deployment
            notification = Notification(
                user_id=deployment.user_id,
                title="Deletion Successful",
                message=f"Microservice '{deployment.name}' has been deleted successfully.",
                type=NotificationType.SUCCESS,
                link="/catalog"
            )
            db.add(notification)
            db.commit()
            log_message(db, "INFO", "Notification created for successful deletion")
            
            # Unlink jobs from this deployment to avoid ForeignKeyViolation
            jobs = db.execute(select(Job).where(Job.deployment_id == deployment.id)).scalars().all()
            for job in jobs:
                job.deployment_id = None
                db.add(job)
            db.commit()
            log_message(db, "INFO", "Unlinked jobs from deployment to preserve history")
            
            # Update deletion job status to success
            if deletion_job:
                deletion_job.status = JobStatus.SUCCESS
                deletion_job.finished_at = datetime.now(timezone.utc)
                db.add(deletion_job)
                db.commit()
                log_message(db, "INFO", "Deletion job completed successfully")
            
            # Delete deployment record
            db.delete(deployment)
            db.commit()
            log_message(db, "INFO", "Microservice deployment deleted successfully")
            logger.info(f"Microservice deployment {deployment_id} deleted successfully")
            
        except Exception as e:
            error_details = traceback.format_exc()
            logger.error(f"[CELERY ERROR] Microservice deletion {deployment_id} failed: {error_details}")
            
            try:
                if deletion_job:
                    deletion_job.status = JobStatus.FAILED
                    deletion_job.finished_at = datetime.now(timezone.utc)
                    log_message(db, "ERROR", f"Internal Error: {str(e)}")
                    db.add(deletion_job)
                
                # Update deployment status if exists
                # Handle UUID conversion for deployment_id
                from uuid import UUID
                deployment_uuid = UUID(deployment_id) if isinstance(deployment_id, str) else deployment_id
                deployment = db.execute(select(Deployment).where(Deployment.id == deployment_uuid)).scalar_one_or_none()
                if deployment:
                    deployment.status = DeploymentStatus.FAILED
                    db.add(deployment)
                
                # Create failure notification
                if deployment:
                    try:
                        user = db.execute(select(User).where(User.id == deployment.user_id)).scalar_one()
                        notification = Notification(
                            user_id=user.id,
                            title="Deletion Failed",
                            message=f"Failed to delete microservice '{deployment.name}': {str(e)}",
                            type=NotificationType.ERROR,
                            link=f"/deployments/{deployment.id}" if deployment else None
                        )
                        db.add(notification)
                    except Exception:
                        pass
                
                db.commit()
            except Exception as db_error:
                logger.error(f"[CELERY ERROR] Failed to update job status for {deployment_id}: {db_error}")


@celery_app.task(name="cleanup_stuck_deployments")
def cleanup_stuck_deployments():
    """
    Periodic task to find and fix deployments stuck in PROVISIONING status.
    This handles cases where:
    1. Jobs failed but deployment status wasn't updated
    2. Jobs are in DEAD_LETTER but deployment is still PROVISIONING
    3. Deployments have been in PROVISIONING for too long with no job updates
    """
    from sqlalchemy import select, and_, or_
    from sqlalchemy.orm import Session
    from datetime import datetime, timedelta, timezone
    from app.models import Deployment, DeploymentStatus, Job, JobStatus
    
    # Use shared sync engine for better connection pooling
    SessionLocal = _shared_SessionLocal
    
    with SessionLocal() as db:
        try:
            # Find deployments stuck in PROVISIONING
            stuck_deployments = db.execute(
                select(Deployment).where(
                    Deployment.status == DeploymentStatus.PROVISIONING
                )
            ).scalars().all()
            
            if not stuck_deployments:
                logger.info("No stuck deployments found")
                return
            
            logger.info(f"Checking {len(stuck_deployments)} deployments in PROVISIONING status")
            
            updated_count = 0
            timeout_threshold = datetime.now(timezone.utc) - timedelta(hours=2)  # 2 hours timeout
            
            for deployment in stuck_deployments:
                try:
                    # Find the most recent job for this deployment
                    job_result = db.execute(
                        select(Job).where(
                            Job.deployment_id == deployment.id
                        ).order_by(Job.created_at.desc())
                    )
                    job = job_result.scalar_one_or_none()
                    
                    should_fail = False
                    reason = ""
                    
                    if job:
                        # Check if job is in a failed state - mark deployment as failed immediately
                        if job.status in [JobStatus.FAILED, JobStatus.DEAD_LETTER]:
                            should_fail = True
                            reason = f"Associated job is in {job.status} status"
                            if job.error_message:
                                reason += f": {job.error_message[:100]}"  # Include error message
                        # Check if job has been pending/running for too long without updates
                        elif job.status == JobStatus.PENDING:
                            # If job is pending and deployment is old, it might be stuck
                            check_time = job.created_at if job.created_at else deployment.created_at
                            if check_time:
                                # Ensure timezone-aware comparison
                                if check_time.tzinfo is None:
                                    check_time = check_time.replace(tzinfo=timezone.utc)
                                if check_time < timeout_threshold:
                                    should_fail = True
                                    reason = f"Job has been PENDING for over 2 hours (created: {check_time})"
                        elif job.status == JobStatus.RUNNING:
                            # If job is running but deployment is very old, it might be stuck
                            check_time = job.created_at if job.created_at else deployment.created_at
                            if check_time:
                                # Ensure timezone-aware comparison
                                if check_time.tzinfo is None:
                                    check_time = check_time.replace(tzinfo=timezone.utc)
                                if check_time < timeout_threshold:
                                    should_fail = True
                                    reason = f"Job has been RUNNING for over 2 hours (created: {check_time})"
                    else:
                        # No job found - if deployment is old, mark as failed
                        if deployment.created_at:
                            check_time = deployment.created_at
                            # Ensure timezone-aware comparison
                            if check_time.tzinfo is None:
                                check_time = check_time.replace(tzinfo=timezone.utc)
                            if check_time < timeout_threshold:
                                should_fail = True
                                reason = f"No associated job found and deployment is over 2 hours old (created: {check_time})"
                    
                    if should_fail:
                        logger.warning(f"Marking deployment {deployment.id} ({deployment.name}) as FAILED: {reason}")
                        deployment.status = DeploymentStatus.FAILED
                        db.add(deployment)
                        updated_count += 1
                        
                        # Create notification for user if possible
                        try:
                            from app.models import User, Notification, NotificationType
                            user = db.execute(select(User).where(User.id == deployment.user_id)).scalar_one_or_none()
                            if user:
                                notification = Notification(
                                    user_id=user.id,
                                    title="Deployment Failed",
                                    message=f"Deployment '{deployment.name}' was automatically marked as failed: {reason}",
                                    type=NotificationType.ERROR,
                                    link=f"/deployments/{deployment.id}"
                                )
                                db.add(notification)
                        except Exception as notif_error:
                            logger.warning(f"Failed to create notification: {notif_error}")
                    
                except Exception as e:
                    logger.error(f"Error processing deployment {deployment.id}: {e}", exc_info=True)
                    continue
            
            if updated_count > 0:
                db.commit()
                logger.info(f"Updated {updated_count} stuck deployment(s) to FAILED status")
            else:
                logger.info("No deployments needed to be updated")
                
        except Exception as e:
            logger.error(f"Error in cleanup_stuck_deployments task: {e}", exc_info=True)
            db.rollback()

@celery_app.task(name="cleanup_expired_refresh_tokens")
def cleanup_expired_refresh_tokens():
    """
    Periodic task to delete expired refresh tokens from the database.
    This prevents database bloat and improves security by removing stale tokens.
    """
    from sqlalchemy import select, delete
    from sqlalchemy.orm import Session
    from datetime import datetime, timezone
    from app.models.rbac import RefreshToken
    
    # Use shared sync engine for better connection pooling
    SessionLocal = _shared_SessionLocal
    
    with SessionLocal() as db:
        try:
            # Delete all expired refresh tokens
            now = datetime.now(timezone.utc)
            result = db.execute(
                delete(RefreshToken).where(RefreshToken.expires_at < now)
            )
            deleted_count = result.rowcount
            db.commit()
            
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} expired refresh token(s)")
            else:
                logger.debug("No expired refresh tokens to clean up")
                
        except Exception as e:
            logger.error(f"Error cleaning up expired refresh tokens: {e}", exc_info=True)
            db.rollback()

@celery_app.task(name="poll_github_actions_status")
def poll_github_actions_status():
    """
    Periodic task to poll GitHub Actions status for active microservice deployments.
    This serves as a fallback when webhooks are not available or fail.
    Runs periodically (e.g., every 60 seconds) via Celery beat.
    """
    from sqlalchemy import select
    from sqlalchemy.orm import Session
    from datetime import datetime, timedelta
    from app.models import Deployment, DeploymentStatus
    from app.services.github_actions_service import github_actions_service
    
    # Use shared sync engine for better connection pooling
    SessionLocal = _shared_SessionLocal
    
    with SessionLocal() as db:
        try:
            # Find deployments that need status polling
            # Only poll microservices with active CI/CD (pending or running)
            active_statuses = ["pending", "running"]
            deployments = db.execute(
                select(Deployment).where(
                    Deployment.deployment_type == "microservice",
                    Deployment.github_repo_name.isnot(None),
                    Deployment.ci_cd_status.in_(active_statuses)
                )
            ).scalars().all()
            
            logger.info(f"Polling CI/CD status for {len(deployments)} deployments")
            
            github_token = settings.GITHUB_TOKEN if hasattr(settings, 'GITHUB_TOKEN') else ""
            if not github_token:
                logger.warning("GitHub token not configured, skipping CI/CD status polling")
                return
            
            updated_count = 0
            for deployment in deployments:
                try:
                    if not deployment.github_repo_name:
                        continue
                    
                    # Get latest workflow status
                    ci_cd_status = github_actions_service.get_latest_workflow_status(
                        repo_full_name=deployment.github_repo_name,
                        user_github_token=github_token,
                        branch="main"  # Default branch
                    )
                    
                    if ci_cd_status:
                        # Update deployment if status changed
                        new_status = ci_cd_status.get("ci_cd_status")
                        if new_status and new_status != deployment.ci_cd_status:
                            deployment.ci_cd_status = new_status
                            deployment.ci_cd_run_id = ci_cd_status.get("ci_cd_run_id")
                            deployment.ci_cd_run_url = ci_cd_status.get("ci_cd_run_url")
                            deployment.ci_cd_updated_at = datetime.now(timezone.utc)
                            db.add(deployment)
                            updated_count += 1
                            logger.info(f"Updated CI/CD status for {deployment.github_repo_name}: {new_status}")
                    
                except Exception as e:
                    logger.error(f"Error polling status for deployment {deployment.id}: {e}")
                    continue
            
            if updated_count > 0:
                db.commit()
                logger.info(f"Updated CI/CD status for {updated_count} deployments")
            
        except Exception as e:
            logger.error(f"Error in CI/CD status polling task: {e}", exc_info=True)


if __name__ == "__main__":
    celery_app.start()
