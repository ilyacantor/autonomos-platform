# AAM Gauntlet - Stress Testing Demo

A comprehensive stress-testing harness for the Adaptive API Mesh (AAM), demonstrating resilience, error handling, rate limiting, and drift adaptation capabilities under various chaos conditions.

## 🚀 Quick Start

### Using Docker Compose (Recommended)
```bash
cd aam_gauntlet
docker-compose up
```

Visit http://localhost:3000 to access the UI.

### Manual Setup
```bash
# Terminal 1: Start API Farm
cd aam_gauntlet/api_farm
pip install -r requirements.txt
python main.py

# Terminal 2: Start AAM Backend
cd aam_gauntlet/aam
pip install -r requirements.txt
python api.py

# Terminal 3: Start Frontend
cd aam_gauntlet/ui
npm install
npm run dev
```

## 🏗️ Architecture

```
┌─────────────────┐     ┌──────────────┐     ┌──────────────┐
│  Synthetic API  │────▶│     AAM      │────▶│  Workflows   │
│      Farm       │     │    Layer     │     │              │
│   (Port 8001)   │     │ (Port 8002)  │     │              │
└─────────────────┘     └──────────────┘     └──────────────┘
         ▲                      ▲                     ▲
         │                      │                     │
         └──────────────────────┴─────────────────────┘
                              │
                     ┌──────────────┐
                     │   React UI   │
                     │ (Port 3000)  │
                     └──────────────┘
```

### Components

1. **API Farm** (Port 8001): Synthetic APIs with configurable chaos
   - Multiple mock services (Salesforce, MongoDB, Stripe, etc.)
   - OAuth2 and API key authentication
   - Token bucket rate limiting
   - Error injection profiles
   - Schema drift simulation

2. **AAM Layer** (Port 8002): Adaptive API Mesh
   - Connector management
   - Adaptive rate limiting
   - Automatic token refresh
   - Error classification & retry logic
   - Dead Letter Queue (DLQ)
   - Idempotency handling
   - SQLite metrics storage

3. **Workflows**: Test scenarios
   - High-Volume Read: Stress test rate limits
   - Idempotent Write: Test write resilience
   - Drift-Sensitive: Test schema evolution handling

4. **React UI** (Port 3000): Visualization & Control
   - Live topology view
   - Real-time metrics charts
   - Chaos control panel
   - Connector status monitoring

## 🎮 Scenarios to Try

### 1. Token Expiry Resilience
Test AAM's ability to automatically refresh OAuth2 tokens:

1. Open the UI at http://localhost:3000
2. Select "Salesforce Mock" connector
3. Run "High Volume Read" workflow
4. Watch AAM auto-refresh tokens in the metrics

### 2. Rate Limit Handling
Test adaptive rate limiting under pressure:

1. Set chaos mode to "Storm" (20% error rate)
2. Run multiple workflows simultaneously
3. Observe AAM's backoff and retry behavior
4. Check token bucket metrics in connector details

### 3. Schema Drift Recovery
Test handling of evolving API schemas:

1. Run "Drift Sensitive" workflow on Salesforce
2. After 50 calls, watch field "account_name" rename to "name"
3. Observe AAM adapting to schema changes
4. Check drift events in the metrics

### 4. Network Chaos & DLQ
Test resilience to network issues:

1. Set chaos mode to "Hell" (50% error rate)
2. Run "Idempotent Write" workflow
3. Watch failed requests enter DLQ
4. Observe automatic retry behavior
5. Check DLQ statistics in metrics panel

### 5. Multi-Service Stress Test
Test system-wide resilience:

1. Select all services in Chaos Control
2. Set duration to 60 seconds
3. Set chaos level to "Storm"
4. Click "Run Scenario"
5. Monitor all connectors handling chaos simultaneously

## 🔧 Configuration

### Chaos Levels

| Level | Error Rate | Rate Limits | Network Issues | Use Case |
|-------|-----------|-------------|----------------|----------|
| Mild  | 5%        | Normal      | Minimal        | Baseline testing |
| Storm | 20%       | 50% reduced | Moderate       | Degraded conditions |
| Hell  | 50%       | 80% reduced | Severe         | Extreme stress test |

### Synthetic Services

| Service | Auth Type | Error Profile | Special Features |
|---------|-----------|--------------|------------------|
| Salesforce | OAuth2 | Aggressive rate limits | Schema drift |
| MongoDB | API Key | Network flakiness | Document operations |
| Stripe | API Key | Server errors (5xx) | Payment processing |
| GitHub | OAuth2 | Rate limits | Pagination |
| Supabase | OAuth2 | Token rotation | Database operations |
| Datadog | API Key | Schema drift | Metrics ingestion |

