# AutonomOS Platform - Complete Remediation Plan
**Version**: 2.0 FINAL  
**Date**: November 14, 2025  
**Scope**: All 65 identified issues across platform  
**Approach**: Foundation-first, then scale

---

## Executive Summary

**Total Issues**: 65 (11 Critical, 23 High, 31 Medium)  
**Philosophy**: Fix foundational architecture first, then build on solid ground  
**Phases**: 7 major phases covering entire platform

**Critical Success Factor**: Phase 1 (Foundation) MUST complete before others - it unblocks everything else.

---

# PHASE 0: Emergency Security & Stability
**Duration**: 1 week  
**Goal**: Stop active security/performance issues immediately  
**Blockers**: None - can start immediately  
**Team**: 1 senior engineer

## Issues Addressed
- **C1**: Authentication disabled on DCL
- **C8**: Frontend archive bloat (1,237 lines)
- **C11**: Dead code cleanup
- **H8**: Pydantic V2 warnings
- **H9**: Rate limiting unused

## Detailed Tasks

### Day 1-2: Critical Security
**Task 1.1: Enable DCL Authentication with Development Suspension (4 hours)**

**CRITICAL**: The suspension logic must be implemented INSIDE the `get_current_user` dependency to return a mock user when auth is disabled. Otherwise, endpoints will crash trying to access `current_user.tenant_id`.

```python
# app/security.py (implement suspension logic HERE)
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import os
import logging

logger = logging.getLogger(__name__)

# Mock user for development
class MockUser:
    def __init__(self, tenant_id, user_id, email):
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.email = email
        self.id = user_id

# Configuration check
AUTH_ENABLED = os.getenv('DCL_AUTH_ENABLED', 'true').lower() == 'true'

# auto_error=False allows us to handle missing tokens manually
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)

def get_current_user(token: str | None = Depends(oauth2_scheme)):
    """
    Dependency that returns current user.
    If AUTH_ENABLED=false (dev mode), returns mock user.
    If AUTH_ENABLED=true (prod), validates JWT and returns real user.
    """
    if not AUTH_ENABLED:
        # Development mode - return mock user
        logger.warning("⚠️  Authentication disabled. Using MockUser for development.")
        return MockUser(
            tenant_id="default-dev-tenant",
            user_id="dev-001",
            email="dev@localhost"
        )
    
    # Production mode - require valid JWT
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Authorization header missing.",
        )
    
    # Validate JWT and fetch user
    try:
        # ... JWT validation logic ...
        user = decode_token_and_fetch_user(token)
        return user
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {str(e)}",
        )
```

```python
# app/dcl_engine/app.py
# Add to ALL DCL endpoints:
from app.security import get_current_user
from fastapi import Depends

@dcl_app.get("/state")
async def get_state(current_user = Depends(get_current_user)):
    tenant_id = current_user.tenant_id  # Works in both dev and prod!
    # ... existing logic using tenant_id
```

**Files to Modify**:
- `app/security.py` - Add MockUser class and suspension logic
- `app/dcl_engine/app.py` - Add auth dependency to 24 endpoints
- `.env.local` - Add `DCL_AUTH_ENABLED=false` for local development
- Test: Verify 401 on unauthenticated requests (prod mode)
- Test: Verify mock user works (dev mode)
- Test: Verify tenant isolation (user A can't see user B's data)

**Success Criteria**:
- ✅ All `/dcl/*` endpoints require valid JWT (when AUTH_ENABLED=true)
- ✅ Dev mode works seamlessly (when AUTH_ENABLED=false)
- ✅ WebSocket connections check auth on handshake
- ✅ Multi-tenant test passes (see test below)

**Test Script**:
```python
# tests/test_dcl_auth.py
import os
import pytest

def test_dcl_auth_required_in_production():
    """Test that auth is enforced when enabled"""
    os.environ['DCL_AUTH_ENABLED'] = 'true'
    
    response = client.get("/dcl/state")
    assert response.status_code == 401
    assert "Authentication required" in response.json()["detail"]

def test_dev_mode_uses_mock_user():
    """Test that dev mode allows unauthenticated access"""
    os.environ['DCL_AUTH_ENABLED'] = 'false'
    
    response = client.get("/dcl/state")
    assert response.status_code == 200
    # Should work without token, using mock user

def test_tenant_isolation():
    """Test that tenants cannot see each other's data"""
    os.environ['DCL_AUTH_ENABLED'] = 'true'
    
    # Create two tenants
    user_a = create_test_user(tenant_id="tenant-a")
    user_b = create_test_user(tenant_id="tenant-b")
    
    # User A creates graph
    token_a = get_jwt_token(user_a)
    client.post("/dcl/connect", headers={"Authorization": f"Bearer {token_a}"})
    
    # User B shouldn't see User A's graph
    token_b = get_jwt_token(user_b)
    response = client.get("/dcl/state", headers={"Authorization": f"Bearer {token_b}"})
    assert response.json()["nodes"] == []  # Empty for user B
```

**Developer Experience**:
```bash
# Local development (no auth required)
echo "DCL_AUTH_ENABLED=false" >> .env.local

# Production/staging (auth required)
echo "DCL_AUTH_ENABLED=true" >> .env
```

---

**Task 1.2: Implement Rate Limiting (4 hours)**
```python
# app/middleware/rate_limit.py (NEW FILE)
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)

# app/main.py
from app.middleware.rate_limit import limiter

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# app/dcl_engine/app.py
from app.middleware.rate_limit import limiter

@dcl_app.post("/toggle_aam_mode")
@limiter.limit("5/minute")  # Max 5 toggles per minute
async def toggle_mode(...):
    ...

@dcl_app.post("/connect")
@limiter.limit("10/minute")  # Max 10 connect calls per minute
async def connect(...):
    ...
```

**Dependencies to Add**:
```bash
pip install slowapi
```

**Success Criteria**:
- ✅ Toggle endpoint returns 429 after 5 requests in 1 minute
- ✅ Connect endpoint returns 429 after 10 requests in 1 minute
- ✅ Different users have separate rate limit counters

---

### Day 3: Frontend Cleanup

**Task 3.1: Delete Archive Folder (30 minutes)**
```bash
# Verify no imports first
grep -r "from.*archive" frontend/src/
grep -r "import.*archive" frontend/src/

# If clean, delete
rm -rf frontend/src/components/archive/

# Update .gitignore if needed
echo "# Archived components removed 2025-11-14" >> .gitignore

# Rebuild to verify
cd frontend && npm run build
```

**Success Criteria**:
- ✅ Archive folder deleted
- ✅ Build succeeds without errors
- ✅ Bundle size reduced by ~200KB

---

**Task 3.2: Fix Pydantic V2 Warnings (1 hour)**
```python
# Find all instances
grep -r "schema_extra" app/ aam_hybrid/

# Update each file:
# BEFORE
class Config:
    schema_extra = {"example": {...}}

# AFTER
class Config:
    json_schema_extra = {"example": {...}}
```

**Files to Update**:
- `app/schemas/connection_intent.py`
- `app/api/v1/aam_connections.py`
- `app/api/v1/aam_monitoring.py`

**Success Criteria**:
- ✅ No Pydantic warnings on startup
- ✅ OpenAPI docs still render correctly

---

### Day 4-5: Mode Toggle Fix

