"""Storage service for plugin artifacts"""
import os
import shutil
from pathlib import Path
from typing import BinaryIO
from app.config import settings

class StorageService:
    """Service for storing plugin artifacts (local or cloud)"""
    
    def __init__(self):
        # Use local storage by default
        self.base_path = Path(settings.PLUGINS_STORAGE_PATH if hasattr(settings, 'PLUGINS_STORAGE_PATH') else "./storage/plugins")
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def save_plugin(self, plugin_id: str, version: str, file: BinaryIO) -> str:
        """
        Save a plugin ZIP file
        Returns the storage path
        """
        plugin_dir = self.base_path / plugin_id / version
        plugin_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = plugin_dir / "plugin.zip"
        
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file, f)
        
        return str(file_path)
    
    def get_plugin_path(self, plugin_id: str, version: str) -> Path:
        """Get the path to a plugin ZIP file"""
        return self.base_path / plugin_id / version / "plugin.zip"
    
    def delete_plugin(self, plugin_id: str, version: str):
        """Delete a plugin version"""
        plugin_dir = self.base_path / plugin_id / version
        if plugin_dir.exists():
            shutil.rmtree(plugin_dir)
    
    def extract_plugin(self, plugin_id: str, version: str, extract_to: Path) -> Path:
        """
        Extract a plugin ZIP to a temporary directory.
        Returns the path that contains the __main__.py file.
        """
        import zipfile
        from pathlib import Path

        zip_path = self.get_plugin_path(plugin_id, version)
        extract_to.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            for member in zip_ref.infolist():
                # Skip macOS metadata and junk files
                if member.filename.startswith('__MACOSX') or member.filename.endswith('.DS_Store'):
                    continue
                zip_ref.extract(member, extract_to)

        # Find __main__.py inside the extracted directory
        # We need to return the directory containing __main__.py
        for root, dirs, files in os.walk(extract_to):
            if '__main__.py' in files:
                # Found it! Return this directory
                return Path(root)
                
        # Fallback: return the original extraction dir (will raise later if missing)
        return extract_to

# Singleton instance
storage_service = StorageService()
