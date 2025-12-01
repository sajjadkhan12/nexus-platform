"""Plugin validation service"""
import yaml
import zipfile
from pathlib import Path
from typing import Dict, Tuple
from pydantic import BaseModel, ValidationError
import logging

logger = logging.getLogger("devplatform")

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
        logger.info(f"Validating ZIP file: {zip_path}")
        
        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                file_list = zf.namelist()
                logger.info(f"ZIP file opened successfully. Files in archive: {len(file_list)}")
                logger.debug(f"File list: {file_list[:20]}...")  # Log first 20 files
                
                # Check for required files
                logger.info(f"Checking for required files: {self.REQUIRED_FILES}")
                for required_file in self.REQUIRED_FILES:
                    matching_files = [f for f in file_list if f.endswith(required_file)]
                    logger.debug(f"Looking for {required_file}, found: {matching_files}")
                    if not matching_files:
                        error_msg = f"Missing required file: {required_file}"
                        logger.error(error_msg)
                        logger.error(f"Available files: {file_list}")
                        return False, error_msg, None
                    logger.info(f"✓ Found {required_file}: {matching_files[0]}")
                
                # Find and validate plugin.yaml
                manifest_file = next((f for f in file_list if f.endswith("plugin.yaml")), None)
                if not manifest_file:
                    error_msg = "Missing plugin.yaml"
                    logger.error(error_msg)
                    logger.error(f"Available files: {file_list}")
                    return False, error_msg, None
                
                logger.info(f"Found plugin.yaml at: {manifest_file}")
                
                with zf.open(manifest_file) as f:
                    manifest_data = yaml.safe_load(f)
                
                logger.info(f"Loaded manifest data. Keys: {list(manifest_data.keys())}")
                logger.debug(f"Manifest data: {manifest_data}")
                
                # Validate manifest schema
                try:
                    logger.info("Validating manifest schema against PluginManifest model")
                    manifest = PluginManifest(**manifest_data)
                    logger.info(f"✓ Manifest schema valid. Entrypoint: {manifest.entrypoint}")
                except ValidationError as e:
                    error_msg = f"Invalid manifest schema: {str(e)}"
                    logger.error(error_msg)
                    logger.error(f"Validation errors: {e.errors()}")
                    logger.error(f"Manifest data received: {manifest_data}")
                    return False, error_msg, None
                
                # Check for entrypoint
                entrypoint = manifest.entrypoint
                logger.info(f"Checking for entrypoint file: {entrypoint}")
                matching_entrypoints = [f for f in file_list if f.endswith(entrypoint)]
                logger.debug(f"Files matching entrypoint '{entrypoint}': {matching_entrypoints}")
                
                if not matching_entrypoints:
                    error_msg = f"Entrypoint file not found: {entrypoint}"
                    logger.error(error_msg)
                    logger.error(f"Available files: {file_list}")
                    return False, error_msg, None
                
                logger.info(f"✓ Found entrypoint: {matching_entrypoints[0]}")
                logger.info("Plugin validation successful!")
                return True, "", manifest_data
                
        except zipfile.BadZipFile as e:
            error_msg = "Invalid ZIP file"
            logger.error(f"{error_msg}: {str(e)}")
            return False, error_msg, None
        except yaml.YAMLError as e:
            error_msg = f"Invalid YAML in manifest: {str(e)}"
            logger.error(error_msg)
            return False, error_msg, None
        except Exception as e:
            error_msg = f"Validation error: {str(e)}"
            logger.error(f"{error_msg}", exc_info=True)
            return False, error_msg, None

# Singleton instance
plugin_validator = PluginValidator()
