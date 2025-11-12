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

.PHONY: ingest-filesource
ingest-filesource:
	@python scripts/filesource_ingest.py --connection-id 10ca3a88-5105-4e24-b984-6e350a5fa443 --namespace demo

.PHONY: drift-filesource
drift-filesource:
	@python scripts/filesource_drift_sim.py --connection-id 10ca3a88-5105-4e24-b984-6e350a5fa443 --namespace demo

.PHONY: verify-filesource
verify-filesource:
	@python -c "import os; from sqlalchemy import create_engine, text; db = os.getenv('DATABASE_URL'); engine = create_engine(db) if db else exit(1); conn = engine.connect(); result = conn.execute(text(\"SELECT COUNT(*) FROM mapping_registry WHERE connection_id='10ca3a88-5105-4e24-b984-6e350a5fa443'\")).scalar(); print(f'📊 FilesSource mapping_count: {result}'); exit(0 if result > 0 else 1)"

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
	@echo ""
	@echo "FilesSource Data Targets:"
	@echo "  make ingest-filesource  - Ingest FilesSource CSV data to mapping_registry"
	@echo "  make drift-filesource   - Simulate schema drift (add column + event)"
	@echo "  make verify-filesource  - Verify FilesSource mapping_count from DB"
