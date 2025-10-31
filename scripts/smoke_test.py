#!/usr/bin/env python3
"""
AutonomOS Platform Smoke Test
Non-destructive smoke test for core platform endpoints
"""

import requests
import time
import sys
import os
from typing import Dict, Any, Tuple, Optional, List

# Color codes for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

class SmokeTest:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.results = []
        self.total_time = 0
        
    def log(self, message: str, color: str = RESET):
        """Print colored log message"""
        print(f"{color}{message}{RESET}")
    
    def test_endpoint(self, 
                     method: str, 
                     path: str, 
                     expected_status: int = 200,
                     expected_keys: Optional[List[str]] = None,
                     json_data: Optional[Dict[str, Any]] = None,
                     test_name: Optional[str] = None) -> Tuple[bool, float]:
        """
        Test an endpoint and validate response
        Returns (success, elapsed_time)
        """
        if test_name is None:
            test_name = f"{method} {path}"
        
        url = f"{self.base_url}{path}"
        self.log(f"\n[TEST] {test_name}", BLUE)
        self.log(f"  URL: {url}")
        
        start_time = time.time()
        try:
            if method == "GET":
                response = requests.get(url, timeout=5)
            elif method == "POST":
                response = requests.post(url, json=json_data, timeout=5)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            elapsed = time.time() - start_time
            
            # Check status code
            if response.status_code != expected_status:
                self.log(f"  ✗ FAIL: Expected status {expected_status}, got {response.status_code}", RED)
                self.log(f"  Response: {response.text[:200]}", RED)
                self.results.append({
                    'test': test_name,
                    'status': 'FAIL',
                    'reason': f'Status {response.status_code}',
                    'time': elapsed
                })
                return False, elapsed
            
            # Check JSON response
            try:
                data = response.json()
            except Exception as e:
                self.log(f"  ✗ FAIL: Invalid JSON response: {e}", RED)
                self.results.append({
                    'test': test_name,
                    'status': 'FAIL',
                    'reason': 'Invalid JSON',
                    'time': elapsed
                })
                return False, elapsed
            
            # Check expected keys
            if expected_keys:
                missing_keys = [key for key in expected_keys if key not in data]
                if missing_keys:
                    self.log(f"  ✗ FAIL: Missing keys: {missing_keys}", RED)
                    self.log(f"  Response: {data}", RED)
                    self.results.append({
                        'test': test_name,
                        'status': 'FAIL',
                        'reason': f'Missing keys: {missing_keys}',
                        'time': elapsed
                    })
                    return False, elapsed
            
            # Success!
            self.log(f"  ✓ PASS ({elapsed:.3f}s)", GREEN)
            self.log(f"  Response: {data}")
            self.results.append({
                'test': test_name,
                'status': 'PASS',
                'time': elapsed
            })
            return True, elapsed
            
        except requests.exceptions.Timeout:
            elapsed = time.time() - start_time
            self.log(f"  ✗ FAIL: Request timeout after 5s", RED)
            self.results.append({
                'test': test_name,
                'status': 'FAIL',
                'reason': 'Timeout',
                'time': elapsed
            })
            return False, elapsed
        except Exception as e:
            elapsed = time.time() - start_time
            self.log(f"  ✗ FAIL: {str(e)}", RED)
            self.results.append({
                'test': test_name,
                'status': 'FAIL',
                'reason': str(e),
                'time': elapsed
            })
            return False, elapsed
    
    def run_all_tests(self):
        """Run all smoke tests"""
        self.log("=" * 80, BLUE)
        self.log("AutonomOS Platform Smoke Test", BLUE)
        self.log(f"Base URL: {self.base_url}", BLUE)
        self.log("=" * 80, BLUE)
        
        start_total = time.time()
        
        # TEST 1: Health Check
        self.test_endpoint(
            method="GET",
            path="/api/v1/health",
            expected_status=200,
            expected_keys=["ok", "service", "mode"],
            test_name="1. GET /api/v1/health"
        )
        
        # TEST 2: DCL Views - Opportunities
        self.test_endpoint(
            method="GET",
            path="/api/v1/dcl/views/opportunities",
            expected_status=200,
            expected_keys=["items", "page", "page_size", "total"],
            test_name="2. GET /api/v1/dcl/views/opportunities"
        )
        
        # TEST 3: DCL Views - Accounts
        self.test_endpoint(
            method="GET",
            path="/api/v1/dcl/views/accounts",
            expected_status=200,
            expected_keys=["items", "page", "page_size", "total"],
            test_name="3. GET /api/v1/dcl/views/accounts"
        )
        
        # TEST 4: RevOps Intent Execute
        self.test_endpoint(
            method="POST",
            path="/api/v1/intents/revops/execute",
            expected_status=202,  # Accepts async task
            expected_keys=["task_id", "trace_id"],
            json_data={"intent": "noop", "explain_only": True},
            test_name="4. POST /api/v1/intents/revops/execute"
        )
        
        # TEST 5: FinOps Intent Execute
        self.test_endpoint(
            method="POST",
            path="/api/v1/intents/finops/execute",
            expected_status=202,  # Accepts async task
            expected_keys=["task_id", "trace_id"],
            json_data={"intent": "noop", "dry_run": True},
            test_name="5. POST /api/v1/intents/finops/execute"
        )
        
        self.total_time = time.time() - start_total
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary"""
        self.log("\n" + "=" * 80, BLUE)
        self.log("TEST SUMMARY", BLUE)
        self.log("=" * 80, BLUE)
        
        passed = sum(1 for r in self.results if r['status'] == 'PASS')
        failed = sum(1 for r in self.results if r['status'] == 'FAIL')
        total = len(self.results)
        
        self.log(f"\nTotal Tests: {total}")
        self.log(f"Passed: {passed}", GREEN if passed == total else YELLOW)
        self.log(f"Failed: {failed}", RED if failed > 0 else GREEN)
        self.log(f"Total Time: {self.total_time:.3f}s")
        
        if failed > 0:
            self.log("\n--- FAILED TESTS ---", RED)
            for result in self.results:
                if result['status'] == 'FAIL':
                    reason = result.get('reason', 'Unknown')
                    self.log(f"  ✗ {result['test']}: {reason}", RED)
        
        self.log("\n--- DETAILED RESULTS ---", BLUE)
        for result in self.results:
            status_color = GREEN if result['status'] == 'PASS' else RED
            status_symbol = "✓" if result['status'] == 'PASS' else "✗"
            self.log(f"  {status_symbol} {result['test']} - {result['status']} ({result['time']:.3f}s)", status_color)
        
        self.log("\n" + "=" * 80, BLUE)
        if failed == 0:
            self.log("🎉 ALL TESTS PASSED!", GREEN)
        else:
            self.log(f"⚠️  {failed} TEST(S) FAILED", RED)
        self.log("=" * 80, BLUE)
        
        # Return exit code
        return 0 if failed == 0 else 1


def get_public_url():
    """Get the public URL of the Replit instance"""
    repl_slug = os.getenv("REPL_SLUG")
    repl_owner = os.getenv("REPL_OWNER")
    
    if repl_slug and repl_owner:
        # Construct Replit public URL
        return f"https://{repl_slug}.{repl_owner}.repl.co"
    
    # Fallback to localhost
    return "http://localhost:5000"


if __name__ == "__main__":
    # Determine base URL
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    else:
        base_url = "http://localhost:5000"
    
    # Get public URL for display
    public_url = get_public_url()
    
    print(f"\n{BLUE}Public Base URL: {public_url}/api/v1{RESET}")
    print(f"{YELLOW}Testing against: {base_url}{RESET}\n")
    
    # Run tests
    tester = SmokeTest(base_url)
    exit_code = tester.run_all_tests()
    
    sys.exit(exit_code)
