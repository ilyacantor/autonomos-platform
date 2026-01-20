# Agentic Orchestration Platform - Technical Plan

**Date**: 2026-01-20
**Status**: Approved for Implementation
**Codebase**: autonomos-platform

---

## Executive Summary

This document outlines the transformation of the AutonomOS platform from a demo application into a production-ready **Agentic Orchestration Platform** with:
- NLP front-end for natural language control
- Control center for all AOS applications
- Fast, responsive UI (fixing current slow load times)

---

## Part 1: Performance Fix (Slow Loading)

### Root Cause Analysis

| Issue | Impact | Location |
|-------|--------|----------|
| **No lazy loading** | All 10 pages load on startup | `frontend/src/App.tsx:6-14` |
| **Inline CSS in components** | 750+ lines parsed upfront | `PlatformGuidePage.tsx`, `FAQPage.tsx` |
| **Unused dependencies** | D3, ReactFlow bundled but not used | `package.json` |
| **Sequential backend init** | Blocking startup operations | `app/main.py:66-200` |
| **Demo content pages** | 2000+ lines of static FAQ/Glossary | `GlossaryPage.tsx`, `FAQPage.tsx` |

### Fix 1: Lazy Loading Routes (Frontend)

**Current** (`App.tsx`):
```typescript
import PlatformGuidePage from './components/PlatformGuidePage';
import FAQPage from './components/FAQPage';
// ... all pages imported eagerly
```

**Fixed**:
```typescript
import { lazy, Suspense } from 'react';

// Lazy load all pages
const ControlCenterPage = lazy(() => import('./components/ControlCenterPage'));
const DiscoverPage = lazy(() => import('./components/DiscoverPage'));
const ConnectPage = lazy(() => import('./components/ConnectPage'));
// ... etc

// Wrap in Suspense
<Suspense fallback={<LoadingSpinner />}>
  {renderPage()}
</Suspense>
```

**Impact**: Initial bundle reduced by ~60%, pages load on-demand

### Fix 2: Remove Unused Dependencies

**Remove from `package.json`**:
```json
{
  "dependencies": {
    "d3": "^7.9.0",           // NOT USED
    "d3-sankey": "^0.12.3",   // NOT USED
    "reactflow": "^11.11.4",  // NOT USED
    "@types/d3": "^7.4.3",    // NOT USED
    "@types/d3-sankey": "^0.12.4"  // NOT USED
  }
}
```

**Impact**: ~200KB removed from bundle

### Fix 3: Remove Demo Content Pages

**Delete these files** (2000+ lines of static content):
- `frontend/src/components/FAQPage.tsx` (708 lines)
- `frontend/src/components/GlossaryPage.tsx` (479 lines)
- `frontend/src/components/PlatformGuidePage.tsx` (749 lines)

**Replace with**: Minimal placeholder or external docs link

### Fix 4: Optimize Backend Startup

**Current issues in `app/main.py` lifespan**:
```python
# Line 75: Blocking database init with 5s timeout
await asyncio.wait_for(init_db(), timeout=5.0)

# Line 139: Blocking event bus connect
await event_bus.connect()

# Line 155: Blocking AAM initializer
await run_aam_initializer()
```

**Fix**: Move non-critical initialization to background tasks:
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Only critical init here (< 500ms)
    logger.info("Starting AutonomOS...")

    # Schedule non-blocking background init
    asyncio.create_task(deferred_initialization())

    yield

async def deferred_initialization():
    """Non-blocking initialization after server is ready"""
    await init_db()
    await event_bus.connect()
    await run_aam_initializer()
