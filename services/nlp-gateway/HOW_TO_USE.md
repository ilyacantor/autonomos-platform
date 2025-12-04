# How to Use the AOS NLP Gateway

**Last Updated:** November 19, 2025

Welcome! This guide will help you get started with the AOS NLP Gateway - your natural language interface to AutonomOS services.

## What is the NLP Gateway?

The NLP Gateway lets you ask questions and get answers about your AutonomOS infrastructure using plain English. No need to remember complex commands or navigate through multiple screens - just type your question and get instant answers.

**Think of it as:** A smart assistant that knows everything about your FinOps costs, RevOps incidents, service dependencies, connector health, and internal documentation.

## Quick Start

### 1. Access the Gateway

- Navigate to the **Control Center** tab in AutonomOS
- You'll see the **AOS NLP Gateway** prominently at the top of the page
- The large input box is ready for your questions

### 2. Choose Your Service

In the top-right corner, select which service you want to query:

- **Knowledge Base** 📖 - Search documentation, runbooks, and guides
- **FinOps** 💰 - Get cost summaries and optimization insights
- **RevOps** ⚠️ - Look up incidents and resolution details
- **Discovery** 🌐 - Check service dependencies and health
- **Connectors** 💾 - Monitor AAM connector status and drift

### 3. Ask Your Question

Type your question in the large input box and click **Send**. The gateway will:
1. Route your question to the appropriate service
2. Fetch relevant data
3. Display the answer with citations and metadata

## Service-by-Service Guide

### 📖 Knowledge Base (RAG Search)

**What it does:** Searches your organization's documentation, runbooks, incident reports, and knowledge articles using AI-powered hybrid search.

**Best for:**
- "How do I configure the Salesforce connector?"
- "Show me the runbook for handling RevOps incidents"
- "What are best practices for cost optimization?"
- "Explain how the DCL engine works"

**What you'll get:**
- Ranked search results with relevance scores
- Source citations (document title and section)
- Actual content excerpts from your knowledge base
- Trace ID for debugging

**Example:**
```
Question: "How does hybrid search work?"
Answer: 
1. AAM Hybrid Retrieval Guide
   Hybrid search combines BM25 (keyword) and vector embeddings...
   Score: 0.947

2. Platform Architecture Overview
   The RAG system uses Reciprocal Rank Fusion (RRF)...
   Score: 0.823

Sources: AAM Hybrid Retrieval Guide: Technical Details, Platform Architecture: Search Systems
```

### 💰 FinOps (Cost Summaries)

**What it does:** Provides cost analysis and optimization recommendations for your cloud infrastructure.

**Best for:**
- "Show me the FinOps summary for this month"
- "What are our top cost drivers?"
- "Give me cost optimization recommendations"

**What you'll get:**
- Monthly cost breakdown
- Savings opportunities
- Budget vs actual spending
- Trend analysis

**Note:** Currently queries the current month automatically. Future versions will support custom date ranges from your natural language input.

### ⚠️ RevOps (Incident Lookup)

**What it does:** Retrieves details about revenue operations incidents, including root causes and resolutions.

**Best for:**
- "What happened with incident I-9A03?"
- "Show me incident details for I-9A03"
- "Tell me about the last RevOps incident"

**What you'll get:**
- Incident summary and timeline
- Root cause analysis
- Resolution steps taken
- Impact assessment
- Related incidents

**Example:**
```
Question: "What happened with incident I-9A03?"
Answer:
{
  "incident_id": "I-9A03",
  "title": "Salesforce sync failure",
  "status": "Resolved",
  "root_cause": "API rate limit exceeded",
  "resolution": "Implemented exponential backoff retry logic"
}
```

### 🌐 Discovery (Service Dependencies)

**What it does:** Maps service dependencies and shows health status across your infrastructure.

**Best for:**
- "Show me dependencies for checkout-service"
- "What services depend on the payment gateway?"
- "Check health of authentication-service"

**What you'll get:**
- Dependency graph
- Upstream and downstream services
- Health status for each service
- Critical path identification

**Example:**
```
Question: "Show me dependencies for checkout-service"
Answer:
{
  "service": "checkout-service",
  "dependencies": {
    "upstream": ["payment-gateway", "inventory-service"],
    "downstream": ["order-processor", "shipping-service"]
  },
  "health": "healthy"
}
```

### 💾 Connectors (AAM Health Monitoring)

**What it does:** Lists all Adaptive API Mesh connectors with their health status and schema drift information.

**Best for:**
- "What are the current drifted connectors?"
- "Show me all healthy connectors"
- "List connectors with errors"

**What you'll get:**
- Complete connector inventory
- Health status (Healthy, Drifted, Error)
- Last sync time
- Schema fingerprints
- Drift detection details

**Filter options:**
- All (default)
- Healthy only
- Drifted only
- Error only

## Tips for Better Results

### ✅ DO:
- **Be specific**: "Show me FinOps summary for November 2025" is better than "costs"
- **Use natural language**: Ask like you're talking to a person
- **Try prompt starters**: Click the suggested prompts to see what's possible
- **Check sources**: Look at the citations to verify information
- **Use the right service**: Select the appropriate service button before asking

### ❌ DON'T:
- Use technical jargon when not needed - the gateway understands plain English
- Expect real-time data updates - results are based on the last sync
- Ask multiple unrelated questions in one message - break them up

## Understanding Your Results

### Conversation Format

