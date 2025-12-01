import asyncio
import yaml
import sys
import os

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import AsyncSessionLocal
from app.models.plugins import PluginVersion
from sqlalchemy import select

async def update_manifest():
    plugin_id = "gcp-bucket"
    version = "1.0.0"
    yaml_path = "storage/plugins/gcp-bucket/1.0.0/gcp-bucket/plugin.yaml"
    
    print(f"Reading manifest from {yaml_path}...")
    with open(yaml_path, "r") as f:
        manifest = yaml.safe_load(f)
    
    print(f"Updating DB for {plugin_id} v{version}...")
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(PluginVersion).where(
                PluginVersion.plugin_id == plugin_id,
                PluginVersion.version == version
            )
        )
        plugin_version = result.scalar_one_or_none()
        
        if not plugin_version:
            print("Plugin version not found in DB!")
            return
            
        plugin_version.manifest = manifest
        await session.commit()
        print("✅ Manifest updated successfully!")

if __name__ == "__main__":
    asyncio.run(update_manifest())
