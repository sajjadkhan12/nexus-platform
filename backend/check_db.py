import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database import AsyncSessionLocal
from app.models.rbac import User, Role, Permission

async def check_admin():
    async with AsyncSessionLocal() as session:
        # Check if admin user exists
        result = await session.execute(select(User).where(User.email == "admin@devplatform.com"))
        admin = result.scalars().first()
        
        if not admin:
            print("❌ Admin user NOT found!")
            return
        
        print(f"✅ Admin user found: {admin.email}")
        print(f"   - ID: {admin.id}")
        print(f"   - Active: {admin.is_active}")
        print(f"   - Roles count: {len(admin.roles)}")
        
        for role in admin.roles:
            print(f"   - Role: {role.name}")
            print(f"     Permissions: {len(role.permissions)}")
            for perm in role.permissions[:5]:  # Show first 5
                print(f"       • {perm.slug}")
        
        # Check total roles
        result = await session.execute(select(Role))
        all_roles = result.scalars().all()
        print(f"\n📊 Total roles in DB: {len(all_roles)}")
        for role in all_roles:
            print(f"   - {role.name}")
        
        # Check total permissions
        result = await session.execute(select(Permission))
        all_perms = result.scalars().all()
        print(f"\n🔐 Total permissions in DB: {len(all_perms)}")

if __name__ == "__main__":
    asyncio.run(check_admin())
