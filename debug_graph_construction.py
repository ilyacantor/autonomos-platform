"""
Debug script to trace graph construction for multi-source scenarios.
Simulates what happens when connecting salesforce then hubspot.
"""
import sys
import os

# Mock the state_access module behavior
class MockStateAccess:
    def __init__(self):
        self.graph_state = {"nodes": [], "edges": []}
        self.sources = []
        self.entity_sources = {}
        self.source_schemas = {}
        self.selected_agents = ["revops_pilot"]
        self.event_log = []
    
    def get_graph_state(self, tenant_id):
        return self.graph_state
    
    def set_graph_state(self, tenant_id, state):
        self.graph_state = state
    
    def get_sources(self, tenant_id):
        return self.sources
    
    def set_sources(self, tenant_id, sources):
        self.sources = sources
    
    def get_entity_sources(self, tenant_id):
        return self.entity_sources
    
    def set_entity_sources(self, tenant_id, entity_sources):
        self.entity_sources = entity_sources
    
    def get_selected_agents(self, tenant_id):
        return self.selected_agents

# Simplified version of add_graph_nodes_for_source
def add_graph_nodes_for_source_debug(source_key, tables, state_access, tenant_id="default"):
    """
    Simplified version of add_graph_nodes_for_source to debug node construction.
    """
    current_graph = state_access.get_graph_state(tenant_id)
    
    print(f"\n=== Adding nodes for {source_key} ===")
    print(f"Current nodes before: {len(current_graph['nodes'])}")
    print(f"Node IDs: {[n['id'] for n in current_graph['nodes']]}")
    
    # CRITICAL FIX: Use a SINGLE shared parent node for ALL sources
    parent_node_id = "sys_sources"  # Shared across all sources
    parent_label = "Data Sources"
    
    if not any(n["id"] == parent_node_id for n in current_graph["nodes"]):
        print(f"  Adding SHARED parent node: {parent_node_id}")
        current_graph["nodes"].append({
            "id": parent_node_id,
            "label": parent_label,
            "type": "source_parent"
        })
    else:
        print(f"  Shared parent node already exists: {parent_node_id}")
    
    # Add source nodes for each table
    source_system = source_key.replace('_', ' ').title()
    
    for t, table_data in tables.items():
        node_id = f"src_{source_key}_{t}"
        label = f"{t} ({source_system})"
        fields = list(table_data.get("schema", {}).keys()) if isinstance(table_data, dict) else []
        
        if not any(n["id"] == node_id for n in current_graph["nodes"]):
            print(f"  Adding source node: {node_id}")
            current_graph["nodes"].append({
                "id": node_id,
                "label": label,
                "type": "source",
                "sourceSystem": source_system,
                "parentId": parent_node_id,
                "fields": fields
            })
        else:
            print(f"  Source node already exists: {node_id}")
        
        # Create hierarchy edge
        edge_exists = any(
            e["source"] == parent_node_id and e["target"] == node_id and e.get("edgeType") == "hierarchy"
            for e in current_graph["edges"]
        )
        if not edge_exists:
            current_graph["edges"].append({
                "source": parent_node_id,
                "target": node_id,
                "edgeType": "hierarchy",
                "value": 1
            })
    
    # Add agent nodes
    selected_agents = state_access.get_selected_agents(tenant_id)
    for agent_id in selected_agents:
        if not any(n["id"] == f"agent_{agent_id}" for n in current_graph["nodes"]):
            print(f"  Adding agent node: agent_{agent_id}")
            current_graph["nodes"].append({
                "id": f"agent_{agent_id}",
                "label": agent_id.title(),
                "type": "agent"
            })
        else:
            print(f"  Agent node already exists: agent_{agent_id}")
    
    state_access.set_graph_state(tenant_id, current_graph)
    
    print(f"Current nodes after: {len(current_graph['nodes'])}")
    print(f"Node IDs: {[n['id'] for n in current_graph['nodes']]}")
    
    return current_graph

# Simulate the test scenario
if __name__ == "__main__":
    state_access = MockStateAccess()
    tenant_id = "test-tenant"
    
    # Scenario 1: Connect salesforce
    print("\n" + "="*60)
    print("SCENARIO 1: Connect Salesforce")
    print("="*60)
    
    salesforce_tables = {
        "Account": {"schema": {"id": "string", "name": "string"}},
        "Opportunity": {"schema": {"id": "string", "name": "string"}}
    }
    
    graph1 = add_graph_nodes_for_source_debug("salesforce", salesforce_tables, state_access, tenant_id)
    print(f"\n✅ After Salesforce: {len(graph1['nodes'])} nodes")
    print(f"   Expected: 1 parent + 2 sources + 1 agent = 4 nodes")
    
    # Scenario 2: Connect hubspot (sequential)
    print("\n" + "="*60)
    print("SCENARIO 2: Connect HubSpot (after Salesforce)")
    print("="*60)
    
    hubspot_tables = {
        "Company": {"schema": {"id": "string", "name": "string"}},
        "Deal": {"schema": {"id": "string", "name": "string"}}
    }
    
    graph2 = add_graph_nodes_for_source_debug("hubspot", hubspot_tables, state_access, tenant_id)
    print(f"\n✅ After HubSpot: {len(graph2['nodes'])} nodes")
    print(f"   Expected: 2 parents + 4 sources + 1 agent = 7 nodes")
    print(f"   Test expects: 6 nodes (why?)")
    
    # Scenario 3: Reconnect salesforce (simulating data update)
    print("\n" + "="*60)
    print("SCENARIO 3: Reconnect Salesforce (data update)")
    print("="*60)
    
    graph3 = add_graph_nodes_for_source_debug("salesforce", salesforce_tables, state_access, tenant_id)
    print(f"\n✅ After reconnecting Salesforce: {len(graph3['nodes'])} nodes")
    print(f"   Expected: Should stay at 7 nodes (idempotent)")
    print(f"   Test expects: 6 nodes")
    
    # Analysis
    print("\n" + "="*60)
    print("ANALYSIS")
    print("="*60)
    print(f"Current implementation creates {len(graph2['nodes'])} nodes for 2 sources")
    print(f"Tests expect 6 nodes")
    print(f"\nPossible issues:")
    print("  1. Tests might expect shared agent node (not duplicated)")
    print("  2. Tests might expect ontology nodes instead of source nodes")
    print("  3. Tests might use different node construction logic")
    print(f"\nNode breakdown:")
    for node in graph2['nodes']:
        print(f"  - {node['id']}: {node['type']}")
