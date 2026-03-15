-- Maestra human review table for 4-tier HITL workflow.
-- Separate from DCL's resolution_workspaces (different purpose).

CREATE TABLE IF NOT EXISTS human_reviews (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id                   UUID NOT NULL,
    engagement_id               TEXT NOT NULL,
    action                      TEXT NOT NULL,
    context                     JSONB NOT NULL DEFAULT '{}',
    tier                        INT NOT NULL DEFAULT 3,
    status                      TEXT NOT NULL DEFAULT 'pending',
    requested_by                TEXT NOT NULL DEFAULT 'maestra',
    approved_by                 TEXT,
    rejected_by                 TEXT,
    rejection_reason            TEXT,
    resolved_at                 TIMESTAMPTZ,
    created_at                  TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_reviews_tenant ON human_reviews (tenant_id, status);
CREATE INDEX IF NOT EXISTS idx_reviews_engagement ON human_reviews (engagement_id);
