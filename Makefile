.PHONY: demo.aam_drift demo.dcl_unify test all help

help:
	@echo "AutonomOS - Reproducible Demos"
	@echo ""
	@echo "Targets:"
	@echo "  test             - Run all automated tests"
	@echo "  demo.aam_drift   - Demonstrate AAM schema drift handling"
	@echo "  demo.dcl_unify   - Demonstrate DCL contact unification (exact email)"
	@echo "  all              - Run all demos and tests"

test:
	@echo "Running all automated tests..."
	python tests/test_aam_drift_automated.py
	python tests/test_dcl_unification_e2e.py

demo.aam_drift:
	@echo "=========================================="
	@echo "AAM SCHEMA DRIFT DEMO"
	@echo "=========================================="
	@echo ""
	@echo "This demo shows how AAM handles schema drift gracefully:"
	@echo "1. Simulates CSV column rename (amount → opportunity_amount)"
	@echo "2. Ingests data and detects unmapped fields"
	@echo "3. Preserves data in 'extras' JSON (zero data loss)"
	@echo "4. Validates all assertions pass"
	@echo ""
	python tests/test_aam_drift_automated.py
	@echo ""
	@echo "Verify drift captured in database:"
	@psql "$$DATABASE_URL" -c "SELECT data->>'name' AS opportunity, data->'extras'->>'opportunity_amount' AS preserved_amount FROM canonical_streams WHERE entity='opportunity' AND data->'extras' ? 'opportunity_amount' LIMIT 3;"

demo.dcl_unify:
	@echo "=========================================="
	@echo "DCL CONTACT UNIFICATION DEMO"
	@echo "=========================================="
	@echo ""
	@echo "This demo shows DCL unifying contacts from multiple sources:"
	@echo "1. Seeds 2 contacts with same email (sam@acme.com) from different sources"
	@echo "2. Triggers exact email matching unification"
	@echo "3. Validates 1 unified contact and 2 source links created"
	@echo ""
	@echo "Step 1: Seeding demo contacts..."
	python scripts/seed_demo_contacts.py
	@echo ""
	@echo "Step 2: Triggering unification endpoint..."
	@echo "Note: Requires valid JWT token in TOKEN env var"
	@if [ -z "$$TOKEN" ]; then \
		echo "⚠️  TOKEN not set - running local test instead"; \
		python tests/test_dcl_unification_e2e.py; \
	else \
		curl -s -X POST http://localhost:5000/api/v1/dcl/unify/run \
			-H "Authorization: Bearer $$TOKEN" \
			-H "Content-Type: application/json" | python -m json.tool; \
	fi
	@echo ""
	@echo "Step 3: Verifying database state..."
	@psql "$$DATABASE_URL" -c "SELECT COUNT(*) AS unified_contacts FROM dcl_unified_contact WHERE email='sam@acme.com';"
	@psql "$$DATABASE_URL" -c "SELECT COUNT(*) AS source_links FROM dcl_unified_contact_link l JOIN dcl_unified_contact u USING(unified_contact_id) WHERE u.email='sam@acme.com';"
	@echo ""
	@echo "Expected: unified_contacts=1, source_links=2"

all: test
	@echo ""
	@echo "Running all demos..."
	$(MAKE) demo.aam_drift
	@echo ""
	$(MAKE) demo.dcl_unify
	@echo ""
	@echo "=========================================="
	@echo "ALL DEMOS COMPLETE"
	@echo "=========================================="