**Your messages** appear in blue boxes with "You" label
**Gateway responses** appear in gray boxes with "NLP Gateway" label

### Metadata You'll See

Every response includes:
- **Trace ID**: Unique identifier for debugging (e.g., `nlp_20251108053524_a1b2c3d4`)
- **Sources**: Document citations for Knowledge Base searches
- **Scope**: Tenant, environment, and time window used

At the bottom of the interface:
- **Port**: 8001 (where the NLP Gateway service runs)
- **Tenant**: demo-tenant (your organization scope)
- **Env**: prod (production environment)
- **Auth**: JWT (secure authentication)

## Advanced Usage

### Switching Services Mid-Conversation

You can change services at any time by clicking a different service button. Your conversation history stays visible, but new questions will route to the selected service.

### Understanding Relevance Scores

Knowledge Base results include a score (0.000 to 1.000):
- **0.900+**: Highly relevant, exact match
- **0.700-0.899**: Good match, relevant content
- **0.500-0.699**: Moderate relevance, may be helpful
- **Below 0.500**: Low relevance, likely not what you're looking for

### Using Trace IDs for Support

If you get unexpected results or errors:
1. Copy the trace ID from the response
2. Check the NLP Gateway logs: `grep <trace_id> /tmp/logs/*`
3. Contact support with the trace ID for faster troubleshooting

## Troubleshooting

### "Failed to connect to NLP Gateway"

**Problem:** The NLP Gateway service isn't running on port 8001

**Solution:**
```bash
cd services/nlp-gateway
make run
```

### "401 Unauthorized"

**Problem:** Your JWT token is missing or expired

**Solution:**
1. Log in again through the AutonomOS interface
2. Your token will refresh automatically

### No Results from Knowledge Base

**Problem:** The knowledge base is empty

**Solution:**
```bash
cd services/nlp-gateway
make seed  # Populate with demo data
```

### Slow Response Times

**Problem:** Complex queries or large knowledge bases can take time

**What to expect:**
- Knowledge Base searches: 500ms - 1.5s
- Service endpoints (FinOps, RevOps, etc.): 200ms - 800ms

**If consistently slow:**
- Check your database connection
- Verify pgvector extension is enabled
- Ensure indexes are created properly

## Example Workflows

### Workflow 1: Investigating a Cost Spike

1. Select **FinOps** service
2. Ask: "Show me the FinOps summary for this month"
3. Review cost breakdown in the response
4. Switch to **Knowledge Base**
5. Ask: "What are cost optimization best practices?"
6. Implement recommendations from the results

### Workflow 2: Troubleshooting an Incident

1. Select **RevOps** service
2. Ask: "What happened with incident I-9A03?"
3. Review the incident details
4. Switch to **Knowledge Base**
5. Ask: "Show me runbooks for RevOps incident response"
6. Follow the recommended steps

### Workflow 3: Understanding Service Health

1. Select **Discovery** service
2. Ask: "Show me dependencies for checkout-service"
3. Review the dependency graph
4. Switch to **Connectors**
5. Ask: "What are the current drifted connectors?"
6. Identify any issues in the dependency chain

### Workflow 4: Learning the Platform

1. Select **Knowledge Base**
2. Ask: "How does the AAM connector system work?"
3. Read the overview
4. Ask: "What is schema drift detection?"
5. Ask: "How do I configure a Salesforce connector?"
6. Build your understanding step-by-step

## Best Practices

### For Daily Use

- **Start your day**: Check for drifted connectors and failed jobs
- **Monitor costs**: Review FinOps summaries weekly
- **Document learnings**: If you solve a problem, add it to the knowledge base
- **Use citations**: Always verify information by checking sources

### For Team Collaboration

- **Share trace IDs**: When discussing issues, include the trace ID
- **Build the knowledge base**: Add runbooks and documentation
- **Report feedback**: Use the feedback endpoint to improve results
- **Create prompt libraries**: Save useful queries for common tasks

### For Incident Response

1. **Check RevOps** for existing incident details
2. **Query Discovery** to understand service impact
3. **Review Connectors** to identify any schema drift
4. **Search Knowledge Base** for similar past incidents
5. **Document resolution** for future reference

## What's Next?

### Coming Soon (Phase 2)

- **MCP Protocol Integration**: Use the gateway from VS Code, Slack, and other tools
- **Custom Date Ranges**: Ask "Show me costs from Oct 1-15" naturally
- **Multi-turn Conversations**: Gateway remembers context across questions
- **Proactive Alerts**: Gateway notifies you of issues before you ask
- **Advanced Analytics**: Trend analysis and predictive insights

### How to Provide Feedback

Your feedback helps improve the gateway. To log feedback:

1. Note the trace ID from a response
2. Rate it (thumbs up/down mentally)
3. Consider what would make it better

Future versions will have a feedback button in the UI.

## Getting Help

- **Documentation**: `/services/nlp-gateway/README.md`
- **Technical Setup**: `/services/nlp-gateway/REPLIT_AGENT_SETUP.md`
- **API Reference**: `http://localhost:8001/docs` (when gateway is running)
- **Main Platform**: `http://localhost:5000/api/docs`

## Summary

The AOS NLP Gateway makes your AutonomOS infrastructure accessible through natural language:

1. **Choose** your service (Knowledge Base, FinOps, RevOps, Discovery, or Connectors)
2. **Ask** your question in plain English
3. **Get** instant answers with citations and metadata
4. **Act** on the insights to optimize your operations

Happy querying! 🚀
