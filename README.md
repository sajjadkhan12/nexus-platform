# DevPlatform IDP - Quick Start Guide

## Running the Application

### Option 1: With Centralized Logging (Recommended)

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
source venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

## Access Points

- **Frontend**: http://localhost:3000 (or http://localhost:5173)
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## Default Login Credentials

## Quick Test

1. Open http://localhost:3000 (or http://localhost:5173)
2. Login with admin credentials
3. Navigate to "My Deployments"
4. Create a new deployment
5. Logout and login as engineer
6. Verify you only see your own deployments

## Troubleshooting

### Backend won't start - "Field required" error

The `.env` file might not be loading. Verify it exists:
```bash
cd backend
cat .env
```

If missing, recreate it:
```bash
cd backend
python3 -c "
with open('.env', 'w') as f:
    f.write('DATABASE_URL=postgresql://sajjad@localhost:5432/devplatform_idp\n')
    f.write('SECRET_KEY=dev-secret-key-change-in-production-min-32-characters-long\n')
    f.write('ALGORITHM=HS256\n')
    f.write('ACCESS_TOKEN_EXPIRE_MINUTES=15\n')
    f.write('REFRESH_TOKEN_EXPIRE_DAYS=7\n')
    f.write('CORS_ORIGINS=http://localhost:5173,http://localhost:3000\n')
"
```

### CORS Error

Make sure the `.env` file includes both ports:
```
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

### Database Connection Error

Ensure PostgreSQL is running and the database exists:
```bash
psql -d postgres -c "SELECT 1;"
psql -d devplatform_idp -c "SELECT COUNT(*) FROM users;"
```

## Features

- ✅ JWT Authentication with auto-refresh
- ✅ Role-Based Access Control (RBAC)
- ✅ Protected Routes
- ✅ Real-time API Integration
- ✅ User Profile Management
- ✅ Deployment CRUD Operations
- ✅ Centralized Logging

## Architecture

**Backend:** FastAPI + PostgreSQL + JWT  
**Frontend:** React + TypeScript + Vite  
**Auth:** JWT tokens (15min access, 7day refresh)  
**Database:** PostgreSQL with SQLAlchemy ORM
