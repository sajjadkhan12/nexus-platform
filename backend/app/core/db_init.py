from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.rbac import User
from app.models.plugins import Job
from sqlalchemy import delete
from app.core.security import get_password_hash
from app.core.casbin import enforcer

async def init_db(db: AsyncSession):
    """
    Initialize database with default admin user and RBAC policies.
    Only runs if the database is empty (no users exist).
    """
    
    # Check if any users exist
    result = await db.execute(select(User))
    existing_users = result.scalars().first()
    
    if existing_users:
        # Database already initialized, skip
        return
    
    # Database is empty, proceed with initialization
    print("Database is empty. Initializing with default admin user and RBAC policies...")
    
    # Create Default Admin User from environment variables
    from app.config import settings
    admin_email = getattr(settings, "ADMIN_EMAIL")
    admin_username = getattr(settings, "ADMIN_USERNAME")
    admin_password = getattr(settings, "ADMIN_PASSWORD")
    
    admin_user = User(
        email=admin_email,
        username=admin_username,
        hashed_password=get_password_hash(admin_password),
        full_name="System Admin",
        is_active=True
    )
    db.add(admin_user)
    await db.commit()
    await db.refresh(admin_user)
    
    # Assign admin role in Casbin
    user_id = str(admin_user.id)
    enforcer.add_grouping_policy(user_id, "admin")
    
    # Add default permissions for roles
    # Admin gets ALL permissions
    admin_permissions = [
        ("admin", "profile", "read"),
        ("admin", "profile", "update"),
        ("admin", "users", "list"),
        ("admin", "users", "create"),
        ("admin", "users", "read"),
        ("admin", "users", "update"),
        ("admin", "users", "delete"),
        ("admin", "roles", "list"),
        ("admin", "roles", "create"),
        ("admin", "roles", "update"),
        ("admin", "roles", "delete"),
        ("admin", "permissions", "list"),
        ("admin", "deployments", "list"),
        ("admin", "deployments", "create"),
        ("admin", "deployments", "read"),
        ("admin", "deployments", "update"),
        ("admin", "deployments", "delete"),
        ("admin", "plugins", "upload"),
        ("admin", "plugins", "delete"),
        ("admin", "plugins", "provision"),  # Allow admins to provision resources
        ("admin", "groups", "list"),
        ("admin", "groups", "create"),
        ("admin", "groups", "read"),
        ("admin", "groups", "update"),
        ("admin", "groups", "delete"),
        ("admin", "groups", "manage"),
    ]
    
    # Engineer gets limited permissions
    engineer_permissions = [
        ("engineer", "profile", "read"),
        ("engineer", "profile", "update"),
        ("engineer", "deployments", "list:own"),
        ("engineer", "deployments", "create"),
        ("engineer", "deployments", "read:own"),
        ("engineer", "deployments", "update:own"),
        ("engineer", "deployments", "delete:own"),
        ("engineer", "plugins", "provision"),  # Allow engineers to provision resources
    ]
    
    for role, obj, act in admin_permissions:
        enforcer.add_policy(role, obj, act)
        
    for role, obj, act in engineer_permissions:
        enforcer.add_policy(role, obj, act)
    
    print("✅ Database initialized with admin user and RBAC policies")
