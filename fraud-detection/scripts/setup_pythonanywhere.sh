#!/usr/bin/env bash
# One-shot setup script for PythonAnywhere.
#
# Run this once from a Bash console after cloning the repo:
#
#   git clone https://github.com/idanginsler-cmyk/Insurance.git ~/Insurance
#   cd ~/Insurance/fraud-detection
#   bash scripts/setup_pythonanywhere.sh
#
# What it does:
#   1. pip-installs the package (--user, no virtualenv on the free tier).
#   2. Downloads the Hebrew Tesseract language data into ~/tessdata.
#   3. Prints the snippet you need to paste into your PythonAnywhere
#      WSGI configuration file.

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

PYBIN="$(command -v python3.11 || command -v python3.10 || command -v python3)"
PIPBIN="$(command -v pip3.11 || command -v pip3.10 || command -v pip3 || command -v pip)"

echo "==> Using Python: $($PYBIN --version)"
echo "==> Project dir:  $PROJECT_DIR"

# 1. Install the package + extras.
echo "==> Installing Python dependencies (--user)..."
"$PIPBIN" install --user --upgrade pip --quiet
"$PIPBIN" install --user --upgrade -e . pytesseract --quiet

# 2. Download the Hebrew Tesseract training file (~10 MB).
TESSDATA_DIR="$HOME/tessdata"
mkdir -p "$TESSDATA_DIR"
HEB_URL="https://github.com/tesseract-ocr/tessdata/raw/main/heb.traineddata"
ENG_URL="https://github.com/tesseract-ocr/tessdata/raw/main/eng.traineddata"

if [ ! -f "$TESSDATA_DIR/heb.traineddata" ]; then
  echo "==> Downloading Hebrew Tesseract data..."
  curl -fsSL "$HEB_URL" -o "$TESSDATA_DIR/heb.traineddata"
fi
if [ ! -f "$TESSDATA_DIR/eng.traineddata" ]; then
  echo "==> Downloading English Tesseract data..."
  curl -fsSL "$ENG_URL" -o "$TESSDATA_DIR/eng.traineddata"
fi

echo "==> Tesseract languages ready in $TESSDATA_DIR"

# 3. Quick sanity check.
echo "==> Verifying tesseract binary and languages..."
TESSDATA_PREFIX="$TESSDATA_DIR" tesseract --list-langs 2>&1 | head -10 || true

# 4. Print the WSGI snippet.
USERNAME="${USER:-yourusername}"
WSGI_FILE="/var/www/${USERNAME}_pythonanywhere_com_wsgi.py"

cat <<EOF

============================================================
 ✓ Setup complete.

 Next step — open the Web tab in PythonAnywhere and paste
 the following into the WSGI configuration file:

   $WSGI_FILE

 ────────────── PASTE EVERYTHING BELOW THIS LINE ──────────────
import sys, os
PROJECT = '$PROJECT_DIR'
if PROJECT not in sys.path:
    sys.path.insert(0, PROJECT)
os.environ.setdefault('TESSDATA_PREFIX', '$TESSDATA_DIR')

from wsgi import application
 ────────────── PASTE EVERYTHING ABOVE THIS LINE ──────────────

 Then click "Reload <username>.pythonanywhere.com" on the Web tab.
============================================================

EOF
