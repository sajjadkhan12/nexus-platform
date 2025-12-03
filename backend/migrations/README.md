# Database Migration Guide

## Issue
The database schema is missing columns that the User model expects:
- `aws_role_arn`
- `gcp_service_account`
- `azure_client_id`

## Solution

### Option 1: Run the Migration SQL (Recommended for existing databases)

```bash
# Connect to your database
psql -U your_username -d devplatform_idp

# Run the migration
\i backend/migrations/001_add_cloud_identity_columns.sql
```

Or directly:
```bash
psql -U your_username -d devplatform_idp -f backend/migrations/001_add_cloud_identity_columns.sql
```

### Option 2: Recreate the Database (Only if you can lose data)

If you don't have important data, you can drop and recreate:

```bash
# Drop the database
psql -U your_username -c "DROP DATABASE IF EXISTS devplatform_idp;"

# Recreate it
psql -U your_username -c "CREATE DATABASE devplatform_idp;"

# Run the updated schema
psql -U your_username -d devplatform_idp -f backend/schema.sql
```

### Option 3: Manual SQL (Quick fix)

```sql
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS aws_role_arn VARCHAR(255),
ADD COLUMN IF NOT EXISTS gcp_service_account VARCHAR(255),
ADD COLUMN IF NOT EXISTS azure_client_id VARCHAR(255);
```

## Verification

After running the migration, verify the columns exist:

```sql
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'users' 
AND column_name IN ('aws_role_arn', 'gcp_service_account', 'azure_client_id');
```

You should see all three columns listed.

## Notes

- These columns are optional (nullable) and are used for cloud identity bindings
- They allow users to have per-user AWS roles, GCP service accounts, or Azure client IDs
- If not set, the system will use the global configuration from environment variables

