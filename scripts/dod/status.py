#!/usr/bin/env python3
"""
DoD Status Script - Lists configured sources
Usage: python3 scripts/dod/status.py
"""
import os
import sys
import httpx


def main():
    """Check status of all configured sources"""
    api_base = os.getenv("API_BASE_URL", "http://localhost:5000")
    
    try:
        response = httpx.get(
            f"{api_base}/api/v1/debug/source-status",
            timeout=10.0
        )
        
        if response.status_code != 200:
            print(f"DOD_STATUS: FAIL")
            sys.exit(1)
        
        data = response.json()
        
        # Print status for each source
        for source_name, source_data in data.items():
            configured = "YES" if source_data.get("configured") else "NO"
            canonical = "FOUND" if source_data.get("last_canonical_at") else "NONE"
            
            print(f"DOD_SOURCE:{source_name}:CONFIGURED: {configured}")
            print(f"DOD_SOURCE:{source_name}:CANONICAL: {canonical}")
        
        print("DOD_STATUS: PASS")
        sys.exit(0)
    
    except Exception as e:
        print(f"DOD_STATUS: FAIL ({str(e)})")
        sys.exit(1)


if __name__ == "__main__":
    main()
