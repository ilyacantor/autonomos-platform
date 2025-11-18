# AutonomOS Platform - Developer Guide

**Version:** 1.0  
**Last Updated:** November 18, 2025  
**Target Audience:** Software Engineers, Contributors

---

## Table of Contents

1. [Local Development Setup](#local-development-setup)
2. [Running Tests](#running-tests)
3. [Code Structure](#code-structure)
4. [Adding New Connectors](#adding-new-connectors)
5. [Extending RAG Intelligence](#extending-rag-intelligence)
6. [Database Migrations](#database-migrations)
7. [Frontend Development](#frontend-development)
8. [CI/CD Pipeline](#cicd-pipeline)
9. [Performance Benchmarking](#performance-benchmarking)
10. [Debugging Tips](#debugging-tips)

---

## Local Development Setup

### Prerequisites

```bash
# Verify prerequisites
python3 --version  # 3.11+
node --version     # 20+
git --version      # 2.x
```

### Step 1: Clone Repository

```bash
git clone https://github.com/your-org/autonomos.git
cd autonomos
```

### Step 2: Python Environment Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Development tools (pytest, black, etc.)
```

### Step 3: Environment Configuration

```bash
# Copy example .env
cp .env.example .env

# Edit .env with your credentials
vim .env

# Minimal .env for local development:
DATABASE_URL=postgresql://localhost:5432/autonomos_dev
REDIS_URL=redis://localhost:6379
JWT_SECRET_KEY=$(openssl rand -hex 32)
DCL_AUTH_ENABLED=false  # Disable auth for easier local dev
GOOGLE_API_KEY=your_gemini_api_key_here
```

### Step 4: Start Dependencies (Docker Compose)

```bash
# Start PostgreSQL + Redis
docker-compose up -d

# Verify services
docker ps
# Should show postgres and redis containers running
```

**Alternative:** Use local PostgreSQL and Redis:

```bash
# PostgreSQL
createdb autonomos_dev

# Redis
redis-server
```

### Step 5: Initialize Database

```bash
# Run migrations
alembic upgrade head

# Seed demo data (optional)
python3 scripts/provision_demo_tenant.py
python3 scripts/seed_aam_test_data.py
```

### Step 6: Start Backend

```bash
# Development server with auto-reload
uvicorn app.main:app --host 0.0.0.0 --port 5000 --reload

# Or use start script
bash start.sh
```

Visit http://localhost:5000/docs for interactive API documentation.

### Step 7: Start Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start dev server (Vite)
npm run dev

# Frontend available at http://localhost:3000
```

### Step 8: Start Background Workers

```bash
# Terminal 3: Start RQ worker
rq worker default --url redis://localhost:6379
```

---

## Running Tests

### Unit Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# View coverage report
open htmlcov/index.html
```

### Integration Tests

```bash
# Run integration tests (requires running services)
pytest tests/integration/

# Test specific module
pytest tests/integration/test_bulk_mappings.py
```

### Load Tests

```bash
# Run load test with 100 concurrent users
cd benchmarks
python3 run_load_test.py --profile=test --connectors=10 --jobs=5

# View results
cat results/latest.json
```

### Multi-Tenant Tests

```bash
# Test tenant isolation
pytest tests/multi_tenant/ -v

# Key tests:
# - test_tenant_data_isolation.py
# - test_tenant_job_isolation.py
# - test_redis_namespace_isolation.py
```

### Test Configuration

**pytest.ini:**
```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    --verbose
    --strict-markers
    --tb=short
    --cov=app
    --cov-report=term-missing

markers =
    unit: Unit tests
    integration: Integration tests
    slow: Slow-running tests
    multi_tenant: Multi-tenant isolation tests
```

### Running Specific Test Categories

```bash
# Unit tests only (fast)
pytest -m unit

# Integration tests (require running services)
pytest -m integration

# Skip slow tests
pytest -m "not slow"

# Multi-tenant tests
pytest -m multi_tenant
```

---

## Code Structure

### Project Layout

```
autonomos/
├── app/                          # Backend (FastAPI)
│   ├── main.py                   # Application entry point
│   ├── config.py                 # Settings and environment variables
│   ├── database.py               # SQLAlchemy setup
│   ├── models.py                 # Database models
│   ├── schemas.py                # Pydantic schemas
│   ├── crud.py                   # Database operations
│   ├── security.py               # Auth (JWT, Argon2)
│   ├── api/                      # REST endpoints
│   │   └── v1/
│   │       ├── auth.py           # /api/v1/auth
│   │       ├── aam_monitoring.py # /api/v1/aam/monitoring
│   │       ├── bulk_mappings.py  # /api/v1/bulk-mappings
│   │       ├── dcl_views.py      # /api/v1/dcl/views
│   │       └── ...
│   └── middleware/               # Request/response interceptors
│       ├── tracing.py
│       ├── rate_limit.py
│       └── audit_log.py
│
├── services/                     # Business logic services
│   ├── aam/                      # Adaptive API Mesh
│   │   ├── orchestrator.py      # Main orchestrator
│   │   ├── connectors/           # Data source adapters
│   │   │   ├── salesforce_connector.py
│   │   │   ├── supabase_connector.py
│   │   │   └── mongodb_connector.py
│   │   ├── drift_repair_agent.py # Schema drift detection
│   │   └── schema_observer.py    # Background schema monitoring
│   │
│   ├── mapping_intelligence/     # RAG-powered mapping
│   │   ├── job_processor.py      # RQ worker logic
│   │   ├── rag_matcher.py        # Semantic field matching
│   │   └── job_state.py          # Job state management (Redis)
│   │
│   ├── dcl/                      # Data Connection Layer
│   │   ├── graph_builder.py      # Build knowledge graph
│   │   ├── duckdb_engine.py      # Query engine
│   │   └── subscriber.py         # Event subscriber
│   │
│   └── nlp-gateway/              # NLP services
│       ├── api/
│       │   └── persona.py        # Persona classification
│       └── utils/
│           └── persona_classifier.py
│
├── shared/                       # Shared utilities
│   ├── redis_client.py           # Redis singleton
│   ├── database.py               # Database utilities
│   └── canonical_schema.py       # Pydantic canonical models
│
├── alembic/                      # Database migrations
│   ├── versions/                 # Migration scripts
│   └── env.py                    # Alembic environment
│
├── frontend/                     # React UI
│   ├── src/
│   │   ├── pages/                # Route components
│   │   │   ├── Home.tsx
│   │   │   ├── DCLGraph.tsx
│   │   │   └── AAMMonitor.tsx
│   │   ├── components/           # Reusable components
│   │   └── hooks/                # Custom React hooks
│   ├── public/
│   └── vite.config.ts
│
├── tests/                        # Test suite
│   ├── unit/
│   ├── integration/
│   └── multi_tenant/
│
├── scripts/                      # Utility scripts
│   ├── provision_demo_tenant.py
│   ├── seed_aam_test_data.py
│   └── job_reconciliation.py
│
├── benchmarks/                   # Performance testing
│   ├── run_load_test.py
│   └── baselines/
│
├── docs/                         # Documentation
│   ├── api/
│   ├── deployment/
│   ├── operations/
│   └── ...
│
├── requirements.txt              # Python dependencies
├── requirements-dev.txt          # Dev dependencies (pytest, black, etc.)
├── alembic.ini                   # Alembic configuration
├── docker-compose.yml            # Local dev services
└── start.sh                      # Startup script
```

### Code Conventions

**Python:**
- Follow PEP 8
- Use type hints (Python 3.10+)
- Max line length: 100 characters
- Use `black` for formatting
- Use `isort` for import sorting

**TypeScript/React:**
- Follow Airbnb style guide
- Use functional components + hooks
- Use TypeScript strict mode
- Use `prettier` for formatting

**Formatting:**

```bash
# Format Python code
black .
isort .

# Format TypeScript/React
cd frontend
npm run format
```

**Linting:**

```bash
# Lint Python
flake8 app/ services/ tests/

# Lint TypeScript
cd frontend
npm run lint
```

---

## Adding New Connectors

### Step 1: Create Connector Class

Create `services/aam/connectors/hubspot_connector.py`:

```python
from typing import List, Dict, Any
from .base_connector import BaseConnector
from shared.canonical_schema import CanonicalEvent, CanonicalAccount

class HubSpotConnector(BaseConnector):
    """
    HubSpot CRM connector for AutonomOS AAM.
    
    Connects to HubSpot API and normalizes to canonical schema.
    """
    
    def __init__(self, connection_id: str, config: Dict[str, Any]):
        super().__init__(connection_id, config)
        self.api_key = config.get("api_key")
        self.base_url = "https://api.hubapi.com"
    
    async def discover_schema(self) -> Dict[str, Any]:
        """
        Discover HubSpot account object schema.
        
        Returns:
            Schema with fields: name, domain, industry, etc.
        """
        # Example: GET /crm/v3/schemas/companies
        response = await self._api_request("GET", "/crm/v3/schemas/companies")
        return response["properties"]
    
    async def fetch_accounts(self, limit: int = 100) -> List[CanonicalEvent]:
        """
        Fetch accounts from HubSpot and normalize to canonical schema.
        """
        # Example: GET /crm/v3/objects/companies
        response = await self._api_request("GET", "/crm/v3/objects/companies", params={"limit": limit})
        
        canonical_events = []
        for company in response["results"]:
            # Map HubSpot fields to canonical schema
            canonical_account = CanonicalAccount(
                account_id=company["id"],
                name=company["properties"].get("name"),
                industry=company["properties"].get("industry"),
                # ... map other fields
            )
            
            canonical_event = CanonicalEvent(
                entity="account",
                data=canonical_account,
                meta={
                    "tenant_id": self.config.get("tenant_id"),
                    "trace_id": self._generate_trace_id()
                },
                source={
                    "system": "hubspot",
                    "connection_id": self.connection_id
                }
            )
            
            canonical_events.append(canonical_event)
        
        return canonical_events
    
    async def _api_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make authenticated API request to HubSpot."""
        import httpx
        
        headers = {"Authorization": f"Bearer {self.api_key}"}
        url = f"{self.base_url}{endpoint}"
        
        async with httpx.AsyncClient() as client:
            response = await client.request(method, url, headers=headers, **kwargs)
            response.raise_for_status()
            return response.json()
```

### Step 2: Register Connector

Add to `services/aam/connector_registry.py`:

```python
from .connectors.hubspot_connector import HubSpotConnector

CONNECTOR_REGISTRY = {
    "salesforce": SalesforceConnector,
    "supabase": SupabaseConnector,
    "mongodb": MongoDBConnector,
    "hubspot": HubSpotConnector,  # New connector
}
```

### Step 3: Create Field Mappings

Add to `services/aam/mappings/hubspot.yaml`:

```yaml
vendor: hubspot
entity_type: account
version: 1.0

mappings:
  - vendor_field: name
    canonical_field: account_name
    coercion: null
    confidence: 1.0
  
  - vendor_field: domain
    canonical_field: website
    coercion: lowercase
    confidence: 1.0
  
  - vendor_field: industry
    canonical_field: industry
    coercion: null
    confidence: 1.0
  
  - vendor_field: numberofemployees
    canonical_field: employee_count
    coercion: int
    confidence: 0.95
```

### Step 4: Write Tests

Create `tests/unit/test_hubspot_connector.py`:

```python
import pytest
from services.aam.connectors.hubspot_connector import HubSpotConnector

@pytest.mark.asyncio
async def test_hubspot_connector_fetch_accounts():
    """Test HubSpot connector can fetch and normalize accounts."""
    connector = HubSpotConnector(
        connection_id="test-hubspot",
        config={"api_key": "test_key", "tenant_id": "test-tenant"}
    )
    
    # Mock API response
    with patch.object(connector, "_api_request") as mock_api:
        mock_api.return_value = {
            "results": [
                {
                    "id": "12345",
                    "properties": {
                        "name": "Acme Corp",
                        "domain": "acme.com",
                        "industry": "Technology"
                    }
                }
            ]
        }
        
        events = await connector.fetch_accounts()
        
        assert len(events) == 1
        assert events[0].entity == "account"
        assert events[0].data.account_name == "Acme Corp"
        assert events[0].source["system"] == "hubspot"
```

### Step 5: Document Connector

Add to `docs/connectors/HUBSPOT.md`:

```markdown
# HubSpot Connector

## Setup

1. Create HubSpot private app: https://app.hubspot.com/settings/integrations/private-apps
2. Grant scopes: `crm.objects.companies.read`
3. Copy API token

## Configuration

```bash
# Add to .env
HUBSPOT_API_KEY=your_api_key_here
```

## Supported Entities

- ✅ Accounts (companies)
- ⏳ Opportunities (deals) - Coming soon
- ⏳ Contacts - Coming soon
```

---

## Extending RAG Intelligence

### Step 1: Add Custom Embeddings

Create `services/mapping_intelligence/custom_embeddings.py`:

```python
from sentence_transformers import SentenceTransformer
from typing import List
import numpy as np

class CustomEmbeddingModel:
    """
    Custom embedding model for domain-specific field matching.
    
    Example: Train on your company's internal data schemas.
    """
    
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)
    
    def encode(self, texts: List[str]) -> np.ndarray:
        """Encode texts to embeddings."""
        return self.model.encode(texts, convert_to_numpy=True)
    
    def fine_tune(self, training_data: List[tuple]):
        """
        Fine-tune model on domain-specific data.
        
        Args:
            training_data: List of (field1, field2, similarity_score) tuples
        """
        # Example: Use Sentence-BERT training
        from sentence_transformers import InputExample, losses
        from torch.utils.data import DataLoader
        
        examples = [
            InputExample(texts=[f1, f2], label=score)
            for f1, f2, score in training_data
        ]
        
        train_dataloader = DataLoader(examples, shuffle=True, batch_size=16)
        train_loss = losses.CosineSimilarityLoss(self.model)
        
        self.model.fit(
            train_objectives=[(train_dataloader, train_loss)],
            epochs=3,
            warmup_steps=100
        )
        
        # Save fine-tuned model
        self.model.save("models/custom_rag_embeddings")
```

### Step 2: Integrate with RAG Matcher

Update `services/mapping_intelligence/rag_matcher.py`:

```python
from .custom_embeddings import CustomEmbeddingModel

class RAGFieldMatcher:
    def __init__(self):
        # Use custom fine-tuned model instead of default
        self.embedding_model = CustomEmbeddingModel()
        # Load fine-tuned weights if available
        if os.path.exists("models/custom_rag_embeddings"):
            self.embedding_model.model = SentenceTransformer("models/custom_rag_embeddings")
```

### Step 3: Add Training Script

Create `scripts/train_rag_model.py`:

```python
from services.mapping_intelligence.custom_embeddings import CustomEmbeddingModel

# Load training data (from historical successful mappings)
training_data = [
    ("company_name", "account_name", 0.95),
    ("org_name", "account_name", 0.90),
    ("business_name", "account_name", 0.85),
    # ... more examples
]

# Train model
model = CustomEmbeddingModel()
model.fine_tune(training_data)

print("✅ RAG model fine-tuned successfully")
```

---

## Database Migrations

### Alembic Workflow

**Create New Migration:**

```bash
# Auto-generate migration from model changes
alembic revision --autogenerate -m "Add connector_health table"

# Manually create migration
alembic revision -m "Add index on tenant_id"
```

**Edit Migration:**

```python
# alembic/versions/abc123_add_connector_health_table.py

def upgrade():
    op.create_table(
        'connector_health',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('connector_id', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('last_check', sa.DateTime(timezone=True), nullable=False),
        sa.Column('error_message', sa.String(), nullable=True),
    )
    
    # Add index
    op.create_index(
        'idx_connector_health_tenant_id',
        'connector_health',
        ['tenant_id']
    )

def downgrade():
    op.drop_index('idx_connector_health_tenant_id')
    op.drop_table('connector_health')
```

**Apply Migration:**

```bash
# Upgrade to latest
alembic upgrade head

# Upgrade to specific version
alembic upgrade abc123

# Downgrade one version
alembic downgrade -1

# View migration history
alembic history
```

**Best Practices:**

1. Always test migrations on staging first
2. Create backups before running migrations in production
3. Use `op.batch_alter_table()` for large tables (avoids table locks)
4. Add indexes in separate migrations (allows parallel execution)
5. Never edit applied migrations (create new ones instead)

---

## Frontend Development

### Component Structure

```tsx
// frontend/src/components/AAMMetricsCard.tsx
import { useState, useEffect } from 'react';
import { Card, CardHeader, CardContent } from '@/components/ui/card';

interface AAMMetricsCardProps {
  tenantId: string;
}

export function AAMMetricsCard({ tenantId }: AAMMetricsCardProps) {
  const [metrics, setMetrics] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchMetrics();
  }, [tenantId]);

  async function fetchMetrics() {
    const response = await fetch(`/api/v1/aam/monitoring/metrics`, {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('token')}`
      }
    });
    
    const data = await response.json();
    setMetrics(data);
    setLoading(false);
  }

  if (loading) return <div>Loading...</div>;

  return (
    <Card>
      <CardHeader>AAM Metrics</CardHeader>
      <CardContent>
        <div>Drift Events (24h): {metrics.drift_events_24h}</div>
        <div>Auto-Repairs: {metrics.auto_repairs}</div>
      </CardContent>
    </Card>
  );
}
```

### State Management

```tsx
// Use Zustand for global state
import create from 'zustand';

interface AuthStore {
  token: string | null;
  tenantId: string | null;
  login: (token: string, tenantId: string) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthStore>((set) => ({
  token: localStorage.getItem('token'),
  tenantId: localStorage.getItem('tenantId'),
  
  login: (token, tenantId) => {
    localStorage.setItem('token', token);
    localStorage.setItem('tenantId', tenantId);
    set({ token, tenantId });
  },
  
  logout: () => {
    localStorage.removeItem('token');
    localStorage.removeItem('tenantId');
    set({ token: null, tenantId: null });
  }
}));
```

### Build for Production

```bash
cd frontend

# Build optimized bundle
npm run build

# Copy to backend static directory
cp -r dist/* ../static/

# Preview production build
npm run preview
```

---

## CI/CD Pipeline

### GitHub Actions Workflow

Create `.github/workflows/ci.yml`:

```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:14
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
      
      redis:
        image: redis:6
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt
      
      - name: Run tests
        run: pytest --cov=app --cov-report=xml
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost/test
          REDIS_URL: redis://localhost:6379
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml

  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Deploy to production
        run: |
          # Example: Deploy to Replit, Heroku, etc.
          echo "Deploying to production..."
```

---

## Performance Benchmarking

### Run Benchmark

```bash
cd benchmarks

# Run benchmark with specific workload profile
python3 run_load_test.py \
  --profile test \
  --connectors 10 \
  --jobs 5 \
  --fields 50

# View results
cat results/latest.json
```

### Analyze Results

```python
import json

with open('benchmarks/results/latest.json') as f:
    results = json.load(f)

print(f"Throughput: {results['performance']['throughput']['jobs_per_sec']} jobs/sec")
print(f"P95 Latency: {results['performance']['latency']['p95']}ms")
print(f"Success Rate: {results['execution']['success_rate_percent']}%")
```

---

## Debugging Tips

### Enable Debug Logging

```bash
# Set log level
export LOG_LEVEL=DEBUG

# Start with verbose output
uvicorn app.main:app --log-level debug
```

### Use Python Debugger

```python
# Add breakpoint
import pdb; pdb.set_trace()

# Or use IPython debugger
import ipdb; ipdb.set_trace()
```

### Debug RQ Workers

```bash
# Run worker in foreground with verbose logging
rq worker default --url $REDIS_URL --verbose

# View failed jobs
rq info --url $REDIS_URL --only-failures
```

### Database Query Logging

```python
# In app/database.py, enable echo
engine = create_engine(settings.DATABASE_URL, echo=True)
# This will print all SQL queries to console
```

### Frontend Debugging

```tsx
// Use React DevTools
console.log('Component props:', props);

// Network requests
console.log('API response:', await response.json());
```

---

## References

- [Architecture Overview](../architecture/ARCHITECTURE_OVERVIEW.md)
- [API Reference](../api/API_REFERENCE.md)
- [Deployment Guide](../deployment/DEPLOYMENT_GUIDE.md)
- [Performance Tuning](../performance/PERFORMANCE_TUNING.md)
