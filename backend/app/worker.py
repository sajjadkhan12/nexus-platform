"""Celery worker for background job processing"""
from celery import Celery
from app.config import settings
import os
import asyncio
import json
from datetime import datetime
from dotenv import load_dotenv
from app.logger import logger  # Use centralized logger

# Load environment variables from .env file
load_dotenv()

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
    
    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import Session, sessionmaker
    
    from app.models import Job, JobLog, JobStatus, PluginVersion, CloudCredential, Deployment, DeploymentStatus, Notification, NotificationType
    from app.services.storage import storage_service
    from app.services.pulumi_service import pulumi_service
    from app.services.crypto import crypto_service
    
    # Create sync engine
    # Use psycopg2 instead of asyncpg
    sync_db_url = settings.DATABASE_URL.replace("+asyncpg", "")
    if "postgresql://" not in sync_db_url and "postgresql+psycopg2://" not in sync_db_url:
         # Fallback if URL doesn't have driver
         sync_db_url = sync_db_url.replace("postgresql:", "postgresql+psycopg2:")
         
    engine = create_engine(sync_db_url, echo=False)
    SessionLocal = sessionmaker(bind=engine)
    
    # Helper to log messages
    def log_message(db: Session, level: str, message: str):
        log = JobLog(job_id=job_id, level=level, message=message)
        db.add(log)
        db.commit()
        # Log to server.log using appropriate level
        log_func = getattr(logger, level.lower(), logger.info)
        log_func(f"[Job {job_id}] {message}")

    with SessionLocal() as db:
        try:
            # Update job status
            job = db.execute(select(Job).where(Job.id == job_id)).scalar_one()
            job.status = JobStatus.RUNNING
            db.commit()
            
            log_message(db, "INFO", "Starting provisioning job")
            
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
            if deployment_id:
                deployment = db.execute(select(Deployment).where(Deployment.id == deployment_id)).scalar_one_or_none()
                if deployment:
                    # Use stack name from record if it exists and is not None, otherwise keep the generated one
                    if deployment.stack_name:
                        stack_name = deployment.stack_name
                    # If stack_name is None or empty, keep the generated one from line 85
                    user_id = deployment.user_id  # Get user_id for OIDC exchange
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
                    deployment.status = DeploymentStatus.ACTIVE
                    deployment.outputs = result["outputs"]
                    db.add(deployment)
                
                log_message(db, "INFO", "Provisioning completed successfully")
                
                # Create notification
                user_id = db.execute(select(Job.triggered_by).where(Job.id == job_id)).scalar_one()
                from app.models import User
                user = db.execute(select(User).where(User.email == user_id)).scalar_one_or_none()
                
                if user:
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
                job.status = JobStatus.FAILED
                error_msg = result.get('error', 'Unknown error')
                
                if deployment:
                    deployment.status = DeploymentStatus.FAILED
                    db.add(deployment)
                
                log_message(db, "ERROR", f"Provisioning failed: {error_msg}")
                
                # Create notification
                user_id = db.execute(select(Job.triggered_by).where(Job.id == job_id)).scalar_one()
                from app.models import User
                user = db.execute(select(User).where(User.email == user_id)).scalar_one_or_none()
                
                if user:
                    notification = Notification(
                        user_id=user.id,
                        title="Provisioning Failed",
                        message=f"Failed to provision '{resource_name}': {error_msg}",
                        type=NotificationType.ERROR,
                        link=f"/jobs/{job_id}"
                    )
                    db.add(notification)
                    
                db.commit()
            
            # Clean up
            shutil.rmtree(temp_dir, ignore_errors=True)
            
        except Exception as e:
            error_details = traceback.format_exc()
            logger.error(f"[CELERY ERROR] Job {job_id} failed: {error_details}")
            
            # Re-fetch job and deployment to ensure attached to session
            try:
                job = db.execute(select(Job).where(Job.id == job_id)).scalar_one()
                job.status = JobStatus.FAILED
                log_message(db, "ERROR", f"Internal Error: {str(e)}")
                
                # Also update deployment status if it exists
                if deployment_id:
                    try:
                        deployment = db.execute(select(Deployment).where(Deployment.id == deployment_id)).scalar_one_or_none()
                        if deployment:
                            deployment.status = DeploymentStatus.FAILED
                            db.add(deployment)
                            log_message(db, "ERROR", f"Deployment status updated to FAILED")
                    except Exception as deploy_error:
                        logger.warning(f"Failed to update deployment status: {deploy_error}")
                
                # Also try to find deployment by job_id if deployment_id wasn't set
                if not deployment_id:
                    try:
                        deployment = db.execute(select(Deployment).where(Deployment.id == job.deployment_id)).scalar_one_or_none()
                        if deployment:
                            deployment.status = DeploymentStatus.FAILED
                            db.add(deployment)
                            log_message(db, "ERROR", f"Deployment status updated to FAILED")
                    except Exception as deploy_error:
                        logger.warning(f"Failed to update deployment status: {deploy_error}")
                
                db.commit()
            except Exception as db_error:
                # Log but don't fail if we can't update the job status
                logger.error(f"[CELERY ERROR] Failed to update job status for {job_id}: {db_error}")

