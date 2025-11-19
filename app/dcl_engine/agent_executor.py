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
import json
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
    
    def __init__(self, get_db_path_fn, agents_config: Dict[str, Any], results_cache: Dict[str, Dict], redis_client=None):
        """
        Initialize AgentExecutor with tenant-scoped DuckDB support.
        
        Args:
            get_db_path_fn: Callable function that accepts tenant_id and returns DB path
                           Example: get_db_path(tenant_id) -> "registry_{tenant_id}.duckdb"
            agents_config: Loaded agents configuration from config.yml
            results_cache: In-memory dict for storing results (tenant_id -> {agent_id -> results})
            redis_client: Redis client for accessing Phase 4 metadata (optional)
        """
        self.get_db_path = get_db_path_fn
        self.agents_config = agents_config
        self.results_cache = results_cache
        self.redis_client = redis_client
        self.logger = logging.getLogger(__name__)
    
    def _ensure_metadata_table(self, tenant_id: str):
        """
        Ensure DuckDB metadata table exists for a given tenant.
        
        Creates dcl_metadata table if it doesn't exist with schema:
        - tenant_id: Tenant identifier
        - source_id: Source connector identifier
        - metadata_json: JSON column containing Phase 4 metadata
        - created_at: Timestamp of metadata storage
        
        Args:
            tenant_id: Tenant identifier for scoped DB file
        """
        try:
            db_path = self.get_db_path(tenant_id)
            con = duckdb.connect(db_path)
            
            con.execute("""
                CREATE TABLE IF NOT EXISTS dcl_metadata (
                    tenant_id VARCHAR NOT NULL,
                    source_id VARCHAR NOT NULL,
                    metadata_json JSON NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (tenant_id, source_id, created_at)
                )
            """)
            
            con.close()
            self.logger.debug(f"✅ Ensured dcl_metadata table exists (tenant: {tenant_id})")
            
        except Exception as e:
            self.logger.warning(f"Failed to ensure metadata table for tenant {tenant_id}: {e}")
    
    def store_metadata_in_duckdb(self, tenant_id: str, source_id: str, metadata: dict):
        """
        Store Phase 4 metadata in DuckDB for historical analysis.
        
        Args:
            tenant_id: Tenant identifier
            source_id: Source connector identifier
            metadata: Aggregated metadata dictionary
        """
        try:
            # Ensure metadata table exists for this tenant
            self._ensure_metadata_table(tenant_id)
            
            # Connect to tenant-scoped DB file
            db_path = self.get_db_path(tenant_id)
            con = duckdb.connect(db_path)
            
            # Convert metadata to JSON string
            metadata_json = json.dumps(metadata)
            
            # Insert metadata record
            con.execute("""
                INSERT INTO dcl_metadata (tenant_id, source_id, metadata_json)
                VALUES (?, ?, ?)
            """, [tenant_id, source_id, metadata_json])
            
            con.close()
            self.logger.debug(f"📊 Stored metadata in DuckDB for {source_id} (tenant: {tenant_id})")
            
        except Exception as e:
            self.logger.error(f"Failed to store metadata in DuckDB: {e}")
    
    def get_data_quality_metadata(self, tenant_id: str, source_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Fetch Phase 4 data quality metadata from Redis (fast) or DuckDB (historical).
        
        Hybrid approach:
        1. Try Redis first for fast access to latest metadata
        2. Fallback to DuckDB for historical data if Redis unavailable
        3. Aggregate metadata across all sources for tenant-wide view
        
        Args:
            tenant_id: Tenant identifier
            source_ids: Optional list of source IDs to filter (None = all sources)
            
        Returns:
            Aggregated metadata dictionary with tenant-wide data quality insights
        """
        aggregated = {
            "overall_confidence": None,
            "drift_detected": False,
            "repair_processed": False,
            "auto_applied_repairs": 0,
            "hitl_pending_repairs": 0,
            "processing_stages": set(),
            "sources_with_drift": [],
            "low_confidence_sources": [],
            "sources": {}
        }
        
        try:
            # Try Redis first (fast access)
            if self.redis_client:
                # If no source_ids specified, try to discover them
                if not source_ids:
                    # Scan for metadata keys for this tenant
                    pattern = f"dcl:metadata:{tenant_id}:*"
                    cursor = 0
                    source_ids = []
                    
                    while True:
                        cursor, keys = self.redis_client.scan(cursor, match=pattern, count=100)
                        for key in keys:
                            key_str = key.decode('utf-8') if isinstance(key, bytes) else key
                            parts = key_str.split(':')
                            if len(parts) >= 4:
                                source_id = parts[3]
                                if source_id not in source_ids:
                                    source_ids.append(source_id)
                        if cursor == 0:
                            break
                
                # Fetch metadata for each source
                for source_id in source_ids or []:
                    redis_key = f"dcl:metadata:{tenant_id}:{source_id}"
                    
                    try:
                        metadata_json = self.redis_client.get(redis_key)
                        if metadata_json:
                            metadata = json.loads(metadata_json)
                            
                            # Store per-source metadata
                            aggregated["sources"][source_id] = metadata
                            
                            # Aggregate tenant-wide metrics
                            if metadata.get("drift_detected"):
                                aggregated["drift_detected"] = True
                                if source_id not in aggregated["sources_with_drift"]:
                                    aggregated["sources_with_drift"].append(source_id)
                            
                            if metadata.get("repair_processed"):
                                aggregated["repair_processed"] = True
                            
                            aggregated["auto_applied_repairs"] += metadata.get("auto_applied_count", 0)
                            aggregated["hitl_pending_repairs"] += metadata.get("hitl_queued_count", 0)
                            
                            for stage in metadata.get("processing_stages", []):
                                aggregated["processing_stages"].add(stage)
                            
                            # Track low confidence sources
                            if metadata.get("overall_data_quality_score") is not None and metadata["overall_data_quality_score"] < 0.7:
                                if source_id not in aggregated["low_confidence_sources"]:
                                    aggregated["low_confidence_sources"].append(source_id)
                    
                    except Exception as e:
                        self.logger.warning(f"Failed to fetch metadata from Redis for {source_id}: {e}")
                        continue
                
                # Convert sets to lists
                aggregated["processing_stages"] = list(aggregated["processing_stages"])
                
                self.logger.info(f"📊 Fetched metadata from Redis for {len(aggregated['sources'])} sources")
                return aggregated
            
            else:
                # Fallback to DuckDB if Redis unavailable
                self.logger.info("Redis unavailable, fetching metadata from DuckDB")
                
                # Connect to tenant-scoped DB file
                db_path = self.get_db_path(tenant_id)
                con = duckdb.connect(db_path, read_only=True)
                
                # Query latest metadata for each source
                if source_ids:
                    placeholders = ','.join(['?' for _ in source_ids])
                    query = f"""
                        SELECT source_id, metadata_json, created_at
                        FROM dcl_metadata
                        WHERE tenant_id = ? AND source_id IN ({placeholders})
                        ORDER BY created_at DESC
                    """
                    params = [tenant_id] + source_ids
                else:
                    query = """
                        SELECT source_id, metadata_json, created_at
                        FROM dcl_metadata
                        WHERE tenant_id = ?
                        ORDER BY created_at DESC
                    """
                    params = [tenant_id]
                
                results = con.execute(query, params).fetchall()
                
                # Process results (take latest per source)
                seen_sources = set()
                for row in results:
                    source_id, metadata_json, created_at = row
                    
                    if source_id in seen_sources:
                        continue
                    
                    seen_sources.add(source_id)
                    
                    try:
                        metadata = json.loads(metadata_json)
                        aggregated["sources"][source_id] = metadata
                        
                        # Aggregate metrics (same logic as Redis)
                        if metadata.get("drift_detected"):
                            aggregated["drift_detected"] = True
                            if source_id not in aggregated["sources_with_drift"]:
                                aggregated["sources_with_drift"].append(source_id)
                        
                        if metadata.get("repair_processed"):
                            aggregated["repair_processed"] = True
                        
                        aggregated["auto_applied_repairs"] += metadata.get("auto_applied_count", 0)
                        aggregated["hitl_pending_repairs"] += metadata.get("hitl_queued_count", 0)
                        
                        for stage in metadata.get("processing_stages", []):
                            aggregated["processing_stages"].add(stage)
                    
                    except Exception as e:
                        self.logger.warning(f"Failed to parse metadata for {source_id}: {e}")
                        continue
                
                con.close()
                
                aggregated["processing_stages"] = list(aggregated["processing_stages"])
                
                self.logger.info(f"📊 Fetched metadata from DuckDB for {len(aggregated['sources'])} sources")
                return aggregated
        
        except Exception as e:
            self.logger.error(f"Failed to fetch data quality metadata: {e}")
            return aggregated
    
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
        
        agent_input: Dict[str, Any] = {"metadata": {"prepared_at": datetime.utcnow().isoformat(), "row_counts": {}}}
        
        # Fetch Phase 4 data quality metadata
        data_quality_metadata = self.get_data_quality_metadata(tenant_id)
        agent_input["data_quality_metadata"] = data_quality_metadata
        
        self.logger.info(f"📊 Data quality metadata: drift={data_quality_metadata.get('drift_detected')}, repairs={data_quality_metadata.get('auto_applied_repairs')}, sources={len(data_quality_metadata.get('sources', {}))}")
        
        try:
            # Connect to tenant-scoped DB file
            db_path = self.get_db_path(tenant_id)
            con = duckdb.connect(db_path, read_only=True)
            
            for entity_name in consumes:
                table_name = f"dcl_{entity_name}"
                
                try:
                    # Check if table exists
                    result = con.execute(
                        f"SELECT COUNT(*) FROM information_schema.tables WHERE table_name = '{table_name}'"
                    ).fetchone()
                    table_exists = result is not None and result[0] > 0
                    
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
        
        # Extract data quality metadata for intelligent insights
        data_quality = agent_input.get("data_quality_metadata", {})
        
        # Generate data quality insights
        if data_quality.get("drift_detected"):
            drift_sources = data_quality.get("sources_with_drift", [])
            insights.append({
                "type": "data_quality_alert",
                "severity": "warning",
                "message": f"Schema drift detected in {len(drift_sources)} source(s): {', '.join(drift_sources)}",
                "recommendation": "Review drift details and approve/reject automated repairs",
                "sources_affected": drift_sources
            })
        
        if data_quality.get("repair_processed"):
            auto_repairs = data_quality.get("auto_applied_repairs", 0)
            hitl_repairs = data_quality.get("hitl_pending_repairs", 0)
            
            if auto_repairs > 0:
                insights.append({
                    "type": "data_quality_info",
                    "severity": "info",
                    "message": f"Auto-applied {auto_repairs} field mapping repair(s)",
                    "recommendation": "Data quality automatically maintained"
                })
            
            if hitl_repairs > 0:
                insights.append({
                    "type": "data_quality_action_required",
                    "severity": "warning",
                    "message": f"{hitl_repairs} repair(s) require human review",
                    "recommendation": "Review and approve pending field mappings in AAM dashboard"
                })
        
        if data_quality.get("low_confidence_sources"):
            low_conf_sources = data_quality.get("low_confidence_sources", [])
            insights.append({
                "type": "data_quality_alert",
                "severity": "warning",
                "message": f"Low confidence data from {len(low_conf_sources)} source(s): {', '.join(low_conf_sources)}",
                "recommendation": "Consider manual review of data mappings for these sources",
                "sources_affected": low_conf_sources
            })
        
        # Calculate overall data quality confidence
        if data_quality.get("overall_data_quality_score") is not None:
            statistics["data_quality_score"] = data_quality["overall_data_quality_score"]
            
            if data_quality["overall_data_quality_score"] >= 0.9:
                confidence_level = "high"
            elif data_quality["overall_data_quality_score"] >= 0.7:
                confidence_level = "medium"
            else:
                confidence_level = "low"
            
            insights.append({
                "type": "data_quality_score",
                "severity": "info",
                "message": f"Overall data quality: {confidence_level} ({data_quality['overall_data_quality_score']:.2%})",
                "confidence_level": confidence_level
            })
        
        for entity_name, records in agent_input.items():
            if entity_name in ["metadata", "data_quality_metadata"]:
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
            "data_quality_metadata": data_quality,
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
                
                # P4-5: Publish telemetry event for task dispatch
                if hasattr(self, 'flow_publisher') and self.flow_publisher:
                    try:
                        await self.flow_publisher.publish_agent_task_dispatched(
                            task_id=agent_id,
                            tenant_id=tenant_id,
                            metadata={
                                'agent_name': agent_config.get("name", agent_id),
                                'workflow_name': agent_config.get("workflow", "unknown")
                            }
                        )
                    except Exception as e:
                        self.logger.warning(f"Failed to publish task dispatch telemetry: {e}")
                
                # Step 1: Prepare input
                agent_input = self.prepare_agent_input(agent_id, agent_config, tenant_id)
                
                # Step 2: Execute agent
                results = self.execute_agent(agent_id, agent_config, agent_input, tenant_id)
                
                # Step 3: Store results
                self.store_results(agent_id, results, tenant_id)
                
                # P4-5: Publish telemetry event for task completion
                if hasattr(self, 'flow_publisher') and self.flow_publisher:
                    try:
                        duration_ms = int(results.get("execution_time_seconds", 0) * 1000)
                        await self.flow_publisher.publish_agent_task_completed(
                            task_id=agent_id,
                            tenant_id=tenant_id,
                            duration_ms=duration_ms,
                            metadata={
                                'agent_name': agent_config.get("name", agent_id),
                                'status': results.get("status"),
                                'insights_count': len(results.get("insights", []))
                            }
                        )
                    except Exception as e:
                        self.logger.warning(f"Failed to publish task completion telemetry: {e}")
                
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
                
                # P4-5: Publish telemetry event for task failure
                if hasattr(self, 'flow_publisher') and self.flow_publisher:
                    try:
                        from app.telemetry.flow_events import FlowEventLayer, FlowEventStage, FlowEventStatus
                        await self.flow_publisher.publish(
                            layer=FlowEventLayer.AGENT,
                            stage=FlowEventStage.TASK_FAILED,
                            status=FlowEventStatus.FAILURE,
                            entity_id=agent_id,
                            tenant_id=tenant_id,
                            metadata={
                                'agent_name': agent_config.get("name", agent_id) if agent_config else agent_id,
                                'error_message': str(e)
                            }
                        )
                    except Exception as telemetry_error:
                        self.logger.warning(f"Failed to publish task failure telemetry: {telemetry_error}")
                
                # Broadcast: Agent failed
                if ws_manager:
                    await ws_manager.broadcast({
                        "type": "agent_failed",
                        "agent_id": agent_id,
                        "error": str(e),
                        "timestamp": time.time()
                    })
