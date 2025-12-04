#!/usr/bin/env python3
"""
Feature Flag Management CLI

This script provides command-line interface for managing Redis-backed feature flags.
Supports tenant-scoped flags and percentage-based rollouts.

Usage:
    # Get flag value
    python scripts/manage_feature_flags.py get USE_DCL_MAPPING_REGISTRY
    
    # Set flag to true
    python scripts/manage_feature_flags.py set USE_DCL_MAPPING_REGISTRY --value true
    
    # Set flag to false
    python scripts/manage_feature_flags.py set USE_DCL_MAPPING_REGISTRY --value false
    
    # Set percentage rollout
    python scripts/manage_feature_flags.py set-percentage USE_DCL_MAPPING_REGISTRY --percentage 50
    
    # Tenant-specific flags
    python scripts/manage_feature_flags.py set USE_DCL_MAPPING_REGISTRY --value true --tenant acme-corp
    
    # List all flags for a tenant
    python scripts/manage_feature_flags.py list --tenant default
    
    # Clear a flag
    python scripts/manage_feature_flags.py clear USE_DCL_MAPPING_REGISTRY --tenant default
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.feature_flags import (
    set_feature_flag,
    get_feature_flag,
    set_feature_flag_percentage,
    get_feature_flag_percentage,
    clear_feature_flag,
    list_all_flags,
    is_feature_enabled_for_user
)
from shared.redis_client import is_redis_available


def main():
    parser = argparse.ArgumentParser(
        description="Manage AutonomOS feature flags",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        'action',
        choices=['get', 'set', 'set-percentage', 'clear', 'list', 'test-user'],
        help='Action to perform'
    )
    
    parser.add_argument(
        'flag_name',
        nargs='?',
        help='Feature flag name (required for get, set, set-percentage, clear, test-user)'
    )
    
    parser.add_argument(
        '--value',
        type=str,
        help='Value for set action (true/false)'
    )
    
    parser.add_argument(
        '--percentage',
        type=int,
        help='Percentage for set-percentage action (0-100)'
    )
    
    parser.add_argument(
        '--tenant',
        default='default',
        help='Tenant ID (default: "default")'
    )
    
    parser.add_argument(
        '--user-id',
        help='User ID for test-user action'
    )
    
    args = parser.parse_args()
    
    if not is_redis_available():
        print("❌ ERROR: Redis is not available. Feature flags require Redis.")
        print("   Please ensure Redis is running and REDIS_URL is configured.")
        sys.exit(1)
    
    if args.action in ['get', 'set', 'set-percentage', 'clear', 'test-user']:
        if not args.flag_name:
            parser.error(f"flag_name is required for '{args.action}' action")
    
    try:
        if args.action == 'get':
            enabled = get_feature_flag(args.flag_name, args.tenant)
            percentage = get_feature_flag_percentage(args.flag_name, args.tenant)
            
            print(f"Feature Flag: {args.flag_name}")
            print(f"Tenant: {args.tenant}")
            print(f"Enabled: {enabled}")
            if percentage is not None:
                print(f"Percentage Rollout: {percentage}%")
            else:
                print("Percentage Rollout: Not set (using boolean flag)")
        
        elif args.action == 'set':
            if args.value is None:
                parser.error("--value is required for 'set' action")
            
            value = args.value.lower() in ['true', '1', 'yes', 'on']
            success = set_feature_flag(args.flag_name, value, args.tenant)
            
            if success:
                print(f"✅ Set {args.flag_name} = {value} (tenant: {args.tenant})")
            else:
                print(f"❌ Failed to set {args.flag_name}")
                sys.exit(1)
        
        elif args.action == 'set-percentage':
            if args.percentage is None:
                parser.error("--percentage is required for 'set-percentage' action")
            
            if not 0 <= args.percentage <= 100:
                parser.error("--percentage must be between 0 and 100")
            
            success = set_feature_flag_percentage(args.flag_name, args.percentage, args.tenant)
            
            if success:
                print(f"✅ Set {args.flag_name} percentage = {args.percentage}% (tenant: {args.tenant})")
                print(f"   ~{args.percentage}% of users will have this feature enabled")
            else:
                print(f"❌ Failed to set percentage for {args.flag_name}")
                sys.exit(1)
        
        elif args.action == 'clear':
            success = clear_feature_flag(args.flag_name, args.tenant)
            
            if success:
                print(f"✅ Cleared {args.flag_name} (tenant: {args.tenant})")
            else:
                print(f"❌ Failed to clear {args.flag_name}")
                sys.exit(1)
        
        elif args.action == 'list':
            flags = list_all_flags(args.tenant)
            
            if not flags:
                print(f"No feature flags found for tenant: {args.tenant}")
            else:
                print(f"Feature Flags for tenant '{args.tenant}':")
                print("=" * 60)
                for flag_name, enabled in sorted(flags.items()):
                    status = "✅ ENABLED" if enabled else "❌ DISABLED"
                    percentage = get_feature_flag_percentage(flag_name, args.tenant)
                    if percentage is not None:
                        print(f"{flag_name:40s} {status} ({percentage}% rollout)")
                    else:
                        print(f"{flag_name:40s} {status}")
        
        elif args.action == 'test-user':
            if args.user_id is None:
                parser.error("--user-id is required for 'test-user' action")
            
            enabled = is_feature_enabled_for_user(args.flag_name, args.user_id, args.tenant)
            percentage = get_feature_flag_percentage(args.flag_name, args.tenant)
            
            print(f"Feature Flag: {args.flag_name}")
            print(f"Tenant: {args.tenant}")
            print(f"User ID: {args.user_id}")
            if percentage is not None:
                print(f"Percentage Rollout: {percentage}%")
            print(f"Enabled for this user: {enabled}")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