**Task 4.1: Add Request Debouncing (8 hours)**
```typescript
// frontend/src/hooks/useDCLState.ts

const [isToggling, setIsToggling] = useState(false);
const toggleTimeoutRef = useRef<NodeJS.Timeout>();

const toggleMode = useCallback(async () => {
  // Prevent rapid-fire calls
  if (isToggling) {
    console.log('Toggle already in progress, ignoring');
    return;
  }
  
  // Clear any pending toggle
  if (toggleTimeoutRef.current) {
    clearTimeout(toggleTimeoutRef.current);
  }
  
  // Debounce: wait 500ms before actual toggle
  toggleTimeoutRef.current = setTimeout(async () => {
    setIsToggling(true);
    try {
      await fetch('/dcl/toggle_aam_mode', { method: 'POST' });
      // Don't refetch - WebSocket will update state
    } catch (error) {
      console.error('Toggle failed:', error);
    } finally {
      setIsToggling(false);
    }
  }, 500);
}, [isToggling]);
```

**Backend Changes**:
```python
# app/dcl_engine/app.py

# Add request deduplication
_active_toggle_requests = {}  # tenant_id -> timestamp

@dcl_app.post("/toggle_aam_mode")
async def toggle_mode(current_user = Depends(get_current_user)):
    tenant_id = current_user.tenant_id
    
    # Deduplicate concurrent requests
    now = time.time()
    last_toggle = _active_toggle_requests.get(tenant_id, 0)
    
    if now - last_toggle < 1.0:  # Ignore if < 1 second since last toggle
        logger.info(f"Ignoring duplicate toggle for {tenant_id}")
        return {"status": "debounced"}
    
    _active_toggle_requests[tenant_id] = now
    
    # ... rest of toggle logic
```

**Success Criteria**:
- ✅ Toggle completes in < 1 second (p95)
- ✅ No duplicate API calls in logs
- ✅ WebSocket receives exactly 1 event per toggle

---

## Phase 0 Deliverables
- ✅ All DCL endpoints authenticated
- ✅ Rate limiting enforced
- ✅ Archive folder deleted, bundle optimized
- ✅ No Pydantic warnings
- ✅ Toggle latency < 1 second
- ✅ Test suite for auth & rate limiting

**Exit Criteria**: All tests pass, production deployment ready from security perspective

---

# PHASE 1: Foundation Architecture
**Duration**: 5 weeks  
**Goal**: Fix core architectural issues blocking scalability  
**Blockers**: None (can start after Phase 0)  
**Team**: 2 senior engineers  
**CRITICAL**: Everything else depends on this phase

## Issues Addressed
- **C2**: Dual base architecture
- **C5**: sys.path manipulation (50+ instances)
- **C9**: Circular imports (app ↔ aam_hybrid)
- **C10**: Three SQLAlchemy Bases causing Alembic conflicts
- **M27**: Hardcoded database names
- **M31**: Environment-specific configs mixed

## Overview
This is the MOST IMPORTANT phase. It fixes foundational problems that block all future work:
- Consolidates `app/` and `aam_hybrid/` into single package
- Eliminates all sys.path hacks
- Creates single SQLAlchemy Base
- Breaks circular dependencies
- Makes codebase pip-installable

---

## Week 1: Planning & Inventory

### Task 1.1: Complete Code Audit
**Create inventory of current structure**:
```bash
# Document all imports
python scripts/audit_imports.py > /tmp/import_map.json

# Document all models
python scripts/audit_models.py > /tmp/model_inventory.json

# Document all sys.path manipulations
grep -rn "sys.path" . > /tmp/syspath_inventory.txt
```

**Deliverable**: Complete map of dependencies

---

### Task 1.2: Design New Package Structure
**Target Structure**:
```
workspace/
  ├── pyproject.toml           # Package definition
  ├── setup.py                 # Build script
  └── autonomos/               # Single unified package
      ├── __init__.py
      ├── database/
      │   ├── __init__.py
      │   ├── base.py          # SINGLE Base for all models
      │   ├── session.py       # Session factories
      │   └── engine.py        # Database engine config
      ├── models/
      │   ├── __init__.py
      │   ├── app_models.py    # User, Task, ApiJournal, etc.
      │   ├── aam_models.py    # Connection, JobHistory, etc.
      │   └── nlp_models.py    # Knowledge base, etc.
      ├── api/
      │   ├── __init__.py
      │   └── v1/
      │       ├── __init__.py
      │       ├── auth.py
      │       ├── aoa.py
      │       ├── aam_monitoring.py
      │       └── ...
      ├── services/
      │   ├── __init__.py
      │   ├── dcl/
      │   │   ├── __init__.py
      │   │   ├── state_service.py
      │   │   ├── connection_service.py
      │   │   ├── mapping_service.py
      │   │   └── graph_service.py
      │   ├── aam/
      │   │   ├── __init__.py
      │   │   ├── monitoring/
      │   │   ├── connectors/
      │   │   └── repair/
      │   └── nlp_gateway/
      │       └── ...
      ├── shared/
      │   ├── __init__.py
      │   ├── event_bus.py
      │   ├── redis_client.py
      │   └── config.py
      ├── config/
      │   ├── __init__.py
      │   ├── settings.py      # Centralized config
      │   └── feature_flags.py
      └── utils/
          ├── __init__.py
          └── ...
```

**Key Principles**:
1. Single package: `autonomos`
2. All imports: `from autonomos.X import Y`
3. No relative imports across major boundaries
4. Clear hierarchy: api → services → models → database

---

### Task 1.3: Create Migration Plan
**Database Migration Strategy**:
```python
# Step 1: Inventory existing tables
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public';

# Step 2: Create consolidated base.py
# autonomos/database/base.py
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()  # SINGLE shared base

# Step 3: Import ALL models in one place
# alembic/env.py
from autonomos.models.app_models import *
from autonomos.models.aam_models import *
from autonomos.models.nlp_models import *
from autonomos.database.base import Base

target_metadata = Base.metadata  # Now sees ALL tables

# Step 4: Generate baseline migration
alembic revision --autogenerate -m "Consolidate to single Base"

# Step 5: Review migration (should show no changes if done right)
# Step 6: Mark as applied without executing
alembic stamp head
```

**Safety Check**:
```sql
-- Before migration
SELECT table_name, column_name, data_type 
FROM information_schema.columns 
WHERE table_schema = 'public'
ORDER BY table_name, ordinal_position;

-- Save output, compare after migration
-- Tables should be IDENTICAL
```

---

## Week 2: Create New Package Structure

### Task 2.1: Set Up Package Definition
```toml
# pyproject.toml
[project]
name = "autonomos"
version = "1.0.0"
description = "Multi-tenant AI orchestration platform"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.104.0",
    "uvicorn>=0.24.0",
    "sqlalchemy>=2.0.0",
    "alembic>=1.12.0",
    "pydantic>=2.0.0",
    "redis>=5.0.0",
    "httpx>=0.25.0",
    # ... all other dependencies
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0",
    "pytest-cov>=4.1.0",
    "mypy>=1.7.0",
    "ruff>=0.1.0",
]

[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["."]
include = ["autonomos*"]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = "test_*.py"
python_classes = "Test*"
python_functions = "test_*"
asyncio_mode = "auto"

[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
```

---

### Task 2.2: Create Database Foundation
```python
# autonomos/database/__init__.py
from .base import Base
from .session import SessionLocal, AsyncSessionLocal, get_db, get_async_db
from .engine import engine, async_engine

__all__ = [
    "Base",
    "SessionLocal",
    "AsyncSessionLocal",
    "get_db",
    "get_async_db",
    "engine",
    "async_engine",
]

# autonomos/database/base.py
from sqlalchemy.ext.declarative import declarative_base

# SINGLE Base for entire platform
Base = declarative_base()

# autonomos/database/engine.py
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine
from autonomos.config.settings import settings

# Sync engine (for RQ workers, scripts)
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=20,
    max_overflow=10,
)

# Async engine (for FastAPI endpoints)
async_engine = create_async_engine(
    settings.ASYNC_DATABASE_URL,
    pool_pre_ping=True,
    pool_size=20,
    max_overflow=10,
)

# autonomos/database/session.py
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from .engine import engine, async_engine

# Sync session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    engine=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# FastAPI dependency
async def get_async_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

def get_db():
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
```

