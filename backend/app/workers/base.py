"""Base task class with common functionality for all Celery tasks"""
from sqlalchemy.orm import Session
from app.logger import logger
from app.models import JobLog, JobStatus
from app.workers.db import get_sync_db_session


class BaseTask:
    """Base class for all Celery tasks with common functionality"""
    
    def __init__(self, job_id: str = None):
        self.job_id = job_id
        self.db = None
    
    def __enter__(self):
        """Context manager entry"""
        self.db = get_sync_db_session()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if self.db:
            self.db.close()
    
    def log_message(self, level: str, message: str):
        """Log message to both JobLog and server log"""
        if self.job_id and self.db:
            try:
                log = JobLog(job_id=self.job_id, level=level, message=message)
                self.db.add(log)
                self.db.commit()
            except Exception as e:
                logger.warning(f"Failed to write job log: {e}")
        
        # Log to server.log
        log_func = getattr(logger, level.lower(), logger.info)
        log_func(f"[Job {self.job_id or 'N/A'}] {message}")
    
    def update_job_status(self, status: JobStatus, error_message: str = None, error_state: str = None):
        """Update job status"""
        if not self.job_id or not self.db:
            return
        
        from app.models import Job
        from sqlalchemy import select
        
        try:
            job = self.db.execute(select(Job).where(Job.id == self.job_id)).scalar_one()
            job.status = status
            if error_message:
                job.error_message = error_message
            if error_state:
                job.error_state = error_state
            self.db.commit()
        except Exception as e:
            logger.error(f"Failed to update job status: {e}")

