# AutonomOS Deployment Targets

.PHONY: deploy-check
deploy-check:
        @./scripts/deploy_guard.sh

.PHONY: db-audit
db-audit:
        @./scripts/db_audit.sh

.PHONY: stamp-prod
stamp-prod:
        @./scripts/stamp_prod_baseline.sh

.PHONY: autonomy-mode
autonomy-mode:
        @echo "🔒 Setting AAM to Autonomy Mode (Safe Mode + allowlist + caps)"
        @python scripts/autonomy_mode.py

.PHONY: smoke-90
smoke-90:
        @echo "🚀 Running smoke test with 5 seed intents..."
        @python scripts/smoke_90.py

.PHONY: heal
heal:
        @echo "🏥 Promoting HEALING connections to ACTIVE..."
        @python scripts/heal_connections.py

.PHONY: help
help:
        @echo "AutonomOS Deployment Targets:"
        @echo "  make deploy-check    - Run pre-publish safety checks"
        @echo "  make db-audit        - Audit dev/prod database schemas"
        @echo "  make stamp-prod      - One-time production baseline stamp"
        @echo ""
        @echo "AAM Auto-Onboarding Targets:"
        @echo "  make autonomy-mode   - Enable Safe Mode + allowlist + rate caps"
        @echo "  make smoke-90        - POST 5 seed intents and verify 90% SLO"
        @echo "  make heal            - Promote HEALING connections to ACTIVE"
