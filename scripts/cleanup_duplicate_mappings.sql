-- ============================================================================
-- Cleanup Script: Remove Capitalized Duplicate Mappings
-- ============================================================================
-- Problem: Migration script ran with inconsistent casing, creating duplicates
-- Solution: Keep lowercase entries (complete YAML data), delete capitalized
-- 
-- Architect Approved: November 18, 2025
-- ============================================================================

BEGIN;

-- Show current state before cleanup
SELECT 'BEFORE CLEANUP:' as status;
SELECT source_table, canonical_entity, COUNT(*) as field_count 
FROM field_mappings 
GROUP BY source_table, canonical_entity 
ORDER BY canonical_entity, field_count DESC;

-- Delete capitalized duplicates (partial data)
-- Keep lowercase entries which contain complete YAML mappings
DELETE FROM field_mappings 
WHERE source_table IN (
    'Opportunity',  -- 66 fields (partial) - DELETE
    'Contact',      -- 41 fields (partial) - DELETE
    'Account',      -- 53 fields (partial) - DELETE
    'Aws_resources', -- 26 fields (partial) - DELETE
    'Cost_reports'   -- 7 fields (partial) - DELETE
);

-- Show results after cleanup
SELECT 'AFTER CLEANUP:' as status;
SELECT source_table, canonical_entity, COUNT(*) as field_count 
FROM field_mappings 
GROUP BY source_table, canonical_entity 
ORDER BY canonical_entity, field_count DESC;

-- Verify all source_table values are now lowercase
SELECT 'CASING VERIFICATION:' as status;
SELECT source_table, 
       CASE 
           WHEN source_table = LOWER(source_table) THEN 'lowercase ✓'
           ELSE 'MIXED CASE ✗'
       END as casing_check,
       COUNT(*) as count
FROM field_mappings
GROUP BY source_table, casing_check
ORDER BY source_table;

COMMIT;

-- ============================================================================
-- Expected Results:
-- - Opportunity, Contact, Account, Aws_resources, Cost_reports DELETED
-- - Only lowercase entries remain (opportunity, contact, account, aws_resources, cost_reports)
-- - Field counts: opportunity=204, contact=165, account=159, aws_resources=78, cost_reports=21
-- ============================================================================
