"""Plugin management API - aggregated router"""
from fastapi import APIRouter
from . import upload, crud, versions, access

router = APIRouter(prefix="/plugins", tags=["Plugins"])

# Include all sub-routers
router.include_router(upload.router)
router.include_router(crud.router)
router.include_router(versions.router)
router.include_router(access.router)

