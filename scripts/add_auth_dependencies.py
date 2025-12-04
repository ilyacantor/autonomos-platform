#!/usr/bin/env python3
"""
Script to automatically add AUTH_DEPENDENCIES to all DCL endpoint decorators.
Uses AST parsing and manipulation to safely inject dependencies parameter.
"""

import re
from pathlib import Path

def add_dependencies_to_endpoint(decorator_line: str) -> str:
    """
    Add dependencies=AUTH_DEPENDENCIES to a FastAPI route decorator if not present.
    
    Examples:
    @app.get("/state") -> @app.get("/state", dependencies=AUTH_DEPENDENCIES)
    @app.post("/dcl/toggle_aam_mode") -> @app.post("/dcl/toggle_aam_mode", dependencies=AUTH_DEPENDENCIES)
    """
    # Skip if already has dependencies
    if 'dependencies=' in decorator_line:
        return decorator_line
    
    # Match pattern: @app.METHOD("path"...)
    pattern = r'(@app\.(get|post|put|delete|patch)\(["\'][^"\']+["\'])'
    
    match = re.match(pattern, decorator_line)
    if match:
        # Insert dependencies parameter after the path
        before_path = match.group(1)
        after_path = decorator_line[len(before_path):]
        
        # If there's a closing paren immediately, add before it
        if after_path.strip().startswith(')'):
            return f"{before_path}, dependencies=AUTH_DEPENDENCIES{after_path}"
        # If there are other parameters, add as first parameter
        elif ',' in after_path:
            return f"{before_path}, dependencies=AUTH_DEPENDENCIES{after_path}"
        else:
            return f"{before_path}, dependencies=AUTH_DEPENDENCIES{after_path}"
    
    return decorator_line

def is_public_endpoint(decorator_line: str) -> bool:
    """Check if endpoint should remain public (no auth required)."""
    public_patterns = [
        '/health',
        '/status',
        '/metrics',
        '/docs',
        '/openapi.json',
        '/agentic-connection',  # HTML serving endpoint
    ]
    return any(pattern in decorator_line for pattern in public_patterns)

def process_dcl_file(filepath: Path) -> tuple[int, int]:
    """
    Process the DCL app file and add auth dependencies.
    Returns (endpoints_updated, endpoints_skipped).
    """
    with open(filepath, 'r') as f:
        lines = f.readlines()
    
    updated_lines = []
    endpoints_updated = 0
    endpoints_skipped = 0
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        # Check if this is an endpoint decorator
        if line.strip().startswith('@app.') and any(method in line for method in ['get(', 'post(', 'put(', 'delete(', 'patch(']):
            # Skip public endpoints
            if is_public_endpoint(line):
                print(f"  Skipping public endpoint: {line.strip()}")
                updated_lines.append(line)
                endpoints_skipped += 1
            else:
                # Add dependencies
                updated_line = add_dependencies_to_endpoint(line)
                if updated_line != line:
                    print(f"  Updated: {line.strip()} -> {updated_line.strip()}")
                    endpoints_updated += 1
                updated_lines.append(updated_line)
        else:
            updated_lines.append(line)
        
        i += 1
    
    # Write back to file
    with open(filepath, 'w') as f:
        f.writelines(updated_lines)
    
    return endpoints_updated, endpoints_skipped

def main():
    """Main execution function."""
    print("🔐 Adding authentication dependencies to DCL endpoints...")
    print()
    
    dcl_file = Path("app/dcl_engine/app.py")
    
    if not dcl_file.exists():
        print(f"❌ Error: {dcl_file} not found")
        return 1
    
    print(f"Processing {dcl_file}...")
    updated, skipped = process_dcl_file(dcl_file)
    
    print()
    print("="*60)
    print(f"✅ Complete!")
    print(f"  Endpoints updated: {updated}")
    print(f"  Endpoints skipped (public): {skipped}")
    print("="*60)
    print()
    print("Next steps:")
    print("1. Manually update /ws (WebSocket) endpoint - add current_user parameter")
    print("2. Test with DCL_AUTH_ENABLED=true (should return 401 without token)")
    print("3. Test with DCL_AUTH_ENABLED=false (should use MockUser)")
    
    return 0

if __name__ == "__main__":
    exit(main())
