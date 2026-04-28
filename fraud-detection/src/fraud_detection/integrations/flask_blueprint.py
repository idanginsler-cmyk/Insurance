"""Flask Blueprint that exposes the fraud-detection POC inside an
existing Flask application — used to mount the POC into the user's
PythonAnywhere site under /fraud/ alongside their other dashboards.

Key design points:

- Auth is enforced by a ``before_request`` handler that reads the
  *host* application's ``session["logged_in"]``. There is no separate
  auth state — login is shared with the host app.
- The HTML upload page from ``api/static/index.html`` is reused as a
  Jinja template, with the API base URL injected so it posts to
  ``<prefix>/v1/analyze`` regardless of where the blueprint is mounted.
- Tesseract data path is set on first request from the
  ``FD_TESSDATA_PREFIX`` env var or ``~/tessdata``, accommodating
  PythonAnywhere where Hebrew language data must be installed manually.

Usage in the host Flask app::

    from fraud_detection.integrations.flask_blueprint import (
        make_fraud_blueprint,
    )
    fraud_bp = make_fraud_blueprint()
    app.register_blueprint(fraud_bp)
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Optional

from flask import (
    Blueprint, Response, current_app, jsonify, redirect, request,
    render_template_string, session, url_for,
)

from ..config import Config
from ..duplicates.store import DocumentStore
from ..pipeline import analyze


# ---- Tesseract data discovery ----------------------------------------

def _ensure_tessdata() -> None:
    """Point pytesseract at locally-installed Hebrew data if present.
    No-op if TESSDATA_PREFIX is already set or no local data exists."""
    if "TESSDATA_PREFIX" in os.environ:
        return
    candidates = [
        os.environ.get("FD_TESSDATA_PREFIX"),
        str(Path.home() / "tessdata"),
    ]
    for c in candidates:
        if c and Path(c).is_dir():
            os.environ["TESSDATA_PREFIX"] = c
            return


# ---- HTML loading ----------------------------------------------------

_INDEX_HTML_PATH = Path(__file__).resolve().parent.parent / "api" / "static" / "index.html"


def _load_index_template() -> str:
    """Return the upload page HTML, with the analyze endpoint URL
    rewritten to be Jinja-templatable."""
    raw = _INDEX_HTML_PATH.read_text(encoding="utf-8")
    # Replace the hard-coded fetch URL with a Jinja variable so the
    # blueprint can mount under any prefix.
    raw = raw.replace(
        "fetch('/v1/analyze'",
        "fetch('{{ analyze_url }}'",
    )
    return raw


# ---- Blueprint factory ------------------------------------------------

def make_fraud_blueprint(
    *,
    url_prefix: str = "/fraud",
    db_path: Optional[Path] = None,
    require_login_session_key: str = "logged_in",
    login_endpoint: str = "login",
    name: str = "fraud",
) -> Blueprint:
    """Build a Blueprint that serves the fraud-detection POC.

    Parameters
    ----------
    url_prefix
        Where the blueprint mounts. Default ``/fraud``.
    db_path
        SQLite store location. Defaults to ``data/store/fraud_detection.db``
        under the blueprint's working directory.
    require_login_session_key
        The Flask session key the host app sets after a successful
        login. The default matches the user's web_app.py.
    login_endpoint
        Endpoint name to redirect unauthenticated visitors to.
    """
    bp = Blueprint(name, __name__, url_prefix=url_prefix)

    cfg = Config.from_env()
    if db_path:
        cfg.db_path = Path(db_path)
    cfg.db_path.parent.mkdir(parents=True, exist_ok=True)

    _ensure_tessdata()
    INDEX_TEMPLATE = _load_index_template()

    # ---- Auth gate ----------------------------------------------------
    @bp.before_request
    def _require_login():
        if not session.get(require_login_session_key):
            return redirect(url_for(login_endpoint))

    # ---- Routes -------------------------------------------------------
    @bp.route("/")
    def index() -> Response:
        return Response(
            render_template_string(
                INDEX_TEMPLATE,
                analyze_url=url_for(f"{name}.analyze_endpoint"),
            ),
            mimetype="text/html; charset=utf-8",
        )

    @bp.route("/health")
    def health() -> Response:
        return jsonify({"ok": True, "version": "0.1.0"})

    @bp.route("/v1/analyze", methods=["POST"])
    def analyze_endpoint() -> Response:
        f = request.files.get("file")
        if f is None or not f.filename:
            return jsonify({"detail": "missing file"}), 400

        claim_id = (request.form.get("claim_id") or "").strip() or None
        persist = request.form.get("persist", "false").lower() in ("1", "true", "yes")

        suffix = Path(f.filename).suffix or ".bin"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            f.save(tmp.name)
            tmp_path = Path(tmp.name)

        store = DocumentStore(cfg.db_path)
        try:
            record, score, ocr = analyze(
                tmp_path, store, claim_id=claim_id, persist=persist, cfg=cfg,
            )
        except Exception as e:
            current_app.logger.exception("analyze failed: %s", e)
            return jsonify({"detail": f"{type(e).__name__}: {e}"}), 400
        finally:
            store.close()
            try:
                tmp_path.unlink()
            except OSError:
                pass

        return jsonify({
            "record": record.model_dump(mode="json"),
            "score":  score.model_dump(mode="json"),
            "ocr":    {"engine": ocr.engine, "chars": len(ocr.text)},
        })

    @bp.route("/v1/documents")
    def list_documents() -> Response:
        store = DocumentStore(cfg.db_path)
        try:
            claim_id = request.args.get("claim_id")
            records = list(store.iter_records(claim_id=claim_id))
            return jsonify({
                "count": len(records),
                "items": [r.model_dump(mode="json") for r in records],
            })
        finally:
            store.close()

    return bp
