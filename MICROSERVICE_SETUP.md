# Microservice Provisioning Setup Guide

This guide walks you through setting up microservice provisioning in the IDP platform.

## Prerequisites

1. **GitHub Token**: A GitHub personal access token with the following permissions:
   - `repo` (full control) - for creating repositories
   - `admin:repo_hook` - for creating webhooks (if you want automatic webhook setup)
   - `workflow` - for reading GitHub Actions status

2. **Database**: PostgreSQL database with existing IDP schema

3. **Environment Variables**: Configure the following in your `.env` file

## Step 1: Database Migration

Run the migration script to add microservice support columns to your existing database:

```bash
cd backend
uv run python scripts/run_migrations.py
```

Or manually run the SQL migration:

```bash
psql -d devplatform_idp -f scripts/migrate_microservice_support.sql
```

## Step 2: Configure Environment Variables

Add the following to your `backend/.env` file:

```bash
# GitHub Integration (Required)
GITHUB_TOKEN=your_github_personal_access_token_here

# Template Repository (Optional - defaults to idp-templates)
GITHUB_TEMPLATE_REPO_URL=https://github.com/sajjadkhan-academy/idp-templates.git

# Webhook Configuration (Required for CI/CD status updates)
GITHUB_WEBHOOK_SECRET=your_webhook_secret_here
WEBHOOK_BASE_URL=https://your-platform-domain.com/api/v1/webhooks/github

# Optional: Organization for creating repos (leave empty for user account)
MICROSERVICE_REPO_ORG=
```

### Generating Webhook Secret

Generate a secure random string for the webhook secret:

```bash
# Using Python
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Or using OpenSSL
openssl rand -hex 32
```

## Step 3: Create Microservice Templates via UI

Admins can now create microservice templates directly through the Plugin Upload UI:

1. Navigate to **Plugin Upload** page (admin only)
2. Select **Microservice Template** option
3. Fill in the form:
   - **Plugin Name**: e.g., "Python Microservice"
   - **Version**: e.g., "1.0.0"
   - **Description**: Brief description of the template
   - **Template Repository URL**: GitHub repository URL (e.g., `https://github.com/org/repo.git`)
   - **Template Path**: Subdirectory path in the repository (e.g., `python-service`)
4. Click **Create Microservice Template**

The template will be immediately available in the Services catalog for users to provision.

## Step 4: Set Up GitHub Webhooks

### Option A: Automatic Webhook Setup (Recommended)

Since your GitHub token has all permissions, you can use the setup script:

```bash
cd backend

# Set up webhook for template repository (for testing)
uv run python scripts/setup_github_webhook.py --template

# Or set up webhook for a specific repository
uv run python scripts/setup_github_webhook.py --repo owner/repo-name

# List existing webhooks
uv run python scripts/setup_github_webhook.py --list owner/repo-name
```

### Option B: Manual Webhook Setup

1. Go to your GitHub repository (or the template repository)
2. Navigate to **Settings** → **Webhooks** → **Add webhook**
3. Configure:
   - **Payload URL**: `https://your-platform-domain.com/api/v1/webhooks/github`
   - **Content type**: `application/json`
   - **Secret**: The value from `GITHUB_WEBHOOK_SECRET` in your `.env`
   - **Events**: Select "Let me select individual events" → Check "Workflow runs"
4. Click **Add webhook**

### Option C: Automatic Webhook Creation on Repository Creation

The microservice service can automatically create webhooks when repositories are created. To enable this:

1. Uncomment the webhook creation code in `backend/app/services/microservice_service.py` (around line 200)
2. Ensure `WEBHOOK_BASE_URL` is set in your `.env`

## Step 5: Verify Setup

1. **Check Database**: Verify columns were added:
   ```sql
   \d deployments
   \d plugins
   \d plugin_versions
   ```

2. **Check Templates**: Verify microservice templates exist:
   ```bash
   # Via API or database query
   SELECT id, name, deployment_type FROM plugins WHERE deployment_type = 'microservice';
   ```
   
   Or check the Services page in the UI - microservice templates will appear when you filter by "Microservices".

3. **Test Webhook**: 
   - Create a test microservice deployment
   - Check if webhook events are received (check backend logs)
   - Verify CI/CD status updates in the deployment details page

## Step 6: Test Microservice Provisioning

1. **Start the backend**:
   ```bash
   cd backend
   uv run uvicorn app.main:app --reload
   ```

2. **Start Celery worker**:
   ```bash
   cd backend
   uv run celery -A app.worker worker --loglevel=info
   ```

3. **Start the frontend**:
   ```bash
   cd frontend
   npm run dev
   ```

4. **Create a microservice**:
   - Navigate to Services page
   - Filter by "Microservices"
   - Click on "Python Microservice"
   - Enter a deployment name
   - Click "Create Microservice"
   - Monitor the deployment details page for CI/CD status

## Troubleshooting

### Webhook Not Receiving Events

1. **Check webhook URL**: Ensure `WEBHOOK_BASE_URL` is publicly accessible
2. **Verify secret**: Ensure `GITHUB_WEBHOOK_SECRET` matches what's configured in GitHub
3. **Check GitHub webhook delivery**: Go to repository Settings → Webhooks → Recent Deliveries
4. **Check backend logs**: Look for webhook processing errors

### Repository Creation Fails

1. **Check GitHub token**: Verify token has `repo` permissions
2. **Check repository name**: Ensure name follows GitHub naming rules (alphanumeric, hyphens, underscores, dots)
3. **Check token expiration**: GitHub tokens can expire, regenerate if needed

### CI/CD Status Not Updating

1. **Check webhook**: Verify webhook is configured and receiving events
2. **Check polling**: The system falls back to polling every 60 seconds if webhooks fail
3. **Check GitHub Actions**: Ensure workflows are running in the repository
4. **Check logs**: Look for errors in Celery worker logs

## Architecture Notes

- **Webhooks**: Primary method for real-time CI/CD status updates
- **Polling**: Fallback method that runs every 60 seconds for active deployments
- **Repository Creation**: Happens in user's GitHub account (or specified organization)
- **Template Extraction**: Clones template repo and extracts specific subdirectory
- **CI/CD Tracking**: Monitors GitHub Actions workflow runs

## Next Steps

- Add more microservice templates (Node.js, Go, Java, etc.)
- Configure custom repository settings (visibility, description, topics)
- Set up organization-level webhooks for better management
- Add support for template variables/customization

