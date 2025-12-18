"""
FastAPI main application entry point for DevPlatform IDP
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from pathlib import Path

from app.config import settings
from app.logger import logger
from app.core.db_init import init_db
from app.core.audit_middleware import AuditLoggingMiddleware

# Import all API routers
from app.api.v1 import auth, users, roles, groups, permissions, audit, notifications, deployments
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
    
    # Initialize database tables and admin user
    try:
        from app.database import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            await init_db(db)
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}", exc_info=True)
        raise
    
    # Create storage directories
    plugins_storage = Path(settings.PLUGINS_STORAGE_PATH)
    plugins_storage.mkdir(parents=True, exist_ok=True)
    
    git_work_dir = Path(settings.GIT_WORK_DIR)
    git_work_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Storage directories created: {plugins_storage}, {git_work_dir}")
    
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
    openapi_url="/openapi.json"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
    """Simple health check endpoint"""
    return {"status": "healthy", "service": "DevPlatform IDP"}

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
