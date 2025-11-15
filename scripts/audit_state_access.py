#!/usr/bin/env python3
"""
AST-Based State Access Audit Script

This script enforces the wrapper-only pattern for DCL state access by detecting
direct usage of tenant_state_manager or global variables outside the approved
state_access.py wrapper module.

Purpose:
    Prevent state access violations that could break tenant isolation or cause
    AttributeError crashes when TenantStateManager is unavailable.

Detection Rules:
    1. Direct tenant_state_manager attribute access (e.g., tenant_state_manager.get_*())
    2. Direct TenantStateManager imports
    3. Direct global variable access (GRAPH_STATE, SOURCES_ADDED, etc.)
    4. Classify operations as read vs write (Store context in AST)

Allowlist:
    - app/dcl_engine/state_access.py (wrapper definitions)
    - app/dcl_engine/tenant_state.py (TenantStateManager class)
    - app/dcl_engine/app.py (initialization only: state_access.initialize_state_access)

Usage:
    # Run audit (default mode - shows violations)
    python -m scripts.audit_state_access
    
    # CI mode (fails on any violation)
    python -m scripts.audit_state_access --strict
    
    # Summary mode (count only, no details)
    python -m scripts.audit_state_access --summary

Exit Codes:
    0: No violations found (clean)
    1: Violations detected

Example Output:
    VIOLATION: app/dcl_engine/some_module.py:45 - Direct tenant_state_manager access: tenant_state_manager.get_graph_state(tenant_id)
    VIOLATION: app/dcl_engine/another.py:123 - Direct global access (write): GRAPH_STATE = new_value
    
    Summary: 2 violations found
"""

import ast
import os
import sys
import argparse
from pathlib import Path
from typing import List, Dict, Tuple, Optional


# Global state variables to detect
GLOBAL_VARS = [
    "GRAPH_STATE",
    "SOURCES_ADDED",
    "ENTITY_SOURCES",
    "SOURCE_SCHEMAS",
    "SELECTED_AGENTS",
    "EVENT_LOG",
]

# Modules allowed to access state directly
ALLOWLIST_MODULES = [
    "state_access.py",  # Wrapper definitions
    "tenant_state.py",  # TenantStateManager class
]


class StateAccessViolation:
    """Represents a state access violation detected by AST analysis."""
    
    def __init__(
        self,
        file_path: str,
        line_number: int,
        violation_type: str,
        snippet: str,
        is_write: bool = False,
    ):
        self.file_path = file_path
        self.line_number = line_number
        self.violation_type = violation_type
        self.snippet = snippet
        self.is_write = is_write
    
    def __str__(self) -> str:
        operation = "write" if self.is_write else "read"
        return (
            f"VIOLATION: {self.file_path}:{self.line_number} - "
            f"{self.violation_type} ({operation}): {self.snippet}"
        )


