import casbin
from casbin_sqlalchemy_adapter import Adapter
from sqlalchemy import create_engine
from app.config import settings
import os

# Create a synchronous engine for Casbin adapter
# The adapter currently requires a sync engine
sync_db_url = settings.DATABASE_URL.replace("+asyncpg", "")
if "postgresql://" not in sync_db_url and "postgresql+psycopg2://" not in sync_db_url:
    sync_db_url = sync_db_url.replace("postgresql:", "postgresql+psycopg2:")

engine = create_engine(sync_db_url)

# Initialize adapter
adapter = Adapter(engine)

# Path to model.conf
model_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "rbac_model.conf")

# Initialize enforcer
enforcer = casbin.Enforcer(model_path, adapter)

def get_enforcer():
    """Dependency to get Casbin enforcer"""
    # Reload policy to ensure we have latest changes
    enforcer.load_policy()
    return enforcer
