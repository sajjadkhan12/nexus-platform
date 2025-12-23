"""Deployment management API - aggregated router"""
from fastapi import APIRouter
from . import crud, cicd, tags, history, stats, cost

router = APIRouter(prefix="/deployments", tags=["deployments"])

# Include all sub-routers
router.include_router(crud.router)
router.include_router(cicd.router)
router.include_router(tags.router)
router.include_router(history.router)
router.include_router(stats.router)
router.include_router(cost.router)