class StateAccessAuditor(ast.NodeVisitor):
    """AST visitor that detects direct state access violations."""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.violations: List[StateAccessViolation] = []
        self.lines: List[str] = []
    
    def _should_check_global_access(self) -> bool:
        """Only check files other than state_access.py for global access."""
        return 'state_access.py' not in self.file_path
    
    def audit_file(self, source_code: str) -> List[StateAccessViolation]:
        """
        Parse and audit a Python file for state access violations.
        
        Args:
            source_code: Python source code as string
        
        Returns:
            List of detected violations
        """
        try:
            self.lines = source_code.splitlines()
            tree = ast.parse(source_code, filename=self.file_path)
            self.visit(tree)
        except SyntaxError as e:
            print(f"⚠️  Syntax error in {self.file_path}:{e.lineno} - skipping", file=sys.stderr)
        
        return self.violations
    
    def _get_snippet(self, node: ast.AST) -> str:
        """Extract source code snippet for AST node."""
        if hasattr(node, "lineno") and 1 <= node.lineno <= len(self.lines):
            return self.lines[node.lineno - 1].strip()
        return "<unknown>"
    
    def _is_write_context(self, node: ast.AST) -> bool:
        """Check if AST node is in write (Store) context."""
        if isinstance(node, ast.Name):
            return isinstance(node.ctx, ast.Store)
        elif isinstance(node, ast.Attribute):
            return isinstance(node.ctx, ast.Store)
        return False
    
    def visit_Attribute(self, node: ast.Attribute) -> None:
        """Detect attribute access on tenant_state_manager."""
        # Check if this is tenant_state_manager.some_method()
        if isinstance(node.value, ast.Name) and node.value.id == "tenant_state_manager":
            snippet = self._get_snippet(node)
            is_write = self._is_write_context(node)
            
            violation = StateAccessViolation(
                file_path=self.file_path,
                line_number=node.lineno,
                violation_type="Direct tenant_state_manager access",
                snippet=snippet,
                is_write=is_write,
            )
            self.violations.append(violation)
        
        self.generic_visit(node)
    
    def visit_Name(self, node: ast.Name) -> None:
        """Detect direct global variable access."""
        # Skip global access checks in state_access.py (it's the wrapper that uses them)
        if not self._should_check_global_access():
            self.generic_visit(node)
            return
        
        if node.id in GLOBAL_VARS:
            snippet = self._get_snippet(node)
            is_write = self._is_write_context(node)
            
            violation = StateAccessViolation(
                file_path=self.file_path,
                line_number=node.lineno,
                violation_type=f"Direct global access ({node.id})",
                snippet=snippet,
                is_write=is_write,
            )
            self.violations.append(violation)
        
        self.generic_visit(node)
    
    def visit_Import(self, node: ast.Import) -> None:
        """
        Detect direct imports of tenant_state module.
        
        Catches patterns like:
            import app.dcl_engine.tenant_state as tsm
            import app.dcl_engine.tenant_state
        """
        for alias in node.names:
            if 'tenant_state' in alias.name and 'app.dcl_engine' in alias.name:
                snippet = self._get_snippet(node)
                
                violation = StateAccessViolation(
                    file_path=self.file_path,
                    line_number=node.lineno,
                    violation_type="Direct tenant_state module import",
                    snippet=snippet,
                    is_write=False,
                )
                self.violations.append(violation)
        
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """
        Detect direct TenantStateManager and tenant_state_manager imports.
        
        Catches patterns like:
            from app.dcl_engine.tenant_state import TenantStateManager
            from app.dcl_engine import tenant_state_manager
        """
        # Check for TenantStateManager import
        if node.module == "app.dcl_engine.tenant_state":
            for alias in node.names:
                if alias.name == "TenantStateManager":
                    snippet = self._get_snippet(node)
                    
                    violation = StateAccessViolation(
                        file_path=self.file_path,
                        line_number=node.lineno,
                        violation_type="Direct TenantStateManager import",
                        snippet=snippet,
                        is_write=False,
                    )
                    self.violations.append(violation)
        
        # Check for tenant_state_manager import from app.dcl_engine
        elif node.module and 'tenant_state' in node.module:
            for alias in node.names:
                if 'tenant_state_manager' in alias.name or alias.name == 'tenant_state_manager':
                    snippet = self._get_snippet(node)
                    
                    violation = StateAccessViolation(
                        file_path=self.file_path,
                        line_number=node.lineno,
                        violation_type="Direct tenant_state_manager import",
                        snippet=snippet,
                        is_write=False,
                    )
                    self.violations.append(violation)
        
        self.generic_visit(node)


def is_allowlisted(file_path: str) -> bool:
    """
    Check if file is in allowlist and can access state directly.
    
    Args:
        file_path: Path to Python file
    
    Returns:
        True if file is allowed to access state directly
    """
    file_name = os.path.basename(file_path)
    
    # Allow wrapper and class definition modules
    if file_name in ALLOWLIST_MODULES:
        return True
    
    # app.py is NOT fully allowlisted - it will be audited with pattern-based filtering
    # See filter_app_py_violations() for allowed patterns
    
    return False


def audit_directory(
    directory: str,
    exclude_patterns: Optional[List[str]] = None,
) -> List[StateAccessViolation]:
    """
    Recursively audit all Python files in directory for state access violations.
    
    Args:
        directory: Root directory to audit
        exclude_patterns: List of patterns to exclude (e.g., __pycache__, tests)
    
    Returns:
        List of all detected violations
    """
    if exclude_patterns is None:
        exclude_patterns = ["__pycache__", "test_", "migrations"]
    
    all_violations: List[StateAccessViolation] = []
    
    # Walk directory tree
    for root, dirs, files in os.walk(directory):
        # Filter out excluded directories
        dirs[:] = [d for d in dirs if not any(pattern in d for pattern in exclude_patterns)]
        
        for file in files:
            if not file.endswith(".py"):
                continue
            
            file_path = os.path.join(root, file)
            
            # Skip allowlisted files
            if is_allowlisted(file_path):
                continue
            
            # Skip test files
            if any(pattern in file for pattern in exclude_patterns):
                continue
            
            # Read and audit file
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    source_code = f.read()
                
                auditor = StateAccessAuditor(file_path)
                violations = auditor.audit_file(source_code)
                
                if violations:
                    all_violations.extend(violations)
            
            except Exception as e:
                print(f"⚠️  Error auditing {file_path}: {e}", file=sys.stderr)
    
    return all_violations