@celery_app.task(name="destroy_infrastructure")
def destroy_infrastructure(deployment_id: str):
    """
    Celery task to destroy infrastructure using Pulumi and delete deployment record
    """
    from pathlib import Path
    import tempfile
    import shutil
    import traceback
    
    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import Session, sessionmaker
    
    from app.models import Deployment, DeploymentStatus, PluginVersion, CloudCredential, Job, JobStatus, JobLog
    from app.services.storage import storage_service
    from app.services.pulumi_service import pulumi_service
    from app.services.crypto import crypto_service
    
    # Create sync engine
    sync_db_url = settings.DATABASE_URL.replace("+asyncpg", "")
    if "postgresql://" not in sync_db_url and "postgresql+psycopg2://" not in sync_db_url:
        sync_db_url = sync_db_url.replace("postgresql:", "postgresql+psycopg2:")
        
    engine = create_engine(sync_db_url, echo=False)
    SessionLocal = sessionmaker(bind=engine)
    
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
            logger.info(f"Starting infrastructure destruction for deployment {deployment_id}")
            
            # Get deployment
            deployment = db.execute(select(Deployment).where(Deployment.id == deployment_id)).scalar_one_or_none()
            
            if not deployment:
                logger.error(f"Deployment {deployment_id} not found")
                return {"status": "error", "message": "Deployment not found"}
            
            # Find the deletion job for this deployment
            from app.models import JobStatus
            # First try to find a PENDING job
            deletion_job = db.execute(
                select(Job).where(
                    Job.deployment_id == deployment.id,
                    Job.status == JobStatus.PENDING
                ).order_by(Job.created_at.desc())
            ).scalar_one_or_none()
            
            # If not found, try to find any job for this deployment (might already be RUNNING or created differently)
            if not deletion_job:
                deletion_job = db.execute(
                    select(Job).where(
                        Job.deployment_id == deployment.id
                    ).order_by(Job.created_at.desc())
                ).scalar_one_or_none()
            
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
                    deletion_job.finished_at = datetime.utcnow()
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
                        log_message(db, "INFO", f"Deleting deployment branch '{deployment.git_branch}' from GitHub repository '{plugin_version.git_repo_url}' (after infrastructure removal)")
                        logger.info(f"Attempting to delete branch '{deployment.git_branch}' from {plugin_version.git_repo_url} (after infrastructure removal)")
                        git_service.delete_branch(plugin_version.git_repo_url, deployment.git_branch)
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
                    deletion_job.finished_at = datetime.utcnow()
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


if __name__ == "__main__":
    celery_app.start()