```

### Fix 5: Update Vite Config for Better Splitting

**Update `vite.config.ts`**:
```typescript
rollupOptions: {
  output: {
    manualChunks: {
      'react-vendor': ['react', 'react-dom'],
      'ui-vendor': ['framer-motion', 'lucide-react'],
      // Remove d3-vendor - not used
    },
  },
},
```

---

## Part 2: Files to Strip/Remove

### Definitely Remove (Demo Content)

| File | Lines | Reason |
|------|-------|--------|
| `frontend/src/components/FAQPage.tsx` | 708 | Static demo content |
| `frontend/src/components/GlossaryPage.tsx` | 479 | Static demo content |
| `frontend/src/components/PlatformGuidePage.tsx` | 749 | Static demo content, inline CSS |
| `frontend/src/components/HeroSection.tsx` | ~50 | Marketing content |
| `frontend/src/components/LegacyToggle.tsx` | ~30 | Legacy mode toggle |

### Consider Removing (Low Value)

| File | Lines | Reason |
|------|-------|--------|
| `frontend/src/components/TypingText.tsx` | ~40 | Cosmetic animation |
| `frontend/src/components/DiscoverConsole.tsx` | 285 | Simulated terminal (demo) |
| `frontend/src/data/*` | ~200 | Mock data files |
| `frontend/src/mocks/*` | ~100 | Mock handlers |

### Keep and Enhance

| File | Purpose |
|------|---------|
| `ControlCenterPage.tsx` | NLP interface - enhance with LLM |
| `NLPGateway.tsx` | Query input - enhance with streaming |
| `PersonaDashboard.tsx` | Agent dashboard template |
| `FlowMonitor.tsx` | Real-time telemetry - keep for agents |
| `ConnectPage.tsx` | Connection management |
| `DiscoverPage.tsx` | Iframe embed - keep pattern |
| `DemoPage.tsx` | Rename to AgentRunnerPage |

### Backend Files to Remove

| File | Reason |
|------|--------|
| `app/api/v1/aod_mock.py` | Mock AOD responses |
| `app/api/v1/platform_stubs.py` | Placeholder endpoints |
| `app/api/v1/mesh_test.py` | Dev-only test routes |

---

## Part 3: Agentic Orchestration Platform Roadmap

### Phase 1: Foundation (Week 1-2)

#### 1.1 Performance Fixes
- [ ] Implement lazy loading in App.tsx
- [ ] Remove unused D3/ReactFlow dependencies
- [ ] Delete demo content pages (FAQ, Glossary, PlatformGuide)
- [ ] Optimize backend lifespan startup
- [ ] Rebuild frontend bundle

#### 1.2 Fix Blocking Issues
- [ ] Fix AAM background task event loop blocking (`app/main.py:159-170`)
- [ ] Re-enable audit middleware with async-safe implementation
- [ ] Fix idempotency middleware blocking

#### 1.3 Routing Upgrade
- [ ] Add React Router for dynamic routes
- [ ] Support routes like `/agent/:agentId/run/:runId`
- [ ] Remove custom URL routing code

### Phase 2: Agent Infrastructure (Week 3-4)

#### 2.1 Agent Data Model

```python
# New file: app/models/agent.py

class Agent(Base):
    __tablename__ = "agents"

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID, ForeignKey("tenants.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(String)
    agent_type = Column(String(50))  # orchestrator, worker, specialist
    status = Column(String(20), default="idle")  # idle, running, paused, failed
    config = Column(JSON)  # LLM config, tools, prompts
    created_at = Column(DateTime, server_default=func.now())

class AgentRun(Base):
    __tablename__ = "agent_runs"

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    agent_id = Column(UUID, ForeignKey("agents.id"), nullable=False)
    tenant_id = Column(UUID, ForeignKey("tenants.id"), nullable=False)
    status = Column(String(20))  # pending, running, completed, failed
    input_data = Column(JSON)
    output_data = Column(JSON)
    error = Column(String)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    tokens_used = Column(Integer)

class AgentStep(Base):
    __tablename__ = "agent_steps"

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID, ForeignKey("agent_runs.id"), nullable=False)
    step_number = Column(Integer, nullable=False)
    step_type = Column(String(50))  # think, tool_call, tool_result, output
    content = Column(JSON)
    created_at = Column(DateTime, server_default=func.now())
```

#### 2.2 Agent Registry API

```python
# New file: app/api/v1/agents.py

router = APIRouter(prefix="/agents", tags=["Agents"])

@router.post("/", response_model=AgentResponse)
async def create_agent(agent: AgentCreate, user: User = Depends(get_current_user)):
    """Register a new agent"""

@router.get("/", response_model=List[AgentResponse])
async def list_agents(user: User = Depends(get_current_user)):
    """List all agents for tenant"""

@router.post("/{agent_id}/run", response_model=AgentRunResponse)
async def start_agent_run(agent_id: UUID, input: AgentInput, user: User = Depends(get_current_user)):
    """Start a new agent run"""

@router.get("/{agent_id}/runs/{run_id}", response_model=AgentRunResponse)
async def get_agent_run(agent_id: UUID, run_id: UUID):
    """Get agent run status and results"""

@router.get("/{agent_id}/runs/{run_id}/steps")
async def get_agent_steps(agent_id: UUID, run_id: UUID):
    """Get all steps from an agent run"""

@router.websocket("/ws/{agent_id}/runs/{run_id}")
async def agent_run_stream(websocket: WebSocket, agent_id: UUID, run_id: UUID):
    """Stream agent execution in real-time"""
```

#### 2.3 Event Bus Extensions

```python
# Extend aam_hybrid/shared/event_bus.py

# New channels for agent orchestration
AGENT_CHANNELS = [
    "agent:started",
    "agent:step",
    "agent:tool_call",
    "agent:tool_result",
    "agent:completed",
    "agent:failed",
    "agent:approval_needed",
]
```

### Phase 3: NLP Enhancement (Week 5-6)

#### 3.1 LLM Integration

```python
# New file: app/services/llm.py

from openai import AsyncOpenAI
from anthropic import AsyncAnthropic

class LLMService:
    def __init__(self):
        self.openai = AsyncOpenAI()
        self.anthropic = AsyncAnthropic()

    async def complete(
        self,
        messages: List[dict],
        model: str = "gpt-4o",
        tools: Optional[List[dict]] = None,
        stream: bool = False
    ) -> AsyncGenerator[str, None]:
        """Generate completion with optional tool calling"""

    async def classify_intent(self, query: str) -> dict:
        """Classify user query intent and extract entities"""
```

#### 3.2 Tool Framework

```python
# New file: app/services/tools.py

class Tool:
    name: str
    description: str
    parameters: dict

    async def execute(self, **params) -> dict:
        raise NotImplementedError

class AgentInvokeTool(Tool):
    """Invoke another agent"""
    name = "invoke_agent"
    description = "Run a registered agent with given input"

class QueryDataTool(Tool):
    """Query canonical data layer"""
    name = "query_data"
    description = "Query unified data from DCL"

class SearchKnowledgeTool(Tool):
    """Search knowledge base"""
    name = "search_kb"
    description = "Search organizational knowledge base"
```

#### 3.3 Enhanced NLP Gateway

```python
# Update app/nlp_simple.py -> app/nlp_gateway.py

@router.post("/chat")
async def chat(
    request: ChatRequest,
    user: User = Depends(get_current_user)
) -> StreamingResponse:
    """
    Process natural language query with:
    - Intent classification
    - Tool selection
    - LLM response generation
    - Streaming output
    """

@router.websocket("/ws/chat")
async def chat_stream(websocket: WebSocket):
    """Bidirectional chat with streaming"""
```

### Phase 4: Control Center UI (Week 7-8)

#### 4.1 Agent Dashboard

```typescript
// New file: frontend/src/components/AgentDashboard.tsx

interface AgentDashboardProps {
  agents: Agent[];
  runs: AgentRun[];
}

export default function AgentDashboard({ agents, runs }: AgentDashboardProps) {
  return (
    <div className="grid grid-cols-3 gap-4">
      <AgentList agents={agents} />
      <RunHistory runs={runs} />
      <LiveRunViewer />
    </div>
  );
}
```

#### 4.2 Agent Run Viewer

```typescript
// New file: frontend/src/components/AgentRunViewer.tsx

export default function AgentRunViewer({ runId }: { runId: string }) {
  const [steps, setSteps] = useState<AgentStep[]>([]);

  useEffect(() => {
    const ws = new WebSocket(`/api/v1/agents/ws/runs/${runId}`);
    ws.onmessage = (event) => {
      const step = JSON.parse(event.data);
      setSteps(prev => [...prev, step]);
    };
    return () => ws.close();
  }, [runId]);

  return (
    <div className="agent-run-viewer">
      {steps.map(step => (
        <AgentStepCard key={step.id} step={step} />
      ))}
    </div>
  );
}
```

#### 4.3 NLP Chat Interface

```typescript
// Update frontend/src/components/NLPGateway.tsx

export default function NLPGateway({ persona }: { persona: PersonaSlug }) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [streaming, setStreaming] = useState(false);

  const sendMessage = async (content: string) => {
    setStreaming(true);

    const response = await fetch('/api/v1/nlp/chat', {
      method: 'POST',
      body: JSON.stringify({ content, persona }),
      headers: { 'Content-Type': 'application/json' }
    });

    const reader = response.body?.getReader();
    // Stream response chunks to UI
  };

  return (
    <div className="chat-interface">
      <MessageList messages={messages} />
      <ChatInput onSend={sendMessage} disabled={streaming} />
    </div>
  );
}
```

---

## Part 4: Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     CONTROL CENTER (React)                       │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ NLP Chat    │  │ Agent       │  │ Embedded Services       │  │
│  │ Interface   │  │ Dashboard   │  │ (AOD/AAM/DCL iframes)   │  │
│  └──────┬──────┘  └──────┬──────┘  └───────────┬─────────────┘  │
└─────────┼────────────────┼─────────────────────┼────────────────┘
          │                │                     │
          ▼                ▼                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                     API GATEWAY (FastAPI)                        │
├─────────────────────────────────────────────────────────────────┤
│  Auth │ Rate Limit │ Tracing │ Audit │ Multi-Tenant            │
├───────┴────────────┴─────────┴───────┴──────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ /nlp/*      │  │ /agents/*   │  │ /aam/* /dcl/* /aod/*    │  │
│  │ NLP Gateway │  │ Agent API   │  │ Service APIs            │  │
│  └──────┬──────┘  └──────┬──────┘  └───────────┬─────────────┘  │
└─────────┼────────────────┼─────────────────────┼────────────────┘
          │                │                     │
          ▼                ▼                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                     ORCHESTRATION LAYER                          │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ LLM Service │  │ Agent       │  │ Event Bus               │  │
│  │ (GPT/Claude)│  │ Executor    │  │ (Redis Pub/Sub)         │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ Tool        │  │ Workflow    │  │ HITL Approval           │  │
│  │ Framework   │  │ Engine      │  │ Queue                   │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
          │                │                     │
          ▼                ▼                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                     DATA LAYER                                   │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ PostgreSQL  │  │ Redis       │  │ Vector Store            │  │
│  │ (State)     │  │ (Cache/Q)   │  │ (Embeddings)            │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Part 5: Implementation Checklist

### Immediate Actions (This Week)

- [ ] **Performance**: Implement lazy loading in App.tsx
- [ ] **Performance**: Remove unused D3/ReactFlow from package.json
- [ ] **Cleanup**: Delete FAQPage.tsx, GlossaryPage.tsx, PlatformGuidePage.tsx
- [ ] **Cleanup**: Remove demo mock files
- [ ] **Fix**: Optimize backend lifespan startup
- [ ] **Test**: Measure load time before/after

### Short-Term (Next 2 Weeks)

- [ ] **Routing**: Add React Router
- [ ] **Backend**: Fix AAM background task blocking
- [ ] **Backend**: Re-enable audit middleware
- [ ] **Database**: Add Agent, AgentRun, AgentStep models
- [ ] **API**: Create /agents/* endpoints

### Medium-Term (Weeks 3-6)

- [ ] **LLM**: Integrate OpenAI/Anthropic SDK
- [ ] **Tools**: Build tool framework
- [ ] **NLP**: Upgrade /nlp/* to use LLM
- [ ] **UI**: Build AgentDashboard component
- [ ] **UI**: Add streaming chat interface

---

## Appendix: Files to Delete

```bash
# Demo content pages (2000+ lines)
rm frontend/src/components/FAQPage.tsx
rm frontend/src/components/GlossaryPage.tsx
rm frontend/src/components/PlatformGuidePage.tsx

# Demo-only components
rm frontend/src/components/HeroSection.tsx
rm frontend/src/components/LegacyToggle.tsx
rm frontend/src/components/TypingText.tsx
rm frontend/src/components/DiscoverConsole.tsx

# Mock data
rm -rf frontend/src/data/
rm -rf frontend/src/mocks/

# Backend stubs
rm app/api/v1/aod_mock.py
rm app/api/v1/platform_stubs.py
rm app/api/v1/mesh_test.py
```

## Appendix: Package.json Changes

```diff
  "dependencies": {
    "@supabase/supabase-js": "^2.57.4",
-   "@types/d3": "^7.4.3",
-   "@types/d3-sankey": "^0.12.4",
    "clsx": "^2.1.1",
-   "d3": "^7.9.0",
-   "d3-sankey": "^0.12.3",
    "framer-motion": "^12.23.24",
    "lucide-react": "^0.344.0",
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
-   "reactflow": "^11.11.4",
+   "react-router-dom": "^6.22.0",
    "tailwind-merge": "^3.4.0"
  }
```
