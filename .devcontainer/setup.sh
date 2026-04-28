#!/usr/bin/env bash
# Runs once, when the Codespace is first created.
# Installs OS-level OCR + PDF tools and the Python package.
set -e

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "==> Installing system packages (tesseract + heb + poppler)..."
sudo apt-get update -qq
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
  tesseract-ocr tesseract-ocr-heb tesseract-ocr-eng poppler-utils

echo "==> Installing fraud-detection Python package..."
cd "$HERE/fraud-detection"
pip install --upgrade pip --quiet
pip install -e . --quiet
pip install pytesseract pdf2image --quiet

echo ""
echo "✓ Setup complete."
echo "  The API server will start automatically on every container attach."
echo "  Look for the URL under the PORTS tab (port 8000)."
