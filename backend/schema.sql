-- DevPlatform IDP Database Schema
-- This schema creates all required tables for the application
-- Note: Casbin tables (casbin_rule) are created automatically by the casbin-sqlalchemy-adapter

-- Create database
CREATE DATABASE devplatform_idp;

-- Connect to the database
\c devplatform_idp;

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- RBAC Tables
-- ============================================================================

-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    avatar_url VARCHAR(500),
    is_active BOOLEAN DEFAULT TRUE,
    -- Cloud Identity Bindings
    aws_role_arn VARCHAR(255),
    gcp_service_account VARCHAR(255),
    azure_client_id VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Refresh tokens table
CREATE TABLE refresh_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE NOT NULL,
    token VARCHAR(500) UNIQUE NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Roles table
CREATE TABLE roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) UNIQUE NOT NULL,
    description VARCHAR(500),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Groups table
CREATE TABLE groups (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) UNIQUE NOT NULL,
    description VARCHAR(500),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- Plugin System Tables
-- ============================================================================

-- Plugins table
CREATE TABLE plugins (
    id VARCHAR PRIMARY KEY,
    name VARCHAR NOT NULL,
    description TEXT,
    author VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Plugin versions table
CREATE TABLE plugin_versions (
    id SERIAL PRIMARY KEY,
    plugin_id VARCHAR REFERENCES plugins(id) ON DELETE CASCADE NOT NULL,
    version VARCHAR NOT NULL,
    manifest JSONB NOT NULL,
    storage_path VARCHAR NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(plugin_id, version)
);

-- Cloud credentials table
CREATE TYPE cloud_provider_enum AS ENUM ('aws', 'gcp', 'azure', 'kubernetes');

CREATE TABLE cloud_credentials (
    id SERIAL PRIMARY KEY,
    name VARCHAR UNIQUE NOT NULL,
    provider cloud_provider_enum NOT NULL,
    encrypted_data TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- Deployment Tables
-- ============================================================================

-- Deployments table
-- Note: status is stored as VARCHAR, valid values: 'active', 'provisioning', 'failed', 'deleted'
CREATE TABLE deployments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'provisioning',
    plugin_id VARCHAR(100) NOT NULL,
    version VARCHAR(50) NOT NULL,
    stack_name VARCHAR(255),
    cloud_provider VARCHAR(50),
    region VARCHAR(100),
    inputs JSONB,
    outputs JSONB,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- Job Management Tables
-- ============================================================================

-- Job status enum
CREATE TYPE job_status_enum AS ENUM ('pending', 'running', 'success', 'failed', 'cancelled');

-- Jobs table
CREATE TABLE jobs (
    id VARCHAR PRIMARY KEY,
    plugin_version_id INTEGER REFERENCES plugin_versions(id) NOT NULL,
    deployment_id UUID REFERENCES deployments(id),
    status job_status_enum DEFAULT 'pending',
    triggered_by VARCHAR NOT NULL,
    inputs JSONB DEFAULT '{}',
    outputs JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    finished_at TIMESTAMP
);

-- Job logs table
CREATE TABLE job_logs (
    id SERIAL PRIMARY KEY,
    job_id VARCHAR REFERENCES jobs(id) ON DELETE CASCADE NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    level VARCHAR DEFAULT 'INFO',
    message TEXT NOT NULL
);

-- ============================================================================
-- Notification Tables
-- ============================================================================

-- Notifications table
CREATE TABLE notifications (
    id VARCHAR PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE NOT NULL,
    title VARCHAR NOT NULL,
    message VARCHAR NOT NULL,
    type VARCHAR DEFAULT 'info',
    is_read BOOLEAN DEFAULT FALSE,
    link VARCHAR,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- Audit Tables
-- ============================================================================

-- Audit logs table
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100),
    resource_id UUID,
    details JSONB,
    ip_address VARCHAR(45),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- Indexes for Performance
-- ============================================================================

-- Users indexes
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);

-- Refresh tokens indexes
CREATE INDEX idx_refresh_tokens_user ON refresh_tokens(user_id);
CREATE INDEX idx_refresh_tokens_token ON refresh_tokens(token);

-- Roles indexes
CREATE INDEX idx_roles_name ON roles(name);

-- Groups indexes
CREATE INDEX idx_groups_name ON groups(name);

-- Plugin indexes
CREATE INDEX idx_plugin_versions_plugin_id ON plugin_versions(plugin_id);

-- Job indexes
CREATE INDEX idx_jobs_plugin_version_id ON jobs(plugin_version_id);
CREATE INDEX idx_jobs_deployment_id ON jobs(deployment_id);
CREATE INDEX idx_jobs_status ON jobs(status);
CREATE INDEX idx_jobs_triggered_by ON jobs(triggered_by);
CREATE INDEX idx_jobs_created_at ON jobs(created_at);

-- Job logs indexes
CREATE INDEX idx_job_logs_job_id ON job_logs(job_id);
CREATE INDEX idx_job_logs_timestamp ON job_logs(timestamp);

-- Deployment indexes
CREATE INDEX idx_deployments_user_id ON deployments(user_id);
CREATE INDEX idx_deployments_status ON deployments(status);
CREATE INDEX idx_deployments_plugin_id ON deployments(plugin_id);
CREATE INDEX idx_deployments_created_at ON deployments(created_at);

-- Notification indexes
CREATE INDEX idx_notifications_user_id ON notifications(user_id);
CREATE INDEX idx_notifications_is_read ON notifications(is_read);
CREATE INDEX idx_notifications_created_at ON notifications(created_at);

-- Audit log indexes
CREATE INDEX idx_audit_logs_user ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_created ON audit_logs(created_at);
CREATE INDEX idx_audit_logs_resource ON audit_logs(resource_type, resource_id);

-- ============================================================================
-- Initial Data (Optional - can be created via db_init.py)
-- ============================================================================

-- Note: Default admin user is created via app/core/db_init.py using environment variables
-- The following is for reference only and should match your .env ADMIN_* variables

-- Example admin user (password: admin123)
-- INSERT INTO users (email, username, hashed_password, full_name, is_active)
-- VALUES (
--     'admin@devplatform.com',
--     'admin',
--     '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYzS6ZhHZUu',
--     'System Admin',
--     TRUE
-- );

-- ============================================================================
-- Notes
-- ============================================================================

-- Casbin RBAC tables (casbin_rule) are automatically created by casbin-sqlalchemy-adapter
-- when the application starts. No manual creation needed.

-- The application uses SQLAlchemy ORM which will create tables automatically
-- if they don't exist when using Base.metadata.create_all()
-- This schema.sql is provided for reference and manual database setup if needed.