---

### Task 2.3: Consolidate All Models
```python
# autonomos/models/__init__.py
from .app_models import User, Task, ApiJournal, RateLimitCounter
from .aam_models import Connection, JobHistory, SyncCatalogVersion
from .nlp_models import KnowledgeBase, EmbeddingCache

__all__ = [
    # App models
    "User", "Task", "ApiJournal", "RateLimitCounter",
    # AAM models
    "Connection", "JobHistory", "SyncCatalogVersion",
    # NLP models
    "KnowledgeBase", "EmbeddingCache",
]

# autonomos/models/app_models.py
from autonomos.database.base import Base
from sqlalchemy import Column, String, Integer, DateTime, JSON
import uuid

class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, nullable=False, index=True)
    email = Column(String, unique=True, nullable=False)
    # ... rest of fields

# autonomos/models/aam_models.py
from autonomos.database.base import Base
from sqlalchemy import Column, String, Integer, Enum
from enum import Enum as PyEnum

class ConnectionStatus(PyEnum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    FAILED = "FAILED"
    HEALING = "HEALING"
    INACTIVE = "INACTIVE"

class Connection(Base):
    __tablename__ = "connections"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, nullable=False, index=True)
    status = Column(Enum(ConnectionStatus), nullable=False)
    # ... rest of fields

# autonomos/models/nlp_models.py
from autonomos.database.base import Base
# ... similar pattern
```

**Success Criteria**:
- ✅ Single Base imported everywhere
- ✅ All models reference same Base
- ✅ No duplicate table definitions

---

## Week 3: Migrate Codebase to New Structure

### Task 3.1: Move Files Systematically
**Order of Operations** (critical to avoid breakage):

