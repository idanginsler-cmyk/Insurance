"""WSGI entry point for PythonAnywhere (and any other WSGI host).

PythonAnywhere's free tier serves apps via WSGI, but our FastAPI app is
ASGI-native. `a2wsgi.ASGIMiddleware` bridges the two — every WSGI
request is translated into an ASGI scope, run against the FastAPI app,
and the response is converted back.

Two deployment patterns:

1. **Imported directly by PythonAnywhere's WSGI file**
   In /var/www/<username>_pythonanywhere_com_wsgi.py, paste:

       import sys
       project = '/home/<username>/Insurance/fraud-detection'
       if project not in sys.path:
           sys.path.insert(0, project)
       from wsgi import application

2. **Inline (simplest)**
   Copy the body of this file into the PA WSGI file directly.

The TESSDATA_PREFIX env var is set so pytesseract finds Hebrew
training data installed under ~/tessdata (see PYTHONANYWHERE.md).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


# --- path setup ---------------------------------------------------------
HERE = Path(__file__).resolve().parent
SRC = HERE / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


# --- Tesseract data discovery ------------------------------------------
# PythonAnywhere ships tesseract but only with English by default. Users
# install the Hebrew data file under ~/tessdata; point pytesseract at it.
_user_tessdata = Path.home() / "tessdata"
if _user_tessdata.is_dir() and "TESSDATA_PREFIX" not in os.environ:
    os.environ["TESSDATA_PREFIX"] = str(_user_tessdata)


# --- bridge FastAPI (ASGI) -> WSGI -------------------------------------
from a2wsgi import ASGIMiddleware  # noqa: E402

from fraud_detection.api.server import app as _asgi_app  # noqa: E402

application = ASGIMiddleware(_asgi_app)
