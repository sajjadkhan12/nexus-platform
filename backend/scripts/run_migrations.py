"""
Run database migrations for microservice support.
This script applies the migration SQL to add new columns.
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text
from app.config import settings
from app.logger import logger


async def run_migrations():
    """Run migration SQL to add microservice support columns"""
    
    # Ensure DATABASE_URL uses asyncpg driver
    db_url = settings.DATABASE_URL
    if not db_url.startswith("postgresql+asyncpg://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")
        db_url = db_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://")
    
    # Create async engine
    engine = create_async_engine(db_url, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    migration_sql = """
    -- Add deployment_type to plugins table
    ALTER TABLE plugins 
    ADD COLUMN IF NOT EXISTS deployment_type VARCHAR(50) DEFAULT 'infrastructure' NOT NULL;

    -- Add template fields to plugin_versions table
    ALTER TABLE plugin_versions 
    ADD COLUMN IF NOT EXISTS template_repo_url VARCHAR(500);

    ALTER TABLE plugin_versions 
    ADD COLUMN IF NOT EXISTS template_path VARCHAR(255);

    -- Make storage_path nullable for microservice templates (which don't use file storage)
    ALTER TABLE plugin_versions 
    ALTER COLUMN storage_path DROP NOT NULL;

    -- Add microservice fields to deployments table
    ALTER TABLE deployments 
    ADD COLUMN IF NOT EXISTS deployment_type VARCHAR(50) DEFAULT 'infrastructure' NOT NULL;

    ALTER TABLE deployments 
    ADD COLUMN IF NOT EXISTS github_repo_url VARCHAR(500);

    ALTER TABLE deployments 
    ADD COLUMN IF NOT EXISTS github_repo_name VARCHAR(255);

    ALTER TABLE deployments 
    ADD COLUMN IF NOT EXISTS ci_cd_status VARCHAR(50);

    ALTER TABLE deployments 
    ADD COLUMN IF NOT EXISTS ci_cd_run_id BIGINT;

    ALTER TABLE deployments 
    ADD COLUMN IF NOT EXISTS ci_cd_run_url VARCHAR(500);

    ALTER TABLE deployments 
    ADD COLUMN IF NOT EXISTS ci_cd_updated_at TIMESTAMP WITH TIME ZONE;

    -- Add dead-lettering columns to jobs table
    ALTER TABLE jobs 
    ADD COLUMN IF NOT EXISTS retry_count INTEGER DEFAULT 0 NOT NULL;

    ALTER TABLE jobs 
    ADD COLUMN IF NOT EXISTS error_state VARCHAR(255);

    ALTER TABLE jobs 
    ADD COLUMN IF NOT EXISTS error_message TEXT;

    -- Add 'dead_letter' to job_status_enum if it doesn't exist
    DO $$ 
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'dead_letter' AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'job_status_enum')) THEN
            ALTER TYPE job_status_enum ADD VALUE 'dead_letter';
        END IF;
    END $$;

    -- Update existing deployments to have infrastructure type (if NULL)
    UPDATE deployments 
    SET deployment_type = 'infrastructure' 
    WHERE deployment_type IS NULL;

    -- Update existing plugins to have infrastructure type (if NULL)
    UPDATE plugins 
    SET deployment_type = 'infrastructure' 
    WHERE deployment_type IS NULL;
    """
    
    async with async_session() as db:
        try:
            # Split SQL into individual statements
            statements = [s.strip() for s in migration_sql.split(';') if s.strip()]
            
            for statement in statements:
                if statement:
                    try:
                        await db.execute(text(statement))
                        logger.info(f"✅ Executed: {statement[:50]}...")
                    except Exception as e:
                        # IF NOT EXISTS should prevent errors, but log if something fails
                        if "already exists" not in str(e).lower() and "duplicate" not in str(e).lower():
                            logger.warning(f"⚠️  Statement may have failed (non-critical): {e}")
            
            await db.commit()
            logger.info("✅ Migration completed successfully")
            
        except Exception as e:
            await db.rollback()
            logger.error(f"❌ Migration failed: {e}", exc_info=True)
            raise
        finally:
            await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run_migrations())

