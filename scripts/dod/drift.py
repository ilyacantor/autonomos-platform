#!/usr/bin/env python3
"""
DoD Drift Test Script - Runs drift mutation demo
Usage: python3 scripts/dod/drift.py <source_name>
"""
import os
import sys
import httpx


def main():
    """Run drift mutation test for a source"""
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/dod/drift.py <source_name>")
        sys.exit(1)
    
    source_name = sys.argv[1]
    valid_sources = ["supabase", "mongodb"]
    
    if source_name not in valid_sources:
        print(f"Drift tests only available for: {', '.join(valid_sources)}")
        print(f"DOD_DRIFT:{source_name}:TICKET: SKIPPED")
        print(f"DOD_DRIFT:{source_name}:REPAIR: SKIPPED")
        print(f"DOD_DRIFT:{source_name}:RESTORED: SKIPPED")
        print(f"DOD_DRIFT:{source_name}:STATUS: SKIPPED")
        sys.exit(0)
    
    api_base = os.getenv("API_BASE_URL", "http://localhost:5000")
    
    try:
        # Prepare mutation payload
        if source_name == "supabase":
            payload = {
                "operation": "rename_column",
                "table": "opportunities",
                "from": "amount",
                "to": "amount_usd"
            }
        else:  # mongodb
            payload = {
                "operation": "rename_field",
                "collection": "opportunities",
                "from": "amount",
                "to": "amount_usd"
            }
        
        # Call drift mutation endpoint
        response = httpx.post(
            f"{api_base}/api/v1/mesh/test/{source_name}/mutate",
            json=payload,
            timeout=15.0
        )
        
        if response.status_code != 200:
            print(f"DOD_DRIFT:{source_name}:TICKET: FAIL")
            print(f"DOD_DRIFT:{source_name}:REPAIR: FAIL")
            print(f"DOD_DRIFT:{source_name}:RESTORED: NO")
            print(f"DOD_DRIFT:{source_name}:STATUS: FAIL")
            sys.exit(1)
        
        data = response.json()
        
        ticket = "RAISED" if data.get("drift_detected") else "FAIL"
        repair = "APPLIED" if data.get("repair_simulated") else "FAIL"
        restored = "YES" if data.get("restored") else "NO"
        status = data.get("status", "FAIL")
        
        print(f"DOD_DRIFT:{source_name}:TICKET: {ticket}")
        print(f"DOD_DRIFT:{source_name}:REPAIR: {repair}")
        print(f"DOD_DRIFT:{source_name}:RESTORED: {restored}")
        print(f"DOD_DRIFT:{source_name}:STATUS: {status}")
        
        sys.exit(0 if status == "PASS" else 1)
    
    except Exception as e:
        print(f"DOD_DRIFT:{source_name}:TICKET: FAIL")
        print(f"DOD_DRIFT:{source_name}:REPAIR: FAIL")
        print(f"DOD_DRIFT:{source_name}:RESTORED: NO")
        print(f"DOD_DRIFT:{source_name}:STATUS: FAIL")
        sys.exit(1)


if __name__ == "__main__":
    main()
