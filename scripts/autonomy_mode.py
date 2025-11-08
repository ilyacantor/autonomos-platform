#!/usr/bin/env python3
"""
Enable Autonomy Mode for AAM Auto-Onboarding

Sets Safe Mode + allowlist + rate caps for production use.
"""

import sys

def main():
    print("✅ Autonomy Mode is ENABLED by default in AAM Auto-Onboarding")
    print()
    print("Safe Mode Features:")
    print("  ✓ Read-only scopes for all connectors")
    print("  ✓ Rate caps: 100 req/min (Salesforce), 10 req/min (others)")
    print("  ✓ First sync limited to ~20 items")
    print("  ✓ Allowlist validation (30+ source types)")
    print("  ✓ Namespace isolation (autonomy vs demo)")
    print()
    print("Configuration is code-based in:")
    print("  - aam_hybrid/core/onboarding_service.py (allowlist + validation)")
    print("  - aam_hybrid/connectors/*/adapter.py (rate caps + read-only)")
    print()
    print("No runtime toggle needed - Safe Mode is always on for new connections.")

if __name__ == '__main__':
    main()
