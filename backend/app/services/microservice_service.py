"""
Microservice provisioning service
Handles repository creation from templates and GitHub operations
"""
import shutil
import re
from pathlib import Path
from typing import Optional, Dict, Tuple
import requests
from app.config import settings
from app.logger import logger
from app.services.git_service import GitService


class MicroserviceService:
    """Service for microservice repository creation and management"""
    
    def __init__(self):
        self.git_service = GitService()
        self.github_api_base = "https://api.github.com"
    
    def _get_github_token(self, user_github_token: Optional[str] = None) -> str:
        """Get GitHub token, preferring user token over platform token"""
        if user_github_token:
            return user_github_token
        return settings.GITHUB_TOKEN if hasattr(settings, 'GITHUB_TOKEN') else ""
    
    def _validate_repo_name(self, name: str) -> str:
        """
        Validate and sanitize repository name according to GitHub rules.
        GitHub repo names must:
        - Be alphanumeric, hyphens, underscores, or dots
        - Not start or end with a dot
        - Not be longer than 100 characters
        - Not contain consecutive dots
        """
        # Remove invalid characters, keep alphanumeric, hyphens, underscores, dots
        sanitized = re.sub(r'[^a-zA-Z0-9._-]', '-', name)
        # Remove consecutive dots
        sanitized = re.sub(r'\.{2,}', '.', sanitized)
        # Remove leading/trailing dots and hyphens
        sanitized = sanitized.strip('.-_')
        # Limit length
        if len(sanitized) > 100:
            sanitized = sanitized[:100]
        # Ensure it's not empty
        if not sanitized:
            sanitized = "microservice"
        return sanitized
    
    def extract_template_subdirectory(self, repo_path: Path, template_path: str, target_dir: Path) -> Path:
        """
        Extract a specific subdirectory from a cloned repository.
        
        Args:
            repo_path: Path to cloned repository
            template_path: Subdirectory path to extract (e.g., "python-service")
            target_dir: Directory to extract to
            
        Returns:
            Path to extracted template directory
        """
        try:
            source_dir = repo_path / template_path
            if not source_dir.exists():
                raise Exception(f"Template path '{template_path}' not found in repository")
            
            # Clean target directory
            if target_dir.exists():
                shutil.rmtree(target_dir)
            target_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy entire subdirectory
            shutil.copytree(source_dir, target_dir, dirs_exist_ok=True)
            
            logger.info(f"Extracted template '{template_path}' to {target_dir}")
            return target_dir
            
        except Exception as e:
            logger.error(f"Failed to extract template subdirectory: {e}")
            raise
    
    def create_github_repository(
        self,
        repo_name: str,
        user_github_token: str,
        description: Optional[str] = None,
        private: bool = False,
        organization: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        Create a new GitHub repository using GitHub API.
        
        Args:
            repo_name: Repository name (will be validated)
            user_github_token: User's GitHub personal access token
            description: Repository description
            private: Whether repository should be private
            organization: Organization name (if creating in org, otherwise creates in user's account)
            
        Returns:
            Tuple of (repository_url, repository_full_name)
        """
        try:
            # Validate and sanitize repo name
            repo_name = self._validate_repo_name(repo_name)
            
            # Determine API endpoint
            if organization:
                api_url = f"{self.github_api_base}/orgs/{organization}/repos"
            else:
                api_url = f"{self.github_api_base}/user/repos"
            
            # Prepare repository data
            repo_data = {
                "name": repo_name,
                "description": description or f"Microservice: {repo_name}",
                "private": private,
                "auto_init": False,  # We'll push code ourselves
            }
            
            # Make API request
            headers = {
                "Authorization": f"token {user_github_token}",
                "Accept": "application/vnd.github.v3+json",
                "Content-Type": "application/json"
            }
            
            logger.info(f"Creating GitHub repository: {repo_name} (org: {organization or 'user'})")
            response = requests.post(api_url, json=repo_data, headers=headers)
            
            if response.status_code == 201:
                repo_info = response.json()
                repo_url = repo_info.get("clone_url", "")
                full_name = repo_info.get("full_name", "")
                logger.info(f"Successfully created repository: {full_name}")
                return repo_url, full_name
            elif response.status_code == 422:
                # Repository might already exist
                error_data = response.json()
                errors = error_data.get("errors", [])
                if any("already exists" in str(err).lower() for err in errors):
                    # Try to get existing repository
                    if organization:
                        api_url = f"{self.github_api_base}/repos/{organization}/{repo_name}"
                    else:
                        # Need to get username first
                        user_response = requests.get(
                            f"{self.github_api_base}/user",
                            headers=headers
                        )
                        if user_response.status_code == 200:
                            username = user_response.json().get("login", "")
                            api_url = f"{self.github_api_base}/repos/{username}/{repo_name}"
                    
                    get_response = requests.get(api_url, headers=headers)
                    if get_response.status_code == 200:
                        repo_info = get_response.json()
                        repo_url = repo_info.get("clone_url", "")
                        full_name = repo_info.get("full_name", "")
                        logger.warning(f"Repository already exists, using existing: {full_name}")
                        return repo_url, full_name
                
                raise Exception(f"Failed to create repository: {error_data.get('message', 'Unknown error')}")
            else:
                error_msg = response.text
                logger.error(f"Failed to create repository: {response.status_code} - {error_msg}")
                raise Exception(f"GitHub API error: {response.status_code} - {error_msg}")
                
        except requests.RequestException as e:
            logger.error(f"Network error creating repository: {e}")
            raise Exception(f"Failed to communicate with GitHub API: {str(e)}")
        except Exception as e:
            logger.error(f"Error creating repository: {e}")
            raise
    
    def initialize_and_push_repository(
        self,
        source_dir: Path,
        repo_url: str,
        user_github_token: str,
        commit_message: str = "Initial commit from microservice template"
    ) -> None:
        """
        Initialize a git repository in source_dir and push to GitHub.
        
        Args:
            source_dir: Directory containing the microservice code
            repo_url: GitHub repository URL to push to
            user_github_token: User's GitHub token for authentication
            commit_message: Commit message for initial commit
        """
        try:
            from git import Repo, GitCommandError
            
            # Get authenticated URL
            auth_url = self.git_service._get_authenticated_url(repo_url, user_github_token)
            
            # Initialize git repository if not already
            repo = None
            if (source_dir / ".git").exists():
                repo = Repo(str(source_dir))
            else:
                repo = Repo.init(str(source_dir))
            
            # Add all files
            repo.git.add(A=True)
            
            # Check if there are changes to commit
            if repo.is_dirty(untracked_files=True) or len(list(repo.index.diff(None))) > 0:
                # Configure git user (required for commit)
                repo.config_writer().set_value("user", "name", "IDP Platform").release()
                repo.config_writer().set_value("user", "email", "idp@platform.local").release()
                
                # Commit
                repo.index.commit(commit_message)
                logger.info(f"Committed changes: {commit_message}")
            
            # Add remote if not exists
            remote_name = "origin"
            if remote_name not in [r.name for r in repo.remotes]:
                repo.create_remote(remote_name, auth_url)
            else:
                existing_remote = repo.remotes[remote_name]
                existing_remote.set_url(auth_url)
            
            # Push to GitHub
            logger.info(f"Pushing to repository: {repo_url}")
            repo.git.push(remote_name, "HEAD:main", force=True)
            
            # If main branch doesn't exist, try master
            try:
                repo.git.push(remote_name, "HEAD:master", force=True)
            except GitCommandError:
                pass  # master branch might not exist, that's okay
            
            logger.info(f"Successfully pushed code to {repo_url}")
            
        except Exception as e:
            logger.error(f"Failed to push repository: {e}")
            raise
    
    def create_repository_from_template(
        self,
        template_repo_url: str,
        template_path: str,
        repo_name: str,
        user_github_token: str,
        description: Optional[str] = None,
        organization: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        Complete flow: Clone template, extract subdirectory, create repo, push code.
        
        Args:
            template_repo_url: URL to template repository
            template_path: Subdirectory path in template (e.g., "python-service")
            repo_name: Name for the new repository
            user_github_token: User's GitHub token
            description: Repository description
            organization: Organization name (optional)
            
        Returns:
            Tuple of (repository_url, repository_full_name)
        """
        import tempfile
        
        temp_dir = Path(tempfile.mkdtemp(prefix="microservice_template_"))
        
        try:
            # Step 1: Clone template repository
            logger.info(f"Cloning template repository: {template_repo_url}")
            cloned_repo = self.git_service.clone_repository(
                template_repo_url,
                "main",  # Default branch, could be configurable
                temp_dir / "template"
            )
            
            # Step 2: Extract template subdirectory
            logger.info(f"Extracting template subdirectory: {template_path}")
            extracted_dir = temp_dir / "extracted"
            self.extract_template_subdirectory(cloned_repo, template_path, extracted_dir)
            
            # Step 3: Create GitHub repository
            logger.info(f"Creating GitHub repository: {repo_name}")
            repo_url, repo_full_name = self.create_github_repository(
                repo_name=repo_name,
                user_github_token=user_github_token,
                description=description,
                organization=organization
            )
            
            # Step 4: Push code to new repository
            logger.info(f"Pushing code to new repository: {repo_url}")
            self.initialize_and_push_repository(
                source_dir=extracted_dir,
                repo_url=repo_url,
                user_github_token=user_github_token,
                commit_message=f"Initial commit: {repo_name} from template {template_path}"
            )
            
            # Step 5: Set up webhook for CI/CD status updates (if configured)
            # Since user's token has all permissions, we can create webhooks automatically
            try:
                webhook_base_url = getattr(settings, 'WEBHOOK_BASE_URL', '')
                webhook_secret = getattr(settings, 'GITHUB_WEBHOOK_SECRET', '')
                
                if webhook_base_url:
                    webhook_url = f"{webhook_base_url.rstrip('/')}/api/v1/webhooks/github"
                    logger.info(f"Creating webhook for {repo_full_name}...")
                    self.create_webhook(repo_full_name, user_github_token, webhook_url, webhook_secret)
                    logger.info(f"✅ Webhook created successfully for {repo_full_name}")
                else:
                    logger.info("WEBHOOK_BASE_URL not configured, skipping automatic webhook creation")
                    logger.info("You can set up webhooks manually or run: python scripts/setup_github_webhook.py --repo {repo_full_name}")
            except Exception as e:
                logger.warning(f"Could not create webhook automatically: {e}")
                logger.info("Webhook can be set up manually later using the setup script")
            
            return repo_url, repo_full_name
            
        finally:
            # Cleanup
            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)
    
    def create_webhook(
        self,
        repo_full_name: str,
        user_github_token: str,
        webhook_url: str,
        webhook_secret: Optional[str] = None
    ) -> Dict:
        """
        Create a GitHub webhook for CI/CD status updates.
        
        Args:
            repo_full_name: Repository full name (e.g., "username/repo-name")
            user_github_token: User's GitHub token (needs admin permissions)
            webhook_url: URL where webhooks should be sent
            webhook_secret: Optional webhook secret for verification
            
        Returns:
            Webhook creation response dictionary
        """
        try:
            api_url = f"{self.github_api_base}/repos/{repo_full_name}/hooks"
            
            headers = {
                "Authorization": f"token {user_github_token}",
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
            
            response = requests.post(api_url, json=webhook_data, headers=headers)
            
            if response.status_code == 201:
                logger.info(f"Successfully created webhook for {repo_full_name}")
                return response.json()
            elif response.status_code == 422:
                # Webhook might already exist
                error_data = response.json()
                logger.warning(f"Webhook may already exist for {repo_full_name}: {error_data}")
                return error_data
            else:
                error_msg = response.text
                logger.error(f"Failed to create webhook: {response.status_code} - {error_msg}")
                raise Exception(f"GitHub API error: {response.status_code} - {error_msg}")
                
        except requests.RequestException as e:
            logger.error(f"Network error creating webhook: {e}")
            raise Exception(f"Failed to communicate with GitHub API: {str(e)}")
        except Exception as e:
            logger.error(f"Error creating webhook: {e}")
            raise
    
    def get_repository_info(self, repo_full_name: str, user_github_token: str) -> Dict:
        """
        Get repository information from GitHub API.
        
        Args:
            repo_full_name: Repository full name (e.g., "username/repo-name")
            user_github_token: User's GitHub token
            
        Returns:
            Dictionary with repository information
        """
        try:
            api_url = f"{self.github_api_base}/repos/{repo_full_name}"
            headers = {
                "Authorization": f"token {user_github_token}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            response = requests.get(api_url, headers=headers)
            
            if response.status_code == 200:
                return response.json()
            else:
                raise Exception(f"Failed to get repository info: {response.status_code} - {response.text}")
                
        except Exception as e:
            logger.error(f"Error getting repository info: {e}")
            raise
    
    def delete_github_repository(self, repo_full_name: str, user_github_token: str) -> None:
        """
        Delete a GitHub repository using GitHub API.
        
        Args:
            repo_full_name: Repository full name (e.g., "org/repo-name" or "username/repo-name")
            user_github_token: User's GitHub token (needs delete permissions)
        """
        try:
            api_url = f"{self.github_api_base}/repos/{repo_full_name}"
            headers = {
                "Authorization": f"token {user_github_token}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            logger.info(f"Deleting GitHub repository: {repo_full_name}")
            response = requests.delete(api_url, headers=headers)
            
            if response.status_code == 204:
                logger.info(f"Successfully deleted repository: {repo_full_name}")
            elif response.status_code == 404:
                logger.warning(f"Repository {repo_full_name} does not exist (may have been already deleted)")
            elif response.status_code == 403:
                error_msg = "Insufficient permissions to delete repository"
                logger.error(f"{error_msg}: {repo_full_name}")
                raise Exception(f"{error_msg}. The GitHub token needs 'delete_repo' scope.")
            else:
                error_msg = response.text
                logger.error(f"Failed to delete repository {repo_full_name}: {response.status_code} - {error_msg}")
                raise Exception(f"GitHub API error: {response.status_code} - {error_msg}")
                
        except requests.RequestException as e:
            logger.error(f"Network error deleting repository: {e}")
            raise Exception(f"Failed to communicate with GitHub API: {str(e)}")
        except Exception as e:
            logger.error(f"Error deleting repository: {e}")
            raise


# Singleton instance
microservice_service = MicroserviceService()

