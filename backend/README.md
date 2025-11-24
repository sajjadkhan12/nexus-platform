# DevPlatform IDP Backend

FastAPI backend with JWT authentication and RBAC for the Internal Developer Platform.

## Setup

### 1. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Mac/Linux
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Setup PostgreSQL Database

Make sure PostgreSQL is running locally. Then create the database and tables:

```bash
psql -U postgres -f schema.sql
```

Or manually:
```bash
psql -U postgres
CREATE DATABASE devplatform_idp;
\c devplatform_idp
# Then run the SQL from schema.sql
```

### 4. Configure Environment

Copy `.env.example` to `.env` and update if needed:

```bash
cp .env.example .env
```

### 5. Run the Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

## API Documentation

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Default Users

Two default users are created:

**Admin User:**
- Email: `admin@devplatform.com`
- Password: `admin123`
- Role: `admin`

**Engineer User:**
- Email: `engineer@devplatform.com`
- Password: `engineer123`
- Role: `engineer`

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login
- `POST /api/v1/auth/refresh` - Refresh access token
- `POST /api/v1/auth/logout` - Logout

### Users
- `GET /api/v1/users/me` - Get current user profile
- `PUT /api/v1/users/me` - Update current user profile
- `POST /api/v1/users/me/password` - Change password
- `POST /api/v1/users/me/avatar` - Upload avatar
- `GET /api/v1/users` - List all users (admin only, supports search & role filters)
- `GET /api/v1/users/{user_id}` - Get user by ID
- `PUT /api/v1/users/{user_id}` - Update user (admin only, supports role & password reset)
- `PUT /api/v1/users/{user_id}/role` - Update user role (admin only)

### Deployments
- `GET /api/v1/deployments` - List deployments (filtered by role)
- `GET /api/v1/deployments/{id}` - Get deployment by ID
- `POST /api/v1/deployments` - Create deployment
- `PUT /api/v1/deployments/{id}` - Update deployment
- `DELETE /api/v1/deployments/{id}` - Delete deployment

## RBAC Permissions

### Admin Role
- Full access to all resources
- Can manage users and roles
- Can view all deployments
- Can manage plugins and settings

### Engineer Role
- Can create deployments
- Can only view/edit/delete own deployments
- Cannot manage users or roles
- Cannot manage plugins or settings

## Testing

Test the API using the Swagger UI at `http://localhost:8000/docs` or use curl:

```bash
# Register a new user
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "username": "testuser",
    "password": "password123",
    "full_name": "Test User"
  }'

# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@devplatform.com",
    "password": "admin123"
  }'

# Use the access token in subsequent requests
curl -X GET http://localhost:8000/api/v1/users/me \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```
