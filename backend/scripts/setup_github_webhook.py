"""
Script to automatically set up GitHub webhook for CI/CD status updates.
Uses the GitHub token from environment to create webhooks in repositories.

This script can:
1. Create a webhook in the template repository (idp-templates)
2. Create webhooks in user repositories (if needed)
3. List existing webhooks
"""
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import requests
from app.config import settings
from app.logger import logger


def get_webhook_url() -> str:
    """Get the webhook URL for this platform"""
    webhook_base = getattr(settings, 'WEBHOOK_BASE_URL', '')
    if webhook_base:
        # If base URL is provided, append the webhook path
        webhook_url = f"{webhook_base.rstrip('/')}/api/v1/webhooks/github"
        return webhook_url
    
    # Try to construct from API_V1_STR or use default
    # In production, this should be set explicitly
    webhook_url = "https://your-platform-domain.com/api/v1/webhooks/github"
    logger.warning(f"WEBHOOK_BASE_URL not set, using placeholder: {webhook_url}")
    logger.warning("Please set WEBHOOK_BASE_URL in your .env file (e.g., https://your-domain.com)")
    
    return webhook_url


def create_webhook(repo_full_name: str, github_token: str, webhook_url: str, webhook_secret: str = None) -> dict:
    """
    Create a webhook in a GitHub repository.
    
    Args:
        repo_full_name: Repository full name (e.g., "owner/repo")
        github_token: GitHub personal access token
        webhook_url: URL where webhooks should be sent
        webhook_secret: Optional webhook secret for verification
        
    Returns:
        Webhook creation response
    """
    api_url = f"https://api.github.com/repos/{repo_full_name}/hooks"
    
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json"
    }
    
    webhook_data = {
        "name": "web",
        "active": True,
        "events": ["workflow_run"],  # Only workflow_run events for CI/CD
        "config": {
            "url": webhook_url,
            "content_type": "json",
            "insecure_ssl": "0"  # Use HTTPS
        }
    }
    
    # Add secret if provided
    if webhook_secret:
        webhook_data["config"]["secret"] = webhook_secret
    
    try:
        response = requests.post(api_url, json=webhook_data, headers=headers)
        
        if response.status_code == 201:
            logger.info(f"✅ Webhook created successfully for {repo_full_name}")
            return response.json()
        elif response.status_code == 422:
            # Webhook might already exist
            error_data = response.json()
            if "already exists" in str(error_data).lower():
                logger.warning(f"⚠️  Webhook already exists for {repo_full_name}")
                # Try to get existing webhooks
                return list_webhooks(repo_full_name, github_token)
            else:
                logger.error(f"❌ Failed to create webhook: {error_data}")
                raise Exception(f"Failed to create webhook: {error_data}")
        else:
            logger.error(f"❌ Failed to create webhook: {response.status_code} - {response.text}")
            raise Exception(f"GitHub API error: {response.status_code} - {response.text}")
            
    except requests.RequestException as e:
        logger.error(f"❌ Network error creating webhook: {e}")
        raise


def list_webhooks(repo_full_name: str, github_token: str) -> list:
    """
    List existing webhooks for a repository.
    
    Args:
        repo_full_name: Repository full name
        github_token: GitHub token
        
    Returns:
        List of webhooks
    """
    api_url = f"https://api.github.com/repos/{repo_full_name}/hooks"
    
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    try:
        response = requests.get(api_url, headers=headers)
        
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Failed to list webhooks: {response.status_code} - {response.text}")
            return []
            
    except Exception as e:
        logger.error(f"Error listing webhooks: {e}")
        return []


def setup_template_repo_webhook():
    """
    Set up webhook for the template repository (idp-templates).
    This is useful for testing, but typically webhooks should be set up
    in individual user repositories when they're created.
    """
    github_token = settings.GITHUB_TOKEN if hasattr(settings, 'GITHUB_TOKEN') else ""
    webhook_secret = settings.GITHUB_WEBHOOK_SECRET if hasattr(settings, 'GITHUB_WEBHOOK_SECRET') else None
    template_repo = settings.GITHUB_TEMPLATE_REPO_URL if hasattr(settings, 'GITHUB_TEMPLATE_REPO_URL') else ""
    
    if not github_token:
        logger.error("❌ GITHUB_TOKEN not configured")
        return False
    
    if not template_repo:
        logger.error("❌ GITHUB_TEMPLATE_REPO_URL not configured")
        return False
    
    # Extract repo name from URL
    # Format: https://github.com/owner/repo.git or https://github.com/owner/repo
    repo_full_name = template_repo.replace("https://github.com/", "").replace(".git", "").strip("/")
    
    webhook_url = get_webhook_url()
    
    logger.info(f"Setting up webhook for template repository: {repo_full_name}")
    logger.info(f"Webhook URL: {webhook_url}")
    
    try:
        result = create_webhook(repo_full_name, github_token, webhook_url, webhook_secret)
        logger.info(f"✅ Webhook setup complete: {result.get('url', 'N/A')}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to set up webhook: {e}")
        return False


def main():
    """Main function to set up webhooks"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Set up GitHub webhooks for CI/CD status updates")
    parser.add_argument(
        "--repo",
        type=str,
        help="Repository full name (e.g., 'owner/repo') to set up webhook for"
    )
    parser.add_argument(
        "--list",
        type=str,
        help="List webhooks for a repository (provide repo full name)"
    )
    parser.add_argument(
        "--template",
        action="store_true",
        help="Set up webhook for the template repository (idp-templates)"
    )
    
    args = parser.parse_args()
    
    github_token = settings.GITHUB_TOKEN if hasattr(settings, 'GITHUB_TOKEN') else ""
    
    if not github_token:
        logger.error("❌ GITHUB_TOKEN not configured in environment")
        logger.info("Please set GITHUB_TOKEN in your .env file")
        return
    
    webhook_url = get_webhook_url()
    webhook_secret = settings.GITHUB_WEBHOOK_SECRET if hasattr(settings, 'GITHUB_WEBHOOK_SECRET') else None
    
    if args.list:
        logger.info(f"Listing webhooks for {args.list}...")
        webhooks = list_webhooks(args.list, github_token)
        if webhooks:
            for webhook in webhooks:
                logger.info(f"  - {webhook.get('name', 'web')}: {webhook.get('config', {}).get('url', 'N/A')}")
        else:
            logger.info("  No webhooks found")
    
    elif args.repo:
        logger.info(f"Setting up webhook for {args.repo}...")
        try:
            create_webhook(args.repo, github_token, webhook_url, webhook_secret)
        except Exception as e:
            logger.error(f"Failed: {e}")
    
    elif args.template:
        setup_template_repo_webhook()
    
    else:
        logger.info("GitHub Webhook Setup")
        logger.info("=" * 50)
        logger.info("Usage:")
        logger.info("  --template          Set up webhook for template repository")
        logger.info("  --repo OWNER/REPO   Set up webhook for specific repository")
        logger.info("  --list OWNER/REPO   List existing webhooks")
        logger.info("")
        logger.info("Note: Webhooks are typically created automatically when")
        logger.info("microservice repositories are created. This script is for")
        logger.info("manual setup or testing.")


if __name__ == "__main__":
    main()

