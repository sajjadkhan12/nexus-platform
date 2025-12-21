from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import text
from app.models.rbac import User, Organization, Role
from app.models.plugins import Job
from sqlalchemy import delete
from app.core.security import get_password_hash
from app.core.casbin import enforcer
from app.core.organization import get_or_create_default_organization, get_organization_domain
from app.core.permission_registry import PERMISSIONS, parse_permission_slug, get_all_permissions

async def init_db(db: AsyncSession):
    """
    Initialize database with default organization, admin user and RBAC policies.
    Only runs if the database is empty (no users exist).
    """
    from app.logger import logger
    
    # Check if any users exist
    try:
        result = await db.execute(select(User))
        existing_users = result.scalars().first()
        
        if existing_users:
            # Database already initialized, skip
            return
    except Exception as e:
        # If table doesn't exist yet, we'll create it during initialization
        logger.warning(f"Could not check for existing users (table may not exist yet): {e}")
        # Continue with initialization
    
    # Database is empty, proceed with initialization
    from app.logger import logger
    logger.info("Database is empty. Initializing with default organization, admin user and RBAC policies...")
    
    # Create or get default organization
    default_org = await get_or_create_default_organization(db)
    org_domain = get_organization_domain(default_org)
    logger.info(f"Default organization created/found: {default_org.name} (domain: {org_domain})")
    
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
        is_active=True,
        organization_id=default_org.id
    )
    db.add(admin_user)
    await db.commit()
    await db.refresh(admin_user)
    
    # Create Admin Role in database
    logger.info("Creating default roles...")
    
    # Check if admin role exists, create if not
    result = await db.execute(select(Role).where(Role.name == "admin"))
    admin_role = result.scalar_one_or_none()
    
    if not admin_role:
        admin_role = Role(
            name="admin",
            description="System Administrator with full access to all resources and permissions"
        )
        db.add(admin_role)
        await db.commit()
        await db.refresh(admin_role)
        logger.info("  ✅ Created 'admin' role in database")
    else:
        logger.info("  ✅ 'admin' role already exists in database")
    
    # Assign admin role to admin user in Casbin with organization domain
    user_id = str(admin_user.id)
    enforcer.add_grouping_policy(user_id, "admin", org_domain)
    logger.info(f"  ✅ Assigned 'admin' role to user {admin_email}")
    
    # Get ALL permissions from the permission registry
    # This ensures admin gets every permission that exists in the system
    all_permissions = get_all_permissions()
    admin_permission_slugs = [perm["slug"] for perm in all_permissions]
    
    logger.info(f"  ✅ Found {len(admin_permission_slugs)} total permissions in registry")
    
    # Create Engineer Role
    result = await db.execute(select(Role).where(Role.name == "engineer"))
    engineer_role = result.scalar_one_or_none()
    
    if not engineer_role:
        engineer_role = Role(
            name="engineer",
            description="Engineer with access to development environment"
        )
        db.add(engineer_role)
        await db.commit()
        await db.refresh(engineer_role)
        logger.info("  ✅ Created 'engineer' role in database")
    else:
        logger.info("  ✅ 'engineer' role already exists in database")
    
    # Create Senior Engineer Role
    result = await db.execute(select(Role).where(Role.name == "senior-engineer"))
    senior_engineer_role = result.scalar_one_or_none()
    
    if not senior_engineer_role:
        senior_engineer_role = Role(
            name="senior-engineer",
            description="Senior Engineer with access to development and staging environments"
        )
        db.add(senior_engineer_role)
        await db.commit()
        await db.refresh(senior_engineer_role)
        logger.info("  ✅ Created 'senior-engineer' role in database")
    else:
        logger.info("  ✅ 'senior-engineer' role already exists in database")
    
    # Engineer gets limited permissions
    engineer_permission_slugs = [
        "profile:read",
        "profile:update",
        "deployments:list",
        "deployments:read",
        "plugins:provision",
        # Environment-specific permissions for development only
        "deployments:create:development",
        "deployments:update:development",
        "deployments:delete:development",
    ]
    
    # Senior Engineer gets staging permissions
    senior_engineer_permission_slugs = [
        "profile:read",
        "profile:update",
        "deployments:list",
        "deployments:read",
        "plugins:provision",
        # Development permissions
        "deployments:create:development",
        "deployments:update:development",
        "deployments:delete:development",
        # Staging permissions
        "deployments:create:staging",
        "deployments:update:staging",
        "deployments:delete:staging",
    ]
    
    logger.info("Adding role permissions to Casbin...")
    
    # Add admin permissions - admin gets ALL permissions from registry
    for perm_slug in admin_permission_slugs:
        obj, act = parse_permission_slug(perm_slug)
        enforcer.add_policy("admin", org_domain, obj, act)
    logger.info(f"  ✅ Admin role: {len(admin_permission_slugs)} permissions (ALL permissions)")
    
    # Add engineer permissions
    for perm_slug in engineer_permission_slugs:
        obj, act = parse_permission_slug(perm_slug)
        enforcer.add_policy("engineer", org_domain, obj, act)
    logger.info(f"  ✅ Engineer role: {len(engineer_permission_slugs)} permissions")
    
    # Add senior-engineer permissions
    for perm_slug in senior_engineer_permission_slugs:
        obj, act = parse_permission_slug(perm_slug)
        enforcer.add_policy("senior-engineer", org_domain, obj, act)
    logger.info(f"  ✅ Senior Engineer role: {len(senior_engineer_permission_slugs)} permissions")
    
    # Save all Casbin policies
    enforcer.save_policy()
    
    logger.info("✅ Database initialized with default organization, admin user and multi-tenant RBAC policies")
    logger.info("✅ Permissions use new format: resource:action:environment (e.g., deployments:create:development)")


async def create_performance_indexes(db: AsyncSession):
    """
    Create performance indexes for optimal query performance.
    This function is idempotent - indexes are only created if they don't exist.
    Should be called after table creation.
    """
    from app.logger import logger
    
    # Read the migration SQL file
    from pathlib import Path
    migration_file = Path(__file__).parent.parent.parent / "migrations" / "add_composite_indexes.sql"
    
    if not migration_file.exists():
        return
    
    try:
        with open(migration_file, 'r') as f:
            migration_sql = f.read()
        
        # Execute the entire migration SQL as-is
        # PostgreSQL handles IF NOT EXISTS and DO blocks correctly
        # We'll execute it in one go, which handles multi-statement blocks properly
        await db.execute(text(migration_sql))
        await db.commit()
        
        logger.info("✅ Performance indexes created/verified successfully")
        logger.info("  ✓ Deployment indexes (status, user_id, composite)")
        logger.info("  ✓ Job indexes")
        logger.info("  ✓ Refresh token indexes")
        logger.info("  ✓ Deployment tag indexes")
        logger.info("  ✓ Audit log indexes")
        
    except Exception as e:
        error_msg = str(e).lower()
        # Check if error is just about indexes already existing (which is fine)
        if "already exists" in error_msg or "duplicate" in error_msg:
            logger.info("✅ Performance indexes already exist (skipping)")
        else:
            logger.warning(f"Failed to create some performance indexes (non-critical): {e}")
            # Don't raise - indexes are optional for functionality
            await db.rollback()
