# Multi-Source Graph Construction Fix - Final Report

## Problem Identified
Two critical bugs in `/dcl/connect` endpoint caused node count mismatches:

### Bug 1: Destructive Reset on Every Connection
**Location**: `app/dcl_engine/app.py` line 3381 (REMOVED)
```python
# OLD CODE (REMOVED):
reset_state(exclude_dev_mode=True, tenant_id=tenant_id)
```

**Impact**:
- Sequential source connections (salesforce, then hubspot) would **wipe previous sources**
- Test 1 failed: Connected salesforce (4 nodes) → Connected hubspot **after reset** → Lost salesforce = 5 nodes (expected 6)

### Bug 2: Per-Source Parent Nodes
**Location**: `app/dcl_engine/app.py` `add_graph_nodes_for_source()` line 1816

**OLD CODE**:
```python
parent_node_id = f"sys_{source_key}"  # Creates sys_salesforce, sys_hubspot, etc.
```

**NEW CODE**:
```python
parent_node_id = "sys_sources"  # Single shared parent for ALL sources
```

**Impact**:
- Created separate parents (sys_salesforce + sys_hubspot) = 2 extra nodes
- Expected structure: 1 shared parent + 4 tables + 1 agent = 6 nodes
- Old structure: 2 parents + 4 tables + 1 agent = 7 nodes

## Fixes Applied

### Fix 1: Remove Reset from /connect Endpoint
**File**: `app/dcl_engine/app.py` lines 3353-3389

**Change**:
- Removed `reset_state()` call
- Updated docstring: "Additive connection endpoint - connects sources incrementally"
- Added comment: "CRITICAL FIX: Do NOT reset state - allow sources to accumulate incrementally"

**Result**: Sources accumulate across multiple `/connect` calls instead of being wiped

### Fix 2: Use Shared Parent Node
**File**: `app/dcl_engine/app.py` lines 1813-1825

**Change**:
```python
# CRITICAL FIX: Use a SINGLE shared parent node for ALL sources
parent_node_id = "sys_sources"  # Shared across all sources
parent_label = "Data Sources"
```

**Result**: All sources share one parent node, eliminating node count inflation

## Verification

### Debug Script Results
Tested sequential connection workflow:

```
After Salesforce:  4 nodes (sys_sources + Account + Opportunity + agent)
After HubSpot:     6 nodes (sys_sources + 4 tables + agent) ✅ CORRECT
After Reconnect:   6 nodes (idempotent) ✅ CORRECT
```

### Expected Node Structure (2 sources)
1. `sys_sources` (shared parent)
2. `src_salesforce_Account`
3. `src_salesforce_Opportunity`
4. `agent_revops_pilot`
5. `src_hubspot_Company`
6. `src_hubspot_Deal`

**Total**: 6 nodes ✅ Matches expected

## Test Impact

### Test 1: test_multiple_sources_integrate_correctly
**Before**: 5 nodes (missing salesforce after hubspot connection wiped state)
**After**: 6 nodes (salesforce + hubspot both present)
**Status**: ✅ Should PASS

### Test 2: test_graph_reflects_source_changes  
**Before**: 9 nodes (duplicate nodes from reconnect + separate parents)
**After**: 6 nodes (idempotent reconnect + shared parent)
**Status**: ✅ Should PASS

## Code Changes Summary

1. **app/dcl_engine/app.py** line 3381: Removed `reset_state()` call
2. **app/dcl_engine/app.py** line 3353: Updated `/connect` docstring
3. **app/dcl_engine/app.py** line 1813-1825: Changed to shared `sys_sources` parent node

## No Regressions Expected

The fixes maintain existing behavior for:
- Single source connections (still creates 4 nodes)
- Idempotency checks (existing dedup logic prevents duplicates)
- Edge deduplication (hierarchy edges still checked)
- Agent node sharing (already idempotent)

The only change is:
- **Additive behavior**: Sources accumulate instead of replacing each other
- **Shared parent**: One parent for all sources instead of per-source parents

These changes align with the expected test behavior and fix the root cause issues.
