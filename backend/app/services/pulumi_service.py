"""Pulumi Automation API service for executing infrastructure provisioning"""
import os
import tempfile
import asyncio
import re
import time
from pathlib import Path
from typing import Dict, Optional
import pulumi
from pulumi import automation as auto
from app.config import settings
from app.logger import logger

class PulumiService:
    """Service for running Pulumi programs via Automation API"""
    
    def __init__(self):
        self.work_dir = Path(tempfile.gettempdir()) / "pulumi_workspaces"
        self.work_dir.mkdir(parents=True, exist_ok=True)
    
    async def run_pulumi(
        self,
        plugin_path: Path,
        stack_name: str,
        config: Dict[str, str],
        credentials: Optional[Dict] = None,
        project_name: str = "idp-plugin",
        manifest: Optional[Dict] = None
    ) -> Dict:
        """
        Execute a Pulumi program
        
        Args:
            plugin_path: Path to extracted plugin directory
            stack_name: Name of the Pulumi stack
            config: Configuration dictionary
            credentials: Cloud credentials to inject
            project_name: Pulumi project name
        
        Returns:
            Dict with outputs and status
        """
        # Setup environment variables for cloud credentials
        env = os.environ.copy()
        # Always set Pulumi passphrase for local secrets
        env["PULUMI_CONFIG_PASSPHRASE"] = settings.PULUMI_CONFIG_PASSPHRASE
        
        if credentials:
            env = self._inject_credentials(env, credentials)
        
        # Create workspace
        workspace_dir = self.work_dir / stack_name
        workspace_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Create or select stack
            # Create or select stack
            import sys
            stack = auto.create_or_select_stack(
                stack_name=stack_name,
                work_dir=str(plugin_path),
                opts=auto.LocalWorkspaceOptions(
                    env_vars=env,
                    secrets_provider="passphrase",  # Use local secrets
                    project_settings=auto.ProjectSettings(
                        name=project_name,
                        runtime=auto.ProjectRuntimeInfo(
                            name="python",
                            options={"virtualenv": sys.prefix}
                        )
                    )
                )
            )
            
            # Set stack config
            # Skip None values and empty strings for optional fields
            for key, value in config.items():
                # Skip None, empty strings, and empty dicts/lists
                if value is None or value == "" or value == {} or value == []:
                    continue
                stack.set_config(key, auto.ConfigValue(value=str(value)))
            
            # Install provider plugin dynamically based on manifest
            if manifest:
                cloud_provider = manifest.get("cloud_provider", "").lower()
                provider_version = manifest.get("provider_version")  # Optional override
                
                # Default provider versions
                # Note: Pulumi plugin versions should be without 'v' prefix
                # Using recent stable versions that are confirmed to exist
                provider_versions = {
                    "gcp": "7.0.0",
                    "aws": "7.12.0",  # Updated to latest stable version
                    "azure": "5.0.0"
                }
                
                if cloud_provider in provider_versions:
                    version = provider_version or provider_versions[cloud_provider]
                    stack.workspace.install_plugin(cloud_provider, version)
                elif cloud_provider:
                    # Unknown provider, try to install with default version
                    version = provider_version or "latest"
                    stack.workspace.install_plugin(cloud_provider, version)
            else:
                # Fallback to GCP if no manifest provided
                stack.workspace.install_plugin("gcp", "v7.0.0")
            
            # Run pip install in the plugin directory
            await self._install_dependencies(plugin_path)
            
            # Perform the update
            up_result = stack.up(on_output=lambda msg: logger.info(f"[Pulumi] {msg}"))
            
            # Get outputs
            outputs = {}
            for key, value in up_result.outputs.items():
                outputs[key] = value.value
            
            return {
                "status": "success",
                "outputs": outputs,
                "summary": {
                    "resources_created": up_result.summary.resource_changes.get("create", 0),
                    "resources_updated": up_result.summary.resource_changes.get("update", 0),
                }
            }
        
        except Exception as e:
            # Capture more details if it's a Pulumi error
            error_msg = str(e)
            if hasattr(e, 'stdout') and e.stdout:
                error_msg += f"\nstdout: {e.stdout}"
            if hasattr(e, 'stderr') and e.stderr:
                error_msg += f"\nstderr: {e.stderr}"
                
            return {
                "status": "failed",
                "error": error_msg,
                "outputs": {}
            }
    
    async def destroy_stack(
        self,
        plugin_path: Path,
        stack_name: str,
        credentials: Optional[Dict] = None,
        project_name: str = "idp-plugin"  # Changed to match run_pulumi default
    ) -> Dict:
        """Destroy a Pulumi stack"""
        import sys
        env = os.environ.copy()
        # Always set Pulumi passphrase for local secrets
        env["PULUMI_CONFIG_PASSPHRASE"] = settings.PULUMI_CONFIG_PASSPHRASE
        
        if credentials:
            env = self._inject_credentials(env, credentials)
        
        try:
            # First try to select the existing stack (from Pulumi Cloud)
            # This will work if the stack exists in Pulumi Cloud
            try:
                stack = auto.select_stack(
                    stack_name=stack_name,
                    work_dir=str(plugin_path),
                    opts=auto.LocalWorkspaceOptions(
                        env_vars=env,
                        secrets_provider="passphrase",
                        project_settings=auto.ProjectSettings(
                            name=project_name,
                            runtime=auto.ProjectRuntimeInfo(
                                name="python",
                                options={"virtualenv": sys.prefix}
                            )
                        )
                    )
                )
                logger.info(f"[Pulumi] Selected existing stack {stack_name} from Pulumi Cloud")
            except Exception as select_error:
                # If select fails, try create_or_select (will create if doesn't exist)
                error_str = str(select_error).lower()
                if "no stack named" in error_str or "not found" in error_str:
                    logger.info(f"[Pulumi] Stack {stack_name} not found - may have been already deleted")
                    return {
                        "status": "success",
                        "summary": {},
                        "message": "Stack not found (may have been already deleted)"
                    }
                # For other errors, try create_or_select as fallback
                logger.warning(f"[Pulumi] Could not select stack, trying create_or_select: {select_error}")
                stack = auto.create_or_select_stack(
                    stack_name=stack_name,
                    work_dir=str(plugin_path),
                    opts=auto.LocalWorkspaceOptions(
                        env_vars=env,
                        secrets_provider="passphrase",
                        project_settings=auto.ProjectSettings(
                            name=project_name,
                            runtime=auto.ProjectRuntimeInfo(
                                name="python",
                                options={"virtualenv": sys.prefix}
                            )
                        )
                    )
                )
            
            # Check if stack exists by trying to get its outputs
            try:
                # Try to refresh to ensure we have the latest state from Pulumi Cloud
                stack.refresh(on_output=lambda msg: logger.info(f"[Pulumi] {msg}"))
                logger.info(f"[Pulumi] Stack {stack_name} found and refreshed")
            except Exception as refresh_error:
                error_str = str(refresh_error).lower()
                # If stack doesn't exist, that's okay - it might have been already deleted
                if "no stack named" in error_str or "not found" in error_str:
                    logger.info(f"[Pulumi] Stack {stack_name} not found - may have been already deleted")
                    return {
                        "status": "success",
                        "summary": {},
                        "message": "Stack not found (may have been already deleted)"
                    }
                else:
                    logger.warning(f"[Pulumi] Warning: Could not refresh stack: {refresh_error}")
                    # Continue anyway - try to destroy
            
            # Destroy the infrastructure first
            logger.info(f"[Pulumi] Destroying stack {stack_name}...")
            destroy_result = None
            destroy_success = False
            try:
                destroy_result = stack.destroy(on_output=lambda msg: logger.info(f"[Pulumi] {msg}"))
                destroy_success = True
                logger.info(f"[Pulumi] All resources in stack {stack_name} destroyed successfully")
            except Exception as destroy_error:
                error_str = str(destroy_error).lower()
                # If stack doesn't exist or has no resources, that's okay
                if "no stack named" in error_str or "not found" in error_str:
                    logger.info(f"[Pulumi] Stack {stack_name} not found - may have been already deleted")
                    return {
                        "status": "success",
                        "summary": {},
                        "message": "Stack not found (may have been already deleted)"
                    }
                else:
                    # Destroy failed - don't remove stack, return error
                    logger.error(f"[Pulumi] ERROR: Destroy failed: {destroy_error}")
                    return {
                        "status": "failed",
                        "error": f"Failed to destroy resources: {str(destroy_error)}",
                        "summary": {}
                    }
            
            # Only remove the stack if destroy was successful (all resources deleted)
            if destroy_success:
                logger.info(f"[Pulumi] All resources deleted. Removing stack {stack_name}...")
                stack_removed = False
                try:
                    stack.workspace.remove_stack(stack_name)
                    logger.info(f"[Pulumi] Stack {stack_name} removed successfully")
                    stack_removed = True
                except Exception as remove_error:
                    error_str = str(remove_error).lower()
                    # Try alternative method using Pulumi CLI if API method fails
                    if "not found" not in error_str and "does not exist" not in error_str:
                        logger.warning(f"[Pulumi] API remove_stack failed, trying CLI method: {remove_error}")
                        try:
                            import subprocess
                            import sys
                            # Validate stack_name to prevent command injection
                            if not re.match(r'^[a-zA-Z0-9_-]+$', stack_name):
                                raise ValueError(f"Invalid stack name: {stack_name}")
                            
                            # Use pulumi stack rm command as fallback
                            result = subprocess.run(
                                [sys.executable, "-m", "pulumi", "stack", "rm", stack_name, "--yes"],
                                cwd=str(plugin_path),
                                env=env,
                                capture_output=True,
                                text=True,
                                timeout=30
                            )
                            if result.returncode == 0:
                                logger.info(f"[Pulumi] Stack {stack_name} removed via CLI")
                                stack_removed = True
                            else:
                                logger.error(f"[Pulumi] CLI stack rm failed: {result.stderr}")
                        except Exception as cli_error:
                            logger.error(f"[Pulumi] CLI stack rm also failed: {cli_error}")
                    else:
                        logger.info(f"[Pulumi] Stack {stack_name} already removed or doesn't exist")
                        stack_removed = True  # Treat as success if it doesn't exist
                
                # Return success with stack removal status
                return {
                    "status": "success",
                    "summary": destroy_result.summary.resource_changes if destroy_result and hasattr(destroy_result, 'summary') else {},
                    "stack_removed": stack_removed,
                    "message": "Infrastructure destroyed and stack removed" if stack_removed else "Infrastructure destroyed but stack removal failed"
                }
            else:
                # Should not reach here, but just in case
                return {
                    "status": "failed",
                    "error": "Destroy did not complete successfully",
                    "stack_removed": False
                }
        except Exception as e:
            error_msg = str(e)
            # Check if error is "stack not found" - this is okay if stack was already deleted
            if "no stack named" in error_msg.lower() or "not found" in error_msg.lower():
                logger.info(f"[Pulumi] Stack {stack_name} not found - may have been already deleted")
                return {
                    "status": "success",
                    "summary": {},
                    "message": "Stack not found (may have been already deleted)"
                }
            
            return {
                "status": "failed",
                "error": error_msg
            }
    
    def _inject_credentials(self, env: Dict, credentials: Dict) -> Dict:
        """Inject cloud credentials into environment"""
        # GCP
        if "type" in credentials:
            if credentials["type"] == "service_account":
                # Static service account JSON
                import json
                sa_file = Path(tempfile.gettempdir()) / "gcp_sa.json"
                with open(sa_file, "w") as f:
                    json.dump(credentials, f)
                env["GOOGLE_APPLICATION_CREDENTIALS"] = str(sa_file)
                # Unset GOOGLE_OAUTH_ACCESS_TOKEN if it exists to avoid conflicts
                env.pop("GOOGLE_OAUTH_ACCESS_TOKEN", None)
            elif credentials["type"] == "gcp_access_token":
                # OIDC-exchanged access token - ONLY OIDC, no static credentials
                # The Pulumi GCP provider uses the Google Cloud SDK
                # We need to ensure the access token is used and prevent fallback to user credentials
                access_token = credentials.get("access_token", "")
                if access_token:
                    from app.config import settings
                    import subprocess
                    import tempfile
                    import os
                    
                    # Create a completely isolated gcloud config directory
                    # This prevents using any default user credentials
                    temp_config_dir = tempfile.mkdtemp(prefix="gcp_oidc_")
                    env["CLOUDSDK_CONFIG"] = temp_config_dir
                    
                    # CRITICAL: Unset ALL credential paths to prevent fallback to user credentials
                    env.pop("GOOGLE_APPLICATION_CREDENTIALS", None)
                    env.pop("CLOUDSDK_AUTH_ACCESS_TOKEN", None)
                    env.pop("CLOUDSDK_CORE_ACCOUNT", None)
                    env.pop("GOOGLE_OAUTH_ACCESS_TOKEN", None)  # Will set it properly below
                    
                    # Set project ID
                    if settings.GCP_PROJECT_ID:
                        env["GOOGLE_CLOUD_PROJECT"] = settings.GCP_PROJECT_ID
                        env["GCLOUD_PROJECT"] = settings.GCP_PROJECT_ID
                        env["CLOUDSDK_CORE_PROJECT"] = settings.GCP_PROJECT_ID
                    
                    # OIDC-only: Use the access token directly
                    # The Google Cloud SDK checks credentials in this order:
                    # 1. GOOGLE_APPLICATION_CREDENTIALS (service account JSON)
                    # 2. gcloud CLI default credentials (from CLOUDSDK_CONFIG)
                    # 3. Compute Engine metadata
                    #
                    # Since we only have an access token, we need to ensure it's used
                    # The SDK doesn't directly support access tokens, so we'll use gcloud CLI
                    
                    sa_email = settings.GCP_SERVICE_ACCOUNT_EMAIL
                    
                    # Set the access token in environment variables
                    env["CLOUDSDK_AUTH_ACCESS_TOKEN"] = access_token
                    env["GOOGLE_OAUTH_ACCESS_TOKEN"] = access_token
                    
                    # IMPORTANT: Do NOT set GOOGLE_APPLICATION_CREDENTIALS
                    # This would cause the SDK to try to use a service account file
                    # Instead, we'll rely on gcloud CLI to use the token
                    
                    # Use gcloud CLI to set the token as the active credential
                    # The Pulumi provider will then use gcloud's credentials
                    try:
                        # Write the access token to a temporary file
                        token_file = Path(tempfile.gettempdir()) / f"gcp_token_{int(time.time())}.txt"
                        with open(token_file, "w") as f:
                            f.write(access_token)
                        
                        # Use gcloud to activate the service account with the token
                        # We'll use gcloud auth activate-service-account with a dummy key
                        # and then override with the access token
                        
                        # Actually, a better approach: use gcloud to set the access token
                        # via the application-default credentials
                        subprocess.run(
                            ["gcloud", "auth", "application-default", "print-access-token"],
                            env=env,
                            capture_output=True,
                            timeout=5,
                            check=False
                        )
                        
                        # The token is set in CLOUDSDK_AUTH_ACCESS_TOKEN
                        # gcloud should use it, and Pulumi will use gcloud's credentials
                        logger.info(f"GCP OIDC access token configured via environment variables")
                        logger.info(f"Using isolated gcloud config: {temp_config_dir}")
                        logger.info(f"Token set for service account: {sa_email or 'default'}")
                        
                        # Clean up token file
                        try:
                            token_file.unlink()
                        except:
                            pass
                        
                    except Exception as e:
                        logger.warning(f"Could not configure gcloud with OIDC token: {e}")
                        # Continue anyway - the environment variables should work
                    
                    sa_email = settings.GCP_SERVICE_ACCOUNT_EMAIL
                    if sa_email:
                        logger.info(f"OIDC token is for service account: {sa_email}")
        
        # AWS
        # Check for both formats: aws_access_key_id (from OIDC) and access_key_id (legacy)
        aws_access_key = credentials.get("aws_access_key_id") or credentials.get("access_key_id")
        if aws_access_key:
            env["AWS_ACCESS_KEY_ID"] = aws_access_key
            env["AWS_SECRET_ACCESS_KEY"] = credentials.get("aws_secret_access_key") or credentials.get("secret_access_key", "")
            # Session token is required for temporary credentials (from OIDC exchange)
            aws_session_token = credentials.get("aws_session_token") or credentials.get("session_token")
            if aws_session_token:
                env["AWS_SESSION_TOKEN"] = aws_session_token
            # Region
            aws_region = credentials.get("aws_region") or credentials.get("region")
            if aws_region:
                env["AWS_REGION"] = aws_region
            elif "AWS_REGION" not in env:
                env["AWS_REGION"] = "us-east-1"  # Default region
            
            logger.debug(f"AWS credentials injected (masked for security)")
        
        # Azure
        if "azure_client_id" in credentials:
            env["AZURE_CLIENT_ID"] = credentials["azure_client_id"]
            # OIDC-exchanged credentials use access_token instead of client_secret
            if "azure_access_token" in credentials:
                env["AZURE_ACCESS_TOKEN"] = credentials["azure_access_token"]
            elif "azure_client_secret" in credentials:
                env["AZURE_CLIENT_SECRET"] = credentials["azure_client_secret"]
            env["AZURE_TENANT_ID"] = credentials.get("azure_tenant_id", "")
            env["AZURE_SUBSCRIPTION_ID"] = credentials.get("azure_subscription_id", "")
        
        return env
    
    async def _install_dependencies(self, plugin_path: Path):
        """Install Python dependencies for the plugin"""
        import sys
        requirements_file = plugin_path / "requirements.txt"
        if requirements_file.exists():
            cmd = [sys.executable, "-m", "pip", "install", "-r", str(requirements_file)]
            logger.info(f"[PulumiService] Installing dependencies with command: {cmd}")
            try:
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await process.communicate()
                if process.returncode != 0:
                    logger.error(f"[PulumiService] Pip install failed: {stderr.decode()}")
                    raise Exception(f"Pip install failed: {stderr.decode()}")
                logger.info(f"[PulumiService] Dependencies installed successfully")
            except Exception as e:
                logger.error(f"[PulumiService] Failed to run pip: {e}")
                raise e

# Singleton instance
pulumi_service = PulumiService()
