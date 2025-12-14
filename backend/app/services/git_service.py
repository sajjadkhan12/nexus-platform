"""Git service for GitOps workflow"""
import os
import shutil
from pathlib import Path
from typing import Dict, Optional
try:
    import git
    from git import Repo, Remote
except ImportError:
    git = None
    Repo = None
    Remote = None
from app.config import settings
from app.logger import logger
import yaml
import re


class GitService:
    """Service for Git operations in GitOps workflow"""
    
    def __init__(self):
        self.work_dir = Path(settings.GIT_WORK_DIR if hasattr(settings, 'GIT_WORK_DIR') else "./storage/git-repos")
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.github_token = settings.GITHUB_TOKEN if hasattr(settings, 'GITHUB_TOKEN') else ""
    
    def _get_authenticated_url(self, repo_url: str) -> str:
        """Convert repo URL to authenticated HTTPS URL if token is available"""
        if not self.github_token:
            return repo_url
        
        # Handle different URL formats
        if repo_url.startswith("https://github.com/"):
            # Insert token into URL: https://token@github.com/org/repo.git
            url = repo_url.replace("https://", f"https://{self.github_token}@")
            return url
        elif repo_url.startswith("git@github.com:"):
            # Convert SSH to HTTPS with token
            url = repo_url.replace("git@github.com:", f"https://{self.github_token}@github.com/")
            return url
        else:
            # Assume it's already authenticated or public
            return repo_url
    
    def clone_repository(self, repo_url: str, branch: str, target_dir: Path) -> Path:
        """
        Clone a specific branch from a Git repository
        
        Args:
            repo_url: GitHub repository URL
            branch: Branch name to clone
            target_dir: Directory to clone into
            
        Returns:
            Path to cloned repository
        """
        try:
            # Clean target directory if it exists
            if target_dir.exists():
                shutil.rmtree(target_dir)
            target_dir.mkdir(parents=True, exist_ok=True)
            
            # Get authenticated URL
            auth_url = self._get_authenticated_url(repo_url)
            
            logger.info(f"Cloning repository {repo_url} branch {branch} to {target_dir}")
            
            # Clone with specific branch
            repo = Repo.clone_from(
                auth_url,
                str(target_dir),
                branch=branch,
                depth=1  # Shallow clone for faster performance
            )
            
            logger.info(f"Successfully cloned branch {branch} to {target_dir}")
            return target_dir
            
        except git.exc.GitCommandError as e:
            logger.error(f"Failed to clone repository: {e}")
            # If branch doesn't exist, try cloning main/master and then checking out
            if "not found" in str(e).lower() or "couldn't find remote ref" in str(e).lower():
                logger.warning(f"Branch {branch} not found, trying to clone default branch and checkout")
                try:
                    # Clone without specifying branch
                    repo = Repo.clone_from(auth_url, str(target_dir), depth=1)
                    # Try to checkout the branch
                    repo.git.checkout(branch)
                    logger.info(f"Successfully checked out branch {branch}")
                    return target_dir
                except Exception as e2:
                    logger.error(f"Failed to checkout branch {branch}: {e2}")
                    raise Exception(f"Branch {branch} not found in repository: {e2}")
            raise Exception(f"Failed to clone repository: {e}")
        except Exception as e:
            logger.error(f"Unexpected error cloning repository: {e}")
            raise
    
    def create_deployment_branch(self, repo_path: Path, template_branch: str, deployment_branch: str) -> None:
        """
        Create a new deployment branch from template branch
        
        Args:
            repo_path: Path to local repository
            template_branch: Source branch (template)
            deployment_branch: New branch name for deployment
        """
        try:
            repo = Repo(str(repo_path))
            
            # Ensure we're on the template branch
            if repo.active_branch.name != template_branch:
                repo.git.checkout(template_branch)
            
            # Create and checkout new branch
            if deployment_branch in [ref.name for ref in repo.references]:
                logger.warning(f"Branch {deployment_branch} already exists, checking it out")
                repo.git.checkout(deployment_branch)
            else:
                new_branch = repo.create_head(deployment_branch)
                new_branch.checkout()
                logger.info(f"Created and checked out deployment branch: {deployment_branch}")
            
        except Exception as e:
            logger.error(f"Failed to create deployment branch: {e}")
            raise
    
    def inject_user_values(self, repo_path: Path, inputs: Dict, manifest: Dict, stack_name: str) -> None:
        """
        Inject user-provided values into Pulumi configuration
        
        Args:
            repo_path: Path to local repository
            inputs: User-provided input values
            manifest: Plugin manifest with configuration mapping
            stack_name: Pulumi stack name
        """
        try:
            # Strategy 1: Create/update Pulumi.{stack}.yaml config file
            pulumi_config_file = repo_path / f"Pulumi.{stack_name}.yaml"
            
            # Read existing config if it exists
            config_data = {}
            if pulumi_config_file.exists():
                with open(pulumi_config_file, 'r') as f:
                    config_data = yaml.safe_load(f) or {}
            
            # Ensure config structure exists
            if 'config' not in config_data:
                config_data['config'] = {}
            
            # Get plugin ID from manifest for config namespace
            plugin_id = manifest.get('plugin_id', 'plugin')
            
            # Map user inputs to Pulumi config
            # Format: {plugin_id}:{key} = value
            for key, value in inputs.items():
                if value is not None and value != "":
                    config_key = f"{plugin_id}:{key}"
                    config_data['config'][config_key] = value
            
            # Write updated config file
            with open(pulumi_config_file, 'w') as f:
                yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)
            
            logger.info(f"Injected {len(inputs)} values into {pulumi_config_file}")
            
            # Strategy 2: Also try to inject into __main__.py if it has placeholder patterns
            main_py = repo_path / "__main__.py"
            if main_py.exists():
                self._inject_into_code(main_py, inputs)
            
        except Exception as e:
            logger.error(f"Failed to inject user values: {e}")
            raise
    
    def _inject_into_code(self, file_path: Path, inputs: Dict) -> None:
        """
        Try to inject values into Python code files (fallback strategy)
        
        Args:
            file_path: Path to Python file
            inputs: User input values
        """
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            modified = False
            # Look for common placeholder patterns and replace them
            for key, value in inputs.items():
                # Pattern: {key} = "placeholder" or {key} = 'placeholder'
                patterns = [
                    (rf'{key}\s*=\s*["\']placeholder["\']', f'{key} = "{value}"'),
                    (rf'{key}\s*=\s*["\']PLACEHOLDER["\']', f'{key} = "{value}"'),
                    (rf'{key}\s*=\s*None', f'{key} = "{value}"'),
                ]
                
                for pattern, replacement in patterns:
                    if re.search(pattern, content, re.IGNORECASE):
                        content = re.sub(pattern, replacement, content, flags=re.IGNORECASE)
                        modified = True
                        logger.info(f"Injected {key} into {file_path}")
            
            if modified:
                with open(file_path, 'w') as f:
                    f.write(content)
                    
        except Exception as e:
            logger.warning(f"Failed to inject into code file {file_path}: {e}")
            # Non-fatal, continue
    
    def commit_changes(self, repo_path: Path, message: str, author_name: str = "IDP System", author_email: str = "idp@system") -> None:
        """
        Commit changes to the repository
        
        Args:
            repo_path: Path to local repository
            message: Commit message
            author_name: Git author name
            author_email: Git author email
        """
        try:
            repo = Repo(str(repo_path))
            
            # Check if there are changes to commit
            if repo.is_dirty() or len(repo.untracked_files) > 0:
                # Add all changes
                repo.git.add(A=True)
                
                # Commit with author
                repo.index.commit(
                    message,
                    author=git.Actor(author_name, author_email)
                )
                
                logger.info(f"Committed changes: {message}")
            else:
                logger.info("No changes to commit")
                
        except Exception as e:
            logger.error(f"Failed to commit changes: {e}")
            raise
    
    def push_branch(self, repo_path: Path, branch: str, force: bool = False) -> None:
        """
        Push branch to GitHub
        
        Args:
            repo_path: Path to local repository
            branch: Branch name to push
            force: Whether to force push (default: False)
        """
        try:
            repo = Repo(str(repo_path))
            
            # Check if remote exists
            if not repo.remotes:
                logger.warning("No remote configured, skipping push")
                return
            
            # Ensure we're on the branch
            if repo.active_branch.name != branch:
                repo.git.checkout(branch)
            
            # Push branch to origin
            origin = repo.remotes.origin
            if force:
                origin.push(branch, force=True)
            else:
                origin.push(branch, force=False)
            
            logger.info(f"Pushed branch {branch} to remote")
            
        except Exception as e:
            logger.error(f"Failed to push branch: {e}")
            raise
    
    def delete_branch(self, repo_url: str, branch: str) -> None:
        """
        Delete a branch from GitHub repository

        Args:
            repo_url: GitHub repository URL
            branch: Branch name to delete
        """
        if git is None or Repo is None:
            raise ImportError("GitPython is not installed. Please install it with: pip install GitPython")

        import tempfile
        
        temp_repo_dir = None
        try:
            # Create temporary directory for repo
            temp_repo_dir = Path(tempfile.mkdtemp(prefix="git_delete_branch_"))
            
            # Get authenticated URL
            auth_url = self._get_authenticated_url(repo_url)
            
            # Clone repository (shallow clone for speed, but fetch all branches)
            logger.info(f"Cloning repository {repo_url} to delete branch {branch}")
            repo = Repo.clone_from(auth_url, str(temp_repo_dir), depth=1, no_single_branch=True)
            
            # Fetch all remote branches to see what exists
            repo.git.fetch('origin')
            
            # Check if branch exists in remote
            remote_branches = []
            for ref in repo.remotes.origin.refs:
                ref_name = ref.name.replace('origin/', '')
                if not ref_name.endswith('/HEAD'):
                    remote_branches.append(ref_name)
            
            logger.info(f"Found remote branches: {remote_branches}")
            
            if branch not in remote_branches:
                logger.warning(f"Branch {branch} does not exist in remote repository, skipping deletion")
                return
            
            # Checkout a different branch (main/master) before deleting
            checkout_success = False
            try:
                repo.git.checkout('main')
                checkout_success = True
            except:
                try:
                    repo.git.checkout('master')
                    checkout_success = True
                except:
                    # If neither exists, try to checkout the first available branch that's not the one we're deleting
                    other_branches = [b for b in remote_branches if b != branch]
                    if other_branches:
                        try:
                            repo.git.checkout(f"origin/{other_branches[0]}")
                            checkout_success = True
                        except:
                            pass
            
            if not checkout_success:
                logger.warning("Could not checkout a different branch, but will attempt to delete anyway")
            
            # Delete branch from remote using git push with delete syntax
            origin = repo.remotes.origin
            try:
                # Push with delete syntax: git push origin :branch_name
                # The colon (:) before branch name indicates deletion
                logger.info(f"Attempting to delete remote branch: {branch}")
                origin.push(refspec=f":{branch}")
                logger.info(f"Successfully deleted branch {branch} from remote repository")
            except git.exc.GitCommandError as e:
                # Branch might not exist or already deleted
                error_str = str(e).lower()
                if "remote ref does not exist" in error_str or "not found" in error_str or "does not exist" in error_str:
                    logger.warning(f"Branch {branch} does not exist in remote (may have been already deleted): {e}")
                else:
                    logger.error(f"Failed to delete branch {branch} from remote: {e}")
                    raise

        except Exception as e:
            logger.error(f"Failed to delete branch {branch}: {e}", exc_info=True)
            raise
        finally:
            # Cleanup temporary directory
            if temp_repo_dir and temp_repo_dir.exists():
                shutil.rmtree(temp_repo_dir, ignore_errors=True)
    
    def initialize_and_push_plugin(
        self,
        repo_url: str,
        branch: str,
        source_dir: Path,
        commit_message: str = "Initial plugin upload"
    ) -> None:
        """
        Initialize repository, create branch, copy files, and push to GitHub
        
        Args:
            repo_url: GitHub repository URL
            branch: Branch name to create and push
            source_dir: Directory containing plugin files to push
            commit_message: Commit message
        """
        if git is None or Repo is None:
            raise ImportError("GitPython is not installed. Please install it with: pip install GitPython")
        
        import tempfile
        import shutil
        
        temp_repo_dir = None
        try:
            # Create temporary directory for repo
            temp_repo_dir = Path(tempfile.mkdtemp(prefix="plugin_upload_"))
            
            # Clone repository (or initialize if empty)
            auth_url = self._get_authenticated_url(repo_url)
            try:
                # Try to clone existing repo
                repo = Repo.clone_from(auth_url, str(temp_repo_dir), depth=1)
                logger.info(f"Cloned repository to {temp_repo_dir}")
            except Exception as e:
                # If clone fails, try to initialize new repo
                logger.warning(f"Clone failed ({e}), initializing new repo")
                repo = Repo.init(str(temp_repo_dir))
                # Create remote
                if 'origin' not in [r.name for r in repo.remotes]:
                    repo.create_remote('origin', auth_url)
                else:
                    repo.remotes.origin.set_url(auth_url)
            
            # Checkout or create branch
            try:
                # Try to checkout existing branch
                repo.git.checkout(branch)
                logger.info(f"Checked out existing branch: {branch}")
            except Exception:
                # Branch doesn't exist, create it from current branch or main/master
                try:
                    # Try to checkout main or master first
                    try:
                        repo.git.checkout('main')
                    except:
                        try:
                            repo.git.checkout('master')
                        except:
                            pass  # No main/master, will create from current
                except:
                    pass
                
                # Create new branch
                repo.git.checkout('-b', branch)
                logger.info(f"Created new branch: {branch}")
            
            # Clear existing files in repo (except .git)
            for item in temp_repo_dir.iterdir():
                if item.name != '.git' and item.is_file():
                    item.unlink()
                elif item.name != '.git' and item.is_dir():
                    shutil.rmtree(item)
            
            # Copy all files from source_dir to repo
            for item in source_dir.rglob('*'):
                if item.is_file():
                    # Preserve directory structure
                    rel_path = item.relative_to(source_dir)
                    dest_path = temp_repo_dir / rel_path
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, dest_path)
                    logger.debug(f"Copied {rel_path} to repo")
            
            # Add all files
            repo.git.add(A=True)
            
            # Check if there are changes to commit
            if repo.is_dirty() or len(repo.untracked_files) > 0:
                # Commit
                repo.index.commit(
                    commit_message,
                    author=git.Actor("IDP System", "idp@system")
                )
                logger.info(f"Committed changes: {commit_message}")
            else:
                logger.info("No changes to commit")
            
            # Push branch
            origin = repo.remotes.origin
            try:
                origin.push(branch, force=False)
                logger.info(f"Pushed branch {branch} to remote")
            except Exception as push_error:
                # If branch exists remotely, force push to update
                logger.warning(f"Branch {branch} push failed ({push_error}), attempting force push")
                try:
                    origin.push(branch, force=True)
                    logger.info(f"Force pushed branch {branch} to remote")
                except Exception as force_error:
                    logger.error(f"Failed to push branch even with force: {force_error}")
                    raise Exception(f"Failed to push branch to GitHub: {force_error}")
            
            logger.info(f"Successfully pushed plugin to {repo_url} branch {branch}")
            
        except Exception as e:
            logger.error(f"Failed to initialize and push plugin: {e}", exc_info=True)
            raise
        finally:
            # Cleanup
            if temp_repo_dir and temp_repo_dir.exists():
                shutil.rmtree(temp_repo_dir, ignore_errors=True)
    
    def get_repo_path(self, plugin_id: str, version: str) -> Optional[Path]:
        """
        Get cached repository path (if exists)
        
        Args:
            plugin_id: Plugin identifier
            version: Plugin version
            
        Returns:
            Path to cached repo or None
        """
        cached_path = self.work_dir / plugin_id / version
        if cached_path.exists() and (cached_path / ".git").exists():
            return cached_path
        return None


# Singleton instance
git_service = GitService()
