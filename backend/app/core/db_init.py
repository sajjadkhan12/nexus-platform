from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import text
from app.models.rbac import User, Organization, Role, PermissionMetadata
from app.models.business_unit import BusinessUnitMember
from app.models.plugins import Job
from sqlalchemy import delete
from app.core.security import get_password_hash
from app.core.casbin import enforcer
from app.core.organization import get_or_create_default_organization, get_organization_domain
from app.core.permission_registry import PERMISSIONS, parse_permission_slug, get_all_permissions

async def cleanup_old_permissions(db: AsyncSession, enforcer):
    """
    Clean up all existing permissions, roles, and Casbin policies.
    This function deletes all existing data to start fresh with the new permission format.
    
    WARNING: This will delete all existing permissions, roles, and role assignments!
    This should only be called during migration to the new permission system.
    """
    from app.logger import logger
    from sqlalchemy import delete
    
    logger.info("🧹 Starting cleanup of old permissions and roles...")
    
    try:
        # Delete all Casbin policies
        all_policies = enforcer.get_all_policy()
        policy_count = len(all_policies)
        for policy in all_policies:
            if len(policy) >= 2:
                enforcer.remove_policy(*policy)
        
        # Delete all Casbin grouping policies (role assignments)
        all_grouping_policies = enforcer.get_all_grouping_policy()
        grouping_count = len(all_grouping_policies)
        for policy in all_grouping_policies:
            if len(policy) >= 2:
                enforcer.remove_grouping_policy(*policy)
        
        enforcer.save_policy()
        logger.info(f"✅ Cleared {policy_count} Casbin policies and {grouping_count} role assignments")
        
        # Delete all entries from permissions_metadata table
        try:
            result = await db.execute(delete(PermissionMetadata))
            await db.commit()
            deleted_count = result.rowcount if hasattr(result, 'rowcount') else 0
            logger.info(f"✅ Cleared {deleted_count} entries from permissions_metadata table")
        except Exception as e:
            logger.warning(f"Could not clear permissions_metadata table (may not exist): {e}")
            await db.rollback()
        
        # Delete all roles (we'll recreate admin role in init_db)
        try:
            result = await db.execute(delete(Role))
            await db.commit()
            deleted_count = result.rowcount if hasattr(result, 'rowcount') else 0
            logger.info(f"✅ Deleted {deleted_count} existing roles")
        except Exception as e:
            logger.warning(f"Could not delete roles: {e}")
            await db.rollback()
        
        # Clear business unit member role assignments (set role_id to NULL)
        # We keep the members but remove their role assignments
        try:
            from app.models.business_unit import BusinessUnitMember
            result = await db.execute(
                text("UPDATE business_unit_members SET role_id = NULL WHERE role_id IS NOT NULL")
            )
            await db.commit()
            updated_count = result.rowcount if hasattr(result, 'rowcount') else 0
            logger.info(f"✅ Cleared role assignments for {updated_count} business unit members")
        except Exception as e:
            logger.warning(f"Could not clear business unit member role assignments: {e}")
            await db.rollback()
        
        logger.info("✅ Cleanup completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Error during cleanup: {e}", exc_info=True)
        await db.rollback()
        raise


async def migrate_to_new_permission_format(db: AsyncSession, enforcer):
    """
    Migration function to clean up old permissions and prepare for new format.
    This should be called once during migration to the new permission system.
    """
    from app.logger import logger
    
    logger.info("🔄 Starting migration to new permission format...")
    
    # Clean up old permissions
    await cleanup_old_permissions(db, enforcer)
    
    # Sync new permissions metadata
    await sync_permissions_metadata(db)
    
    logger.info("✅ Migration to new permission format completed")


