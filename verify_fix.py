"""
Verify multi-source graph construction fix without pytest overhead.
Simulates the exact test scenarios to validate node counts.
"""
import sys
import os
import requests
import time
import json

# Test configuration
BASE_URL = "http://localhost:5000"
TEST_USER_EMAIL = f"verify-fix-{int(time.time())}@test.com"
TEST_PASSWORD = "TestPass123!"

def register_and_login():
    """Create test user and get auth token"""
    # Register
    reg_response = requests.post(
        f"{BASE_URL}/users/register",
        json={
            "email": TEST_USER_EMAIL,
            "password": TEST_PASSWORD,
            "tenant_name": "VerifyFixTenant"
        }
    )
    print(f"Registration: {reg_response.status_code}")
    
    if reg_response.status_code != 200:
        print(f"Registration failed: {reg_response.text}")
        return None
    
    # Login
    login_response = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        data={
            "username": TEST_USER_EMAIL,
            "password": TEST_PASSWORD
        }
    )
    print(f"Login: {login_response.status_code}")
    
    if login_response.status_code != 200:
        print(f"Login failed: {login_response.text}")
        return None
    
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def reset_state(headers):
    """Reset DCL state"""
    response = requests.post(f"{BASE_URL}/dcl/reset", headers=headers)
    print(f"Reset: {response.status_code}")
    return response.status_code == 200

def connect_source(source_name, headers):
    """Connect a single source"""
    response = requests.get(
        f"{BASE_URL}/dcl/connect",
        params={
            "sources": source_name,
            "agents": "revops_pilot",
            "llm_model": "gemini-2.5-flash"
        },
        headers=headers,
        timeout=120  # 2 minute timeout
    )
    print(f"Connect {source_name}: {response.status_code}")
    return response.status_code == 200

def get_state(headers):
    """Get current graph state"""
    response = requests.get(f"{BASE_URL}/dcl/state", headers=headers)
    if response.status_code != 200:
        print(f"Get state failed: {response.status_code}")
        return None
    return response.json()

def test_scenario_1(headers):
    """
    Test 1: Sequential source connection
    - Connect salesforce → 4 nodes
    - Connect hubspot → 6 nodes (should ADD, not replace)
    """
    print("\n" + "="*60)
    print("TEST 1: Sequential Multi-Source Integration")
    print("="*60)
    
    # Reset to clean state
    reset_state(headers)
    
    # Connect salesforce
    print("\n1. Connecting Salesforce...")
    if not connect_source("salesforce", headers):
        print("❌ Failed to connect salesforce")
        return False
    
    state1 = get_state(headers)
    if not state1:
        print("❌ Failed to get state after salesforce")
        return False
    
    nodes_after_sf = len(state1["nodes"])
    print(f"   Nodes after Salesforce: {nodes_after_sf}")
    print(f"   Node IDs: {[n['id'] for n in state1['nodes']]}")
    
    # Connect hubspot
    print("\n2. Connecting HubSpot...")
    if not connect_source("hubspot", headers):
        print("❌ Failed to connect hubspot")
        return False
    
    state2 = get_state(headers)
    if not state2:
        print("❌ Failed to get state after hubspot")
        return False
    
    nodes_after_hs = len(state2["nodes"])
    print(f"   Nodes after HubSpot: {nodes_after_hs}")
    print(f"   Node IDs: {[n['id'] for n in state2['nodes']]}")
    
    # Validate
    if nodes_after_hs == 6:
        print("\n✅ TEST 1 PASSED: 6 nodes (expected)")
        return True
    else:
        print(f"\n❌ TEST 1 FAILED: {nodes_after_hs} nodes (expected 6)")
        return False

def test_scenario_2(headers):
    """
    Test 2: Idempotent reconnection
    - Connect both sources → 6 nodes
    - Reconnect salesforce → Still 6 nodes (idempotent)
    """
    print("\n" + "="*60)
    print("TEST 2: Idempotent Source Reconnection")
    print("="*60)
    
    # Reset to clean state
    reset_state(headers)
    
    # Connect both sources together
    print("\n1. Connecting Salesforce + HubSpot together...")
    response = requests.get(
        f"{BASE_URL}/dcl/connect",
        params={
            "sources": "salesforce,hubspot",
            "agents": "revops_pilot",
            "llm_model": "gemini-2.5-flash"
        },
        headers=headers,
        timeout=120
    )
    print(f"Connect both: {response.status_code}")
    
    if response.status_code != 200:
        print("❌ Failed to connect sources")
        return False
    
    state1 = get_state(headers)
    if not state1:
        print("❌ Failed to get initial state")
        return False
    
    nodes_initial = len(state1["nodes"])
    print(f"   Initial nodes: {nodes_initial}")
    print(f"   Node IDs: {[n['id'] for n in state1['nodes']]}")
    
    # Reconnect salesforce (should be idempotent)
    print("\n2. Reconnecting Salesforce (idempotency test)...")
    if not connect_source("salesforce", headers):
        print("❌ Failed to reconnect salesforce")
        return False
    
    state2 = get_state(headers)
    if not state2:
        print("❌ Failed to get state after reconnect")
        return False
    
    nodes_after_reconnect = len(state2["nodes"])
    print(f"   Nodes after reconnect: {nodes_after_reconnect}")
    print(f"   Node IDs: {[n['id'] for n in state2['nodes']]}")
    
    # Validate
    if nodes_after_reconnect == nodes_initial and nodes_initial == 6:
        print("\n✅ TEST 2 PASSED: 6 nodes maintained (idempotent)")
        return True
    else:
        print(f"\n❌ TEST 2 FAILED: {nodes_after_reconnect} nodes (expected {nodes_initial})")
        return False

if __name__ == "__main__":
    print("Multi-Source Graph Construction Fix Verification")
    print("="*60)
    
    # Get auth headers
    print("\nAuthenticating...")
    headers = register_and_login()
    if not headers:
        print("❌ Authentication failed")
        sys.exit(1)
    
    # Run tests
    test1_passed = test_scenario_1(headers)
    time.sleep(2)  # Brief pause between tests
    test2_passed = test_scenario_2(headers)
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Test 1 (Sequential): {'✅ PASSED' if test1_passed else '❌ FAILED'}")
    print(f"Test 2 (Idempotent): {'✅ PASSED' if test2_passed else '❌ FAILED'}")
    
    if test1_passed and test2_passed:
        print("\n🎉 ALL TESTS PASSED! Fix verified.")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed. Fix needs adjustment.")
        sys.exit(1)
