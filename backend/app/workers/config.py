"""Celery configuration"""
import sys
import platform
from celery import Celery
from app.config import settings


def create_celery_app() -> Celery:
    """Create and configure Celery app"""
    celery_app = Celery(
        "idp_worker",
        broker=settings.CELERY_BROKER_URL,
        backend=settings.CELERY_RESULT_BACKEND
    )
    
    # Use 'solo' pool on macOS to avoid fork() issues
    # On Linux/Production, use 'prefork' or 'gevent' for better performance
    worker_pool = 'solo' if platform.system() == 'Darwin' else 'prefork'
    
    celery_app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        # Worker pool configuration
        worker_pool=worker_pool,
        # Retry configuration - disabled (no automatic retries)
        task_acks_late=True,
        task_reject_on_worker_lost=False,  # Changed to False to prevent infinite requeue on worker crash
        task_max_retries=0,  # No automatic retries - jobs fail immediately
        # Task time limits
        task_time_limit=3600,  # Hard time limit: 1 hour
        task_soft_time_limit=3300,  # Soft time limit: 55 minutes (allows cleanup)
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
    
    return celery_app

