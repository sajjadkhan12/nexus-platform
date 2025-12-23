"""Worker module initialization - registers all Celery tasks"""
from .config import create_celery_app
from . import infrastructure, microservice, cleanup

# Create Celery app
celery_app = create_celery_app()


@celery_app.task(name="provision_infrastructure", max_retries=0)
def provision_infrastructure(job_id: str, plugin_id: str, version: str, inputs: dict,
                            credential_name: str = None, deployment_id: str = None):
    """Celery task wrapper for infrastructure provisioning"""
    try:
        task = infrastructure.InfrastructureProvisionTask(job_id)
        return task.execute(plugin_id, version, inputs, credential_name, deployment_id)
    except Exception as e:
        # Ensure error is handled even if task.execute doesn't catch it
        from app.logger import logger
        logger.error(f"[CELERY TASK ERROR] provision_infrastructure failed for job {job_id}: {str(e)}", exc_info=True)
        # The task's _handle_error should have already handled this, but re-raise to ensure Celery marks it as failed
        raise


@celery_app.task(name="destroy_infrastructure")
def destroy_infrastructure(deployment_id: str):
    """Celery task wrapper for infrastructure destruction"""
    task = infrastructure.InfrastructureDestroyTask(deployment_id)
    return task.execute()


@celery_app.task(name="provision_microservice")
def provision_microservice(job_id: str, plugin_id: str, version: str, deployment_name: str,
                          user_id: str, deployment_id: str = None):
    """Celery task wrapper for microservice provisioning"""
    task = microservice.MicroserviceProvisionTask(job_id)
    return task.execute(plugin_id, version, deployment_name, user_id, deployment_id)


@celery_app.task(name="destroy_microservice")
def destroy_microservice(deployment_id: str):
    """Celery task wrapper for microservice destruction"""
    task = microservice.MicroserviceDestroyTask(deployment_id)
    return task.execute()


@celery_app.task(name="cleanup_stuck_deployments")
def cleanup_stuck_deployments():
    """Celery task wrapper for cleanup stuck deployments"""
    return cleanup.cleanup_stuck_deployments()


@celery_app.task(name="cleanup_expired_refresh_tokens")
def cleanup_expired_refresh_tokens():
    """Celery task wrapper for cleanup expired refresh tokens"""
    return cleanup.cleanup_expired_refresh_tokens()


@celery_app.task(name="poll_github_actions_status")
def poll_github_actions_status():
    """Celery task wrapper for polling GitHub Actions status"""
    return cleanup.poll_github_actions_status()

