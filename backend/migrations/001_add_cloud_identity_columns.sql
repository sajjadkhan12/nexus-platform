-- Migration: Add cloud identity binding columns to users table
-- Run this migration if your users table is missing these columns

-- Add cloud identity binding columns to users table
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS aws_role_arn VARCHAR(255),
ADD COLUMN IF NOT EXISTS gcp_service_account VARCHAR(255),
ADD COLUMN IF NOT EXISTS azure_client_id VARCHAR(255);

-- Verify the columns were added
-- SELECT column_name, data_type 
-- FROM information_schema.columns 
-- WHERE table_name = 'users' 
-- AND column_name IN ('aws_role_arn', 'gcp_service_account', 'azure_client_id');

