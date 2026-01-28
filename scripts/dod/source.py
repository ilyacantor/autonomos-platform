#!/usr/bin/env python3
"""
DoD Source Validation Script - Validates one source end-to-end
Usage: python3 scripts/dod/source.py <source_name>
"""
import os
import sys
import httpx


def main():
    """Validate one source end-to-end"""
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/dod/source.py <source_name>")
        sys.exit(1)
    
    source_name = sys.argv[1]
    valid_sources = ["salesforce", "supabase", "mongodb", "filesource"]
    
    if source_name not in valid_sources:
        print(f"Invalid source. Must be one of: {', '.join(valid_sources)}")
        sys.exit(1)
    
    api_base = os.getenv("API_BASE_URL", "http://localhost:5000")
    status = "PASS"
    
    try:
        # Step 1: Check if source is configured
        response = httpx.get(
            f"{api_base}/api/v1/debug/source-status",
            timeout=10.0
        )
        
        if response.status_code != 200:
            print(f"DOD_SOURCE:{source_name}:CONFIGURED: NO")
            print(f"DOD_SOURCE:{source_name}:CANONICAL: NONE")
            print(f"DOD_SOURCE:{source_name}:VIEW_ROWS: 0")
            print(f"DOD_SOURCE:{source_name}:STATUS: FAIL")
            sys.exit(1)
        
        data = response.json()
        source_data = data.get(source_name, {})
        
        configured = "YES" if source_data.get("configured") else "NO"
        canonical = "FOUND" if source_data.get("last_canonical_at") else "NONE"
        
        print(f"DOD_SOURCE:{source_name}:CONFIGURED: {configured}")
        print(f"DOD_SOURCE:{source_name}:CANONICAL: {canonical}")
        
        if not source_data.get("configured"):
            status = "FAIL"
        
        # Step 2: Check view rows (try opportunities and accounts)
        view_rows = 0
        for entity in ["opportunities", "accounts"]:
            try:
                view_response = httpx.get(
                    f"{api_base}/api/v1/dcl/views/{entity}",
                    params={"limit": 100, "offset": 0},
                    timeout=10.0
                )
                if view_response.status_code == 200:
                    view_data = view_response.json()
                    if view_data.get("success"):
                        count = view_data.get("meta", {}).get("count", 0)
                        view_rows += count
            except Exception:
                pass  # Network or timeout error - continue with next entity
        
        print(f"DOD_SOURCE:{source_name}:VIEW_ROWS: {view_rows}")
        
        # Determine final status
        if not source_data.get("configured") or canonical == "NONE":
            status = "FAIL"
        
        print(f"DOD_SOURCE:{source_name}:STATUS: {status}")
        
        # Check REQUIRED_SOURCES env var
        required_sources = os.getenv("REQUIRED_SOURCES", "").split(",")
        required_sources = [s.strip() for s in required_sources if s.strip()]
        
        if source_name in required_sources and status == "FAIL":
            sys.exit(1)
        
        sys.exit(0 if status == "PASS" else 1)
    
    except Exception as e:
        print(f"DOD_SOURCE:{source_name}:CONFIGURED: NO")
        print(f"DOD_SOURCE:{source_name}:CANONICAL: NONE")
        print(f"DOD_SOURCE:{source_name}:VIEW_ROWS: 0")
        print(f"DOD_SOURCE:{source_name}:STATUS: FAIL")
        sys.exit(1)


if __name__ == "__main__":
    main()
