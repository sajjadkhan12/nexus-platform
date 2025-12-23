"""Celery worker entry point"""
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import celery_app and all tasks to register them
from app.workers import celery_app

# Import all task modules to ensure they're registered
from app.workers import (
    infrastructure,
    microservice,
    cleanup
)

if __name__ == "__main__":
    celery_app.start()
