# Root Cause Analysis: Multi-Source Graph Construction Bug

## Problem
`/connect` endpoint resets state on EVERY call, preventing additive multi-source connections.

## Evidence
```python
# Line 3381 in app/dcl_engine/app.py
reset_state(exclude_dev_mode=True, tenant_id=tenant_id)
```

## Impact on Tests

### Test 1: test_multiple_sources_integrate_correctly
1. Connect salesforce → Creates 4 nodes (sys_salesforce + Account + Opportunity + agent)
2. Connect hubspot → **RESETS state first!** → Loses salesforce → Creates 3 nodes (sys_hubspot + Company + Deal)
3. **Result**: Only hubspot nodes remain = 3 nodes (missing salesforce)
4. **Expected**: Both sources = 6 nodes

### Test 2: test_graph_reflects_source_changes  
1. Connects both sources together (via fixture) → 6 nodes
2. Any subsequent reconnect → **RESETS** → Creates duplicates or missing nodes
3. **Result**: 9 nodes (duplicates from reconnect)
4. **Expected**: 6 nodes (stable)

## Solution
**Make `/connect` additive instead of destructive**:
- Remove `reset_state()` call from `/connect` endpoint
- Let sources accumulate naturally
- Existing idempotency checks in `add_graph_nodes_for_source()` prevent duplicates

## Code Changes
1. **Remove line 3381**: `reset_state(exclude_dev_mode=True, tenant_id=tenant_id)`
2. **Update docstring**: Change from "clears prior state" to "adds sources incrementally"
3. **Keep idempotency**: Existing deduplication in `add_graph_nodes_for_source()` handles this

## Expected Outcome
- ✅ Sequential connections accumulate sources (Test 1 passes)
- ✅ Reconnecting same source is idempotent (Test 2 passes)
- ✅ No regressions (other tests unaffected)
