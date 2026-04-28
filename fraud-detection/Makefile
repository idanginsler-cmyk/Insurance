.PHONY: install install-optional test demo run-api info clean

install:
	pip install -e .

install-optional:
	pip install -r requirements-optional.txt

test:
	PYTHONPATH=src pytest -q

# Generate synthetic receipts and ingest them into a fresh DB.
demo:
	rm -f data/store/fraud_detection.db
	PYTHONPATH=src python scripts/generate_synthetic.py data/samples/claim_001
	PYTHONPATH=src python -m fraud_detection.cli ingest \
		data/samples/claim_001/receipt_genuine.png \
		data/samples/claim_001/receipt_resubmitted.png \
		data/samples/claim_001/receipt_amount_forged.png \
		data/samples/claim_001/receipt_unrelated.png \
		--claim claim_001
	@echo ""
	@echo "=== analyzing receipt_resubmitted as a fresh upload ==="
	PYTHONPATH=src python -m fraud_detection.cli analyze \
		data/samples/claim_001/receipt_resubmitted.png --claim claim_001

run-api:
	PYTHONPATH=src uvicorn fraud_detection.api.server:app --reload --port 8000

info:
	PYTHONPATH=src python -m fraud_detection.cli info

clean:
	rm -rf data/store/*.db data/samples build dist *.egg-info src/*.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
