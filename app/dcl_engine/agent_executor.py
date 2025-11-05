"""
Agent Execution Engine for AutonomOS DCL

Orchestrates agent invocation after materialized views are created in DuckDB.
Agents consume AAM-backed data from DCL unified views and produce analytical outputs.

Architecture:
- AgentExecutor: Main orchestrator class
- Async execution: Runs as background task after connect_source()
- Tenant-scoped storage: Results cached per tenant in memory
- WebSocket events: Progress tracking (agent_started, agent_completed, agent_failed)
- Pluggable logic: Mock analysis now, LLM-based analysis in future phases

Phase: 3 (DCL → Agents Integration)
"""

import time
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import duckdb

logger = logging.getLogger(__name__)


class AgentExecutor:
    """
    Orchestrates agent execution using materialized views from DCL.
    
    Workflow:
    1. prepare_agent_input(): Query DuckDB for entity data based on agent.consumes
    2. execute_agent(): Run agent logic (mock analysis for now)
    3. store_results(): Cache results in tenant-scoped storage
    """
    
    def __init__(self, db_path: str, agents_config: Dict[str, Any], results_cache: Dict[str, Dict]):
        """
        Initialize AgentExecutor.
        
        Args:
            db_path: Path to DuckDB database
            agents_config: Loaded agents configuration from config.yml
            results_cache: In-memory dict for storing results (tenant_id -> {agent_id -> results})
        """
        self.db_path = db_path
        self.agents_config = agents_config
        self.results_cache = results_cache
        self.logger = logging.getLogger(__name__)
    
    def prepare_agent_input(self, agent_id: str, agent_config: Dict[str, Any], tenant_id: str) -> Dict[str, Any]:
        """
        Prepare input data for agent by querying materialized views.
        
        Reads from DCL unified views (e.g., dcl_account, dcl_opportunity) and
        filters data based on agent's key_metrics configuration.
        
        Args:
            agent_id: Agent identifier (e.g., 'revops_pilot')
            agent_config: Agent configuration from agents.yml
            tenant_id: Tenant identifier for data scoping
        
        Returns:
            Dict with entity data:
            {
                "account": [{...}, {...}],
                "opportunity": [{...}, {...}],
                "metadata": {"prepared_at": ..., "row_counts": {...}}
            }
        """
        start_time = time.time()
        consumes = agent_config.get("consumes", [])
        key_metrics = agent_config.get("key_metrics", [])
        
        if not consumes:
            self.logger.warning(f"Agent {agent_id} has no 'consumes' entities defined")
            return {"error": "No entities to consume"}
        
        self.logger.info(f"📊 Preparing input for agent '{agent_id}': consuming {len(consumes)} entities")
        
        agent_input = {"metadata": {"prepared_at": datetime.utcnow().isoformat(), "row_counts": {}}}
        
        try:
            con = duckdb.connect(self.db_path, read_only=True)
            
            for entity_name in consumes:
                table_name = f"dcl_{entity_name}"
                
                try:
                    # Check if table exists
                    table_exists = con.execute(
                        f"SELECT COUNT(*) FROM information_schema.tables WHERE table_name = '{table_name}'"
                    ).fetchone()[0] > 0
                    
                    if not table_exists:
                        self.logger.warning(f"Table {table_name} does not exist for agent {agent_id}")
                        agent_input[entity_name] = []
                        agent_input["metadata"]["row_counts"][entity_name] = 0
                        continue
                    
                    # Query all data from entity table
                    # Future optimization: Filter by key_metrics to reduce data transfer
                    df = con.execute(f"SELECT * FROM {table_name}").df()
                    
                    # Convert to dict records
                    records = df.to_dict(orient="records")
                    
                    # Clean NaN values
                    for record in records:
                        for key, value in list(record.items()):
                            if value != value:  # NaN check (NaN != NaN)
                                record[key] = None
                    
                    agent_input[entity_name] = records
                    agent_input["metadata"]["row_counts"][entity_name] = len(records)
                    
                    self.logger.info(f"  ✓ Loaded {len(records)} rows from {table_name}")
                
                except Exception as e:
                    self.logger.error(f"Error loading {table_name}: {e}")
                    agent_input[entity_name] = []
                    agent_input["metadata"]["row_counts"][entity_name] = 0
            
            con.close()
            
            elapsed = time.time() - start_time
            agent_input["metadata"]["preparation_time_seconds"] = round(elapsed, 3)
            
            self.logger.info(f"✅ Agent input prepared in {elapsed:.2f}s")
            
            return agent_input
        
        except Exception as e:
            self.logger.error(f"Failed to prepare agent input: {e}")
            return {"error": str(e), "metadata": {"prepared_at": datetime.utcnow().isoformat()}}
    
    def execute_agent(self, agent_id: str, agent_config: Dict[str, Any], agent_input: Dict[str, Any], tenant_id: str) -> Dict[str, Any]:
        """
        Execute agent logic using prepared input data.
        
        Current implementation: Mock analysis with basic statistics
        Future: LLM-based analysis, ML models, rule engines
        
        Args:
            agent_id: Agent identifier
            agent_config: Agent configuration
            agent_input: Prepared data from prepare_agent_input()
            tenant_id: Tenant identifier
        
        Returns:
            Agent execution results with insights and statistics
        """
        start_time = time.time()
        agent_name = agent_config.get("name", agent_id)
        
        self.logger.info(f"🤖 Executing agent: {agent_name}")
        
        if "error" in agent_input:
            return {
                "agent_id": agent_id,
                "status": "error",
                "error": agent_input["error"],
                "executed_at": datetime.utcnow().isoformat()
            }
        
        # Mock agent logic: Basic statistical analysis
        insights = []
        statistics = {}
        
        for entity_name, records in agent_input.items():
            if entity_name == "metadata":
                continue
            
            if not records:
                continue
            
            record_count = len(records)
            statistics[entity_name] = {"total_records": record_count}
            
            # Generate mock insights based on record counts
            if record_count > 0:
                insights.append({
                    "type": "data_availability",
                    "entity": entity_name,
                    "message": f"Found {record_count} {entity_name} record(s) for analysis",
                    "severity": "info"
                })
                
                # Agent-specific mock insights
                if agent_id == "revops_pilot":
                    if entity_name == "opportunity":
                        # Mock: Analyze opportunity pipeline
                        insights.append({
                            "type": "pipeline_health",
                            "entity": entity_name,
                            "message": f"Pipeline analysis: {record_count} opportunities detected",
                            "severity": "info",
                            "recommendation": "Review high-value opportunities for close date optimization"
                        })
                    elif entity_name == "account":
                        insights.append({
                            "type": "account_coverage",
                            "entity": entity_name,
                            "message": f"Account coverage: {record_count} active accounts",
                            "severity": "info"
                        })
                
                elif agent_id == "finops_pilot":
                    if entity_name == "aws_resources":
                        insights.append({
                            "type": "resource_optimization",
                            "entity": entity_name,
                            "message": f"Resource audit: {record_count} AWS resources identified",
                            "severity": "info",
                            "recommendation": "Review underutilized resources for cost optimization"
                        })
        
        elapsed = time.time() - start_time
        
        result = {
            "agent_id": agent_id,
            "agent_name": agent_name,
            "status": "success",
            "tenant_id": tenant_id,
            "executed_at": datetime.utcnow().isoformat(),
            "execution_time_seconds": round(elapsed, 3),
            "insights": insights,
            "statistics": statistics,
            "metadata": agent_input.get("metadata", {}),
            "execution_mode": "mock_analysis"  # Future: "llm_analysis"
        }
        
        self.logger.info(f"✅ Agent execution complete: {len(insights)} insights generated in {elapsed:.2f}s")
        
        return result
    
    def store_results(self, agent_id: str, results: Dict[str, Any], tenant_id: str):
        """
        Store agent execution results in tenant-scoped cache.
        
        Args:
            agent_id: Agent identifier
            results: Agent execution results
            tenant_id: Tenant identifier
        """
        if tenant_id not in self.results_cache:
            self.results_cache[tenant_id] = {}
        
        self.results_cache[tenant_id][agent_id] = results
        
        self.logger.info(f"💾 Stored results for agent '{agent_id}' (tenant: {tenant_id})")
    
    def get_results(self, agent_id: str, tenant_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve agent execution results from cache.
        
        Args:
            agent_id: Agent identifier
            tenant_id: Tenant identifier
        
        Returns:
            Agent results or None if not found
        """
        return self.results_cache.get(tenant_id, {}).get(agent_id)
    
    def get_all_results(self, tenant_id: str) -> Dict[str, Dict[str, Any]]:
        """
        Retrieve all agent results for a tenant.
        
        Args:
            tenant_id: Tenant identifier
        
        Returns:
            Dict of {agent_id: results}
        """
        return self.results_cache.get(tenant_id, {})
    
    async def execute_agents_async(self, selected_agents: List[str], tenant_id: str, ws_manager = None):
        """
        Execute multiple agents asynchronously with WebSocket progress events.
        
        This is the main entry point called after connect_source() completes.
        
        Args:
            selected_agents: List of agent IDs to execute
            tenant_id: Tenant identifier
            ws_manager: WebSocket manager for broadcasting events (optional)
        """
        self.logger.info(f"🚀 Starting agent execution for {len(selected_agents)} agent(s)")
        
        for agent_id in selected_agents:
            agent_config = self.agents_config.get("agents", {}).get(agent_id)
            
            if not agent_config:
                self.logger.warning(f"Agent config not found for: {agent_id}")
                continue
            
            try:
                # Broadcast: Agent started
                if ws_manager:
                    await ws_manager.broadcast({
                        "type": "agent_started",
                        "agent_id": agent_id,
                        "agent_name": agent_config.get("name", agent_id),
                        "timestamp": time.time()
                    })
                
                # Step 1: Prepare input
                agent_input = self.prepare_agent_input(agent_id, agent_config, tenant_id)
                
                # Step 2: Execute agent
                results = self.execute_agent(agent_id, agent_config, agent_input, tenant_id)
                
                # Step 3: Store results
                self.store_results(agent_id, results, tenant_id)
                
                # Broadcast: Agent completed
                if ws_manager:
                    await ws_manager.broadcast({
                        "type": "agent_completed",
                        "agent_id": agent_id,
                        "agent_name": agent_config.get("name", agent_id),
                        "status": results.get("status"),
                        "insights_count": len(results.get("insights", [])),
                        "execution_time": results.get("execution_time_seconds"),
                        "timestamp": time.time()
                    })
            
            except Exception as e:
                self.logger.error(f"Agent execution failed for {agent_id}: {e}")
                
                # Broadcast: Agent failed
                if ws_manager:
                    await ws_manager.broadcast({
                        "type": "agent_failed",
                        "agent_id": agent_id,
                        "error": str(e),
                        "timestamp": time.time()
                    })
