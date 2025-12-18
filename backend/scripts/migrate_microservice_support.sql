-- Migration script to add microservice support columns
-- Run this on existing databases to add the new columns

-- Add deployment_type to plugins table
ALTER TABLE plugins 
ADD COLUMN IF NOT EXISTS deployment_type VARCHAR(50) DEFAULT 'infrastructure' NOT NULL;

-- Add template fields to plugin_versions table
ALTER TABLE plugin_versions 
ADD COLUMN IF NOT EXISTS template_repo_url VARCHAR(500);

ALTER TABLE plugin_versions 
ADD COLUMN IF NOT EXISTS template_path VARCHAR(255);

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

-- Update existing deployments to have infrastructure type (if NULL)
UPDATE deployments 
SET deployment_type = 'infrastructure' 
WHERE deployment_type IS NULL;

-- Update existing plugins to have infrastructure type (if NULL)
UPDATE plugins 
SET deployment_type = 'infrastructure' 
WHERE deployment_type IS NULL;

