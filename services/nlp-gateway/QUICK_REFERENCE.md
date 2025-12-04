# NLP Gateway Quick Reference

**Last Updated:** November 19, 2025

## 🚀 Getting Started

```bash
cd services/nlp-gateway
make seed    # Load demo data (first time only)
make run     # Start gateway on port 8001
```

Access: **Control Center tab** → Large input box at top

## 🎯 Services Quick Guide

| Service | Icon | Use When You Need | Example Query |
|---------|------|-------------------|---------------|
| **Knowledge Base** | 📖 | Documentation, runbooks, guides | "How does AAM work?" |
| **FinOps** | 💰 | Cost summaries, optimization | "Show me this month's costs" |
| **RevOps** | ⚠️ | Incident details, resolutions | "What's incident I-9A03?" |
| **Discovery** | 🌐 | Service dependencies, health | "Dependencies for checkout-service?" |
| **Connectors** | 💾 | AAM connector status, drift | "What connectors are drifted?" |

## 💬 Sample Prompts

### Knowledge Base
- "How do I configure the Salesforce connector?"
- "Show me runbooks for incident response"
- "What are cost optimization best practices?"
- "Explain schema drift detection"

### FinOps
- "Show me the FinOps summary for this month"
- "What are our top cost drivers?"
- "Give me cost optimization recommendations"

### RevOps
- "What happened with incident I-9A03?"
- "Show me recent incident resolutions"
- "Tell me about the last RevOps incident"

### Discovery
- "Show me dependencies for checkout-service"
- "What services depend on payment-gateway?"
- "Check health of authentication-service"

### Connectors
- "What are the current drifted connectors?"
- "Show me all healthy connectors"
- "List connectors with errors"

## 📊 Understanding Results

### Response Format
```
You: "How does hybrid search work?"

NLP Gateway: [trace_id=nlp_20251108_abc123]
1. AAM Hybrid Retrieval Guide
   Content about BM25 + vector embeddings...
   Score: 0.947

Sources: AAM Hybrid Retrieval Guide: Technical Details
```

### Score Meanings
- **0.900+** ⭐⭐⭐ Excellent match
- **0.700-0.899** ⭐⭐ Good match
- **0.500-0.699** ⭐ Moderate relevance
- **Below 0.500** ❌ Low relevance

## ⚡ Keyboard Shortcuts

- **Enter**: Send message
- **Click prompt**: Auto-fill input
- **Scroll**: View conversation history

## 🔧 Troubleshooting

| Problem | Quick Fix |
|---------|-----------|
| Connection failed | `cd services/nlp-gateway && make run` |
| No results | `make seed` to populate demo data |
| Slow responses | Check database connection, verify indexes |
| 401 error | Re-login to refresh JWT token |

## 📍 Key Info

- **Port**: 8001
- **Tenant**: demo-tenant
- **Environment**: prod
- **Auth**: JWT (automatic)
- **Trace IDs**: Every response includes one for debugging

## 🎓 Pro Tips

1. **Start specific**: "FinOps summary for November" > "costs"
2. **Check sources**: Click citations to verify info
3. **One question**: Break complex queries into parts
4. **Use trace IDs**: Copy them when reporting issues
5. **Try prompts**: Click suggested prompts to explore

## 📚 More Help

- **Full Guide**: `HOW_TO_USE.md`
- **Technical Setup**: `REPLIT_AGENT_SETUP.md`
- **API Docs**: http://localhost:8001/docs
- **Platform Docs**: http://localhost:5000/api/docs

## 🔗 Quick Links

```bash
# Common Commands
make run        # Start gateway
make test       # Run tests
make seed       # Load demo data
make lint       # Check code quality
make eval       # Evaluate on test set

# Logs
grep "nlp_gateway" /tmp/logs/*  # All NLP logs
grep <trace_id> /tmp/logs/*     # Specific query

# Health Check
curl http://localhost:8001/health
```

---

**Remember**: The NLP Gateway makes your infrastructure conversational. Just ask! 💡
