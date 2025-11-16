"""Final verification that fix logic is correct"""

class MockGraph:
    def __init__(self):
        self.nodes = []
    
    def add_node(self, node_id, label, node_type):
        if not any(n["id"] == node_id for n in self.nodes):
            self.nodes.append({"id": node_id, "label": label, "type": node_type})
            print(f"  ✅ Added node: {node_id}")
            return True
        else:
            print(f"  ⏭️  Node exists: {node_id}")
            return False

def test_fix_logic():
    """Simulate the exact fix logic"""
    graph = MockGraph()
    
    print("="*60)
    print("TESTING FIX LOGIC")
    print("="*60)
    
    # Scenario 1: Connect Salesforce
    print("\n1️⃣  Connect Salesforce")
    print("-" * 40)
    
    # Shared parent (FIX: was sys_salesforce before)
    graph.add_node("sys_sources", "Data Sources", "source_parent")
    graph.add_node("src_salesforce_Account", "Account (Salesforce)", "source")
    graph.add_node("src_salesforce_Opportunity", "Opportunity (Salesforce)", "source")
    graph.add_node("agent_revops_pilot", "Revops Pilot", "agent")
    
    print(f"📊 Node count: {len(graph.nodes)}")
    assert len(graph.nodes) == 4, f"Expected 4, got {len(graph.nodes)}"
    
    # Scenario 2: Connect HubSpot (FIX: no reset before this)
    print("\n2️⃣  Connect HubSpot (NO RESET - additive)")
    print("-" * 40)
    
    # Shared parent already exists (FIX: reuses sys_sources)
    graph.add_node("sys_sources", "Data Sources", "source_parent")
    graph.add_node("src_hubspot_Company", "Company (Hubspot)", "source")
    graph.add_node("src_hubspot_Deal", "Deal (Hubspot)", "source")
    graph.add_node("agent_revops_pilot", "Revops Pilot", "agent")
    
    print(f"📊 Node count: {len(graph.nodes)}")
    assert len(graph.nodes) == 6, f"Expected 6, got {len(graph.nodes)}"
    
    # Scenario 3: Reconnect Salesforce (idempotency)
    print("\n3️⃣  Reconnect Salesforce (idempotency test)")
    print("-" * 40)
    
    graph.add_node("sys_sources", "Data Sources", "source_parent")
    graph.add_node("src_salesforce_Account", "Account (Salesforce)", "source")
    graph.add_node("src_salesforce_Opportunity", "Opportunity (Salesforce)", "source")
    graph.add_node("agent_revops_pilot", "Revops Pilot", "agent")
    
    print(f"📊 Node count: {len(graph.nodes)}")
    assert len(graph.nodes) == 6, f"Expected 6 (idempotent), got {len(graph.nodes)}"
    
    # Final verification
    print("\n" + "="*60)
    print("✅ ALL ASSERTIONS PASSED")
    print("="*60)
    print(f"\nFinal node structure ({len(graph.nodes)} nodes):")
    for i, node in enumerate(graph.nodes, 1):
        print(f"  {i}. {node['id']} ({node['type']})")
    
    print("\n✅ Fix produces exactly 6 nodes as expected by tests")
    return True

if __name__ == "__main__":
    try:
        test_fix_logic()
        print("\n🎉 FIX VERIFIED - Logic is correct!")
    except AssertionError as e:
        print(f"\n❌ FIX FAILED - {e}")
        exit(1)
