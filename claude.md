# Claude.md - AutonomOS Platform Guide

## Project Overview

AutonomOS is a **full-stack AI orchestration platform** for autonomous data integration, mapping, and multi-agent coordination. It provides enterprise-grade agent lifecycle management, workflow orchestration, and real-time monitoring.

## Tech Stack

### Backend (Python)
- **Framework**: FastAPI 0.119.0 with Uvicorn
- **Database**: PostgreSQL with SQLAlchemy 2.0+ ORM, pgvector for embeddings
- **Migrations**: Alembic
- **Task Queue**: Redis + RQ (Redis Queue)
- **Auth**: JWT (python-jose) + Argon2 password hashing
- **AI/ML**: Google Generative AI, OpenAI, Sentence Transformers
- **NLP/PII**: Microsoft Presidio

### Frontend (React)
- **Framework**: React 18.3.1 with TypeScript 5.5.3
- **Build**: Vite 7.1.11
- **Styling**: Tailwind CSS 3.4.1
- **UI Components**: Radix UI, Lucide React, Framer Motion
- **State**: React Context API (AutonomyContext, AuthContext)

## Directory Structure

```
/home/user/autonomos-platform/
├── app/                      # Main FastAPI backend
│   ├── api/v1/              # API route handlers (28 modules)
│   ├── agentic/             # Agent orchestration (22 subdirectories)
│   ├── models/              # SQLAlchemy models (split by domain)
│   ├── gateway/             # API gateway middleware
│   ├── main.py              # FastAPI app entry point
│   └── config.py            # Environment settings
├── frontend/                 # React/TypeScript frontend
│   ├── src/components/      # React components
│   ├── src/hooks/           # Custom React hooks
│   ├── src/contexts/        # React context providers
│   └── src/types/           # TypeScript type definitions
├── shared/                   # Shared utilities (database, Redis)
├── services/                 # Service layer (AAM, mapping, NLP)
├── aam_hybrid/              # Agent-to-Agent Mesh system
├── alembic/                 # Database migrations
├── scripts/                 # Operational scripts (60+)
└── tests/                   # Test suite
```

## Key Entry Points

| File | Purpose |
|------|---------|
| `app/main.py` | FastAPI application initialization, router registration |
| `frontend/src/main.tsx` | React app entry point |
| `frontend/src/App.tsx` | Root component with routing |
| `app/worker.py` | RQ background task worker |

## API Routes

All API routes are prefixed with `/api/v1/`. Key route groups:

| Prefix | Module | Purpose |
|--------|--------|---------|
| `/auth/` | `auth.py` | Authentication (login, register, tokens) |
| `/aoa/` | `aoa.py` | AOA orchestration, dashboard, events |
| `/aam/` | `aam_monitoring.py` | AAM monitoring, connectors |
| `/orchestration/` | `orchestration.py` | Dashboard data, vitals |
| `/agents/` | `agents.py` | Agent CRUD, runs, approvals |
| `/events/` | `events.py` | Event streaming |

## Database Models

Models are organized in `app/models/` by domain:

- `base.py` - SQLAlchemy Base and common utilities
- `tenant.py` - Tenant model (multi-tenant isolation)
- `user.py` - User model with tenant association
- `task.py` - Task and TaskLog models
- `agent.py` - Agent-related models
- `connection.py` - Connection and rate limit models
- `workflow.py` - Workflow models

All data is keyed by `tenant_id` (UUID) for multi-tenant isolation.

## Frontend Pages

| Route | Component | Purpose |
|-------|-----------|---------|
| `/aos-overview` | `AOSOverviewPage` | Main dashboard |
| `/orchestration` | `OrchestrationDashboard` | Agent orchestration UI |
| `/discover` | `DiscoverPage` | Data discovery |
| `/connect` | `ConnectPage` | Connector management |
| `/nlq` | `NLQPage` | Natural language queries |
| `/demo` | `DemoPage` | Demo pipeline |

## Configuration

### Environment Variables

Key environment variables (see `.env.example`):

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/autonomos

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Auth
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256

# Rate Limiting
RATE_LIMIT_READ_RPM=300
RATE_LIMIT_WRITE_RPM=100

# External Services
AOD_BASE_URL=http://localhost:8001
```

### Rate Limiting

Rate limits are configured in `app/gateway/middleware/rate_limit.py`:

- **GET requests**: 300/min + 60 burst
- **POST/PUT/DELETE**: 100/min + 30 burst
- **Exempt paths**: `/api/v1/orchestration/`, `/api/v1/aoa/`, `/static/`

## Code Conventions

### Python Backend

1. **API Routes**: Use FastAPI routers, group by feature
2. **Error Handling**: Use `HTTPException` with appropriate status codes
3. **Type Hints**: Use Pydantic for request/response validation
4. **Logging**: Use `logging.getLogger(__name__)`
5. **Async**: Prefer `async def` for I/O-bound operations

### TypeScript Frontend

1. **Components**: Functional components with hooks
2. **State**: Use React Context for global state
3. **Types**: Define interfaces in `types/index.ts`
4. **Styling**: Tailwind CSS utility classes
5. **API Calls**: Use native `fetch` with error handling

### Naming Conventions

- **Files**: snake_case for Python, PascalCase for React components
- **Functions**: snake_case for Python, camelCase for TypeScript
- **Classes**: PascalCase
- **Constants**: UPPER_SNAKE_CASE

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_api.py

# Note: Tests disable rate limiting via TESTING=true env var
```

## Common Tasks

### Adding a New API Endpoint

1. Create/update route handler in `app/api/v1/`
2. Add Pydantic schemas in `app/schemas/`
3. Register router in `app/main.py` if new module
4. Update frontend API calls if needed

### Adding a New Frontend Page

1. Create component in `frontend/src/components/`
2. Add lazy import in `App.tsx`
3. Add route case in `renderPage()` switch
4. Update `validPages` array in `getInitialPage()`

### Database Migrations

```bash
# Create migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Known Issues & Tech Debt

### Recently Addressed
- SQL injection in migrations (fixed)
- Bare `except:` clauses (fixed)
- Monolithic `models.py` (split into domain modules)
- Monolithic `aam_monitoring.py` (split into focused modules)
- Missing `/aoa/dashboard` and `/aoa/events` endpoints (added)

### Remaining
- Some frontend components still use mock `Math.random()` data
- EventSource SSE reconnection can be aggressive
- 8 TODO markers for Phase 2 features remain in code

## Important Files to Know

| File | Why It Matters |
|------|----------------|
| `app/main.py` | App initialization, all router registrations |
| `app/models/__init__.py` | Re-exports all models for imports |
| `app/config.py` | All environment variable settings |
| `app/security.py` | Auth, JWT, password hashing |
| `shared/redis_client.py` | Redis connection management |
| `frontend/src/App.tsx` | React routing and page structure |
| `frontend/src/contexts/AutonomyContext.tsx` | Global autonomy mode state |

## Debugging Tips

1. **Check logs**: Backend logs to stdout, look for `[DEBUG]`, `[ERROR]` prefixes
2. **API issues**: Check `/docs` for Swagger UI, test endpoints directly
3. **Frontend blank screen**: Check browser console for JS errors
4. **Rate limiting**: Check Redis keys with `redis-cli KEYS "ratelimit:*"`
5. **Database**: Use `alembic current` to verify migration state

## Build & Deploy

```bash
# Development
cd frontend && npm run dev  # Frontend on :5000
uvicorn app.main:app --reload  # Backend on :8000

# Production build
./build.sh  # Builds frontend to /static, installs deps

# Docker
docker-compose up
```
