"""
FastAPI main application entry point for DevPlatform IDP
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from pathlib import Path
import json

from app.config import settings
from app.logger import logger
from app.core.db_init import init_db
from app.core.audit_middleware import AuditLoggingMiddleware

# Import all models to register them with Base for table creation
from app.models import *  # noqa: F403, F405

# Import all API routers
from app.api.v1 import auth, users, roles, groups, permissions, audit, notifications, deployments, organizations
from app.api import (
    plugins, 
    provision, 
    webhooks, 
    oidc, 
    aws_oidc, 
    azure_oidc, 
    gcp_oidc,
    credentials
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events
    """
    # Startup
    logger.info("Starting up DevPlatform IDP...")
    
    # Create database tables first (if they don't exist)
    try:
        from app.database import engine, Base
        
        logger.info("Creating database tables...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created/verified")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}", exc_info=True)
        raise
    
    # Create performance indexes (after tables are created)
    try:
        from app.database import AsyncSessionLocal
        from app.core.db_init import create_performance_indexes
        
        async with AsyncSessionLocal() as db:
            await create_performance_indexes(db)
    except Exception as e:
        logger.warning(f"Failed to create performance indexes (non-critical): {e}")
        # Don't raise - indexes are optional for functionality
    
    # Initialize database with default data (admin user, roles, permissions)
    try:
        from app.database import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            await init_db(db)
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}", exc_info=True)
        raise
    
    # Create storage directories
    plugins_storage = Path(settings.PLUGINS_STORAGE_PATH)
    plugins_storage.mkdir(parents=True, exist_ok=True)
    
    git_work_dir = Path(settings.GIT_WORK_DIR)
    git_work_dir.mkdir(parents=True, exist_ok=True)
    
    yield
    
    # Shutdown
    logger.info("Shutting down DevPlatform IDP...")


# Create FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    debug=settings.DEBUG,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    # Request size limits (10MB default, adjust as needed)
    max_request_size=10 * 1024 * 1024,  # 10MB
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
)

# Add audit logging middleware
app.add_middleware(AuditLoggingMiddleware)

# Mount static files for plugin storage and avatars
# Get the backend directory (parent of app directory)
backend_dir = Path(__file__).parent.parent

# Mount storage for plugins
storage_path = backend_dir / "storage"
if storage_path.exists():
    app.mount("/storage", StaticFiles(directory=str(storage_path)), name="storage")
    logger.info(f"Mounted /storage at {storage_path}")

# Mount static files for avatars and other assets
static_path = backend_dir / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")
    logger.info(f"Mounted /static at {static_path}")

# Health check endpoint
@app.get("/health")
async def health_check():
    """
    Health check endpoint that verifies all critical dependencies.
    Returns 200 if healthy, 503 if any dependency is unavailable.
    """
    from app.database import engine
    from sqlalchemy import text
    import asyncio
    
    health_status = {
        "status": "healthy",
        "service": "DevPlatform IDP",
        "checks": {}
    }
    overall_healthy = True
    
    # Check database connectivity
    try:
        async with engine.begin() as conn:
            result = await asyncio.wait_for(
                conn.execute(text("SELECT 1")),
                timeout=5.0
            )
            result.scalar()
        health_status["checks"]["database"] = "healthy"
    except Exception as e:
        health_status["checks"]["database"] = f"unhealthy: {str(e)}"
        overall_healthy = False
    
    # Check Redis (if available)
    try:
        from app.core.redis_client import RedisClient
        redis_client = RedisClient.get_instance()
        await asyncio.wait_for(redis_client.ping(), timeout=2.0)
        health_status["checks"]["redis"] = "healthy"
    except Exception as e:
        health_status["checks"]["redis"] = "unavailable"  # Redis is optional
        # Don't fail health check if Redis is down (it's optional)
    
    # Set overall status
    if not overall_healthy:
        health_status["status"] = "unhealthy"
        from fastapi import Response
        return Response(
            content=json.dumps(health_status),
            status_code=503,
            media_type="application/json"
        )
    
    return health_status

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Welcome to DevPlatform IDP API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }

# Include API v1 routers
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(users.router, prefix=settings.API_V1_STR)
app.include_router(roles.router, prefix=settings.API_V1_STR)
app.include_router(groups.router, prefix=settings.API_V1_STR)
app.include_router(permissions.router, prefix=settings.API_V1_STR)
app.include_router(audit.router, prefix=settings.API_V1_STR)
app.include_router(notifications.router, prefix=settings.API_V1_STR)
app.include_router(deployments.router, prefix=settings.API_V1_STR)
app.include_router(organizations.router, prefix=settings.API_V1_STR)
app.include_router(plugins.router, prefix=settings.API_V1_STR)
app.include_router(provision.router, prefix=settings.API_V1_STR)
app.include_router(credentials.router, prefix=settings.API_V1_STR)

# Include API routers (non-versioned, for webhooks from external services)
app.include_router(webhooks.router, prefix="/api")

# Include OIDC routers
app.include_router(oidc.router, prefix="/.well-known")
app.include_router(aws_oidc.router, prefix="/api/oidc/aws")
app.include_router(azure_oidc.router, prefix="/api/oidc/azure")
app.include_router(gcp_oidc.router, prefix="/api/oidc/gcp")

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler to catch and log all unhandled exceptions
    """
    logger.error(f"Unhandled exception on {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "path": request.url.path,
            "method": request.method
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
