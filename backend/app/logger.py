import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from app.config import settings

# Create logs directory - use absolute path relative to backend directory
backend_dir = Path(__file__).parent.parent
log_dir = backend_dir / "logs"
log_dir.mkdir(exist_ok=True)

# Log file path
log_file = log_dir / "server.log"

# Configure root logger - remove all existing handlers first
root_logger = logging.getLogger()
root_logger.handlers = []

# Create formatter
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# File handler with rotation (10MB per file, keep 5 backups)
# Only log WARNING and ERROR to server.log
file_handler = RotatingFileHandler(
    log_file,
    maxBytes=10 * 1024 * 1024,  # 10MB
    backupCount=5,
    encoding='utf-8'
)
file_handler.setLevel(logging.WARNING)  # Only WARNING and ERROR
file_handler.setFormatter(formatter)

# Only add file handler - NO console output
root_logger.addHandler(file_handler)
root_logger.setLevel(logging.INFO)  # Keep root level at INFO for console if needed

# Suppress noisy loggers
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
logging.getLogger("uvicorn.error").setLevel(logging.INFO)
# Suppress Casbin verbose policy logging
logging.getLogger("casbin").setLevel(logging.WARNING)
logging.getLogger("casbin.policy").setLevel(logging.WARNING)
logging.getLogger("casbin.role").setLevel(logging.WARNING)

# Main application logger
logger = logging.getLogger("devplatform")
logger.info(f"Logging initialized. Logs will be written to: {log_file.absolute()}")