**Step 1: Create new structure** (don't delete old yet)
```bash
mkdir -p autonomos/database
mkdir -p autonomos/models
mkdir -p autonomos/api/v1
mkdir -p autonomos/services/{dcl,aam,nlp_gateway}
mkdir -p autonomos/shared
mkdir -p autonomos/config
```

**Step 2: Copy and adapt files**
```bash
# Example: Move app/models.py → autonomos/models/app_models.py
# Update all imports:
# OLD: from app.database import Base
# NEW: from autonomos.database.base import Base

# Use script for bulk updates:
python scripts/migrate_imports.py app/models.py autonomos/models/app_models.py
```

**Step 3: Update all imports across codebase**
```bash
# Find all imports of old structure
grep -r "from app.models import" .
grep -r "from aam_hybrid.shared.models import" .

# Replace with new structure
# Use automated script:
python scripts/update_all_imports.py
```

**Step 4: Verify imports**
```bash
# Try importing the package
python -c "from autonomos.models import User, Connection"
python -c "from autonomos.database import Base"

# Should work without sys.path hacks!
```

---

### Task 3.2: Remove ALL sys.path Manipulations
**Find and Remove** (50+ instances):
```bash
# Find all sys.path manipulations
grep -rn "sys.path.insert\|sys.path.append" . > /tmp/syspath_locations.txt

# For each file:
# 1. Remove sys.path lines
# 2. Update imports to use autonomos package
# 3. Test that imports still work

# Example:
# BEFORE
sys.path.insert(0, str(Path(__file__).parent.parent))
from core.repair_agent import RepairAgent

# AFTER
from autonomos.services.aam.repair import RepairAgent
```

**Verification Script**:
```python
# scripts/verify_no_syspath.py
import ast
import sys
from pathlib import Path

def check_file(filepath):
    with open(filepath) as f:
        tree = ast.parse(f.read())
    
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Name):
                if node.value.id == 'sys' and node.attr == 'path':
                    return False  # Found sys.path usage!
    return True

# Check all Python files
for py_file in Path('.').rglob('*.py'):
    if not check_file(py_file):
        print(f"❌ {py_file} still uses sys.path")
        sys.exit(1)

print("✅ No sys.path manipulations found!")
```

---

### Task 3.3: Update Alembic Configuration
```python
# alembic/env.py

# OLD (tracked multiple Bases)
from app.models import Base as AppBase
from aam_hybrid.shared.models import Base as AAMBase

for table in AppBase.metadata.tables.values():
    # ...
for table in AAMBase.metadata.tables.values():
    # ...

# NEW (single Base)
from autonomos.database.base import Base
from autonomos.models import *  # Import all models to register with Base

target_metadata = Base.metadata  # Single source of truth
```

**Test Migration**:
```bash
# Generate migration to verify no changes
alembic revision --autogenerate -m "Verify consolidated Base"

# Should show: "No changes detected"
# If it shows DROP/CREATE, something is wrong!
```

---

## Week 4: Break Circular Dependencies

### Task 4.1: Identify All Circular Imports
**Automated Detection**:
```bash
# Use pycycle to detect cycles
pip install pycycle
pycycle --verbose autonomos/

# Manually trace critical paths
python scripts/trace_imports.py autonomos/database/
python scripts/trace_imports.py autonomos/services/
```

---

### Task 4.2: Restructure to Break Cycles
**Current Problem**:
```
autonomos/database/session.py
  → imports autonomos/models/app_models.py (for type hints)
    → imports autonomos/database/base.py
      → imports autonomos/config/settings.py
        → imports autonomos/database/session.py  # CIRCULAR!
```

**Solution**:
```python
# Use TYPE_CHECKING to avoid runtime circular imports

# autonomos/database/session.py
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from autonomos.models.app_models import User  # Only for type checking

# Actual import moved to function scope if needed
def get_user_session(user_id: str):
    from autonomos.models.app_models import User  # Runtime import
    # ...
```

**Alternative**: Dependency injection
```python
# Don't import at module level
# Pass dependencies as function parameters

# BAD
from autonomos.database.session import SessionLocal
session = SessionLocal()  # Module-level

# GOOD
def process_data(db: Session = Depends(get_db)):
    # db injected, no circular import
```

---

### Task 4.3: Verify No Circular Imports
```bash
# Import every module to test
python -c "import autonomos.api.v1.aoa"
python -c "import autonomos.services.dcl.state_service"
python -c "import autonomos.database.session"

# Should all succeed without errors

# Run pycycle again
pycycle autonomos/
# Should show: "No cycles detected"
```

---

## Week 5: Testing & Migration

### Task 5.1: Update All Import Statements
**Bulk Update Script**:
```python
# scripts/update_imports.py
import re
from pathlib import Path

replacements = {
    r'from app\.models import': 'from autonomos.models.app_models import',
    r'from app\.database import': 'from autonomos.database import',
    r'from aam_hybrid\.shared\.models import': 'from autonomos.models.aam_models import',
    r'from aam_hybrid\.core\.': 'from autonomos.services.aam.',
    # ... add all patterns
}

for py_file in Path('autonomos').rglob('*.py'):
    content = py_file.read_text()
    
    for old, new in replacements.items():
        content = re.sub(old, new, content)
    
    py_file.write_text(content)
```

---

### Task 5.2: Make Package Installable
```bash
# Install in editable mode
pip install -e .

# Verify install
pip show autonomos

# Test imports from anywhere
cd /tmp
python -c "from autonomos.models import User"
python -c "from autonomos.services.dcl import DCLStateService"

# Should work without sys.path or PYTHONPATH
```

---

### Task 5.3: Update All Scripts
```python
# OLD scripts pattern
# scripts/seed_demo.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from app.models import User

# NEW pattern
# scripts/seed_demo.py
from autonomos.models import User
from autonomos.database import SessionLocal

# Just works!
```

---

### Task 5.4: Database Migration Execution
```bash
# Safety first - backup database
pg_dump $DATABASE_URL > backup_before_base_consolidation.sql

# Generate migration with new consolidated Base
alembic revision --autogenerate -m "Consolidate to single Base"

# Review migration file carefully
# Should show NO DROP TABLES
# If it does, STOP and debug

# If clean (no destructive changes):
alembic upgrade head

# Verify tables still exist
psql $DATABASE_URL -c "\dt"
```

---

## Phase 1 Deliverables
- ✅ Single `autonomos/` package structure
- ✅ Zero sys.path manipulations (down from 50+)
- ✅ Single SQLAlchemy Base (down from 3)
- ✅ No circular imports
- ✅ Package is pip-installable
- ✅ Alembic tracks all models correctly
- ✅ All tests pass with new structure
- ✅ Database migrations safe and tested

**Exit Criteria**:
```bash
# These should all pass
pip install -e .
python -c "import autonomos"
pycycle autonomos/  # No cycles
pytest tests/  # All tests pass
alembic check  # No pending migrations
```

**CRITICAL**: This phase unblocks ALL subsequent work. Don't skip or rush it.

---

# PHASE 2: Service Decomposition & Decoupling
**Duration**: 4 weeks  
**Goal**: Break monolithic files, eliminate tight coupling  
**Blockers**: Requires Phase 1 complete  
**Team**: 2 engineers (1 backend, 1 full-stack)

## Issues Addressed
- **C3**: Monolithic AAM Monitoring (1,468 lines)
- **C4**: Tight HTTP coupling (AOA → DCL)
- **C6**: Global state beyond DCL
- **M1**: 3,236-line DCL monolith
- **M2**: Duplicate connector logic
- **M8**: No dependency injection
- **M16**: Duplicate WebSocket logic

---

## Week 1: Extract AAM Monitoring Services

### Task 1.1: Design Service Architecture
**Current**: 1,468 lines, 6 mixed responsibilities  
**Target**: 5 focused services, each < 300 lines

**New Structure**:
```
autonomos/services/aam/monitoring/
  ├── __init__.py
  ├── api.py                 # 15 REST endpoints (150 lines)
  ├── airbyte_client.py      # Airbyte API integration (200 lines)
  ├── cache_service.py       # Caching logic with TTL (100 lines)
  ├── sync_tracker.py        # Sync activity tracking (150 lines)
  └── schemas.py             # Pydantic models (100 lines)
```

---

### Task 1.2: Extract Airbyte Client
```python
# autonomos/services/aam/monitoring/airbyte_client.py

from typing import List, Dict, Any, Optional
import httpx
from autonomos.config.settings import settings

class AirbyteClient:
    """Client for Airbyte API interactions"""
    
    def __init__(self):
        self.base_url = settings.AIRBYTE_URL
        self.workspace_id = settings.AIRBYTE_WORKSPACE_ID
    
    async def get_connection_jobs(
        self, 
        connection_id: str, 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get recent jobs for a connection"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/v1/jobs/list",
                json={
                    "configTypes": ["sync"],
                    "configId": connection_id,
                    "pagination": {"pageSize": limit}
                },
                headers=self._get_headers()
            )
            response.raise_for_status()
            data = response.json()
            return data.get("jobs", [])
    
    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {settings.AIRBYTE_API_KEY}",
            "Content-Type": "application/json"
        }

# Singleton instance
airbyte_client = AirbyteClient()
```

---

### Task 1.3: Extract Cache Service
```python
# autonomos/services/aam/monitoring/cache_service.py

from typing import Dict, Any, Optional
import time
from dataclasses import dataclass

@dataclass
class CacheEntry:
    data: Dict[str, Any]
    cached_at: float
    ttl: int

class SyncActivityCache:
    """TTL-based cache for Airbyte sync activity"""
    
    def __init__(self, default_ttl: int = 60):
        self._cache: Dict[str, CacheEntry] = {}
        self._default_ttl = default_ttl
    
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get cached value if not expired"""
        entry = self._cache.get(key)
        if not entry:
            return None
        
        if time.time() - entry.cached_at > entry.ttl:
            # Expired, remove
            del self._cache[key]
            return None
        
        return entry.data
    
    def set(
        self, 
        key: str, 
        data: Dict[str, Any],
        ttl: Optional[int] = None
    ):
        """Cache value with TTL"""
        self._cache[key] = CacheEntry(
            data=data,
            cached_at=time.time(),
            ttl=ttl or self._default_ttl
        )
    
    def clear(self):
        """Clear all cache"""
        self._cache.clear()

# Singleton instance
sync_cache = SyncActivityCache(default_ttl=60)
```

---

### Task 1.4: Extract Sync Tracker Service
```python
# autonomos/services/aam/monitoring/sync_tracker.py

from typing import Dict, Any, Optional
from datetime import datetime
from .airbyte_client import airbyte_client
from .cache_service import sync_cache

class SyncActivityTracker:
    """Tracks Airbyte sync activity with caching"""
    
    async def get_latest_sync(
        self, 
        connection_id: Optional[str]
    ) -> Dict[str, Any]:
        """Get latest sync activity for connection"""
        
        # Default empty response
        default = {
            "status": None,
            "records": None,
            "bytes": None,
            "timestamp": None
        }
        
        if not connection_id:
            return default
        
        # Check cache
        cached = sync_cache.get(connection_id)
        if cached:
            return cached
        
        # Fetch from Airbyte
        try:
            jobs = await airbyte_client.get_connection_jobs(
                connection_id, 
                limit=10
            )
            
            if not jobs:
                sync_cache.set(connection_id, default)
                return default
            
            # Get most recent job with data
            latest = self._find_latest_job_with_data(jobs)
            
            result = {
                "status": latest.get("status", "").lower(),
                "records": latest.get("recordsCommitted", 0),
                "bytes": latest.get("bytesCommitted", 0),
                "timestamp": self._parse_timestamp(latest.get("createdAt"))
            }
            
            # Cache result
            sync_cache.set(connection_id, result, ttl=60)
            return result
            
        except Exception as e:
            logger.error(f"Failed to fetch sync activity: {e}")
            return default
    
    def _find_latest_job_with_data(self, jobs: list) -> dict:
        """Find most recent job that has actual data"""
        sorted_jobs = sorted(
            jobs,
            key=lambda j: j.get('createdAt', ''),
            reverse=True
        )
        
        for job in sorted_jobs:
            if job.get('recordsCommitted', 0) > 0:
                return job
        
        return sorted_jobs[0] if sorted_jobs else {}
    
    def _parse_timestamp(self, ts_str: Optional[str]) -> Optional[datetime]:
        """Parse ISO timestamp"""
        if not ts_str:
            return None
        try:
            return datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
        except:
            return None

# Singleton instance
sync_tracker = SyncActivityTracker()
```

---

### Task 1.5: Refactor API Endpoints
```python
# autonomos/services/aam/monitoring/api.py

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from autonomos.database import get_async_db
from .sync_tracker import sync_tracker
from .schemas import ConnectorDTO, ConnectorsResponse

router = APIRouter(prefix="/aam", tags=["AAM Monitoring"])

@router.get("/connectors", response_model=ConnectorsResponse)
async def get_connectors(
    db: AsyncSession = Depends(get_async_db)
):
    """Get all connectors with drift and sync metadata"""
    
    # Query connectors from database
    result = await db.execute(
        select(Connection).where(Connection.tenant_id == current_user.tenant_id)
    )
    connections = result.scalars().all()
    
    # Enrich with sync activity
    enriched = []
    for conn in connections:
        # Get sync activity (cached)
        sync_activity = await sync_tracker.get_latest_sync(
            conn.airbyte_connection_id
        )
        
        enriched.append(ConnectorDTO(
            id=conn.id,
            name=conn.name,
            source_type=conn.source_type,
            status=conn.status,
            mapping_count=len(conn.mappings),
            has_drift=conn.has_active_drift,
            last_sync_status=sync_activity["status"],
            last_sync_records=sync_activity["records"],
            last_sync_bytes=sync_activity["bytes"],
            last_sync_at=sync_activity["timestamp"],
        ))
    
    return ConnectorsResponse(
        connectors=enriched,
        total=len(enriched)
    )
```

**Success Criteria**:
- ✅ All files < 300 lines
- ✅ Single responsibility per class
- ✅ No module-level globals
- ✅ Dependency injection used throughout
- ✅ Tests for each service

---

## Week 2: Decouple AOA from DCL

### Task 2.1: Create Shared DCL Service
**Problem**: AOA makes HTTP calls to DCL localhost  
**Solution**: Shared service layer

```python
# autonomos/services/dcl/__init__.py
from .state_service import DCLStateService
from .connection_service import DCLConnectionService

# autonomos/services/dcl/state_service.py

from typing import Dict, Any
from autonomos.shared.redis_client import get_redis_client

class DCLStateService:
    """Shared service for DCL state management"""
    
    def __init__(self, redis_client):
        self.redis = redis_client
    
    async def get_state(self, tenant_id: str) -> Dict[str, Any]:
        """Get tenant's DCL graph state"""
        key = f"dcl:graph_state:{tenant_id}"
        data = await self.redis.get(key)
        
        if not data:
            return {"nodes": [], "edges": []}
        
        return json.loads(data)
    
    async def save_state(self, tenant_id: str, state: Dict[str, Any]):
        """Save tenant's DCL graph state"""
        key = f"dcl:graph_state:{tenant_id}"
        await self.redis.set(key, json.dumps(state))
    
    async def clear_state(self, tenant_id: str):
        """Clear tenant's DCL state"""
        key = f"dcl:graph_state:{tenant_id}"
        await self.redis.delete(key)

# Dependency injection
async def get_dcl_state_service():
    redis = await get_redis_client()
    return DCLStateService(redis)
```

---

### Task 2.2: Update AOA to Use Service
```python
# autonomos/api/v1/aoa.py

# BEFORE (HTTP coupling)
async with httpx.AsyncClient() as client:
    response = await client.get("http://localhost:5000/dcl/state")
    return response.json()

# AFTER (shared service)
from autonomos.services.dcl import DCLStateService

@router.get("/state")
async def get_aoa_state(
    dcl_service: DCLStateService = Depends(get_dcl_state_service),
    current_user: models.User = Depends(get_current_user)
):
    """Get AOA state via shared service (no HTTP call)"""
    return await dcl_service.get_state(current_user.tenant_id)
```

**Success Criteria**:
- ✅ Zero HTTP calls between AOA and DCL
- ✅ Both services can deploy independently
- ✅ Shared service tested in isolation
- ✅ No hardcoded URLs

---

## Week 3: Decompose DCL Monolith

### Task 3.1: Split DCL Engine (3,236 → 8 files)
**Target Structure**:
```
autonomos/services/dcl/
  ├── api.py                  # REST endpoints (300 lines)
  ├── state_service.py        # State management (200 lines)
  ├── connection_service.py   # Source connection (400 lines)
  ├── mapping_service.py      # Entity mapping (400 lines)
  ├── graph_service.py        # Graph generation (350 lines)
  ├── llm_service.py          # LLM interactions (300 lines)
  ├── rag_service.py          # RAG retrieval (250 lines)
  └── websocket_handler.py    # WebSocket events (200 lines)
```

---

### Task 3.2: Extract Services
**Follow same pattern as AAM monitoring**:
1. Create service class
2. Move business logic from endpoints
3. Add dependency injection
4. Write unit tests
5. Update endpoints to use service

---

## Week 4: Eliminate Global State

### Task 4.1: Convert Globals to Tenant-Scoped Services
**Pattern for all global state**:
```python
# BEFORE (DCL global state)
GRAPH_STATE = {}  # Shared across tenants
DEV_MODE = False

# AFTER (tenant-scoped service)
class DCLStateService:
    def __init__(self, redis_client):
        self.redis = redis_client
    
    async def get_graph(self, tenant_id: str) -> dict:
        key = f"dcl:graph:{tenant_id}"
        data = await self.redis.get(key)
        return json.loads(data) if data else {}
    
    async def get_dev_mode(self, tenant_id: str) -> bool:
        key = f"dcl:dev_mode:{tenant_id}"
        return await self.redis.get(key) == "true"
```

**Apply to All Globals**:
- DCL: `GRAPH_STATE`, `DEV_MODE`, `SOURCE_SCHEMAS`, etc.
- AAM Monitoring: `_airbyte_cache`
- AOA: `redis_conn`, `task_queue`

---

## Phase 2 Deliverables
- ✅ AAM Monitoring split into 5 services (down from 1,468-line monolith)
- ✅ DCL Engine split into 8 services (down from 3,236-line monolith)
- ✅ Zero HTTP coupling between services
- ✅ Zero module-level globals
- ✅ All services use dependency injection
- ✅ All files < 500 lines
- ✅ Services independently testable

**Exit Criteria**:
- No file > 500 lines
- All services deployable independently
- Load test with 10 concurrent tenants (no data bleed)

---

# PHASE 3: Test Infrastructure
**Duration**: 4 weeks  
**Goal**: 80% test coverage across platform  
**Blockers**: Requires Phase 2 complete (services decomposed)  
**Team**: 2 engineers (1 backend, 1 QA)

## Issues Addressed
- **C7**: No test infrastructure
- **M9**: Test coverage gaps
- **M18**: No E2E tests

---

## Week 1: Test Framework Setup

### Task 1.1: Configure pytest
```python
# tests/conftest.py

import pytest
import asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from autonomos.database.base import Base
from autonomos.config.settings import settings

# Test database URL
TEST_DATABASE_URL = settings.TEST_DATABASE_URL or "postgresql://test:test@localhost/autonomos_test"

# Sync engine for setup/teardown
sync_engine = create_engine(TEST_DATABASE_URL)
TestSessionLocal = sessionmaker(bind=sync_engine)

# Async engine for tests
async_engine = create_async_engine(TEST_DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"))
TestAsyncSessionLocal = sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="function")
async def db():
    """Provide test database session"""
    # Create tables
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Provide session
    async with TestAsyncSessionLocal() as session:
        yield session
    
    # Cleanup
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture(scope="function")
async def test_tenant():
    """Create test tenant"""
    from autonomos.models import User
    
    tenant_id = f"test-tenant-{uuid.uuid4()}"
    user = User(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        email="test@example.com",
        hashed_password="hashed"
    )
    
    return user

@pytest.fixture
async def authenticated_client(test_tenant):
    """Provide authenticated test client"""
    from httpx import AsyncClient
    from autonomos.main import app
    from autonomos.security import create_access_token
    
    token = create_access_token({"sub": test_tenant.id})
    
    async with AsyncClient(
        app=app,
        base_url="http://test",
        headers={"Authorization": f"Bearer {token}"}
    ) as client:
        yield client
```

---

### Task 1.2: Configure Coverage
```toml
# pyproject.toml

[tool.coverage.run]
source = ["autonomos"]
omit = [
    "*/tests/*",
    "*/migrations/*",
    "*/__pycache__/*",
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "if TYPE_CHECKING:",
]
```

---

## Week 2: Unit Tests

### Task 2.1: Test Database Models
```python
# tests/unit/test_models.py

import pytest
from autonomos.models import User, Connection, Task

@pytest.mark.asyncio
async def test_user_creation(db):
    """Test creating a user"""
    user = User(
        id="test-user-1",
        tenant_id="tenant-1",
        email="test@example.com",
        hashed_password="hashed"
    )
    
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    assert user.id == "test-user-1"
    assert user.email == "test@example.com"

@pytest.mark.asyncio
async def test_connection_status_enum(db):
    """Test connection status enum"""
    from autonomos.models.aam_models import ConnectionStatus
    
    connection = Connection(
        id="conn-1",
        tenant_id="tenant-1",
        source_type="salesforce",
        status=ConnectionStatus.ACTIVE
    )
    
    db.add(connection)
    await db.commit()
    
    assert connection.status == ConnectionStatus.ACTIVE
```

---

### Task 2.2: Test Services
```python
# tests/unit/test_dcl_state_service.py

import pytest
from unittest.mock import Mock, AsyncMock
from autonomos.services.dcl import DCLStateService

@pytest.mark.asyncio
async def test_get_state_empty():
    """Test getting empty state"""
    # Mock Redis
    redis_mock = AsyncMock()
    redis_mock.get.return_value = None
    
    service = DCLStateService(redis_mock)
    state = await service.get_state("tenant-1")
    
    assert state == {"nodes": [], "edges": []}
    redis_mock.get.assert_called_once_with("dcl:graph_state:tenant-1")

@pytest.mark.asyncio
async def test_save_state():
    """Test saving state"""
    redis_mock = AsyncMock()
    
    service = DCLStateService(redis_mock)
    await service.save_state("tenant-1", {"nodes": [{"id": "1"}]})
    
    redis_mock.set.assert_called_once()
    call_args = redis_mock.set.call_args
    assert call_args[0][0] == "dcl:graph_state:tenant-1"
    assert '"nodes"' in call_args[0][1]  # JSON string
```

---

## Week 3: Integration Tests

### Task 3.1: Test API Endpoints
```python
# tests/integration/test_dcl_api.py

import pytest

@pytest.mark.asyncio
async def test_get_state_requires_auth():
    """Test DCL state endpoint requires authentication"""
    from httpx import AsyncClient
    from autonomos.main import app
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/dcl/state")
        assert response.status_code == 401

@pytest.mark.asyncio
async def test_toggle_mode(authenticated_client, test_tenant):
    """Test mode toggle endpoint"""
    response = await authenticated_client.post("/dcl/toggle_aam_mode")
    
    assert response.status_code == 200
    data = response.json()
    assert "use_aam" in data

@pytest.mark.asyncio
async def test_connect_sources(authenticated_client, test_tenant):
    """Test connecting sources"""
    response = await authenticated_client.post(
        "/dcl/connect",
        params={
            "sources": "salesforce,filesource",
            "agents": "mapper"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "nodes" in data
    assert len(data["nodes"]) > 0
```

---

### Task 3.2: Test Multi-Tenant Isolation
```python
# tests/integration/test_tenant_isolation.py

import pytest
from autonomos.models import User

@pytest.mark.asyncio
async def test_tenant_data_isolation(db):
    """Test that tenants cannot see each other's data"""
    
    # Create two tenants
    tenant_a = User(
        id="user-a",
        tenant_id="tenant-a",
        email="a@example.com",
        hashed_password="hash"
    )
    tenant_b = User(
        id="user-b",
        tenant_id="tenant-b",
        email="b@example.com",
        hashed_password="hash"
    )
    
    db.add_all([tenant_a, tenant_b])
    await db.commit()
    
    # Tenant A creates state
    from autonomos.services.dcl import DCLStateService
    redis_mock = AsyncMock()
    service = DCLStateService(redis_mock)
    
    await service.save_state("tenant-a", {"nodes": [{"id": "a-node"}]})
    
    # Tenant B should see empty state
    state_b = await service.get_state("tenant-b")
    assert state_b == {"nodes": [], "edges": []}
    
    # Tenant A should see their state
    redis_mock.get.return_value = json.dumps({"nodes": [{"id": "a-node"}]})
    state_a = await service.get_state("tenant-a")
    assert len(state_a["nodes"]) == 1
```

---

## Week 4: E2E Tests

### Task 4.1: Test Full Workflows
```python
# tests/e2e/test_dcl_workflow.py

import pytest

@pytest.mark.asyncio
async def test_full_dcl_workflow(authenticated_client):
    """Test complete DCL workflow from start to finish"""
    
    # Step 1: Get initial state (should be empty)
    response = await authenticated_client.get("/dcl/state")
    assert response.status_code == 200
    state = response.json()
    assert len(state.get("nodes", [])) == 0
    
    # Step 2: Toggle to AAM mode
    response = await authenticated_client.post("/dcl/toggle_aam_mode")
    assert response.status_code == 200
    
    # Step 3: Connect sources
    response = await authenticated_client.post(
        "/dcl/connect",
        params={"sources": "salesforce", "agents": "mapper"}
    )
    assert response.status_code == 200
    result = response.json()
    
    # Verify graph created
    assert len(result["nodes"]) > 0
    assert any(n["type"] == "source" for n in result["nodes"])
    assert any(n["type"] == "agent" for n in result["nodes"])
    
    # Step 4: Verify state persisted
    response = await authenticated_client.get("/dcl/state")
    state = response.json()
    assert len(state["nodes"]) > 0
    
    # Step 5: Reset
    response = await authenticated_client.post("/dcl/reset")
    assert response.status_code == 200
    
    # Step 6: Verify state cleared
    response = await authenticated_client.get("/dcl/state")
    state = response.json()
    assert len(state.get("nodes", [])) == 0
```

---

## Phase 3 Deliverables
- ✅ Comprehensive test suite (unit, integration, E2E)
- ✅ Test coverage > 80%
- ✅ CI/CD pipeline configured
- ✅ All tests pass
- ✅ Multi-tenant isolation verified
- ✅ Critical workflows tested

**Exit Criteria**:
```bash
pytest --cov=autonomos --cov-report=term-missing
# Should show > 80% coverage

pytest tests/ -v
# All tests pass
```

---

# PHASE 4: Observability & Monitoring
**Duration**: 3 weeks  
**Goal**: Production-grade observability  
**Blockers**: Requires Phase 2 (services decomposed)  
**Team**: 1 senior engineer

## Issues Addressed
- **H1**: No structured observability
- **H2**: Redis without pooling
- **H3**: Database connection management
- **H17**: No background task monitoring
- **M11**: No monitoring
- **M25**: Missing health checks

---

## Week 1: Structured Logging

### Task 1.1: Configure structlog
```python
# autonomos/config/logging.py

import structlog
import logging

def configure_logging():
    """Configure structured logging for the application"""
    
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()  # JSON output
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        level=logging.INFO,
    )

# autonomos/main.py
from autonomos.config.logging import configure_logging

configure_logging()
logger = structlog.get_logger()
```

---

### Task 1.2: Add Request ID Middleware
```python
# autonomos/middleware/request_id.py

import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import structlog

class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Get or generate request ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        
        # Bind to structlog context
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)
        
        # Add to response headers
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        
        return response

# autonomos/main.py
from autonomos.middleware.request_id import RequestIDMiddleware

app.add_middleware(RequestIDMiddleware)
```

---

### Task 1.3: Update All Logging Calls
```python
# BEFORE
logger.info("Mode toggle started")
logger.error(f"Toggle failed: {error}")

# AFTER
logger = structlog.get_logger()

logger.info(
    "mode_toggle_started",
    tenant_id=tenant_id,
    user_id=user_id,
    timestamp=datetime.utcnow().isoformat()
)

logger.error(
    "mode_toggle_failed",
    tenant_id=tenant_id,
    error=str(error),
    error_type=type(error).__name__
)
```

---

## Week 2: Metrics & Health Checks

### Task 2.1: Add Prometheus Metrics
```python
# autonomos/middleware/metrics.py

from prometheus_client import Counter, Histogram, Gauge, generate_latest
from fastapi import Request
import time

# Define metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration',
    ['method', 'endpoint']
)

dcl_active_tenants = Gauge(
    'dcl_active_tenants',
    'Number of active tenants'
)

dcl_graph_nodes = Gauge(
    'dcl_graph_nodes',
    'Total nodes in DCL graphs',
    ['tenant_id']
)

# Middleware
class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.time()
        
        response = await call_next(request)
        
        duration = time.time() - start
        
        http_requests_total.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code
        ).inc()
        
        http_request_duration_seconds.labels(
            method=request.method,
            endpoint=request.url.path
        ).observe(duration)
        
        return response

# Metrics endpoint
@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")
```

---

### Task 2.2: Add Health Check Endpoints
```python
# autonomos/api/v1/health.py

from fastapi import APIRouter, status
from autonomos.database import async_engine
from autonomos.shared.redis_client import get_redis_client

router = APIRouter(tags=["Health"])

@router.get("/health")
async def health_check():
    """Basic health check"""
    return {"status": "healthy"}

@router.get("/health/ready")
async def readiness_check():
    """Readiness check - verifies dependencies"""
    checks = {}
    
    # Check database
    try:
        async with async_engine.connect() as conn:
            await conn.execute("SELECT 1")
        checks["database"] = "healthy"
    except Exception as e:
        checks["database"] = f"unhealthy: {str(e)}"
    
    # Check Redis
    try:
        redis = await get_redis_client()
        await redis.ping()
        checks["redis"] = "healthy"
    except Exception as e:
        checks["redis"] = f"unhealthy: {str(e)}"
    
    # Overall status
    all_healthy = all(v == "healthy" for v in checks.values())
    status_code = status.HTTP_200_OK if all_healthy else status.HTTP_503_SERVICE_UNAVAILABLE
    
    return JSONResponse(
        content={"status": "ready" if all_healthy else "not ready", "checks": checks},
        status_code=status_code
    )

@router.get("/health/live")
async def liveness_check():
    """Liveness check - just checks if app is running"""
    return {"status": "alive"}
```

---

## Week 3: Infrastructure Improvements

### Task 3.1: Redis Connection Pooling
```python
# autonomos/shared/redis_client.py

from redis.asyncio import Redis, ConnectionPool
from autonomos.config.settings import settings

_redis_pool = None

async def get_redis_pool() -> ConnectionPool:
    """Get or create Redis connection pool"""
    global _redis_pool
    
    if _redis_pool is None:
        _redis_pool = ConnectionPool.from_url(
            settings.REDIS_URL,
            max_connections=50,
            decode_responses=True,
            health_check_interval=30
        )
    
    return _redis_pool

async def get_redis_client() -> Redis:
    """Get Redis client from pool"""
    pool = await get_redis_pool()
    return Redis(connection_pool=pool)

# Replace all direct Redis() instantiations
# OLD: redis_client = Redis.from_url(...)
# NEW: redis_client = await get_redis_client()
```

---

### Task 3.2: Database Connection Pooling
```python
# autonomos/database/engine.py

from sqlalchemy.pool import NullPool, QueuePool

# Production config
async_engine = create_async_engine(
    settings.ASYNC_DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=3600,  # Recycle connections after 1 hour
)
```

---

## Phase 4 Deliverables
- ✅ Structured JSON logging
- ✅ Request ID propagation
- ✅ Prometheus metrics endpoint
- ✅ Health/readiness/liveness checks
- ✅ Redis connection pooling
- ✅ Database connection pooling
- ✅ Grafana dashboards (optional)

**Exit Criteria**:
- Logs are JSON formatted
- Every request has unique ID
- `/metrics` endpoint returns valid Prometheus metrics
- Health checks pass

---

# PHASE 5: Frontend Optimization
**Duration**: 2 weeks  
**Goal**: Clean state management, single source of truth  
**Blockers**: None  
**Team**: 1 frontend engineer

## Issues Addressed
- **H6**: Frontend state management chaos
- **M14**: Frontend bundle too large
- **M15**: No lazy loading
- **M16**: Duplicate WebSocket logic
- **M19**: Hardcoded strings (i18n prep)

---

## Week 1: State Consolidation

### Task 1.1: Create DCL Context
```typescript
// frontend/src/contexts/DCLContext.tsx

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';

interface DCLContextType {
  graph: GraphState;
  useAamMode: boolean;
  selectedSources: string[];
  selectedAgents: string[];
  isLoading: boolean;
  error: string | null;
  toggleMode: () => Promise<void>;
  connect: (sources: string[], agents: string[]) => Promise<void>;
  reset: () => Promise<void>;
}

const DCLContext = createContext<DCLContextType | null>(null);

export const DCLProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [graph, setGraph] = useState<GraphState>({ nodes: [], edges: [] });
  const [useAamMode, setUseAamMode] = useState(false);
  const [selectedSources, setSelectedSources] = useState<string[]>([]);
  const [selectedAgents, setSelectedAgents] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Single WebSocket connection
  useEffect(() => {
    const ws = new WebSocket('/dcl/ws');
    
    ws.addEventListener('message', (event) => {
      const data = JSON.parse(event.data);
      
      switch (data.type) {
        case 'aam_mode_toggled':
          setUseAamMode(data.enabled);
          break;
        case 'graph_updated':
          setGraph(data.graph);
          break;
        case 'state_reset':
          setGraph({ nodes: [], edges: [] });
          break;
      }
    });
    
    return () => ws.close();
  }, []);
  
  const toggleMode = useCallback(async () => {
    if (isLoading) return;
    
    setIsLoading(true);
    setError(null);
    
    try {
      await fetch('/dcl/toggle_aam_mode', { method: 'POST' });
      // WebSocket will update state
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  }, [isLoading]);
  
  const connect = useCallback(async (sources: string[], agents: string[]) => {
    setIsLoading(true);
    setError(null);
    
    try {
      const params = new URLSearchParams({
        sources: sources.join(','),
        agents: agents.join(',')
      });
      
      const response = await fetch(`/dcl/connect?${params}`, { method: 'POST' });
      const data = await response.json();
      
      setGraph(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  }, []);
  
  const reset = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      await fetch('/dcl/reset', { method: 'POST' });
      setGraph({ nodes: [], edges: [] });
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  }, []);
  
  return (
    <DCLContext.Provider value={{
      graph,
      useAamMode,
      selectedSources,
      selectedAgents,
      isLoading,
      error,
      toggleMode,
      connect,
      reset
    }}>
      {children}
    </DCLContext.Provider>
  );
};

export const useDCL = () => {
  const context = useContext(DCLContext);
  if (!context) {
    throw new Error('useDCL must be used within DCLProvider');
  }
  return context;
};
```

---

### Task 1.2: Refactor Components
```typescript
// frontend/src/components/NewOntologyPage.tsx

import { useDCL } from '../contexts/DCLContext';

export const NewOntologyPage = () => {
  const { graph, useAamMode, isLoading, toggleMode, connect } = useDCL();
  
  // Remove all localStorage logic
  // Remove duplicate WebSocket connections
  // Remove feature flag polling
  
  return (
    <div>
      <ModeToggle 
        checked={useAamMode} 
        onChange={toggleMode}
        disabled={isLoading}
      />
      
      <DCLGraphContainer graph={graph} />
    </div>
  );
};
```

---

## Week 2: Performance Optimization

### Task 2.1: Code Splitting
```typescript
// frontend/src/App.tsx

import { lazy, Suspense } from 'react';

const Dashboard = lazy(() => import('./pages/Dashboard'));
const NewOntologyPage = lazy(() => import('./pages/NewOntologyPage'));
const AAMConnections = lazy(() => import('./pages/AAMConnections'));

function App() {
  return (
    <Suspense fallback={<LoadingSpinner />}>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/ontology" element={<NewOntologyPage />} />
        <Route path="/connections" element={<AAMConnections />} />
      </Routes>
    </Suspense>
  );
}
```

---

### Task 2.2: Bundle Optimization
```javascript
// vite.config.ts

export default defineConfig({
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          'react-vendor': ['react', 'react-dom', 'react-router-dom'],
          'graph-vendor': ['reactflow'],
          'ui-vendor': ['@chakra-ui/react']
        }
      }
    }
  }
});
```

---

## Phase 5 Deliverables
- ✅ Single DCL Context (no duplicate state)
- ✅ Zero localStorage usage
- ✅ Single WebSocket connection
- ✅ Code splitting implemented
- ✅ Bundle size < 500KB (gzipped)
- ✅ Lazy loading for routes

---

# PHASE 6: Performance & Scalability
**Duration**: 2 weeks  
**Goal**: Handle 10x traffic  
**Blockers**: Requires Phase 2 (async refactor)  
**Team**: 1 senior engineer

## Issues Addressed
- **H4**: Blocking I/O on event loop
- **M13**: No query optimization
- **M28**: No circuit breakers

---

## Week 1: Async Refactoring

### Task 1.1: Convert Blocking I/O
```python
# BEFORE (blocks event loop)
import duckdb
conn = duckdb.connect()
df = pd.read_csv('file.csv')

# AFTER (runs in thread pool)
from fastapi.concurrency import run_in_threadpool

@dcl_app.post("/connect")
async def connect_sources(...):
    result = await run_in_threadpool(
        _connect_sources_blocking,
        sources,
        agents
    )
    return result

def _connect_sources_blocking(sources, agents):
    # Blocking operations here
    conn = duckdb.connect()
    # ...
```

---

### Task 1.2: Optimize Database Queries
```python
# Add indexes for common queries
# alembic/versions/xxx_add_indexes.py

def upgrade():
    op.create_index('idx_users_tenant_id', 'users', ['tenant_id'])
    op.create_index('idx_connections_tenant_id', 'connections', ['tenant_id'])
    op.create_index('idx_tasks_tenant_id_status', 'tasks', ['tenant_id', 'status'])

# Use eager loading
from sqlalchemy.orm import joinedload

users = await db.execute(
    select(User)
    .options(joinedload(User.tasks))
    .where(User.tenant_id == tenant_id)
)
```

---

## Week 2: Resilience

### Task 2.1: Add Circuit Breakers
```python
# autonomos/shared/circuit_breaker.py

from circuitbreaker import circuit

@circuit(failure_threshold=5, recovery_timeout=60)
async def call_external_api(url: str):
    """Call external API with circuit breaker"""
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()

# Use in services
# autonomos/services/aam/monitoring/airbyte_client.py

from autonomos.shared.circuit_breaker import circuit

class AirbyteClient:
    @circuit(failure_threshold=5, recovery_timeout=60)
    async def get_connection_jobs(self, connection_id: str):
        # ... API call
```

---

## Phase 6 Deliverables
- ✅ All blocking I/O wrapped in threadpool
- ✅ Database indexes optimized
- ✅ Circuit breakers on external calls
- ✅ Can handle 10x current traffic

---

# PHASE 7: Documentation & Handoff
**Duration**: 1 week  
**Goal**: Complete documentation for maintainers  
**Blockers**: All phases complete  
**Team**: 1 engineer + 1 technical writer

## Deliverables

### Week 1: Documentation

**API Documentation**:
- OpenAPI specs complete
- All endpoints documented
- Request/response examples
- Error codes documented

**Architecture Documentation**:
- Package structure explained
- Service boundaries defined
- Data flow diagrams
- Database schema documentation

**Operations Documentation**:
- Deployment guide
- Monitoring runbooks
- Incident response procedures
- Backup/restore procedures

**Developer Documentation**:
- Local setup guide
- Testing guide
- Contributing guide
- Code style guide

---

# OVERALL TIMELINE SUMMARY

| Phase | Duration | Dependencies | Team Size |
|-------|----------|--------------|-----------|
| **Phase 0: Emergency** | 1 week | None | 1 senior |
| **Phase 1: Foundation** | 5 weeks | Phase 0 | 2 senior |
| **Phase 2: Services** | 4 weeks | Phase 1 | 2 engineers |
| **Phase 3: Testing** | 4 weeks | Phase 2 | 2 engineers |
| **Phase 4: Observability** | 3 weeks | Phase 2 | 1 senior |
| **Phase 5: Frontend** | 2 weeks | None (parallel) | 1 frontend |
| **Phase 6: Performance** | 2 weeks | Phase 2 | 1 senior |
| **Phase 7: Docs** | 1 week | All phases | 2 people |
| **TOTAL** | **22 weeks (~5.5 months)** | | **Peak: 4 people** |

---

# SUCCESS CRITERIA BY PHASE

## Phase 0:
- ✅ Auth enabled, 401 on unauthenticated requests
- ✅ Rate limiting working
- ✅ Archive deleted
- ✅ Toggle < 1s

## Phase 1:
- ✅ `pip install -e .` works
- ✅ Zero sys.path calls
- ✅ Single Base
- ✅ No circular imports
- ✅ Alembic sees all models

## Phase 2:
- ✅ No file > 500 lines
- ✅ No HTTP coupling
- ✅ No globals
- ✅ Dependency injection everywhere

## Phase 3:
- ✅ 80% test coverage
- ✅ CI/CD passing
- ✅ Multi-tenant tested

## Phase 4:
- ✅ Structured logging
- ✅ Metrics endpoint
- ✅ Health checks pass

## Phase 5:
- ✅ Bundle < 500KB
- ✅ Single state source
- ✅ No localStorage

## Phase 6:
- ✅ All async
- ✅ Can handle 10x traffic

## Phase 7:
- ✅ All docs complete

---

# RISK MITIGATION

**Risk**: Phase 1 takes longer than expected  
**Mitigation**: This is the MOST IMPORTANT phase. Budget extra time. Don't rush.

**Risk**: Breaking changes during migration  
**Mitigation**: Feature flags, parallel implementation, extensive testing

**Risk**: Data loss during Base consolidation  
**Mitigation**: Database backups before every migration, dry-run migrations

**Risk**: Performance regression  
**Mitigation**: Benchmark before/after each phase, load testing

---

**END OF PLAN**

This plan addresses all 65 identified issues systematically. Phase 1 is critical - everything depends on it. Don't skip steps.

