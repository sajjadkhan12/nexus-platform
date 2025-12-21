"""
GitHub Actions service for CI/CD status tracking
"""
import hmac
import hashlib
import json
from typing import Optional, Dict, List
import requests
from app.config import settings
from app.logger import logger


class GitHubActionsService:
    """Service for tracking GitHub Actions CI/CD status"""
    
    def __init__(self):
        self.github_api_base = "https://api.github.com"
        self.webhook_secret = getattr(settings, 'GITHUB_WEBHOOK_SECRET', '')
    
    def _get_github_token(self, user_github_token: Optional[str] = None) -> str:
        """Get GitHub token, preferring user token over platform token"""
        if user_github_token:
            return user_github_token
        return settings.GITHUB_TOKEN if hasattr(settings, 'GITHUB_TOKEN') else ""
    
    def verify_webhook_signature(self, payload_body: bytes, signature_header: str) -> bool:
        """
        Verify GitHub webhook signature.
        
        Args:
            payload_body: Raw request body bytes
            signature_header: X-Hub-Signature-256 header value
            
        Returns:
            True if signature is valid, False otherwise
        """
        if not self.webhook_secret:
            logger.warning("GitHub webhook secret not configured, skipping signature verification")
            return True  # Allow if secret not configured (development)
        
        if not signature_header:
            return False
        
        # Extract signature from header (format: sha256=...)
        if not signature_header.startswith("sha256="):
            return False
        
        signature = signature_header[7:]  # Remove "sha256=" prefix
        
        # Calculate expected signature
        expected_signature = hmac.new(
            self.webhook_secret.encode('utf-8'),
            payload_body,
            hashlib.sha256
        ).hexdigest()
        
        # Constant-time comparison
        return hmac.compare_digest(signature, expected_signature)
    
    def parse_webhook_event(self, event_type: str, payload: Dict) -> Optional[Dict]:
        """
        Parse GitHub webhook event and extract relevant CI/CD information.
        
        Args:
            event_type: GitHub webhook event type (e.g., "workflow_run")
            payload: Webhook payload dictionary
            
        Returns:
            Dictionary with parsed CI/CD status information or None
        """
        try:
            if event_type == "workflow_run":
                workflow_run = payload.get("workflow_run", {})
                
                return {
                    "run_id": workflow_run.get("id"),
                    "status": workflow_run.get("status"),  # queued, in_progress, completed
                    "conclusion": workflow_run.get("conclusion"),  # success, failure, cancelled, etc.
                    "workflow_name": workflow_run.get("name"),
                    "repository": workflow_run.get("repository", {}).get("full_name"),
                    "html_url": workflow_run.get("html_url"),
                    "created_at": workflow_run.get("created_at"),
                    "updated_at": workflow_run.get("updated_at"),
                    "head_branch": workflow_run.get("head_branch"),
                }
            elif event_type == "workflow_job":
                job = payload.get("workflow_job", {})
                
                return {
                    "run_id": job.get("run_id"),
                    "job_id": job.get("id"),
                    "status": job.get("status"),  # queued, in_progress, completed
                    "conclusion": job.get("conclusion"),  # success, failure, cancelled, etc.
                    "name": job.get("name"),
                    "repository": job.get("repository", {}).get("full_name"),
                    "html_url": job.get("html_url"),
                    "created_at": job.get("created_at"),
                    "updated_at": job.get("updated_at"),
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error parsing webhook event: {e}")
            return None
    
    def get_workflow_status_from_webhook(self, webhook_data: Dict) -> Dict:
        """
        Convert webhook data to deployment CI/CD status format.
        
        Args:
            webhook_data: Parsed webhook data from parse_webhook_event
            
        Returns:
            Dictionary with ci_cd_status, ci_cd_run_id, ci_cd_run_url
        """
        status = webhook_data.get("status", "").lower()
        conclusion = webhook_data.get("conclusion", "").lower() if webhook_data.get("conclusion") else None
        
        # Map GitHub status/conclusion to our CI/CD status
        if status == "queued":
            ci_cd_status = "pending"
        elif status == "in_progress":
            ci_cd_status = "running"
        elif status == "completed":
            if conclusion == "success":
                ci_cd_status = "success"
            elif conclusion == "failure" or conclusion == "cancelled":
                ci_cd_status = "failed" if conclusion == "failure" else "cancelled"
            else:
                ci_cd_status = "failed"  # Default for unknown conclusions
        else:
            ci_cd_status = "pending"  # Default
        
        return {
            "ci_cd_status": ci_cd_status,
            "ci_cd_run_id": webhook_data.get("run_id"),
            "ci_cd_run_url": webhook_data.get("html_url"),
        }
    
    def get_workflow_runs(
        self,
        repo_full_name: str,
        user_github_token: str,
        branch: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict]:
        """
        Get latest workflow runs for a repository.
        
        Args:
            repo_full_name: Repository full name (e.g., "username/repo-name")
            user_github_token: User's GitHub token
            branch: Branch name to filter by (optional)
            limit: Maximum number of runs to return
            
        Returns:
            List of workflow run dictionaries
        """
        try:
            api_url = f"{self.github_api_base}/repos/{repo_full_name}/actions/runs"
            headers = {
                "Authorization": f"token {user_github_token}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            params = {"per_page": limit}
            if branch:
                params["branch"] = branch
            
            response = requests.get(api_url, headers=headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                return data.get("workflow_runs", [])
            else:
                logger.error(f"Failed to get workflow runs: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"Error getting workflow runs: {e}")
            return []
    
    def get_workflow_run_status(
        self,
        repo_full_name: str,
        run_id: int,
        user_github_token: str
    ) -> Optional[Dict]:
        """
        Get status of a specific workflow run.
        
        Args:
            repo_full_name: Repository full name
            run_id: Workflow run ID
            user_github_token: User's GitHub token
            
        Returns:
            Workflow run information dictionary or None
        """
        try:
            api_url = f"{self.github_api_base}/repos/{repo_full_name}/actions/runs/{run_id}"
            headers = {
                "Authorization": f"token {user_github_token}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            response = requests.get(api_url, headers=headers)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get workflow run: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting workflow run status: {e}")
            return None
    
    def get_latest_workflow_status(
        self,
        repo_full_name: str,
        user_github_token: str,
        branch: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Get the latest workflow run status for a repository.
        
        Args:
            repo_full_name: Repository full name
            user_github_token: User's GitHub token
            branch: Branch name (optional, defaults to default branch)
            
        Returns:
            Dictionary with ci_cd_status, ci_cd_run_id, ci_cd_run_url or None
        """
        try:
            runs = self.get_workflow_runs(repo_full_name, user_github_token, branch, limit=1)
            
            if not runs:
                return None
            
            latest_run = runs[0]
            status = latest_run.get("status", "").lower()
            conclusion = latest_run.get("conclusion", "").lower() if latest_run.get("conclusion") else None
            
            # Map to our CI/CD status
            if status == "queued":
                ci_cd_status = "pending"
            elif status == "in_progress":
                ci_cd_status = "running"
            elif status == "completed":
                if conclusion == "success":
                    ci_cd_status = "success"
                elif conclusion == "failure":
                    ci_cd_status = "failed"
                elif conclusion == "cancelled":
                    ci_cd_status = "cancelled"
                else:
                    ci_cd_status = "failed"
            else:
                ci_cd_status = "pending"
            
            return {
                "ci_cd_status": ci_cd_status,
                "ci_cd_run_id": latest_run.get("id"),
                "ci_cd_run_url": latest_run.get("html_url"),
            }
            
        except Exception as e:
            logger.error(f"Error getting latest workflow status: {e}")
            return None


# Singleton instance
github_actions_service = GitHubActionsService()

