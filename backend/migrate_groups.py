"""
Quick migration to add updated_at column to groups table
"""
import asyncio
from sqlalchemy import text
from app.database import engine

async def migrate():
    async with engine.begin() as conn:
        # Add updated_at column to groups table
        await conn.execute(text("""
            ALTER TABLE groups 
            ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE 
            DEFAULT CURRENT_TIMESTAMP;
        """))
        print("✅ Added updated_at column to groups table")
        
        # Also add avatar_url to users if missing
        await conn.execute(text("""
            ALTER TABLE users 
            ADD COLUMN IF NOT EXISTS avatar_url VARCHAR(500);
        """))
        print("✅ Added avatar_url column to users table (if missing)")

if __name__ == "__main__":
    asyncio.run(migrate())
