"""
Database migration script to add cloud identity columns to users table
This script safely adds the missing columns without affecting existing data
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.database import engine
from app.logger import logger
from sqlalchemy import text

async def run_migration():
    """Add missing columns to users table"""
    migration_sql = """
    ALTER TABLE users 
    ADD COLUMN IF NOT EXISTS aws_role_arn VARCHAR(255),
    ADD COLUMN IF NOT EXISTS gcp_service_account VARCHAR(255),
    ADD COLUMN IF NOT EXISTS azure_client_id VARCHAR(255);
    """
    
    try:
        async with engine.begin() as conn:
            logger.info("Starting migration: Adding cloud identity columns to users table...")
            
            # Check if columns already exist
            check_sql = """
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'users' 
            AND column_name IN ('aws_role_arn', 'gcp_service_account', 'azure_client_id');
            """
            result = await conn.execute(text(check_sql))
            existing_columns = [row[0] for row in result]
            
            if len(existing_columns) == 3:
                logger.info("All columns already exist. Migration not needed.")
                return
            
            logger.info(f"Existing columns: {existing_columns}")
            
            # Run the migration
            await conn.execute(text(migration_sql))
            logger.info("Migration completed successfully!")
            
            # Verify the columns were added
            result = await conn.execute(text(check_sql))
            new_columns = [row[0] for row in result]
            logger.info(f"Columns after migration: {new_columns}")
            
            # Count users to ensure no data was lost
            count_result = await conn.execute(text("SELECT COUNT(*) FROM users"))
            user_count = count_result.scalar()
            logger.info(f"Total users in database: {user_count}")
            
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(run_migration())

