from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.rbac import Role, Permission, User
from app.core.rbac import Permission as PermConstants
from app.core.security import get_password_hash

async def init_db(db: AsyncSession):
    # 1. Create Permissions
    permissions = [
        # Deployments
        PermConstants.DEPLOYMENT_CREATE,
        PermConstants.DEPLOYMENT_READ_OWN,
        PermConstants.DEPLOYMENT_READ_ALL,
        PermConstants.DEPLOYMENT_UPDATE_OWN,
        PermConstants.DEPLOYMENT_UPDATE_ALL,
        PermConstants.DEPLOYMENT_DELETE_OWN,
        PermConstants.DEPLOYMENT_DELETE_ALL,
        # Plugins
        PermConstants.PLUGIN_READ,
        PermConstants.PLUGIN_MANAGE,
        # Users
        PermConstants.USER_READ_OWN,
        PermConstants.USER_READ_ALL,
        PermConstants.USER_MANAGE,
        # Roles
        PermConstants.ROLE_MANAGE,
        # Costs
        PermConstants.COST_READ_OWN,
        PermConstants.COST_READ_ALL,
        # Settings
        PermConstants.SETTINGS_READ,
        PermConstants.SETTINGS_MANAGE,
    ]
    
    db_perms = {}
    for slug in permissions:
        result = await db.execute(select(Permission).where(Permission.slug == slug))
        perm = result.scalars().first()
        if not perm:
            perm = Permission(slug=slug, description=f"Permission for {slug}")
            db.add(perm)
        db_perms[slug] = perm
    
    # 2. Create Roles
    # Admin
    result = await db.execute(select(Role).where(Role.name == "admin"))
    admin_role = result.scalars().first()
    if not admin_role:
        admin_role = Role(name="admin", description="Administrator with full access")
        db.add(admin_role)
    
    # Engineer
    result = await db.execute(select(Role).where(Role.name == "engineer"))
    engineer_role = result.scalars().first()
    if not engineer_role:
        engineer_role = Role(name="engineer", description="Standard engineer access")
        db.add(engineer_role)
        
    await db.commit()
    await db.refresh(admin_role)
    await db.refresh(engineer_role)
    
    # 3. Assign Permissions to Roles
    # Admin gets ALL permissions
    admin_role.permissions = list(db_perms.values())
    
    # Engineer gets specific permissions
    engineer_perms = [
        PermConstants.DEPLOYMENT_CREATE,
        PermConstants.DEPLOYMENT_READ_OWN,
        PermConstants.DEPLOYMENT_UPDATE_OWN,
        PermConstants.DEPLOYMENT_DELETE_OWN,
        PermConstants.PLUGIN_READ,
        PermConstants.USER_READ_OWN,
        PermConstants.COST_READ_OWN,
        PermConstants.SETTINGS_READ,
    ]
    engineer_role.permissions = [db_perms[p] for p in engineer_perms if p in db_perms]
    
    await db.commit()
    
    # 4. Create Default Admin User
    result = await db.execute(select(User).where(User.email == "admin@devplatform.com"))
    admin_user = result.scalars().first()
    if not admin_user:
        admin_user = User(
            email="admin@devplatform.com",
            hashed_password=get_password_hash("admin123"),
            full_name="System Admin",
            is_active=True
        )
        db.add(admin_user)
        await db.commit()
        await db.refresh(admin_user)
    
    # Ensure admin user has admin role (even if user already existed)
    if admin_role not in admin_user.roles:
        admin_user.roles.append(admin_role)
        await db.commit()
