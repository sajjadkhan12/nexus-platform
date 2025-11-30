# DevPlatform IDP - Internal Developer Platform

A production-ready Internal Developer Platform (IDP) for streamlined microservice provisioning and management.

## 🚀 Quick Start

### Prerequisites
- **PostgreSQL** (v14+)
- **Node.js** (v18+)
- **Python** (v3.11+)
- **UV** package manager

### Option 1: Automated Start (Recommended)

**Terminal 1 - Backend:**
```bash
./start-backend.sh
```

**Terminal 2 - Frontend:**
```bash
./start-frontend.sh
```

Logs will be saved to:
- `logs/backend.log` - Backend API logs
- `logs/frontend.log` - Frontend dev server logs

### Option 2: Manual Start

**Terminal 1 - Backend:**
```bash
cd backend
uv run uvicorn app.main:app --reload --port 8000
```

**Terminal 2 - Celery Worker (for async provisioning):**
```bash
cd backend
uv run celery -A app.worker worker --loglevel=info
```

**Terminal 3 - Frontend:**
```bash
cd frontend
npm run dev
```

## 🌐 Access Points

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Pulumi Console**: https://app.pulumi.com

## ✨ Key Features

### 🔐 Advanced RBAC & Access Control
- **Casbin Integration**: Policy-based access control with high performance
- **Hierarchical Permissions**: User → Groups → Roles → Permissions
- **Multiple Group Membership**: Users can belong to multiple groups simultaneously
- **Granular Permissions**: Fine-grained control over resources and actions
- **Domain Support**: Multi-tenant capable authorization

### 👥 Group Management
- **Create & Manage Groups**: Organize users by team, department, or function
- **Role Assignment**: Assign multiple roles to groups for flexible permission sets
- **Member Management**: Easily add/remove users from groups
- **Permission Inheritance**: Users inherit all permissions from all their groups

### 🎭 Role Management
- **Custom Roles**: Create roles with specific permission sets
- **Built-in Roles**: Admin and Engineer roles pre-configured
- **Dynamic Permissions**: Assign permissions like `users:create`, `deployments:delete`, etc.
- **Visual Management**: Intuitive UI for role and permission management

### 👤 User Management
- **User Creation**: Create users without mandatory role assignment
- **Flexible Assignment**: Assign users to groups for automatic role inheritance
- **Profile Management**: Users can update their own profiles
- **Avatar Support**: Upload custom avatars
- **Activity Tracking**: Monitor user actions and access

### 🔧 Plugin System
- **Upload Plugins**: Upload custom Pulumi-based infrastructure plugins
- **Version Management**: Automatic version tracking and latest version selection
- **Multi-Cloud Support**: Support for GCP, AWS, Azure
- **Dynamic Input Forms**: Automatically generated forms based on plugin schemas
- **Auto-Credentials**: Cloud credentials automatically selected based on plugin provider

### 🚀 Infrastructure Provisioning
- **Pulumi Integration**: Infrastructure as Code using Pulumi
- **Async Processing**: Background job processing with Celery
- **Real-time Status**: Live updates on provisioning progress
- **Job History**: Complete history of provisioning jobs
- **Error Handling**: Detailed error messages and retry capabilities

### 🔔 Notifications
- **Real-time Updates**: Get notified about provisioning status
- **Smart Polling**: Optimized API calls (30s intervals, visibility-aware)
- **Unread Tracking**: Mark notifications as read
- **Action Links**: Direct links to related resources

### 🔒 Authentication & Security
- **JWT Tokens**: Secure authentication with access and refresh tokens
- **HTTP-only Cookies**: Refresh tokens stored securely
- **Auto-refresh**: Seamless token renewal
- **Session Management**: Multi-device support with independent sessions
- **Password Security**: Bcrypt hashing with secure password policies

### 🎨 Modern UI/UX
- **Dark Mode**: Full dark mode support
- **Responsive Design**: Works on all device sizes
- **Real-time Search**: Debounced search with backend filtering
- **Loading States**: Clear feedback for all operations
- **Toast Notifications**: User-friendly success/error messages

## 🏗️ Architecture

### Backend Stack
- **Framework**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Authorization**: Casbin RBAC engine
- **Task Queue**: Celery with Redis/RabbitMQ
- **IaC**: Pulumi for infrastructure provisioning
- **Package Manager**: UV (fast, modern Python package manager)

### Frontend Stack
- **Framework**: React 18 + TypeScript
- **Build Tool**: Vite
- **Routing**: React Router v6
- **State Management**: React Context + Hooks
- **Styling**: Tailwind CSS
- **Icons**: Lucide React