async def init_db(db: AsyncSession):
    """
    Initialize database with default organization and super admin user.
    Only runs if the database is empty (no users exist).
    
    Creates:
    - Default organization
    - Super admin user (from environment variables)
    - Admin role (platform role) with ALL permissions from permission registry
    
    Note: Roles, groups, and business units are NOT created automatically.
    The super admin must create these manually through the UI/API.
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
    logger.info("Database is empty. Initializing with default organization and super admin user...")
    
    # Create or get default organization
    default_org = await get_or_create_default_organization(db)
    org_domain = get_organization_domain(default_org)
    logger.info(f"Default organization created/found: {default_org.name} (domain: {org_domain})")
    
    # Create Super Admin User from environment variables
    from app.config import settings
    admin_email = getattr(settings, "ADMIN_EMAIL")
    admin_username = getattr(settings, "ADMIN_USERNAME")
    admin_password = getattr(settings, "ADMIN_PASSWORD")
    
    admin_user = User(
        email=admin_email,
        username=admin_username,
        hashed_password=get_password_hash(admin_password),
        full_name="Super Admin",
        is_active=True,
        organization_id=default_org.id
    )
    db.add(admin_user)
    await db.commit()
    await db.refresh(admin_user)
    logger.info(f"✅ Super admin user created: {admin_email}")
    
    # Create admin role (platform role) if it doesn't exist
    result = await db.execute(select(Role).where(Role.name == "admin"))
    admin_role = result.scalar_one_or_none()
    
    if not admin_role:
        admin_role = Role(
            name="admin",
            description="Super Administrator with full access to all resources and permissions",
            is_platform_role=True
        )
        db.add(admin_role)
        await db.commit()
        await db.refresh(admin_role)
        logger.info("✅ Created 'admin' role (platform role)")
    else:
        # Ensure admin role is marked as platform role
        if not admin_role.is_platform_role:
            admin_role.is_platform_role = True
            await db.commit()
            logger.info("✅ Updated 'admin' role to platform role")
    
    # Assign admin role to super admin user in Casbin
    user_id = str(admin_user.id)
    enforcer.add_grouping_policy(user_id, "admin", org_domain)
    logger.info(f"✅ Assigned 'admin' role to super admin user")
    
    # Get ALL platform permissions from the permission registry
    # Super admin gets all platform-level permissions (platform:*)
    from app.core.permission_registry import get_platform_permissions
    platform_permission_slugs = get_platform_permissions()
    
    logger.info(f"✅ Found {len(platform_permission_slugs)} platform permissions in registry")
    
    # Add all platform permissions to admin role in Casbin
    logger.info("Adding all platform permissions to admin role...")
    for perm_slug in platform_permission_slugs:
        try:
            obj, act = parse_permission_slug(perm_slug)
            enforcer.add_policy("admin", org_domain, obj, act)
        except Exception as e:
            logger.warning(f"Failed to add permission {perm_slug} to admin role: {e}")
    
    # Save all Casbin policies
    enforcer.save_policy()
    logger.info(f"✅ Admin role granted {len(platform_permission_slugs)} platform permissions")
    
    logger.info("✅ Database initialized successfully")
    logger.info("   - Default organization created")
    logger.info("   - Super admin user created")
    logger.info("   - Admin role created with ALL permissions")
    logger.info("")
    logger.info("📝 Next steps:")
    logger.info("   1. Login as super admin")
    logger.info("   2. Create business units")
    logger.info("   3. Create roles (platform or BU-scoped)")
    logger.info("   4. Create groups and assign roles")
    logger.info("   5. Add users to business units with roles")


async def sync_permissions_metadata(db: AsyncSession):
    """
    Sync permissions metadata from permission registry to database.
    This ensures the database has up-to-date permission metadata for UI display.
    Called on startup to keep permissions in sync.
    """
    from app.logger import logger
    
    try:
        # Get all permissions from registry
        all_permissions = get_all_permissions()
        
        logger.info(f"Syncing {len(all_permissions)} permissions from registry to database...")
        
        synced_count = 0
        updated_count = 0
        
        for perm_def in all_permissions:
            slug = perm_def["slug"]
            
            # Check if permission metadata exists in database
            result = await db.execute(
                select(PermissionMetadata).where(PermissionMetadata.slug == slug)
            )
            existing_perm = result.scalar_one_or_none()
            
            if existing_perm:
                # Update existing permission metadata
                existing_perm.name = perm_def.get("name", slug)
                existing_perm.description = perm_def.get("description", "")
                existing_perm.category = perm_def.get("category", "Other")
                existing_perm.resource = perm_def.get("resource")
                existing_perm.action = perm_def.get("action")
                existing_perm.environment = perm_def.get("environment")
                existing_perm.icon = perm_def.get("icon")
                updated_count += 1
            else:
                # Create new permission metadata
                new_perm = PermissionMetadata(
                    slug=slug,
                    name=perm_def.get("name", slug),
                    description=perm_def.get("description", ""),
                    category=perm_def.get("category", "Other"),
                    resource=perm_def.get("resource"),
                    action=perm_def.get("action"),
                    environment=perm_def.get("environment"),
                    icon=perm_def.get("icon")
                )
                db.add(new_perm)
                synced_count += 1
        
        await db.commit()
        
        if synced_count > 0 or updated_count > 0:
            logger.info(f"✅ Permissions metadata synced: {synced_count} new, {updated_count} updated")
        else:
            logger.info("✅ Permissions metadata already up to date")
            
    except Exception as e:
        logger.warning(f"Failed to sync permissions metadata: {e}")
        await db.rollback()
        # Don't fail initialization if sync fails


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


async def create_deployment_update_fields(db: AsyncSession):
    """
    Add deployment update tracking fields to the deployments table.
    This function is idempotent - columns are only added if they don't exist.
    Should be called after table creation.
    """
    from app.logger import logger
    
    # Read the migration SQL file
    from pathlib import Path
    migration_file = Path(__file__).parent.parent.parent / "migrations" / "add_deployment_update_fields.sql"
    
    if not migration_file.exists():
        return
    
    try:
        with open(migration_file, 'r') as f:
            migration_sql = f.read()
        
        # Split SQL into individual statements (asyncpg doesn't support multiple statements in one execute)
        # Remove comments and split by semicolon
        statements = [
            stmt.strip() 
            for stmt in migration_sql.split(';') 
            if stmt.strip() and not stmt.strip().startswith('--')
        ]
        
        # Execute each statement separately
        for statement in statements:
            if statement:
                await db.execute(text(statement))
        
        await db.commit()
        
        logger.info("✅ Deployment update fields created/verified successfully")
        
    except Exception as e:
        error_msg = str(e).lower()
        # Check if error is just about columns already existing (which is fine)
        if "already exists" in error_msg or "duplicate" in error_msg:
            logger.info("✅ Deployment update fields already exist (skipping)")
        else:
            logger.warning(f"Failed to create deployment update fields (non-critical): {e}")
            # Don't raise - fields are optional for functionality
            await db.rollback()


async def create_deployment_history_table(db: AsyncSession):
    """
    Create deployment_history table for tracking deployment versions.
    This function is idempotent - table is only created if it doesn't exist.
    Should be called after table creation.
    """
    from app.logger import logger
    
    # Read the migration SQL file
    from pathlib import Path
    migration_file = Path(__file__).parent.parent.parent / "migrations" / "add_deployment_history.sql"
    
    if not migration_file.exists():
        return
    
    try:
        with open(migration_file, 'r') as f:
            migration_sql = f.read()
        
        # Split SQL into individual statements (asyncpg doesn't support multiple statements in one execute)
        # Remove comments and split by semicolon
        statements = [
            stmt.strip() 
            for stmt in migration_sql.split(';') 
            if stmt.strip() and not stmt.strip().startswith('--')
        ]
        
        # Execute each statement separately
        for statement in statements:
            if statement:
                await db.execute(text(statement))
        
        await db.commit()
        
        logger.info("✅ Deployment history table created/verified successfully")
        
    except Exception as e:
        error_msg = str(e).lower()
        # Check if error is just about table already existing (which is fine)
        if "already exists" in error_msg or "duplicate" in error_msg:
            logger.info("✅ Deployment history table already exists (skipping)")
        else:
            logger.warning(f"Failed to create deployment history table (non-critical): {e}")
            # Don't raise - table is optional for functionality
            await db.rollback()


async def migrate_bu_members_to_roles(db: AsyncSession):
    """
    Migrate business_unit_members from enum role to role_id foreign key.
    This function handles the migration of existing data.
    """
    from app.logger import logger
    from app.models.business_unit import BusinessUnitMember
    from app.models.rbac import Role
    
    try:
        # Check if migration is needed (role_id column exists but has NULLs)
        result = await db.execute(
            text("SELECT COUNT(*) FROM business_unit_members WHERE role_id IS NULL")
        )
        null_count = result.scalar() or 0
        
        if null_count == 0:
            logger.info("✅ All business unit members already have role_id assigned")
            return
        
        logger.info(f"Migrating {null_count} business unit members from enum to role_id...")
        
        # Get role IDs
        bu_owner_result = await db.execute(select(Role).where(Role.name == "bu-owner"))
        bu_owner = bu_owner_result.scalar_one_or_none()
        
        viewer_result = await db.execute(select(Role).where(Role.name == "viewer"))
        viewer = viewer_result.scalar_one_or_none()
        
        if not bu_owner or not viewer:
            logger.warning("Default roles (bu-owner, viewer) not found. Please run BU-scoped RBAC migration first.")
            return
        
        # Check if enum column still exists
        column_check = await db.execute(
            text("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = 'business_unit_members' AND column_name = 'role'
                )
            """)
        )
        enum_column_exists = column_check.scalar()
        
        if enum_column_exists:
            # Migrate owner -> bu-owner
            owner_members_result = await db.execute(
                text("SELECT id FROM business_unit_members WHERE role::text = 'owner' AND role_id IS NULL")
            )
            owner_ids = [row[0] for row in owner_members_result.fetchall()]
            
            if owner_ids:
                await db.execute(
                    text("UPDATE business_unit_members SET role_id = :role_id WHERE id = ANY(:ids)"),
                    {"role_id": bu_owner.id, "ids": owner_ids}
                )
                logger.info(f"  ✅ Migrated {len(owner_ids)} 'owner' members to 'bu-owner' role")
            
            # Migrate member -> viewer
            member_members_result = await db.execute(
                text("SELECT id FROM business_unit_members WHERE role::text = 'member' AND role_id IS NULL")
            )
            member_ids = [row[0] for row in member_members_result.fetchall()]
            
            if member_ids:
                await db.execute(
                    text("UPDATE business_unit_members SET role_id = :role_id WHERE id = ANY(:ids)"),
                    {"role_id": viewer.id, "ids": member_ids}
                )
                logger.info(f"  ✅ Migrated {len(member_ids)} 'member' members to 'viewer' role")
        else:
            logger.info("  ℹ️  Enum column 'role' no longer exists - migration already completed")
        
        await db.commit()
        logger.info("✅ Business unit member role migration completed")
        
    except Exception as e:
        logger.warning(f"Failed to migrate business unit members: {e}")
        await db.rollback()


