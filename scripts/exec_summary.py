#!/usr/bin/env python3
"""
Executive Summary Script for AAM Auto-Onboarding Funnel Metrics

Reads funnel metrics from GET /api/v1/aam/metrics/funnel and prints an
English summary for executive stakeholders.

Usage:
    python scripts/exec_summary.py [--namespace autonomy|demo] [--api-url http://localhost:5000]
"""

import sys
import os
import argparse
import requests
from typing import Dict, Any


def format_percentage(value: float) -> str:
    """Format percentage with color coding"""
    pct = value * 100
    if pct >= 90:
        return f"✅ {pct:.1f}%"
    elif pct >= 75:
        return f"⚠️  {pct:.1f}%"
    else:
        return f"🚨 {pct:.1f}%"


def get_funnel_metrics(api_url: str, namespace: str, token: str = None) -> Dict[str, Any]:
    """
    Fetch funnel metrics from AAM API
    
    Args:
        api_url: Base API URL
        namespace: Namespace filter (autonomy or demo)
        token: Optional auth token
        
    Returns:
        Funnel metrics dict
    """
    url = f"{api_url}/api/v1/aam/metrics/funnel?namespace={namespace}"
    headers = {}
    
    if token:
        headers['Authorization'] = f'Bearer {token}'
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching metrics: {e}")
        sys.exit(1)


def print_executive_summary(metrics: Dict[str, Any]) -> None:
    """
    Print executive summary of funnel metrics
    
    Args:
        metrics: Funnel metrics dict
    """
    namespace = metrics.get('namespace', 'unknown')
    coverage = metrics.get('coverage', 0.0)
    slo_met = metrics.get('slo_met', False)
    target = metrics.get('target', 0.90)
    
    eligible = metrics.get('eligible', 0)
    reachable = metrics.get('reachable', 0)
    active = metrics.get('active', 0)
    
    awaiting_credentials = metrics.get('awaiting_credentials', 0)
    network_blocked = metrics.get('network_blocked', 0)
    unsupported_type = metrics.get('unsupported_type', 0)
    healing = metrics.get('healing', 0)
    error = metrics.get('error', 0)
    
    print("=" * 70)
    print("AAM AUTO-ONBOARDING EXECUTIVE SUMMARY")
    print("=" * 70)
    print()
    
    print(f"📊 Namespace: {namespace.upper()}")
    print(f"🎯 SLO Target: {target * 100:.0f}% day-one coverage")
    print()
    
    print("FUNNEL PROGRESSION")
    print("-" * 70)
    print(f"  Eligible:  {eligible:4d}  (Discovered connections)")
    print(f"  Reachable: {reachable:4d}  (Passed health check)")
    print(f"  Active:    {active:4d}  (Successfully onboarded)")
    print()
    
    print("CURRENT PERFORMANCE")
    print("-" * 70)
    print(f"  Coverage:  {format_percentage(coverage)}")
    print(f"  SLO Met:   {'✅ YES' if slo_met else '❌ NO'}")
    print()
    
    if eligible == 0:
        print("📝 STATUS: No connections discovered yet. Waiting for AOD intents.")
        print("=" * 70)
        return
    
    if slo_met:
        print("✅ SUCCESS: AAM is meeting the 90% day-one coverage SLO.")
        print()
        print(f"   Out of {eligible} discovered connections, {active} ({coverage * 100:.1f}%) are")
        print("   successfully onboarded and actively syncing data in Safe Mode.")
    else:
        print("⚠️  ATTENTION: AAM is NOT meeting the 90% SLO target.")
        print()
        print(f"   Coverage gap: {(target - coverage) * 100:.1f}% below target")
        print(f"   Missing: {int(eligible * target) - active} connections need resolution")
        print()
        
        blockers = []
        if awaiting_credentials > 0:
            blockers.append(f"   • {awaiting_credentials} awaiting credentials")
        if network_blocked > 0:
            blockers.append(f"   • {network_blocked} network/firewall blocked")
        if unsupported_type > 0:
            blockers.append(f"   • {unsupported_type} unsupported source types")
        if healing > 0:
            blockers.append(f"   • {healing} in healing mode (drift/permissions)")
        if error > 0:
            blockers.append(f"   • {error} errors during onboarding")
        
        if blockers:
            print("   TOP BLOCKERS:")
            for blocker in blockers:
                print(blocker)
    
    print()
    print("=" * 70)
    
    if not slo_met and eligible > 0:
        print()
        print("📋 RECOMMENDED ACTIONS:")
        if awaiting_credentials > 0:
            print(f"   1. Provision credentials for {awaiting_credentials} connections")
        if network_blocked > 0:
            print(f"   2. Review firewall rules for {network_blocked} blocked connections")
        if unsupported_type > 0:
            print(f"   3. Evaluate {unsupported_type} unsupported source types for allowlist")
        if healing > 0:
            print(f"   4. Investigate {healing} connections in healing mode")
        if error > 0:
            print(f"   5. Review error logs for {error} failed onboardings")
        print()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Print executive summary of AAM auto-onboarding funnel metrics'
    )
    parser.add_argument(
        '--namespace',
        default='autonomy',
        choices=['autonomy', 'demo'],
        help='Namespace filter (default: autonomy)'
    )
    parser.add_argument(
        '--api-url',
        default='http://localhost:5000',
        help='Base API URL (default: http://localhost:5000)'
    )
    parser.add_argument(
        '--token',
        default=None,
        help='Optional auth token (can also use AAM_AUTH_TOKEN env var)'
    )
    
    args = parser.parse_args()
    
    token = args.token or os.getenv('AAM_AUTH_TOKEN')
    
    metrics = get_funnel_metrics(args.api_url, args.namespace, token)
    print_executive_summary(metrics)


if __name__ == '__main__':
    main()
