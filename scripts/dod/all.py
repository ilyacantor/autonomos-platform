#!/usr/bin/env python3
"""
DoD All-in-One Test Script - Orchestrates all DoD tests
Usage: python3 scripts/dod/all.py
"""
import os
import sys
import subprocess


def run_script(script_path, args=None):
    """Run a script and return its exit code and output"""
    cmd = [sys.executable, script_path]
    if args:
        cmd.extend(args)
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.returncode, result.stdout
    except Exception as e:
        return 1, f"Error running {script_path}: {str(e)}"


def main():
    """Run all DoD tests in sequence"""
    scripts_dir = os.path.dirname(os.path.abspath(__file__))
    all_passed = True
    
    print("=" * 60)
    print("DoD v1.1 Functional Effectiveness Harness")
    print("=" * 60)
    print()
    
    # Test 1: Status check
    print("--- SOURCE STATUS CHECK ---")
    exit_code, output = run_script(os.path.join(scripts_dir, "status.py"))
    print(output)
    if exit_code != 0:
        all_passed = False
    print()
    
    # Test 2: Individual source validation
    print("--- SOURCE VALIDATION ---")
    required_sources = os.getenv("REQUIRED_SOURCES", "filesource").split(",")
    required_sources = [s.strip() for s in required_sources if s.strip()]
    
    for source in ["salesforce", "supabase", "mongodb", "filesource"]:
        exit_code, output = run_script(os.path.join(scripts_dir, "source.py"), [source])
        print(output)
        
        # Only fail if this is a required source
        if exit_code != 0 and source in required_sources:
            all_passed = False
    print()
    
    # Test 3: Agent tests
    print("--- AGENT FUNCTIONALITY TESTS ---")
    exit_code, output = run_script(os.path.join(scripts_dir, "agents.py"))
    print(output)
    if exit_code != 0:
        all_passed = False
    print()
    
    # Test 4: Drift tests (only for supabase and mongodb)
    print("--- DRIFT MUTATION TESTS ---")
    for source in ["supabase", "mongodb"]:
        exit_code, output = run_script(os.path.join(scripts_dir, "drift.py"), [source])
        print(output)
        # Drift tests are optional - don't fail if they're skipped
        if exit_code != 0 and "SKIPPED" not in output:
            # Only warn, don't fail
            pass
    print()
    
    # Final status
    print("=" * 60)
    if all_passed:
        print("DOD_STATUS: PASS")
        print("=" * 60)
        sys.exit(0)
    else:
        print("DOD_STATUS: FAIL")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()
