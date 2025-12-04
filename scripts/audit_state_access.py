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
    
    def __init__(self, file_path: str = "", source_code: str = ""):
        self.file_path = file_path
        self.current_file = file_path  # Track current file being audited
        self.violations: List[StateAccessViolation] = []
        self.lines: List[str] = []
        self.source = source_code  # Store source for context extraction
        self.aliases: Dict[str, str] = {}  # Maps alias names to original names (e.g., {'tsm': 'tenant_state_manager'})
    
    def _should_check_global_access(self) -> bool:
        """Only check files other than state_access.py for global access."""
        return 'state_access.py' not in self.file_path
    
    def audit_file(self, filepath: str, source_code: Optional[str] = None) -> List[StateAccessViolation]:
        """
        Parse and audit a Python file for state access violations.
        
        CRITICAL: This method resets ALL per-file state (aliases, violations, lines, source)
        to prevent bleeding between files when reusing the same auditor instance.
        
        Args:
            filepath: Path to the Python file being audited
            source_code: Optional source code string. If None, reads from filepath.
        
        Returns:
            List of detected violations for this file
        """
        # CRITICAL: Reset ALL per-file state before each file
        self.aliases.clear()  # Clear alias map from previous files
        self.violations = []  # Clear violations from previous files
        self.lines = []  # ✅ Clear old line cache to prevent stale buffer usage
        self.source = ""  # ✅ Clear old source buffer to prevent stale buffer usage
        self.file_path = filepath  # Update current file path
        self.current_file = filepath  # Track current file being audited
        
        # Read source code with error handling
        try:
            if source_code is None:
                with open(filepath, 'r', encoding='utf-8') as f:
                    self.source = f.read()
            else:
                self.source = source_code
            
            # Update lines cache AFTER successful read
            self.lines = self.source.splitlines()
            
        except (IOError, UnicodeDecodeError) as e:
            # File read failed - return empty violations
            # Do NOT use stale buffers from previous files
            print(f"⚠️  Error reading {filepath}: {e}", file=sys.stderr)
            return []
        
        # Parse AST with fresh state
        try:
            tree = ast.parse(self.source, filename=self.file_path)
            
            # Add parent tracking for multiline context detection
            self._add_parent_references(tree)
            
            # Visit AST and detect violations
            self.visit(tree)
        except SyntaxError as e:
            # Skip files with syntax errors
            print(f"⚠️  Syntax error in {self.file_path}:{e.lineno} - skipping", file=sys.stderr)
            return []
        
        return self.violations
    
    def _add_parent_references(self, tree: ast.AST) -> None:
        """
        Add parent references to all nodes in the AST.
        
        This enables walking up the tree to find enclosing statements,
        which is critical for detecting multiline initialization patterns.
        
        Args:
            tree: Root AST node
        """
        for parent in ast.walk(tree):
            for child in ast.iter_child_nodes(parent):
                child.parent = parent  # type: ignore
    
    def _get_enclosing_statement(self, node: ast.AST) -> Optional[ast.AST]:
        """
        Walk up AST to find enclosing statement (Assign, FunctionDef, etc.).
        
        This is used to detect multiline patterns where a single line doesn't
        capture the full context (e.g., multiline TenantStateManager initialization).
        
        Args:
            node: AST node to start from
        
        Returns:
            Enclosing statement node, or None if not found
        """
        if not hasattr(node, 'parent'):
            return None
        
        current = getattr(node, 'parent', None)
        while current:
            # Stop at statement-level nodes
            if isinstance(current, (ast.Assign, ast.AnnAssign, ast.FunctionDef, 
                                   ast.AsyncFunctionDef, ast.ClassDef, ast.Expr,
                                   ast.Import, ast.ImportFrom)):
                return current
            current = getattr(current, 'parent', None)
        
        return None
    
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
    
    def _get_all_ancestor_sources(self, node: ast.AST) -> List[str]:
        """
        Get source code for node and ALL ancestors up to module root.
        
        This method walks the entire ancestor tree, collecting source code
        from each level. This enables detection of patterns that span multiple
        lines or are nested deep in the AST (e.g., nested builder initialization).
        
        Args:
            node: AST node to start from
        
        Returns:
            List of source code strings (node + all ancestors)
        
        Example:
            For a node inside:
            def initialize_state():
                manager = TenantStateManager(
                    redis_client=create_client()  # <- node here
                )
            
            Returns:
                [
                    'redis_client=create_client()',  # Node
                    'manager = TenantStateManager(...)',  # Parent (Call)
                    'def initialize_state(): ...'  # Grandparent (FunctionDef)
                ]
        """
        sources = []
        
        # Get node's own source
        if self.source:  # Only if we have valid source
            node_source = ast.get_source_segment(self.source, node)
            if node_source:
                sources.append(node_source)
        
        # Walk up through ALL ancestors to module root
        current = getattr(node, 'parent', None)
        while current is not None:
            # Get source for this ancestor
            if self.source:
                ancestor_source = ast.get_source_segment(self.source, current)
                if ancestor_source:
                    sources.append(ancestor_source)
            
            # Move to parent
            current = getattr(current, 'parent', None)
        
        return sources
    
    def _is_initialization_function(self, node: ast.AST) -> bool:
        """
        Check if node is inside an initialization function.
        
        Walks up the AST to find enclosing FunctionDef and checks if the
        function name matches common initialization patterns.
        
        Args:
            node: AST node to check
        
        Returns:
            True if node is inside an initialization function
        
        Recognized patterns:
            - initialize*, init*, setup*, configure*
            - set_redis*, create_manager*, build_*
        """
        current = node
        while current:
            if isinstance(current, ast.FunctionDef):
                # Check function name patterns
                func_name = current.name.lower()
                init_patterns = [
                    'initialize', 'init', 'setup', 'configure',
                    'set_redis', 'create_manager', 'build_'
                ]
                if any(pattern in func_name for pattern in init_patterns):
                    return True
            current = getattr(current, 'parent', None)
        return False
    
    def _is_allowed_initialization_pattern(self, node: ast.AST) -> bool:
        """
        Analyze AST structure to detect legitimate initialization patterns.
        
        This method uses AST analysis (not string matching) to detect patterns like:
        - Direct call: TenantStateManager(redis_client=..., enabled=...)
        - Dict unpacking: TenantStateManager(**config)
        - Assignment: tenant_state_manager = TenantStateManager(...)
        - Function context: Inside initialize_*, setup_*, configure_* functions
        
        Args:
            node: AST node to check
        
        Returns:
            True if node is part of an allowed initialization pattern
        
        Example patterns detected:
            # Pattern 1: Direct call
            manager = TenantStateManager(redis_client=client)
            
            # Pattern 2: Dict unpacking
            config = build_config()
            manager = TenantStateManager(**config)
            
            # Pattern 3: Inside initialization function
            def initialize_tenant_state():
                manager = TenantStateManager(...)
        """
        current = node
        while current:
            # Pattern 1: Call node with TenantStateManager
            if isinstance(current, ast.Call):
                # Check if calling TenantStateManager directly
                if isinstance(current.func, ast.Name) and current.func.id == 'TenantStateManager':
                    return True
                if isinstance(current.func, ast.Attribute) and current.func.attr == 'TenantStateManager':
                    return True
            
            # Pattern 2: Assignment to tenant_state_manager
            if isinstance(current, ast.Assign):
                for target in current.targets:
                    if isinstance(target, ast.Name) and target.id == 'tenant_state_manager':
                        return True
            
            # Pattern 3: Inside initialization function (delegate to existing method)
            if isinstance(current, ast.FunctionDef):
                func_name = current.name.lower()
                init_keywords = ['initialize', 'init', 'setup', 'configure', 'create', 'build']
                if any(keyword in func_name for keyword in init_keywords):
                    return True
            
            # Move to parent
            current = getattr(current, 'parent', None)
        
        return False
    
    def _is_builder_pattern(self, node: ast.AST) -> bool:
        """
        Detect builder/factory patterns that create TenantStateManager.
        
        This method detects patterns where TenantStateManager is initialized
        using config/kwargs from builder functions.
        
        Args:
            node: AST node to check
        
        Returns:
            True if node is part of a builder pattern
        
        Recognized builder patterns:
            config = build_tenant_state_config()
            manager = TenantStateManager(**config)
            
            kwargs = get_manager_kwargs()
            manager = TenantStateManager(**kwargs)
        """
        current = node
        while current:
            # Check for function calls that return config dicts
            if isinstance(current, ast.Call):
                func_name = None
                if isinstance(current.func, ast.Name):
                    func_name = current.func.id.lower()
                elif isinstance(current.func, ast.Attribute):
                    func_name = current.func.attr.lower()
                
                # Builder function patterns
                if func_name and any(keyword in func_name for keyword in 
                    ['build', 'create', 'configure', 'get_config', 'make']):
                    return True
            
            current = getattr(current, 'parent', None)
        
        return False
    
    def _is_allowed_context(self, node: ast.AST) -> bool:
        """
        Check if usage is in allowed context (e.g., app.py initialization).
        
        COMPREHENSIVE MULTI-LEVEL CHECKING:
        - AST-based pattern analysis (preferred - detects Call/Assign nodes)
        - Builder pattern detection (detects helper functions)
        - String-based fallback (for edge cases)
        
        This solves the problem where nested initialization like:
            def initialize_tenant_state():
                config = build_tenant_state_config()
                manager = TenantStateManager(**config)  # <- Now correctly allowed
        
        Args:
            node: AST node to check
        
        Returns:
            True if usage is allowed in current context
        """
        # Only check app.py for special allowlist
        if 'app.py' not in self.current_file:
            return False
        
        # ✅ Check 1: AST-based initialization pattern analysis (preferred)
        # This detects patterns using AST structure, not string matching
        if self._is_allowed_initialization_pattern(node):
            return True
        
        # ✅ Check 2: Builder pattern detection
        # This detects helper functions that return config dicts
        if self._is_builder_pattern(node):
            return True
        
        # ✅ Check 3: Get ALL ancestor sources for string-based fallback
        all_sources = self._get_all_ancestor_sources(node)
        
        # Combine all sources for comprehensive pattern matching
        # This catches patterns at ANY level in the ancestor tree
        combined_source = '\n'.join(all_sources)
        
        # Allowed patterns in app.py (will match at ANY ancestor level)
        allowed_patterns = [
            'state_access.initialize_state_access',  # Wrapper initialization
            'TenantStateManager(',                    # Manager construction (multiline safe)
            'tenant_state_manager = TenantStateManager',  # Assignment pattern
            '**config',                               # Dict unpacking pattern
            '**kwargs',                               # Keyword unpacking pattern
            'from app.dcl_engine.tenant_state import TenantStateManager',  # Import (required for init)
            'import app.dcl_engine.tenant_state',    # Module import (rare but valid for init)
            # Initialization function contexts
            'def initialize_tenant_state',
            'def set_redis_client',
            # Global variable declarations
            'global GRAPH_STATE',
            'global SOURCES_ADDED',
            'global ENTITY_SOURCES',
            'global SOURCE_SCHEMAS',
            'global SELECTED_AGENTS',
            'global EVENT_LOG',
        ]
        
        # Check if ANY pattern matches in combined source
        for pattern in allowed_patterns:
            if pattern in combined_source:
                return True
        
        # ✅ Check 4: Module-level global variable definitions (not usage)
        # Get node's own source for this check
        node_source = ''
        if all_sources:
            node_source = all_sources[0]  # First element is node's own source
        
        for var in GLOBAL_VARS:
            # Pattern: GRAPH_STATE = ... or GRAPH_STATE: Dict = ...
            if (node_source.strip().startswith(f"{var} =") or 
                node_source.strip().startswith(f"{var}:") or
                f"{var} =" in combined_source or
                f"{var}:" in combined_source):
                return True
        
        return False
    
    def visit_Attribute(self, node: ast.Attribute) -> None:
        """Detect attribute access on tenant_state_manager (direct or aliased)."""
        if isinstance(node.value, ast.Name):
            var_name = node.value.id
            
            # Check if it's a known alias for forbidden imports
            if var_name in self.aliases:
                original = self.aliases[var_name]
                
                # Check if it's in allowed context before recording violation
                if not self._is_allowed_context(node):
                    snippet = self._get_snippet(node)
                    is_write = self._is_write_context(node)
                    
                    violation = StateAccessViolation(
                        file_path=self.file_path,
                        line_number=node.lineno,
                        violation_type=f"Aliased usage: {var_name} (alias for {original})",
                        snippet=snippet,
                        is_write=is_write,
                    )
                    self.violations.append(violation)
            
            # Also check direct usage (no alias)
            elif var_name == "tenant_state_manager":
                # Check if it's in allowed context before recording violation
                if not self._is_allowed_context(node):
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
            # Check if it's in allowed context before recording violation
            if not self._is_allowed_context(node):
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
                # Track alias for later attribute access detection
                alias_name = alias.asname if alias.asname else alias.name.split('.')[-1]
                self.aliases[alias_name] = 'tenant_state_manager'
                
                # Check if it's in allowed context before recording violation
                if not self._is_allowed_context(node):
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
            from app.dcl_engine.tenant_state import TenantStateManager as TSM
            from app.dcl_engine import tenant_state_manager as tsm
        """
        if not node.module:
            self.generic_visit(node)
            return
        
        for alias in node.names:
            # Check if importing TenantStateManager (from tenant_state module)
            if node.module == "app.dcl_engine.tenant_state" and alias.name == "TenantStateManager":
                # Track alias for later usage detection
                alias_name = alias.asname if alias.asname else alias.name
                self.aliases[alias_name] = "TenantStateManager"
                
                # Check if it's in allowed context before recording violation
                if not self._is_allowed_context(node):
                    snippet = self._get_snippet(node)
                    
                    violation = StateAccessViolation(
                        file_path=self.file_path,
                        line_number=node.lineno,
                        violation_type="Direct TenantStateManager import",
                        snippet=snippet,
                        is_write=False,
                    )
                    self.violations.append(violation)
            
            # Check if importing tenant_state_manager (from app.dcl_engine or tenant_state module)
            elif alias.name == 'tenant_state_manager':
                # Track alias for later usage detection
                alias_name = alias.asname if alias.asname else alias.name
                self.aliases[alias_name] = "tenant_state_manager"
                
                # Check if it's in allowed context before recording violation
                if not self._is_allowed_context(node):
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
    
    CRITICAL: Uses a single auditor instance with per-file state reset to prevent
    alias bleeding between files while maintaining efficiency.
    
    Args:
        directory: Root directory to audit
        exclude_patterns: List of patterns to exclude (e.g., __pycache__, tests)
    
    Returns:
        List of all detected violations
    """
    if exclude_patterns is None:
        exclude_patterns = ["__pycache__", "test_", "migrations"]
    
    all_violations: List[StateAccessViolation] = []
    
    # Create single auditor instance (will reset state per file)
    auditor = StateAccessAuditor()
    
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
            
            # Audit file (reads source internally, resets state per file)
            try:
                violations = auditor.audit_file(file_path)
                
                if violations:
                    all_violations.extend(violations)
            
            except Exception as e:
                print(f"⚠️  Error auditing {file_path}: {e}", file=sys.stderr)
    
    return all_violations


def filter_app_py_violations(violations: List[StateAccessViolation]) -> List[StateAccessViolation]:
    """
    Legacy filter function - now mostly handled by _is_allowed_context() in visitor.
    
    This function is kept for backward compatibility but does minimal filtering
    since the allowlist logic has been moved upstream into the AST visitor.
    
    Args:
        violations: All detected violations
    
    Returns:
        Violations (no filtering needed since visitor handles allowlist)
    """
    # Allowlist logic now handled in StateAccessAuditor._is_allowed_context()
    # This function is now a no-op but kept for backward compatibility
    return violations


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
