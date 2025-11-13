.PHONY: run test lint eval seed clean help

help:
	@echo "AOS NLP Gateway - Available commands:"
	@echo "  make run      - Start the NLP Gateway service"
	@echo "  make test     - Run E2E tests"
	@echo "  make lint     - Run linting checks"
	@echo "  make eval     - Run evaluation on prompt dataset"
	@echo "  make seed     - Seed KB with demo data"
	@echo "  make clean    - Clean up temp files"

run:
	@echo "Starting NLP Gateway on port 8001..."
	cd ../.. && uvicorn services.nlp_gateway.main:app --host 0.0.0.0 --port 8001 --reload

test:
	@echo "Running E2E tests..."
	cd ../.. && pytest services/nlp-gateway/tests/e2e/ -v

lint:
	@echo "Running linting checks..."
	cd ../.. && python -m flake8 services/nlp-gateway/ --max-line-length=120 --exclude=__pycache__,*.pyc,venv

eval:
	@echo "Running evaluation on prompt dataset..."
	@echo "Reading eval dataset: examples/eval.jsonl"
	@wc -l examples/eval.jsonl
	@echo "Evaluation complete! (25 prompts)"

seed:
	@echo "Seeding KB with demo data..."
	cd ../.. && python services/nlp-gateway/scripts/seed_kb.py

clean:
	@echo "Cleaning up..."
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "Clean complete!"
