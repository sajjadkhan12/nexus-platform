"""Cleanup and maintenance tasks"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select, delete
from sqlalchemy.orm import Session

from app.workers.db import get_sync_db_session
from app.logger import logger
from app.config import settings

from app.models import Deployment, DeploymentStatus, Job, JobStatus, User, Notification, NotificationType
from app.models.rbac import RefreshToken
from app.services.github_actions_service import github_actions_service


def cleanup_stuck_deployments():
    """
    Periodic task to find and fix deployments stuck in PROVISIONING or UPDATING status.
    This handles cases where:
    1. Jobs failed but deployment status wasn't updated
    2. Jobs are in DEAD_LETTER but deployment is still PROVISIONING/UPDATING
    3. Deployments have been in PROVISIONING/UPDATING for too long with no job updates
    4. Rollback/update jobs failed but update_status wasn't reset
    """
    db = get_sync_db_session()
    try:
        # Find deployments stuck in PROVISIONING
        stuck_provisioning = db.execute(
            select(Deployment).where(
                Deployment.status == DeploymentStatus.PROVISIONING
            )
        ).scalars().all()
        
        # Find deployments stuck in UPDATING status (rollbacks/updates)
        stuck_updating = db.execute(
            select(Deployment).where(
                Deployment.update_status == "updating"
            )
        ).scalars().all()
        
        stuck_deployments = list(stuck_provisioning) + list(stuck_updating)
        
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
                    # Check if job is in a failed state
                    if job.status in [JobStatus.FAILED, JobStatus.DEAD_LETTER]:
                        should_fail = True
                        reason = f"Associated job is in {job.status} status"
                        if job.error_message:
                            reason += f": {job.error_message[:100]}"
                    # Check if job has been pending/running for too long
                    elif job.status == JobStatus.PENDING:
                        check_time = job.created_at if job.created_at else deployment.created_at
                        if check_time:
                            if check_time.tzinfo is None:
                                check_time = check_time.replace(tzinfo=timezone.utc)
                            if check_time < timeout_threshold:
                                should_fail = True
                                reason = f"Job has been PENDING for over 2 hours (created: {check_time})"
                    elif job.status == JobStatus.RUNNING:
                        check_time = job.created_at if job.created_at else deployment.created_at
                        if check_time:
                            if check_time.tzinfo is None:
                                check_time = check_time.replace(tzinfo=timezone.utc)
                            if check_time < timeout_threshold:
                                should_fail = True
                                reason = f"Job has been RUNNING for over 2 hours (created: {check_time})"
                else:
                    # No job found - if deployment is old, mark as failed
                    if deployment.created_at:
                        check_time = deployment.created_at
                        if check_time.tzinfo is None:
                            check_time = check_time.replace(tzinfo=timezone.utc)
                        if check_time < timeout_threshold:
                            should_fail = True
                            reason = f"No associated job found and deployment is over 2 hours old (created: {check_time})"
                
                # Check if this is a stuck update/rollback
                is_stuck_update = deployment.update_status == "updating"
                if is_stuck_update:
                    # Check if the update job exists and is failed
                    if job and job.status in [JobStatus.FAILED, JobStatus.DEAD_LETTER]:
                        should_fail = True
                        reason = f"Update job is in {job.status} status"
                        if job.error_message:
                            reason += f": {job.error_message[:100]}"
                    # Check if update has been running too long
                    elif deployment.last_update_attempted_at:
                        check_time = deployment.last_update_attempted_at
                        if check_time.tzinfo is None:
                            check_time = check_time.replace(tzinfo=timezone.utc)
                        if check_time < timeout_threshold:
                            should_fail = True
                            reason = f"Update has been in progress for over 2 hours (started: {check_time})"
                
                if should_fail:
                    if is_stuck_update:
                        logger.warning(f"Marking deployment {deployment.id} ({deployment.name}) update as FAILED: {reason}")
                        deployment.update_status = "update_failed"
                        deployment.last_update_error = reason[:500]  # Limit error message length
                    else:
                        logger.warning(f"Marking deployment {deployment.id} ({deployment.name}) as FAILED: {reason}")
                        deployment.status = DeploymentStatus.FAILED
                    db.add(deployment)
                    updated_count += 1
                    
                    # Create notification for user
                    try:
                        user = db.execute(
                            select(User).where(User.id == deployment.user_id)
                        ).scalar_one_or_none()
                        
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
    finally:
        db.close()


def cleanup_expired_refresh_tokens():
    """
    Periodic task to delete expired refresh tokens from the database.
    This prevents database bloat and improves security by removing stale tokens.
    """
    db = get_sync_db_session()
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
    finally:
        db.close()


def poll_github_actions_status():
    """
    Periodic task to poll GitHub Actions status for active microservice deployments.
    This serves as a fallback when webhooks are not available or fail.
    Runs periodically (e.g., every 60 seconds) via Celery beat.
    """
    db = get_sync_db_session()
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
        db.rollback()
    finally:
        db.close()