### Security
- **Authentication**: JWT with 15min access + 7day refresh tokens
- **Authorization**: Casbin policy-based access control
- **CORS**: Configured for development and production
- **HTTPS**: Support for secure cookies in production

## 📦 Installation

### 1. Install UV Package Manager
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Clone Repository
```bash
git clone <repository-url>
cd devplatform-idp
```

### 3. Backend Setup
```bash
cd backend

# Install dependencies
uv sync

# Create .env file
cat > .env << EOF
DATABASE_URL=postgresql://sajjad@localhost:5432/devplatform_idp
SECRET_KEY=your-secret-key-min-32-characters-long-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
PULUMI_ACCESS_TOKEN=your-pulumi-token
EOF

# Setup PostgreSQL database
createdb devplatform_idp

# Run migrations (tables are auto-created on startup)
# Initialize default data
uv run python -c "from app.core.db_init import init_db; import asyncio; asyncio.run(init_db())"
```

### 4. Frontend Setup
```bash
cd frontend
npm install

# Create .env file
echo "VITE_API_URL=http://localhost:8000" > .env
```

### 5. Start Services
```bash
# Terminal 1: Backend
cd backend && uv run uvicorn app.main:app --reload

# Terminal 2: Celery Worker
cd backend && uv run celery -A app.worker worker --loglevel=info

# Terminal 3: Frontend
cd frontend && npm run dev
```

## 🧪 Testing

### Default Credentials
- **Admin User**: Created automatically on first run
  - Check console logs for credentials

### Quick Test Flow
1. Login with admin credentials
2. Navigate to "Users" → Create a new user (no role required)
3. Navigate to "Groups" → Create a group (e.g., "DevOps Team")
4. Navigate to "Roles" → View available roles
5. Assign the group to a role (e.g., "engineer")
6. Add the user to the group
7. User now has all permissions from the "engineer" role!

## 🎯 Permission System

### Permission Hierarchy
```
User → Groups → Roles → Permissions
```

### Available Permissions
- **Users**: `users:list`, `users:create`, `users:update`, `users:delete`
- **Groups**: `groups:list`, `groups:create`, `groups:update`, `groups:delete`, `groups:manage`
- **Roles**: `roles:list`, `roles:create`, `roles:update`, `roles:delete`
- **Deployments**: `deployments:list`, `deployments:create`, `deployments:update`, `deployments:delete`
- **Plugins**: `plugins:list`, `plugins:upload`, `plugins:delete`
- **Profile**: `profile:read`, `profile:update`

### Example: Complex Permission Setup
```
1. Create "Cloud Admins" group → Assign "admin" role
2. Create "Backend Team" group → Assign "engineer" role
3. Create "DevOps Team" group → Assign custom "devops" role
4. Add user "Alice" to both "Backend Team" AND "DevOps Team"
   → Alice gets permissions from BOTH roles!
```

## 🔧 Troubleshooting

### Backend Issues

**"Field required" error:**
```bash
cd backend
cat .env  # Verify .env exists and has all required fields
```

**Database connection error:**
```bash
psql -d postgres -c "SELECT 1;"
createdb devplatform_idp  # If database doesn't exist
```

**Casbin permission errors:**
```bash
# Check Casbin policies
cd backend
uv run python -c "from app.core.casbin import get_enforcer; e = get_enforcer(); print(e.get_policy())"
```

### Frontend Issues

**CORS error:**
- Ensure `.env` has correct backend URL
- Check backend `.env` includes frontend URL in `CORS_ORIGINS`

**Authentication loop:**
- Clear browser localStorage
- Check if backend is running
- Verify cookies are being set (check browser DevTools)

## 📚 Documentation

- **API Documentation**: http://localhost:8000/docs
- **Group Management**: See `GROUP_MANAGEMENT_IMPLEMENTATION.md`
- **Credentials**: See `GLOBAL_CREDENTIALS_IMPLEMENTATION.md`

## 🚦 Production Deployment

### Security Checklist
- [ ] Change `SECRET_KEY` to a strong random value (32+ characters)
- [ ] Set `secure=True` for cookies in `backend/app/api/v1/auth.py`
- [ ] Use HTTPS for all connections
- [ ] Use a production-grade database (not localhost)
- [ ] Set up proper CORS origins (remove localhost)
- [ ] Configure proper logging and monitoring
- [ ] Set up database backups
- [ ] Use environment variables for all secrets
- [ ] Enable rate limiting
- [ ] Configure firewall rules

## 🤝 Contributing

This is a production-ready IDP. Contributions are welcome!

## 📄 License

[Your License Here]

## 🙏 Acknowledgments

- FastAPI for the excellent Python web framework
- Casbin for the powerful authorization engine
- Pulumi for infrastructure as code
- The entire open-source community