### Error Classes

- `auth_expired`: Token needs refresh
- `invalid_creds`: Bad credentials
- `rate_limit`: Rate limit exceeded
- `network_error`: Connection issues
- `server_error`: 5xx responses
- `timeout`: Request timeout

## 📊 Metrics & Monitoring

### Key Metrics

- **Request Metrics**: Total, successful, failed requests
- **Latency**: Average response time per service
- **Rate Limiting**: Token bucket status, backoff state
- **DLQ**: Pending, processed, failed entries
- **Token Refresh**: Successful vs failed refreshes
- **Error Breakdown**: Distribution by error class

### API Endpoints

#### AAM Backend (Port 8002)
- `GET /health` - Health check
- `GET /metrics` - Overall metrics
- `GET /connectors` - List connectors
- `POST /connectors` - Create connector
- `GET /workflows` - List workflows
- `POST /workflows/run` - Run workflow
- `POST /scenarios/run` - Run chaos scenario
- `GET /dlq` - View DLQ entries

#### API Farm (Port 8001)
- `GET /admin/status` - Farm status & metrics
- `POST /admin/chaos` - Set chaos level
- `POST /admin/reset` - Reset metrics
- `POST /oauth2/token` - OAuth2 token endpoint
- Dynamic service endpoints per YAML config

## 🛠️ Development

### Adding a New Service

1. Create YAML config in `api_farm/configs/`:
```yaml
id: my_service_mock
protocol: rest
base_path: /api/myservice
auth:
  type: oauth2_client_credentials
rate_limit:
  max_rps: 10
  burst: 20
error_profile: mostly_ok
# ... rest of config
```

2. Restart API Farm to load new config

### Adding a New Workflow

1. Create workflow in `workflows/`:
```python
async def my_workflow(connector, **params):
    # Workflow logic
    return metrics
```

2. Register in AAM API
3. Add UI controls if needed

### Customizing Chaos Behavior

Edit `api_farm/chaos.py` to modify:
- Error injection rates
- Network delay patterns
- Drift simulation logic

## 🐛 Troubleshooting

### Common Issues

1. **Port conflicts**: Ensure ports 3000, 8001, 8002 are free
2. **CORS errors**: Check proxy configuration in `vite.config.ts`
3. **Database locked**: Remove `aam_metrics.db` and restart
4. **Token refresh failing**: Check OAuth2 endpoint configuration

### Logs

- API Farm logs: Console output on port 8001
- AAM logs: Console output on port 8002
- Browser console: Network requests and errors
- SQLite DB: `aam_metrics.db` for persistent metrics

## 📝 Architecture Decisions

1. **SQLite over PostgreSQL**: Simplicity for demo purposes
2. **In-memory rate limiting**: Fast, no external dependencies
3. **Token bucket algorithm**: Industry standard, predictable behavior
4. **Idempotency keys**: Hash-based, automatic generation
5. **React + Vite**: Fast development, modern tooling
6. **FastAPI**: Async support, automatic OpenAPI docs

## 🎯 Learning Objectives

This demo demonstrates:

1. **Resilience Patterns**
   - Circuit breaking
   - Exponential backoff
   - Dead Letter Queue
   - Idempotency

2. **Rate Limiting**
   - Token bucket algorithm
   - Adaptive rate adjustment
   - Per-tenant limits

3. **Error Handling**
   - Error classification
   - Retry strategies
   - Graceful degradation

4. **Schema Evolution**
   - Drift detection
   - Field mapping
   - Backward compatibility

5. **Observability**
   - Real-time metrics
   - Error tracking
   - Performance monitoring

## 🚦 Performance Benchmarks

Under normal conditions (Mild chaos):
- Throughput: ~100 req/s per connector
- Latency: <50ms p50, <200ms p99
- Token refresh: <100ms
- DLQ processing: <5s delay

Under stress (Hell chaos):
- Throughput: ~20 req/s per connector
- Latency: <500ms p50, <2s p99
- Retry success rate: >80%
- DLQ backlog: <100 entries

## 📚 Further Reading

- [Token Bucket Algorithm](https://en.wikipedia.org/wiki/Token_bucket)
- [Circuit Breaker Pattern](https://martinfowler.com/bliki/CircuitBreaker.html)
- [Idempotency Keys](https://brandur.org/idempotency-keys)
- [Adaptive Rate Limiting](https://blog.cloudflare.com/counting-things-a-lot-of-different-things/)

## 📄 License

This is a demonstration project for educational purposes.

---

Built with ❤️ for stress testing AAM resilience