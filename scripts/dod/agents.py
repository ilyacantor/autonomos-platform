#!/usr/bin/env python3
"""
DoD Agents Test Script - Tests revops + finops read+intent
Usage: python3 scripts/dod/agents.py
"""
import os
import sys
import httpx


def test_agent(agent_name, entity="opportunities"):
    """Test one agent's read and intent capabilities"""
    api_base = os.getenv("API_BASE_URL", "http://localhost:5000")
    
    read_status = "FAIL"
    intent_status = "FAIL"
    trace_id = ""
    
    try:
        # Test read access
        try:
            read_response = httpx.get(
                f"{api_base}/api/v1/dcl/views/{entity}",
                params={"limit": 1, "offset": 0},
                timeout=10.0
            )
            if read_response.status_code == 200:
                read_status = "OK"
        except:
            pass
        
        # Test intent execution
        try:
            intent_response = httpx.post(
                f"{api_base}/api/v1/intents/{agent_name}/execute",
                json={"intent": "noop", "dry_run": True, "explain_only": True},
                timeout=10.0
            )
            if intent_response.status_code in [200, 202]:
                intent_status = "OK"
                response_data = intent_response.json()
                trace_id = response_data.get("trace_id", "")
        except:
            pass
    
    except:
        pass
    
    print(f"DOD_AGENT:{agent_name}:READ: {read_status}")
    print(f"DOD_AGENT:{agent_name}:INTENT: {intent_status} TRACE={trace_id}")
    
    return read_status == "OK" and intent_status == "OK"


def main():
    """Test both revops and finops agents"""
    try:
        revops_pass = test_agent("revops", "opportunities")
        finops_pass = test_agent("finops", "opportunities")
        
        if revops_pass and finops_pass:
            print("DOD_STATUS: PASS")
            sys.exit(0)
        else:
            print("DOD_STATUS: FAIL")
            sys.exit(1)
    
    except Exception as e:
        print("DOD_AGENT:revops:READ: FAIL")
        print("DOD_AGENT:revops:INTENT: FAIL TRACE=")
        print("DOD_AGENT:finops:READ: FAIL")
        print("DOD_AGENT:finops:INTENT: FAIL TRACE=")
        print(f"DOD_STATUS: FAIL ({str(e)})")
        sys.exit(1)


if __name__ == "__main__":
    main()