def filter_app_py_violations(violations: List[StateAccessViolation]) -> List[StateAccessViolation]:
    """
    Filter out allowed violations in app.py (initialization only).
    
    app.py is allowed to:
    - Import TenantStateManager: from app.dcl_engine.tenant_state import TenantStateManager
    - Initialize state_access: state_access.initialize_state_access(tenant_state_manager)
    - Initialize tenant_state_manager: tenant_state_manager = TenantStateManager(...)
    
    But NOT allowed to:
    - Call tenant_state_manager methods directly (except passing to initialize)
    - Access global variables directly (should use state_access wrappers)
    
    Args:
        violations: All detected violations
    
    Returns:
        Filtered list with allowed app.py violations removed
    """
    filtered = []
    
    for v in violations:
        if "app.py" in v.file_path:
            # Allow TenantStateManager import (required for initialization)
            if "from app.dcl_engine.tenant_state import TenantStateManager" in v.snippet:
                continue
            if "import app.dcl_engine.tenant_state" in v.snippet:
                continue
            
            # Allow initialization patterns
            if "state_access.initialize_state_access" in v.snippet:
                continue
            if "tenant_state_manager = TenantStateManager" in v.snippet:
                continue
            if "TenantStateManager(" in v.snippet:
                continue
            
            # Allow global variable definitions (not usage)
            if any(f"{var} =" in v.snippet or f"{var}:" in v.snippet for var in GLOBAL_VARS):
                # This is a definition, not usage - check if it's at module level
                if v.snippet.startswith(tuple(GLOBAL_VARS)):
                    continue
        
        filtered.append(v)
    
    return filtered


def print_report(violations: List[StateAccessViolation], summary_only: bool = False) -> None:
    """
    Print audit report to stdout.
    
    Args:
        violations: List of violations to report
        summary_only: If True, only print summary count
    """
    if not summary_only and violations:
        print("\n" + "=" * 80)
        print("STATE ACCESS AUDIT REPORT")
        print("=" * 80 + "\n")
        
        for v in violations:
            print(str(v))
        
        print("\n" + "=" * 80)
    
    # Always print summary
    if violations:
        print(f"\n❌ Summary: {len(violations)} violation(s) found")
        print("\nViolations by type:")
        
        type_counts: Dict[str, int] = {}
        for v in violations:
            type_counts[v.violation_type] = type_counts.get(v.violation_type, 0) + 1
        
        for vtype, count in sorted(type_counts.items()):
            print(f"  - {vtype}: {count}")
        
        print("\n⚠️  Fix violations by using state_access wrappers:")
        print("  from app.dcl_engine import state_access")
        print("  graph = state_access.get_graph_state(tenant_id)")
        print("  state_access.set_graph_state(tenant_id, new_graph)")
    else:
        print("\n✅ No violations found - all state access uses approved wrappers")


def main() -> int:
    """
    Main entry point for audit script.
    
    Returns:
        Exit code (0 if clean, 1 if violations found)
    """
    parser = argparse.ArgumentParser(
        description="Audit DCL codebase for direct state access violations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail on any violation (exit code 1)",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Show only summary count, not details",
    )
    parser.add_argument(
        "--directory",
        default="app/dcl_engine",
        help="Directory to audit (default: app/dcl_engine)",
    )
    
    args = parser.parse_args()
    
    # Check if directory exists
    if not os.path.isdir(args.directory):
        print(f"❌ Error: Directory not found: {args.directory}", file=sys.stderr)
        return 1
    
    print(f"🔍 Auditing directory: {args.directory}")
    print("   Checking for direct tenant_state_manager and global variable access...")
    
    # Run audit
    violations = audit_directory(args.directory)
    
    # Filter app.py initialization violations
    violations = filter_app_py_violations(violations)
    
    # Print report
    print_report(violations, summary_only=args.summary)
    
    # Determine exit code
    if violations and args.strict:
        return 1
    elif violations:
        return 1  # Always fail on violations (strict mode is default behavior)
    else:
        return 0


if __name__ == "__main__":
    sys.exit(main())
