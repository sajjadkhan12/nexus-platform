"""
GitHub webhook endpoints for CI/CD status updates
"""
from fastapi import APIRouter, Request, HTTPException, Header, status
from fastapi.responses import Response
from typing import Optional
import json
from datetime import datetime, timezone
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.logger import logger
from app.models import Deployment
from app.services.github_actions_service import github_actions_service

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/github")
async def github_webhook(
    request: Request,
    x_github_event: Optional[str] = Header(None, alias="X-GitHub-Event"),
    x_hub_signature_256: Optional[str] = Header(None, alias="X-Hub-Signature-256")
):
    """
    GitHub webhook endpoint for receiving CI/CD status updates.
    
    Handles workflow_run events to update deployment CI/CD status in real-time.
    """
    try:
        # Read request body
        body = await request.body()
        
        # Verify webhook signature if secret is configured
        if x_hub_signature_256:
            if not github_actions_service.verify_webhook_signature(body, x_hub_signature_256):
                logger.warning("Invalid webhook signature")
                raise HTTPException(status_code=401, detail="Invalid webhook signature")
        
        # Parse payload
        try:
            payload = json.loads(body.decode('utf-8'))
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON payload")
        
        # Only process workflow_run events
        if x_github_event != "workflow_run":
            # Return 200 for other events (we don't process them)
            return Response(status_code=200, content="Event type not processed")
        
        # Parse webhook event
        webhook_data = github_actions_service.parse_webhook_event(x_github_event, payload)
        
        if not webhook_data:
            logger.warning(f"Could not parse webhook event: {x_github_event}")
            return Response(status_code=200, content="Event not parsed")
        
        # Get repository full name
        repo_full_name = webhook_data.get("repository")
        if not repo_full_name:
            logger.warning("No repository information in webhook payload")
            return Response(status_code=200, content="No repository info")
        
        # Find deployment by repository name
        sync_db_url = settings.DATABASE_URL.replace("+asyncpg", "")
        if "postgresql://" not in sync_db_url and "postgresql+psycopg2://" not in sync_db_url:
            sync_db_url = sync_db_url.replace("postgresql:", "postgresql+psycopg2:")
        
        engine = create_engine(sync_db_url, echo=False)
        SessionLocal = sessionmaker(bind=engine)
        
        with SessionLocal() as db:
            # Find deployment with matching repository
            deployment = db.execute(
                select(Deployment).where(
                    Deployment.github_repo_name == repo_full_name,
                    Deployment.deployment_type == "microservice"
                )
            ).scalar_one_or_none()
            
            if not deployment:
                logger.info(f"No deployment found for repository: {repo_full_name}")
                return Response(status_code=200, content="Deployment not found")
            
            # Convert webhook data to CI/CD status
            ci_cd_status_data = github_actions_service.get_workflow_status_from_webhook(webhook_data)
            
            # Update deployment
            deployment.ci_cd_status = ci_cd_status_data.get("ci_cd_status")
            deployment.ci_cd_run_id = ci_cd_status_data.get("ci_cd_run_id")
            deployment.ci_cd_run_url = ci_cd_status_data.get("ci_cd_run_url")
            deployment.ci_cd_updated_at = datetime.now(timezone.utc)
            
            db.add(deployment)
            db.commit()
            
            logger.info(
                f"Updated CI/CD status for deployment {deployment.id}: "
                f"{deployment.ci_cd_status} (run_id: {deployment.ci_cd_run_id})"
            )
            
            return Response(status_code=200, content="Webhook processed successfully")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing GitHub webhook: {e}", exc_info=True)
        # Return 200 to prevent GitHub from retrying
        return Response(status_code=200, content=f"Error: {str(e)}")

