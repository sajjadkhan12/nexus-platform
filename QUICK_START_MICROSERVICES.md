# Quick Start: Microservice Provisioning

## ✅ Implementation Complete!

All code has been implemented. Follow these steps to set up and use microservice provisioning.

## 🚀 Setup Steps

### 1. Run Database Migration

```bash
cd backend
uv run python scripts/run_migrations.py
```

This adds the necessary columns for microservice support.

### 2. Create Microservice Templates via UI

Admins can create microservice templates through the Plugin Upload UI:

1. Go to **Plugin Upload** page
2. Select **Microservice Template** option
3. Fill in:
   - Plugin Name (e.g., "Python Microservice")
   - Version (e.g., "1.0.0")
   - Description
   - Template Repository URL (e.g., `https://github.com/org/repo.git`)
   - Template Path (e.g., `python-service`)
4. Click **Create Microservice Template**

### 3. Configure Environment Variables

Add to `backend/.env`:

```bash
# Your GitHub token (with repo and admin:repo_hook permissions)
GITHUB_TOKEN=your_github_token_here

# Webhook secret (generate with Python):
# python3 -c "import secrets; print(secrets.token_urlsafe(32))"
GITHUB_WEBHOOK_SECRET=your_webhook_secret_here

# Your platform's public URL (for webhooks to reach your backend)
WEBHOOK_BASE_URL=https://your-domain.com

# Optional: Template repo (defaults to idp-templates)
GITHUB_TEMPLATE_REPO_URL=https://github.com/sajjadkhan-academy/idp-templates.git
```

### 4. (Optional) Set Up Webhook for Template Repository

**Note**: Webhooks are automatically created when microservice repositories are created (if `WEBHOOK_BASE_URL` is configured). This step is only for testing or manual setup.

Since your GitHub token has all permissions, you can automatically create webhooks:

```bash
cd backend
uv run python scripts/setup_github_webhook.py --template
```

### 5. Start Services

```bash
# Terminal 1: Backend
cd backend
uv run uvicorn app.main:app --reload

# Terminal 2: Celery Worker
cd backend
uv run celery -A app.worker worker --loglevel=info

# Terminal 3: Frontend
cd frontend
npm run dev
```

## 🎯 Using Microservice Provisioning

1. **Navigate to Services**: Go to `/services` in your browser
2. **Filter by Microservices**: Click the "Microservices" tab
3. **Select Template**: Click on a microservice template (e.g., "Python Microservice")
4. **Enter Name**: Provide a deployment name (e.g., "user-api")
5. **Create**: Click "Create Microservice"
6. **Monitor**: View the deployment details page to see:
   - Repository creation status
   - CI/CD pipeline status (auto-updates)
   - Repository information (clone URLs, etc.)

## 🔧 Automatic Webhook Creation

Since your GitHub token has all permissions, webhooks are **automatically created** when microservice repositories are created (if `WEBHOOK_BASE_URL` is set). This means:

- ✅ No manual webhook setup needed
- ✅ Real-time CI/CD status updates
- ✅ Automatic status synchronization

## 📋 What Was Implemented

### Backend
- ✅ Database models extended with microservice fields
- ✅ MicroserviceService for repository creation
- ✅ GitHubActionsService for CI/CD tracking
- ✅ Celery tasks for async provisioning
- ✅ API endpoints for CI/CD status and repository info
- ✅ GitHub webhook endpoint for real-time updates
- ✅ Automatic webhook creation (when configured)
- ✅ UI-based template creation endpoint

### Frontend
- ✅ Services page with microservice filter/tabs
- ✅ Simplified provisioning form for microservices
- ✅ CI/CD status widget with auto-refresh
- ✅ Repository information display
- ✅ Deployment type badges
- ✅ Plugin Upload UI with microservice template option

## 🐛 Troubleshooting

### Webhook Not Working?
- Check `WEBHOOK_BASE_URL` is set and publicly accessible
- Verify `GITHUB_WEBHOOK_SECRET` matches GitHub configuration
- Check GitHub webhook delivery logs (Settings → Webhooks → Recent Deliveries)
- Review backend logs for webhook processing errors

### Repository Creation Fails?
- Verify `GITHUB_TOKEN` has `repo` permissions
- Check repository name follows GitHub rules
- Ensure token hasn't expired

### CI/CD Status Not Updating?
- Webhooks are primary method (real-time)
- Polling fallback runs every 60 seconds
- Check if GitHub Actions workflows are running
- Verify webhook is receiving events

## 📚 Additional Resources

- Full setup guide: `MICROSERVICE_SETUP.md`
- Migration SQL: `backend/scripts/migrate_microservice_support.sql`
