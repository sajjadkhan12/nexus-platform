"""Celery worker for background job processing"""
from celery import Celery
from app.config import settings
import os
import asyncio
import json
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Create Celery app
celery_app = Celery(
    "idp_worker",
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
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
        print(f"[{level}] {message}")

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
            
            # Extract plugin
            temp_dir = Path(tempfile.mkdtemp())
            extract_path = storage_service.extract_plugin(plugin_id, version, temp_dir)
            log_message(db, "INFO", f"Extracted plugin to {extract_path}")
            
            # --- GET DEPLOYMENT RECORD AND USER_ID FIRST ---
            # We need user_id before credential loading for OIDC exchange
            deployment = None
            stack_name = f"{plugin_id}-{job_id[:8]}"
            resource_name = inputs.get("bucket_name") or inputs.get("name") or f"{plugin_id}-{job_id[:8]}"
            user_id = None  # Will be used for OIDC credential exchange
            
            if deployment_id:
                deployment = db.execute(select(Deployment).where(Deployment.id == deployment_id)).scalar_one_or_none()
                if deployment:
                    log_message(db, "INFO", f"Using existing deployment record: {deployment.name}")
                    stack_name = deployment.stack_name # Use stack name from record
                    user_id = deployment.user_id  # Get user_id for OIDC exchange
                else:
                    log_message(db, "WARNING", f"Deployment {deployment_id} not found")
            else:
                # Fallback: Create deployment if not provided (legacy support)
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
                    log_message(db, "INFO", f"Created deployment record: {deployment.name}")
            
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
            
            # Auto-exchange OIDC tokens for cloud credentials if no static credentials provided
            # This enables automatic credential provisioning for AWS, GCP, and Azure
            if not credentials:
                cloud_provider = plugin_version.manifest.get("cloud_provider", "").lower()
                
                if user_id and cloud_provider:
                    try:
                        from app.services.oidc_credentials import oidc_credential_service
                        
                        if cloud_provider == "aws":
                            log_message(db, "INFO", "No static credentials found. Automatically exchanging OIDC token for AWS credentials...")
                            credentials = oidc_credential_service.get_aws_credentials(
                                user_id=str(user_id),
                                duration_seconds=3600  # 1 hour
                            )
                            log_message(db, "INFO", "Successfully obtained AWS credentials via OIDC")
                        
                        elif cloud_provider == "gcp":
                            log_message(db, "INFO", "No static credentials found. Automatically exchanging OIDC token for GCP credentials...")
                            credentials = oidc_credential_service.get_gcp_credentials(
                                user_id=str(user_id)
                            )
                            log_message(db, "INFO", "Successfully obtained GCP credentials via OIDC")
                        
                        elif cloud_provider == "azure":
                            log_message(db, "INFO", "No static credentials found. Automatically exchanging OIDC token for Azure credentials...")
                            credentials = oidc_credential_service.get_azure_credentials(
                                user_id=str(user_id)
                            )
                            log_message(db, "INFO", "Successfully obtained Azure credentials via OIDC")
                            
                    except Exception as e:
                        log_message(db, "WARNING", f"Failed to auto-exchange OIDC credentials: {str(e)}")
                        log_message(db, "WARNING", "Continuing without credentials - deployment may fail if credentials are required")
                        # Don't raise - let Pulumi try without credentials (some plugins might work)
                elif cloud_provider and not user_id:
                    log_message(db, "WARNING", f"Cloud provider '{cloud_provider}' detected but unable to determine user_id for OIDC exchange")

            # Run Pulumi (Async)
            log_message(db, "INFO", "Executing Pulumi program...")
            
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
            print(f"[CELERY ERROR] {error_details}")
            
            # Re-fetch job to ensure attached to session
            try:
                job = db.execute(select(Job).where(Job.id == job_id)).scalar_one()
                job.status = JobStatus.FAILED
                log_message(db, "ERROR", f"Internal Error: {str(e)}")
            except Exception as db_error:
                # Log but don't fail if we can't update the job status
                print(f"[CELERY ERROR] Failed to update job status: {db_error}")

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
    
    from app.models import Deployment, DeploymentStatus, PluginVersion, CloudCredential, Job
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
        try:
            print(f"[INFO] Starting infrastructure destruction for deployment {deployment_id}")
            
            # Get deployment
            deployment = db.execute(select(Deployment).where(Deployment.id == deployment_id)).scalar_one_or_none()
            
            if not deployment:
                print(f"[ERROR] Deployment {deployment_id} not found")
                return {"status": "error", "message": "Deployment not found"}
            
            # Update status to deleting
            deployment.status = DeploymentStatus.PROVISIONING  # Using provisioning as "deleting" status
            db.commit()
            
            # Get plugin version
            plugin_version = db.execute(
                select(PluginVersion).where(
                    PluginVersion.plugin_id == deployment.plugin_id,
                    PluginVersion.version == deployment.version
                )
            ).scalar_one()
            
            # Extract plugin to temp directory
            temp_dir = tempfile.mkdtemp(prefix="pulumi_destroy_")
            extract_path = Path(temp_dir)
            
            print(f"[INFO] Extracting plugin to {extract_path}")
            storage_service.extract_plugin(deployment.plugin_id, deployment.version, extract_path)
            
            # Load credentials if cloud_provider is set
            credentials = None
            if deployment.cloud_provider:
                # Try to find static credentials first
                result = db.execute(
                    select(CloudCredential).where(CloudCredential.provider == deployment.cloud_provider)
                ).first()
                
                if result:
                    cred_record = result[0]
                    try:
                        credentials = crypto_service.decrypt(cred_record.encrypted_data)
                        print(f"[INFO] Loaded static credentials for {deployment.cloud_provider}")
                    except Exception as e:
                        print(f"[WARNING] Failed to decrypt credentials: {str(e)}")
                
                # Auto-exchange OIDC tokens if no static credentials found
                if not credentials and deployment.user_id:
                    try:
                        from app.services.oidc_credentials import oidc_credential_service
                        cloud_provider = deployment.cloud_provider.lower()
                        
                        if cloud_provider == "aws":
                            print(f"[INFO] No static credentials found. Automatically exchanging OIDC token for AWS credentials...")
                            credentials = oidc_credential_service.get_aws_credentials(
                                user_id=str(deployment.user_id),
                                duration_seconds=3600
                            )
                            print(f"[INFO] Successfully obtained AWS credentials via OIDC")
                        
                        elif cloud_provider == "gcp":
                            print(f"[INFO] No static credentials found. Automatically exchanging OIDC token for GCP credentials...")
                            credentials = oidc_credential_service.get_gcp_credentials(
                                user_id=str(deployment.user_id)
                            )
                            print(f"[INFO] Successfully obtained GCP credentials via OIDC")
                        
                        elif cloud_provider == "azure":
                            print(f"[INFO] No static credentials found. Automatically exchanging OIDC token for Azure credentials...")
                            credentials = oidc_credential_service.get_azure_credentials(
                                user_id=str(deployment.user_id)
                            )
                            print(f"[INFO] Successfully obtained Azure credentials via OIDC")
                            
                    except Exception as e:
                        print(f"[WARNING] Failed to auto-exchange OIDC credentials: {str(e)}")
                        print(f"[WARNING] Continuing without credentials - destroy may fail if credentials are required")
            
            # Run Pulumi destroy
            print(f"[INFO] Executing Pulumi destroy for stack: {deployment.stack_name}")
            
            result = asyncio.run(pulumi_service.destroy_stack(
                plugin_path=extract_path,
                stack_name=deployment.stack_name,
                credentials=credentials
            ))
            
            # Clean up temp directory
            shutil.rmtree(temp_dir, ignore_errors=True)
            
            # Check if error is "stack not found" - if so, still delete the deployment
            error_msg = result.get('error', '')
            is_stack_not_found = 'no stack named' in str(error_msg).lower() or 'not found' in str(error_msg).lower()
            
            if result["status"] == "success" or is_stack_not_found:
                if is_stack_not_found:
                    print(f"[INFO] Stack not found in Pulumi, deleting deployment record anyway")
                else:
                    print(f"[INFO] Infrastructure destroyed successfully")
                    
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
                    
                # Unlink jobs from this deployment to avoid ForeignKeyViolation
                # We want to keep the job history, just remove the link to the deleted deployment
                jobs = db.execute(select(Job).where(Job.deployment_id == deployment.id)).scalars().all()
                for job in jobs:
                    job.deployment_id = None
                    db.add(job)
                db.commit()

                # Delete deployment from database
                db.delete(deployment)
                db.commit()
                print(f"[INFO] Deployment record deleted")
                return {"status": "success", "message": "Infrastructure destroyed and deployment deleted"}
            else:
                print(f"[ERROR] Destroy failed: {error_msg}")
                deployment.status = DeploymentStatus.FAILED
                
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
            print(f"[CELERY ERROR] {error_details}")
            
            try:
                if 'deployment' in locals() and deployment:
                    deployment.status = DeploymentStatus.FAILED
                    db.commit()
            except Exception as db_error:
                # Log but don't fail if we can't update the deployment status
                print(f"[CELERY ERROR] Failed to update deployment status: {db_error}")
            
            return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    celery_app.start()
