from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.config import settings
from app.api.v1 import auth, users, deployments, roles, permissions, groups
from app.api import plugins, credentials, provision
from app.database import engine, Base
from app.logger import logger
import time

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    # Skip logging for well-known endpoints to reduce overhead
    if not request.url.path.startswith("/.well-known"):
        logger.info(f"{request.method} {request.url.path} - {response.status_code} - {process_time:.3f}s")
    return response

# Set all CORS enabled origins
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/storage", StaticFiles(directory="storage"), name="storage")

# Include routers
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(users.router, prefix=settings.API_V1_STR)

app.include_router(deployments.router, prefix=settings.API_V1_STR)
app.include_router(roles.router, prefix=settings.API_V1_STR)
app.include_router(permissions.router, prefix=settings.API_V1_STR)
app.include_router(groups.router, prefix=settings.API_V1_STR)
from app.api.v1 import notifications
app.include_router(notifications.router, prefix=settings.API_V1_STR)


# Plugin system routers
app.include_router(plugins.router, prefix=settings.API_V1_STR)
app.include_router(credentials.router, prefix=settings.API_V1_STR)
app.include_router(provision.router, prefix=settings.API_V1_STR)

# OIDC Provider routers
from app.api import oidc, aws_oidc, gcp_oidc, azure_oidc
app.include_router(oidc.router)  # No prefix - these are root-level endpoints
app.include_router(aws_oidc.router)  # /aws/assume-role
app.include_router(gcp_oidc.router)  # /gcp/token
app.include_router(azure_oidc.router)  # /azure/token

from app.core.db_init import init_db as seed_db
from app.database import AsyncSessionLocal

@app.on_event("startup")
async def init_db():
    logger.info("Starting application initialization...")
    async with engine.begin() as conn:
        # await conn.run_sync(Base.metadata.drop_all) # WARNING: DELETES DATA
        await conn.run_sync(Base.metadata.create_all)
    
    # Seed database
    async with AsyncSessionLocal() as session:
        await seed_db(session)
    
    logger.info("Application initialized successfully!")
