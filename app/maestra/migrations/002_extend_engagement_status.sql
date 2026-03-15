-- Extend engagement_state status CHECK constraint to include Maestra lifecycle states.
-- DCL uses: active, paused, complete, archived
-- Maestra adds: draft, review, closed

ALTER TABLE engagement_state DROP CONSTRAINT IF EXISTS engagement_state_status_check;
ALTER TABLE engagement_state ADD CONSTRAINT engagement_state_status_check
    CHECK (status IN ('draft', 'active', 'paused', 'review', 'complete', 'closed', 'archived'));
