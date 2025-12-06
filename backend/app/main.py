from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
import time

from app.config import settings
from app.core.redis_client import RedisClient
from app.core.security_middleware import sanitize_error_message
from app.logger import logger  # Use centralized logger

# Import Routers
from app.api.v1 import auth, users, deployments, roles, permissions, groups, notifications
from app.api import (
    oidc,
    aws_oidc,
    gcp_oidc,
    azure_oidc,
    plugins,
    credentials,
    provision,
    oidc_tokens,
)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Security Middleware (add before other middleware)
from app.core.security_middleware import SecurityHeadersMiddleware, RateLimitMiddleware
app.add_middleware(SecurityHeadersMiddleware)
# Rate limiting - DISABLED for development
# 120 requests/min = 2 requests/sec, 5000/hour = ~83 requests/min average
# app.add_middleware(RateLimitMiddleware, requests_per_minute=120, requests_per_hour=5000)

# Request Logging Middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    logger.info(f"{request.method} {request.url.path} - {response.status_code} - {process_time:.3f}s")
    return response

# CORS - More restrictive configuration
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],  # Specific methods instead of *
        allow_headers=["Content-Type", "Authorization", "Accept"],  # Specific headers instead of *
        expose_headers=["Content-Type"],
        max_age=3600,
    )

# Static Files
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/storage", StaticFiles(directory="storage"), name="storage")

# Include V1 API Routers
app.include_router(auth.router, prefix=settings.API_V1_STR, tags=["auth"])
app.include_router(users.router, prefix=settings.API_V1_STR, tags=["users"])
app.include_router(deployments.router, prefix=settings.API_V1_STR, tags=["deployments"])
app.include_router(roles.router, prefix=settings.API_V1_STR, tags=["roles"])
app.include_router(permissions.router, prefix=settings.API_V1_STR, tags=["permissions"])
app.include_router(groups.router, prefix=settings.API_V1_STR, tags=["groups"])
app.include_router(notifications.router, prefix=settings.API_V1_STR, tags=["notifications"])
app.include_router(plugins.router, prefix=settings.API_V1_STR, tags=["plugins"])
app.include_router(credentials.router, prefix=settings.API_V1_STR, tags=["credentials"])
app.include_router(provision.router, prefix=settings.API_V1_STR, tags=["provision"])

# OIDC & Cloud Routers (Root level or specialized prefixes)
# .well-known endpoints must be at root
app.include_router(oidc.router, tags=["oidc"])

# OIDC test/token endpoints (used by OIDC test page)
app.include_router(oidc_tokens.router, tags=["oidc-test"])

# Cloud Integrations
app.include_router(aws_oidc.router, prefix="/api/v1", tags=["aws-integration"])
app.include_router(gcp_oidc.router, prefix="/api/v1", tags=["gcp-integration"])
app.include_router(azure_oidc.router, prefix="/api/v1", tags=["azure-integration"])

from app.core.db_init import init_db as seed_db
from app.database import AsyncSessionLocal

@app.on_event("startup")
async def startup_event():
    logger.info("Starting application initialization...")
    # Initialize Redis
    try:
        redis_client = RedisClient.get_instance()
        await redis_client.ping()
        logger.info("Redis connection established.")
    except Exception as e:
        logger.warning(f"Redis connection failed: {e}. Caching will not work.")

    # Initialize DB if needed (optional based on your flow)
    # await seed_db() 

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down application...")
    await RedisClient.close()

# Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler to sanitize error messages in production
    """
    is_production = not settings.DEBUG
    
    # Log full error details server-side
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    # Return sanitized error to client
    if isinstance(exc, HTTPException):
        # FastAPI HTTPExceptions are already handled, but we can sanitize the detail
        if is_production:
            sanitized_detail = sanitize_error_message(exc, is_production)
            return JSONResponse(
                status_code=exc.status_code,
                content={"detail": sanitized_detail}
            )
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail}
        )
    
    # For other exceptions, sanitize in production
    error_message = sanitize_error_message(exc, is_production)
    return JSONResponse(
        status_code=500,
        content={"detail": error_message}
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handle validation errors - these are safe to show to users
    """
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()}
    )
