"""Plugin validation service"""
import yaml
import zipfile
from pathlib import Path
from typing import Dict, Tuple
from pydantic import BaseModel, ValidationError

class PluginManifest(BaseModel):
    """Plugin manifest schema"""
    id: str
    name: str
    version: str
    author: str
    description: str
    category: str
    cloud_provider: str
    inputs: dict
    outputs: dict
    entrypoint: str
    permissions: list[str]
    icon: str | None = None
    ui_schema: dict | None = None

class PluginValidator:
    """Validates plugin packages"""
    
    REQUIRED_FILES = ["plugin.yaml", "Pulumi.yaml"]
    
    def validate_zip(self, zip_path: Path) -> Tuple[bool, str, Dict | None]:
        """
        Validate a plugin ZIP file
        Returns (is_valid, error_message, manifest_dict)
        """
        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                file_list = zf.namelist()
                
                # Check for required files
                for required_file in self.REQUIRED_FILES:
                    if not any(f.endswith(required_file) for f in file_list):
                        return False, f"Missing required file: {required_file}", None
                
                # Find and validate plugin.yaml
                manifest_file = next((f for f in file_list if f.endswith("plugin.yaml")), None)
                if not manifest_file:
                    return False, "Missing plugin.yaml", None
                
                with zf.open(manifest_file) as f:
                    manifest_data = yaml.safe_load(f)
                
                # Validate manifest schema
                try:
                    manifest = PluginManifest(**manifest_data)
                except ValidationError as e:
                    return False, f"Invalid manifest schema: {str(e)}", None
                
                # Check for entrypoint
                entrypoint = manifest.entrypoint
                if not any(f.endswith(entrypoint) for f in file_list):
                    return False, f"Entrypoint file not found: {entrypoint}", None
                
                return True, "", manifest_data
                
        except zipfile.BadZipFile:
            return False, "Invalid ZIP file", None
        except yaml.YAMLError as e:
            return False, f"Invalid YAML in manifest: {str(e)}", None
        except Exception as e:
            return False, f"Validation error: {str(e)}", None

# Singleton instance
plugin_validator = PluginValidator()
