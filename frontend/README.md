# DevPlatform IDP Frontend

React-based frontend for the DevPlatform IDP (Internal Developer Platform).

## Tech Stack

- **React 19** with TypeScript
- **Vite** - Build tool and dev server
- **React Router v7** - Client-side routing
- **Tailwind CSS** - Styling (via CDN)
- **Lucide React** - Icons

## Prerequisites

- Node.js v18+
- npm or yarn

## Setup

1. Install dependencies:
   ```bash
   npm install
   ```

2. Create `.env` file (if not exists):
   ```bash
   echo "VITE_API_URL=http://localhost:8000" > .env
   ```

3. Start development server:
   ```bash
   npm run dev
   ```

The frontend will be available at `http://localhost:5173` (or the port specified by Vite).

## Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build

## Project Structure

```
frontend/
├── components/          # Reusable React components
│   ├── Layout.tsx      # Main layout wrapper
│   ├── ProtectedRoute.tsx
│   └── ...
├── contexts/           # React Context providers
│   ├── AuthContext.tsx
│   └── NotificationContext.tsx
├── pages/              # Page components
│   ├── Login.tsx
│   ├── Dashboard.tsx
│   └── ...
├── services/           # API client services
│   └── api/           # Modular API clients
└── types.ts           # TypeScript type definitions
```

## API Integration

The frontend communicates with the backend API at the URL specified in `VITE_API_URL`. The API client handles:
- JWT token authentication
- Automatic token refresh
- Error handling
- Request/response interceptors

## Features

- User authentication and authorization
- RBAC-based access control
- Plugin catalog and management
- Infrastructure provisioning
- Real-time notifications
- Dark mode support

## Development

The frontend uses Vite for fast HMR (Hot Module Replacement). Changes to React components will automatically reload in the browser.

For API development, ensure the backend is running on the port specified in `VITE_API_URL`.
