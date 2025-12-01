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
            
            # --- GET DEPLOYMENT RECORD ---
            deployment = None
            stack_name = f"{plugin_id}-{job_id[:8]}"
            resource_name = inputs.get("bucket_name") or inputs.get("name") or f"{plugin_id}-{job_id[:8]}"
            
            if deployment_id:
                deployment = db.execute(select(Deployment).where(Deployment.id == deployment_id)).scalar_one_or_none()
                if deployment:
                    log_message(db, "INFO", f"Using existing deployment record: {deployment.name}")
                    stack_name = deployment.stack_name # Use stack name from record
                else:
                    log_message(db, "WARNING", f"Deployment {deployment_id} not found")
            else:
                # Fallback: Create deployment if not provided (legacy support)
                from app.models import User
                user = db.execute(select(User).where(User.email == job.triggered_by)).scalar_one_or_none()
                
                if user:
                    deployment = Deployment(
                        name=resource_name,
                        plugin_id=plugin_id,
                        version=version,
                        status=DeploymentStatus.PROVISIONING,
                        user_id=user.id,
                        inputs=inputs,
                        stack_name=stack_name,
                        cloud_provider=plugin_version.manifest.get("cloud_provider", "unknown"),
                        region=inputs.get("location", "unknown")
                    )
                    db.add(deployment)
                    db.commit()
                    log_message(db, "INFO", f"Created deployment record: {deployment.name}")

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
                # Find credential for this provider
                result = db.execute(
                    select(CloudCredential).where(CloudCredential.provider == deployment.cloud_provider)
                ).first()
                
                if result:
                    cred_record = result[0]
                    try:
                        credentials = crypto_service.decrypt(cred_record.encrypted_data)
                        print(f"[INFO] Loaded credentials for {deployment.cloud_provider}")
                    except Exception as e:
                        print(f"[WARNING] Failed to decrypt credentials: {str(e)}")
            
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
