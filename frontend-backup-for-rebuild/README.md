# Frontend Backup - Current Working Version

**Created:** October 20, 2025
**Purpose:** Reference files for frontend rebuild by another Replit agent

## What's Included

This backup contains the complete, working React/TypeScript frontend:

### Source Files (`src/`)
- **Components (21 files):** All React components including:
  - `App.tsx` - Main application with auth routing
  - `AuthModal.tsx` - Login/Register UI
  - `DCLGraphContainer.tsx` - Data Connection Layer visualization
  - `LiveSankeyGraph.tsx` - Sankey diagram for data flow
  - `DashboardPage.tsx` - Main dashboard
  - `TopBar.tsx` - Navigation with logout
  - And 15 other components

- **Contexts:** 
  - `AuthContext.tsx` - Global authentication state
  - `AutonomyContext.tsx` - Legacy/Modern mode toggle

- **Hooks:**
  - `useAuth.ts` - Authentication hook
  - `useDCLState.ts` - DCL state management with dual-backend routing

- **Services:**
  - `aoaApi.ts` - API service for AOA backend with JWT auth

- **Config:**
  - `api.ts` - API base URLs and constants

### Configuration Files
- `package.json` - Dependencies and scripts
- `package-lock.json` - Locked dependency versions
- `tsconfig.json` - TypeScript configuration
- `vite.config.ts` - Vite build configuration
- `index.html` - Entry HTML file

## Key Architecture Features

### Dual-Backend Authentication
- **Modern Mode:** Requires JWT auth, routes to AOA Backend
- **Legacy Mode:** No auth required, routes to Legacy DCL Backend
- Conditional routing in `useDCLState.ts` and `DCLGraphContainer.tsx`

### Authentication Flow
1. User accesses app → `AuthContext` checks for JWT token
2. No token → `AuthModal` shown (login/register)
3. Successful auth → JWT stored in localStorage (30min expiry)
4. All API calls include `Authorization: Bearer <token>` header
5. 401 response → auto-logout and re-login prompt

### Component Structure
```
App.tsx (AuthProvider + AutonomyProvider wrapper)
├── AuthModal (if not authenticated)
└── AppLayout (if authenticated)
    ├── LeftNav
    ├── TopBar (with logout)
    └── Page Content
        ├── DashboardPage
        │   └── DCLGraphContainer
        │       └── LiveSankeyGraph
        ├── DataLineagePage
        ├── ConnectionsPage
        └── xAOPage
```

## Backend URLs (from `config/api.ts`)
- **AOA Backend:** `https://fea934a4-524f-4747-b7ae-c8f06ccd5465-00-19fd0ilimncdg.picard.replit.dev`
- **Legacy DCL:** `https://58361fb5-3a0e-4a4b-bb9f-53f9e64295d0-00-2vdl3eq0bn7l7.picard.replit.dev`

## Installation & Build
```bash
cd frontend-backup-for-rebuild
npm install
npm run dev    # Development server
npm run build  # Production build
```

## Important Notes
- This is a **working snapshot** as of the backup date
- The authentication integration is complete and functional
- Legacy mode toggle allows switching between auth/no-auth modes
- All files are TypeScript/TSX with proper type definitions
