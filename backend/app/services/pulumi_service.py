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
            for key, value in config.items():
                stack.set_config(key, auto.ConfigValue(value=str(value)))
            
            # Install provider plugin dynamically based on manifest
            if manifest:
                cloud_provider = manifest.get("cloud_provider", "").lower()
                provider_version = manifest.get("provider_version")  # Optional override
                
                # Default provider versions
                provider_versions = {
                    "gcp": "v7.0.0",
                    "aws": "v6.0.0",
                    "azure": "v5.0.0"
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
        project_name: str = "Nexus_IDP"
    ) -> Dict:
        """Destroy a Pulumi stack"""
        import sys
        env = os.environ.copy()
        if credentials:
            env = self._inject_credentials(env, credentials)
        
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
            
            # Destroy the infrastructure
            destroy_result = stack.destroy(on_output=lambda msg: print(f"[Pulumi] {msg}"))
            
            # Remove the stack completely after destroying resources
            print(f"[Pulumi] Removing stack {stack_name}")
            stack.workspace.remove_stack(stack_name)
            print(f"[Pulumi] Stack {stack_name} removed successfully")
            
            return {
                "status": "success",
                "summary": destroy_result.summary.resource_changes
            }
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e)
            }
    
    def _inject_credentials(self, env: Dict, credentials: Dict) -> Dict:
        """Inject cloud credentials into environment"""
        # GCP
        if "type" in credentials and credentials["type"] == "service_account":
            # Write service account JSON to temp file
            import json
            sa_file = Path(tempfile.gettempdir()) / "gcp_sa.json"
            with open(sa_file, "w") as f:
                json.dump(credentials, f)
            env["GOOGLE_APPLICATION_CREDENTIALS"] = str(sa_file)
        
        # AWS
        if "aws_access_key_id" in credentials:
            env["AWS_ACCESS_KEY_ID"] = credentials["aws_access_key_id"]
            env["AWS_SECRET_ACCESS_KEY"] = credentials["aws_secret_access_key"]
            if "aws_region" in credentials:
                env["AWS_REGION"] = credentials["aws_region"]
        
        # Azure
        if "azure_client_id" in credentials:
            env["AZURE_CLIENT_ID"] = credentials["azure_client_id"]
            env["AZURE_CLIENT_SECRET"] = credentials["azure_client_secret"]
            env["AZURE_TENANT_ID"] = credentials["azure_tenant_id"]
            env["AZURE_SUBSCRIPTION_ID"] = credentials["azure_subscription_id"]
        
        # Set Pulumi passphrase for local secrets
        env["PULUMI_CONFIG_PASSPHRASE"] = settings.PULUMI_CONFIG_PASSPHRASE
        
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