async def create_business_units_tables(db: AsyncSession):
    """
    Create business units tables and add business_unit_id columns.
    This function is idempotent - tables/columns are only created if they don't exist.
    Should be called after table creation.
    """
    from app.logger import logger
    
    # Read the migration SQL file
    from pathlib import Path
    migration_file = Path(__file__).parent.parent.parent / "migrations" / "add_business_units.sql"
    
    if not migration_file.exists():
        # Migration file is optional - tables are created via SQLAlchemy models
        return
    
    try:
        with open(migration_file, 'r') as f:
            migration_sql = f.read()
        
        # Split SQL into individual statements, handling DO blocks properly
        # DO blocks contain semicolons, so we need to parse them carefully
        statements = []
        current_statement = ""
        in_do_block = False
        do_block_depth = 0
        
        lines = migration_sql.split('\n')
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # Skip empty lines and comments
            if not stripped or stripped.startswith('--'):
                continue
            
            # Check if we're starting a DO block
            if stripped.upper().startswith('DO'):
                in_do_block = True
                do_block_depth = 0
                current_statement = stripped
                continue
            
            # If we're in a DO block, accumulate until we find the matching END
            if in_do_block:
                current_statement += "\n" + line
                # Count $$ markers to know when block ends
                if '$$' in stripped:
                    do_block_depth += stripped.count('$$')
                # DO blocks end with END $$;
                if stripped.upper().startswith('END') and '$$' in stripped and stripped.endswith(';'):
                    statements.append(current_statement.strip())
                    current_statement = ""
                    in_do_block = False
                    do_block_depth = 0
                continue
            
            # Regular statement handling
            current_statement += " " + stripped if current_statement else stripped
            
            # If line ends with semicolon and we're not in a DO block, it's a complete statement
            if stripped.endswith(';') and not in_do_block:
                stmt = current_statement.rstrip(';').strip()
                if stmt:
                    statements.append(stmt)
                current_statement = ""
        
        # Execute each statement separately
        for statement in statements:
            if statement:
                try:
                    await db.execute(text(statement))
                except Exception as stmt_error:
                    error_msg = str(stmt_error).lower()
                    # Ignore errors about things already existing
                    if "already exists" in error_msg or "duplicate" in error_msg:
                        continue
                    # For columns that already exist, that's fine
                    if "column" in error_msg and "already exists" in error_msg:
                        continue
                    # Re-raise if it's a different error
                    raise
        
        await db.commit()
        
        logger.info("✅ Business units tables and columns created/verified successfully")
        
    except Exception as e:
        error_msg = str(e).lower()
        # Check if error is just about tables/columns already existing (which is fine)
        if "already exists" in error_msg or "duplicate" in error_msg:
            logger.info("✅ Business units tables/columns already exist (skipping)")
        else:
            logger.warning(f"Failed to create business units tables/columns: {e}")
            await db.rollback()
            # Don't raise - let the app continue, but log the error


