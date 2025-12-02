"""Pulumi Automation API service for executing infrastructure provisioning"""
import os
import tempfile
import asyncio
from pathlib import Path
from typing import Dict, Optional
import pulumi
from pulumi import automation as auto
from app.config import settings

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
            up_result = stack.up(on_output=lambda msg: print(f"[Pulumi] {msg}"))
            
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
                print(f"[Pulumi] Selected existing stack {stack_name} from Pulumi Cloud")
            except Exception as select_error:
                # If select fails, try create_or_select (will create if doesn't exist)
                error_str = str(select_error).lower()
                if "no stack named" in error_str or "not found" in error_str:
                    print(f"[Pulumi] Stack {stack_name} not found - may have been already deleted")
                    return {
                        "status": "success",
                        "summary": {},
                        "message": "Stack not found (may have been already deleted)"
                    }
                # For other errors, try create_or_select as fallback
                print(f"[Pulumi] Could not select stack, trying create_or_select: {select_error}")
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
                stack.refresh(on_output=lambda msg: print(f"[Pulumi] {msg}"))
                print(f"[Pulumi] Stack {stack_name} found and refreshed")
            except Exception as refresh_error:
                error_str = str(refresh_error).lower()
                # If stack doesn't exist, that's okay - it might have been already deleted
                if "no stack named" in error_str or "not found" in error_str:
                    print(f"[Pulumi] Stack {stack_name} not found - may have been already deleted")
                    return {
                        "status": "success",
                        "summary": {},
                        "message": "Stack not found (may have been already deleted)"
                    }
                else:
                    print(f"[Pulumi] Warning: Could not refresh stack: {refresh_error}")
                    # Continue anyway - try to destroy
            
            # Destroy the infrastructure first
            print(f"[Pulumi] Destroying stack {stack_name}...")
            destroy_result = None
            destroy_success = False
            try:
                destroy_result = stack.destroy(on_output=lambda msg: print(f"[Pulumi] {msg}"))
                destroy_success = True
                print(f"[Pulumi] All resources in stack {stack_name} destroyed successfully")
            except Exception as destroy_error:
                error_str = str(destroy_error).lower()
                # If stack doesn't exist or has no resources, that's okay
                if "no stack named" in error_str or "not found" in error_str:
                    print(f"[Pulumi] Stack {stack_name} not found - may have been already deleted")
                    return {
                        "status": "success",
                        "summary": {},
                        "message": "Stack not found (may have been already deleted)"
                    }
                else:
                    # Destroy failed - don't remove stack, return error
                    print(f"[Pulumi] ERROR: Destroy failed: {destroy_error}")
                    return {
                        "status": "failed",
                        "error": f"Failed to destroy resources: {str(destroy_error)}",
                        "summary": {}
                    }
            
            # Only remove the stack if destroy was successful (all resources deleted)
            if destroy_success:
                print(f"[Pulumi] All resources deleted. Removing stack {stack_name}...")
                stack_removed = False
                try:
                    stack.workspace.remove_stack(stack_name)
                    print(f"[Pulumi] Stack {stack_name} removed successfully")
                    stack_removed = True
                except Exception as remove_error:
                    error_str = str(remove_error).lower()
                    # Try alternative method using Pulumi CLI if API method fails
                    if "not found" not in error_str and "does not exist" not in error_str:
                        print(f"[Pulumi] API remove_stack failed, trying CLI method: {remove_error}")
                        try:
                            import subprocess
                            import sys
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
                                print(f"[Pulumi] Stack {stack_name} removed via CLI")
                                stack_removed = True
                            else:
                                print(f"[Pulumi] CLI stack rm failed: {result.stderr}")
                        except Exception as cli_error:
                            print(f"[Pulumi] CLI stack rm also failed: {cli_error}")
                    else:
                        print(f"[Pulumi] Stack {stack_name} already removed or doesn't exist")
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
                print(f"[Pulumi] Stack {stack_name} not found - may have been already deleted")
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
            elif credentials["type"] == "gcp_access_token":
                # OIDC-exchanged access token
                # For Pulumi GCP provider, we need to set the access token
                # Note: Pulumi GCP provider prefers GOOGLE_APPLICATION_CREDENTIALS
                # but can also use GOOGLE_OAUTH_ACCESS_TOKEN
                env["GOOGLE_OAUTH_ACCESS_TOKEN"] = credentials.get("access_token", "")
        
        # AWS
        if "aws_access_key_id" in credentials:
            env["AWS_ACCESS_KEY_ID"] = credentials["aws_access_key_id"]
            env["AWS_SECRET_ACCESS_KEY"] = credentials["aws_secret_access_key"]
            # Session token is required for temporary credentials (from OIDC exchange)
            if "aws_session_token" in credentials:
                env["AWS_SESSION_TOKEN"] = credentials["aws_session_token"]
            if "aws_region" in credentials:
                env["AWS_REGION"] = credentials["aws_region"]
            elif "AWS_REGION" not in env:
                env["AWS_REGION"] = "us-east-1"  # Default region
        
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
            print(f"[PulumiService] Installing dependencies with command: {cmd}")
            try:
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await process.communicate()
                if process.returncode != 0:
                    print(f"[PulumiService] Pip install failed: {stderr.decode()}")
                    raise Exception(f"Pip install failed: {stderr.decode()}")
                print(f"[PulumiService] Dependencies installed successfully")
            except Exception as e:
                print(f"[PulumiService] Failed to run pip: {e}")
                raise e

# Singleton instance
pulumi_service = PulumiService()
