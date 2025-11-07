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

.PHONY: help
help:
	@echo "AutonomOS Deployment Targets:"
	@echo "  make deploy-check    - Run pre-publish safety checks"
	@echo "  make db-audit        - Audit dev/prod database schemas"
	@echo "  make stamp-prod      - One-time production baseline stamp"