async def add_active_business_unit_to_users(db: AsyncSession):
    """Add active_business_unit_id column to users table if it doesn't exist."""
    from app.logger import logger
    from pathlib import Path
    
    migration_file = Path(__file__).parent.parent.parent / "migrations" / "add_active_business_unit_to_users.sql"
    
    if not migration_file.exists():
        # Migration file is optional - column is created via SQLAlchemy models
        return
    
    try:
        with open(migration_file, 'r') as f:
            migration_sql = f.read()
        
        await db.execute(text(migration_sql))
        await db.commit()
        logger.info("✅ Active business unit column added to users table")
    except Exception as e:
        error_msg = str(e).lower()
        if "already exists" in error_msg or "duplicate" in error_msg:
            logger.info("✅ Active business unit column already exists")
        else:
            logger.warning(f"Failed to add active business unit column: {e}")
            await db.rollback()

async def create_bu_scoped_rbac_tables(db: AsyncSession):
    """
    Create BU-scoped RBAC tables and migrate from enum to role_id.
    This function is idempotent - tables/columns are only created if they don't exist.
    Should be called after business_units tables are created.
    """
    from app.logger import logger
    
    # Read the migration SQL file
    from pathlib import Path
    migration_file = Path(__file__).parent.parent.parent / "migrations" / "add_bu_scoped_rbac.sql"
    
    if not migration_file.exists():
        # Migration file is optional - tables are created via SQLAlchemy models
        return
    
    try:
        with open(migration_file, 'r') as f:
            migration_sql = f.read()
        
        # Split SQL into individual statements, handling DO blocks properly
        statements = []
        current_statement = ""
        in_do_block = False
        do_block_depth = 0
        
        lines = migration_sql.split('\n')
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # Skip empty lines and comments
            if not stripped or stripped.startswith('--'):
                continue
            
            # Check if we're starting a DO block
            if stripped.upper().startswith('DO'):
                in_do_block = True
                do_block_depth = 0
                current_statement = stripped
                continue
            
            # If we're in a DO block, accumulate until we find the matching END
            if in_do_block:
                current_statement += "\n" + line
                # Count $$ markers to know when block ends
                if '$$' in stripped:
                    do_block_depth += stripped.count('$$')
                # DO blocks end with END $$;
                if stripped.upper().startswith('END') and '$$' in stripped and stripped.endswith(';'):
                    statements.append(current_statement.strip())
                    current_statement = ""
                    in_do_block = False
                    do_block_depth = 0
                continue
            
            # Regular statement handling
            current_statement += " " + stripped if current_statement else stripped
            
            # If line ends with semicolon and we're not in a DO block, it's a complete statement
            if stripped.endswith(';') and not in_do_block:
                stmt = current_statement.rstrip(';').strip()
                if stmt:
                    statements.append(stmt)
                current_statement = ""
        
        # Execute each statement separately
        for statement in statements:
            if statement:
                try:
                    await db.execute(text(statement))
                except Exception as stmt_error:
                    error_msg = str(stmt_error).lower()
                    # Ignore errors about things already existing
                    if "already exists" in error_msg or "duplicate" in error_msg:
                        continue
                    # For columns that already exist, that's fine
                    if "column" in error_msg and "already exists" in error_msg:
                        continue
                    # Re-raise if it's a different error
                    raise
        
        await db.commit()
        
        logger.info("✅ BU-scoped RBAC tables and columns created/verified successfully")
        
        # Run the enum to role_id migration
        await migrate_bu_members_to_roles(db)
        
    except Exception as e:
        error_msg = str(e).lower()
        # Check if error is just about tables/columns already existing (which is fine)
        if "already exists" in error_msg or "duplicate" in error_msg:
            logger.info("✅ BU-scoped RBAC tables/columns already exist (skipping)")
        else:
            logger.warning(f"Failed to create BU-scoped RBAC tables/columns: {e}")
            await db.rollback()
            # Don't raise - let the app continue, but log the error
