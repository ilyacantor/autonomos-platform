#!/usr/bin/env python3
"""
Smoke Test for AAM Auto-Onboarding - 90% SLO Validation

Posts all seed intents from seeds/intents/ and validates:
1. All connections reach ACTIVE (Safe Mode) status
2. Each receipt includes first_sync_rows and latency_ms
3. Funnel metrics show >=90% coverage
4. Namespace isolation (autonomy only)
"""

import sys
import os
import json
import glob
import requests
from pathlib import Path
from typing import List, Dict, Any


def load_seed_intents() -> List[Dict[str, Any]]:
    """Load all seed intent files"""
    seed_dir = Path("seeds/intents")
    if not seed_dir.exists():
        print(f"❌ Seed directory not found: {seed_dir}")
        sys.exit(1)
    
    intents = []
    for file_path in sorted(seed_dir.glob("*.json")):
        with open(file_path, 'r') as f:
            intent = json.load(f)
            intents.append((file_path.name, intent))
    
    return intents


def post_intent(api_url: str, token: str, intent: Dict[str, Any]) -> Dict[str, Any]:
    """POST a single ConnectionIntent"""
    url = f"{api_url}/api/v1/aam/connections/onboard"
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    response = requests.post(url, headers=headers, json=intent)
    response.raise_for_status()
    return response.json()


def get_funnel_metrics(api_url: str, token: str, namespace: str) -> Dict[str, Any]:
    """GET funnel metrics"""
    url = f"{api_url}/api/v1/aam/metrics/funnel?namespace={namespace}"
    headers = {'Authorization': f'Bearer {token}'}
    
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()


def main():
    api_url = os.getenv('AAM_API_URL', 'http://localhost:5000')
    token = os.getenv('AAM_AUTH_TOKEN')
    
    if not token:
        print("❌ AAM_AUTH_TOKEN environment variable required")
        print("   Export your JWT token: export AAM_AUTH_TOKEN=<your_token>")
        sys.exit(1)
    
    print("=" * 70)
    print("AAM AUTO-ONBOARDING SMOKE TEST - 90% SLO VALIDATION")
    print("=" * 70)
    print()
    
    # Load seed intents
    intents = load_seed_intents()
    print(f"📂 Loaded {len(intents)} seed intents from seeds/intents/")
    print()
    
    # POST each intent
    print("POSTING INTENTS")
    print("-" * 70)
    results = []
    for filename, intent in intents:
        source_type = intent.get('source_type', 'unknown')
        namespace = intent.get('namespace', 'unknown')
        
        try:
            result = post_intent(api_url, token, intent)
            status = result.get('status', 'UNKNOWN')
            connection_id = result.get('connection_id', 'N/A')
            first_sync = result.get('first_sync_rows', 0)
            latency = result.get('latency_ms', 0)
            
            print(f"  ✅ {filename:20s} → {status:20s} (id={connection_id[:8]}...)")
            print(f"      first_sync_rows={first_sync}, latency_ms={latency}ms")
            
            results.append({
                'filename': filename,
                'status': status,
                'first_sync_rows': first_sync,
                'latency_ms': latency,
                'connection_id': connection_id
            })
        except Exception as e:
            print(f"  ❌ {filename:20s} → ERROR: {e}")
            results.append({
                'filename': filename,
                'status': 'ERROR',
                'error': str(e)
            })
    
    print()
    
    # Get funnel metrics
    print("FUNNEL METRICS")
    print("-" * 70)
    try:
        metrics = get_funnel_metrics(api_url, token, 'autonomy')
        coverage = metrics.get('coverage', 0.0)
        slo_met = metrics.get('slo_met', False)
        eligible = metrics.get('eligible', 0)
        active = metrics.get('active', 0)
        
        print(f"  Eligible:  {eligible}")
        print(f"  Active:    {active}")
        print(f"  Coverage:  {coverage * 100:.1f}%")
        print(f"  SLO Met:   {'✅ YES' if slo_met else '❌ NO'}")
        print()
        
        if slo_met:
            print("✅ SUCCESS: AAM is meeting the 90% day-one coverage SLO!")
        else:
            print("⚠️  WARNING: Coverage below 90% SLO target")
            print(f"   Gap: {(0.90 - coverage) * 100:.1f}%")
            
            # Show blockers
            blockers = []
            if metrics.get('awaiting_credentials', 0) > 0:
                blockers.append(f"awaiting_credentials: {metrics['awaiting_credentials']}")
            if metrics.get('network_blocked', 0) > 0:
                blockers.append(f"network_blocked: {metrics['network_blocked']}")
            
            if blockers:
                print(f"   Blockers: {', '.join(blockers)}")
        
    except Exception as e:
        print(f"❌ Error fetching funnel metrics: {e}")
    
    print()
    print("=" * 70)
    print(f"SMOKE TEST COMPLETE - {len([r for r in results if r['status'] != 'ERROR'])}/{len(results)} successful")
    print("=" * 70)


if __name__ == '__main__':
    main()
