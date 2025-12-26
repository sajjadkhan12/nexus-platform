"""
Plugin management API - backward compatibility layer

This file re-exports the router from the modular structure.
All endpoints are organized in:
- app/api/plugins/upload.py - Upload endpoints
- app/api/plugins/crud.py - CRUD operations (list, get, delete, lock/unlock)
- app/api/plugins/versions.py - Version management
- app/api/plugins/access.py - Access request management

Note: This file exists for backward compatibility. The actual router is defined
in app/api/plugins/__init__.py which aggregates all sub-routers.

To avoid circular import issues (since this file and the plugins/ directory
have the same name), we import directly from the package module.
"""
import importlib.util
from pathlib import Path

# Import from the plugins package (directory) explicitly
_plugins_package_path = Path(__file__).parent / "plugins" / "__init__.py"
spec = importlib.util.spec_from_file_location("app.api.plugins.package", _plugins_package_path)
_plugins_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_plugins_module)

# Re-export the router
router = _plugins_module.router

__all__ = ["router"]
