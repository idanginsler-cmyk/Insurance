.PHONY: install install-optional test demo demo-typography run-api run-api-public info clean tunnel my-ip

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

demo-typography:
	PYTHONPATH=src python scripts/demo_typography.py

# Local-only (127.0.0.1). Open in the desktop browser at http://localhost:8000/
run-api:
	PYTHONPATH=src uvicorn fraud_detection.api.server:app --reload --port 8000

# LAN-accessible. Run this, then open http://<your-laptop-ip>:8000/ on your phone.
# Use `make my-ip` to print the IP.
run-api-public:
	PYTHONPATH=src uvicorn fraud_detection.api.server:app --host 0.0.0.0 --port 8000

my-ip:
	@hostname -I 2>/dev/null | awk '{print "LAN IP: " $$1; print "Phone URL: http://" $$1 ":8000/"}' \
		|| ipconfig getifaddr en0 2>/dev/null \
		|| echo "Could not detect IP — run 'ifconfig' or 'ip addr' manually."

# Public tunnel via cloudflared (no signup, no install of ngrok needed).
# Requires: brew install cloudflared  /  apt install cloudflared
tunnel:
	cloudflared tunnel --url http://localhost:8000

info:
	PYTHONPATH=src python -m fraud_detection.cli info

clean:
	rm -rf data/store/*.db data/samples build dist *.egg-info src/*.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
