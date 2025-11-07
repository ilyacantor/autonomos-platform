# Development convenience targets

.PHONY: deploy-check
deploy-check:
\t@./scripts/deploy_guard.sh

.PHONY: db-audit
db-audit:
\t@./scripts/db_audit.sh

.PHONY: stamp-prod
stamp-prod:
\t@./scripts/stamp_prod_baseline.sh

.PHONY: help
help:
\t@echo "AutonomOS Deployment Targets:"
\t@echo "  make deploy-check    - Run pre-publish safety checks"
\t@echo "  make db-audit        - Audit dev/prod database schemas"
\t@echo "  make stamp-prod      - One-time production baseline stamp"

