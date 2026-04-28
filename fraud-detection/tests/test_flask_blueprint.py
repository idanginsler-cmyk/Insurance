"""Tests for the Flask Blueprint integration.

These verify the most important contracts:
  - Auth gate redirects unauthenticated requests to /login
  - When logged in, GET /fraud/ returns the upload UI
  - GET /fraud/health returns 200 + {ok: true}
  - POST /fraud/v1/analyze returns a valid score for a synthetic image
"""

from __future__ import annotations

import io

import pytest

flask = pytest.importorskip("flask")  # noqa: F841

from flask import Flask, session  # noqa: E402

from fraud_detection.integrations.flask_blueprint import make_fraud_blueprint  # noqa: E402

from .conftest import render_receipt  # noqa: E402


@pytest.fixture
def host_app(tmp_db):
    app = Flask(__name__)
    app.secret_key = "test-secret"

    @app.route("/login")
    def login():
        return "LOGIN PAGE"

    @app.route("/test_login")
    def test_login():
        session["logged_in"] = True
        return "ok"

    bp = make_fraud_blueprint(db_path=tmp_db)
    app.register_blueprint(bp)
    return app


def test_unauthenticated_request_redirects_to_login(host_app):
    client = host_app.test_client()
    r = client.get("/fraud/")
    assert r.status_code == 302
    assert r.location.endswith("/login")


def test_authenticated_user_sees_upload_page(host_app):
    client = host_app.test_client()
    client.get("/test_login")  # set session.logged_in = True
    r = client.get("/fraud/")
    assert r.status_code == 200
    body = r.data.decode("utf-8")
    assert "זיהוי זיופים" in body  # page title text
    # The upload form should post to the blueprint's analyze endpoint.
    assert "/fraud/v1/analyze" in body


def test_health_endpoint(host_app):
    client = host_app.test_client()
    client.get("/test_login")
    r = client.get("/fraud/health")
    assert r.status_code == 200
    assert r.get_json()["ok"] is True


def test_analyze_endpoint_with_synthetic_image(host_app):
    client = host_app.test_client()
    client.get("/test_login")
    img = render_receipt(["receipt for testing", "TOTAL 100"], seed=1)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    r = client.post(
        "/fraud/v1/analyze",
        data={"file": (buf, "test.png"), "claim_id": "claim-1", "persist": "false"},
        content_type="multipart/form-data",
    )
    assert r.status_code == 200
    payload = r.get_json()
    assert "record" in payload
    assert "score" in payload
    assert payload["score"]["score"] >= 0


def test_documents_endpoint_starts_empty(host_app):
    client = host_app.test_client()
    client.get("/test_login")
    r = client.get("/fraud/v1/documents")
    assert r.status_code == 200
    assert r.get_json()["count"] == 0


def test_analyze_rejects_request_without_file(host_app):
    client = host_app.test_client()
    client.get("/test_login")
    r = client.post("/fraud/v1/analyze", data={"claim_id": "x"})
    assert r.status_code == 400
