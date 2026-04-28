"""Reference web_app.py — integrates the existing FraudAnalyst Flask
app with the fraud-detection POC, plus the P0+P1 security fixes from
the code review.

Differences from the user's original web_app.py:

1. Cookie security flags (SESSION_COOKIE_HTTPONLY/SECURE/SAMESITE).
2. Permanent session lifetime (12h).
3. fcntl-based file locking on doctors_reviews.json writes — kills
   the read-modify-write race.
4. Empty-key filter on incoming reviews.
5. NAV_BAR injection via regex instead of fragile str.replace.
6. 404 + 500 error handlers (logged).
7. Third portal card "זיהוי זיופים" linking to /fraud/.
8. Registration of the fraud-detection Flask Blueprint.

The user can copy this file over their ~/web_app.py on PythonAnywhere.
config.py and the HTML files stay untouched.
"""

from __future__ import annotations

import fcntl
import json
import os
import re
from datetime import timedelta
from functools import wraps
from pathlib import Path

from flask import (
    Flask, jsonify, redirect, render_template_string, request,
    session, url_for,
)
from werkzeug.security import check_password_hash

# --- config -----------------------------------------------------------
try:
    from config import (
        WEB_USERNAME, WEB_PASSWORD_HASH, FLASK_SECRET_KEY, PYTHONANYWHERE_USER,
    )
except ImportError:
    WEB_USERNAME        = os.environ.get("WEB_USERNAME", "admin")
    WEB_PASSWORD_HASH   = os.environ.get("WEB_PASSWORD_HASH", "")
    FLASK_SECRET_KEY    = os.environ.get("FLASK_SECRET_KEY", "change-me-in-config")
    PYTHONANYWHERE_USER = os.environ.get("PYTHONANYWHERE_USER", "")

BASE_DIR             = Path(__file__).resolve().parent
REPORT_FILE          = BASE_DIR / "posta_report.html"
DOCTORS_FILE         = BASE_DIR / "fraud_dashboard.html"
DOCTORS_REVIEWS_FILE = BASE_DIR / "doctors_reviews.json"

app = Flask(__name__)
app.secret_key = FLASK_SECRET_KEY

# Cookie security — PA serves over HTTPS, so Secure is correct.
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=True,
    PERMANENT_SESSION_LIFETIME=timedelta(hours=12),
)

# --- auth -------------------------------------------------------------
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


# --- atomic JSON helpers ---------------------------------------------
def _read_json(path: Path) -> dict:
    if not path.exists() or path.stat().st_size == 0:
        return {}
    with open(path, "r", encoding="utf-8") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_SH)
        try:
            return json.load(f)
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)


def _merge_json(path: Path, updates: dict) -> dict:
    """Read-modify-write with an exclusive POSIX file lock so two
    concurrent requests can't corrupt the file. Returns the merged dict."""
    path.touch(exist_ok=True)
    with open(path, "r+", encoding="utf-8") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            content = f.read()
            try:
                existing = json.loads(content) if content.strip() else {}
            except json.JSONDecodeError:
                existing = {}
            existing.update(updates)
            f.seek(0)
            f.truncate()
            json.dump(existing, f, ensure_ascii=False, indent=2)
            return existing
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)


# --- nav bar ----------------------------------------------------------
NAV_BAR = """
<div style="position:fixed;top:0;left:0;right:0;z-index:9999;
    background:rgba(26,26,46,0.95);backdrop-filter:blur(8px);
    padding:10px 20px;display:flex;align-items:center;gap:12px;
    box-shadow:0 2px 12px rgba(0,0,0,.3);direction:rtl">
  <a href="/portal" style="color:#fff;text-decoration:none;font-family:'Segoe UI',Arial,sans-serif;
     font-weight:bold;font-size:1rem;margin-left:auto">דשבורדים</a>
  <a href="/logout" style="background:#c0392b;color:#fff;padding:6px 16px;
     border-radius:6px;text-decoration:none;font-family:'Segoe UI',Arial,sans-serif;
     font-size:0.85rem">התנתק</a>
</div>
<div style="height:48px"></div>
"""

_BODY_RE = re.compile(r"(<body\b[^>]*>)", flags=re.IGNORECASE)


def _inject_nav(html: str) -> str:
    """Insert NAV_BAR right after the <body> tag, regardless of attrs."""
    return _BODY_RE.sub(lambda m: m.group(1) + NAV_BAR, html, count=1)


# --- HTML templates ---------------------------------------------------
LOGIN_HTML = """<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>כניסה – מערכת דשבורדים</title>
  <style>
    *{box-sizing:border-box;margin:0;padding:0}
    body{font-family:'Segoe UI',Arial,sans-serif;
      background:linear-gradient(135deg,#1a1a2e 0%,#16213e 50%,#0f3460 100%);
      min-height:100vh;display:flex;align-items:center;justify-content:center;direction:rtl}
    .login-box{background:#fff;border-radius:16px;padding:40px 36px;
      box-shadow:0 10px 40px rgba(0,0,0,.3);width:100%;max-width:380px;text-align:center}
    .login-box h1{font-size:1.5rem;color:#1a1a2e;margin-bottom:8px}
    .login-box p{color:#888;font-size:0.9rem;margin-bottom:24px}
    .login-box input{width:100%;padding:12px 16px;margin-bottom:14px;
      border:1px solid #ddd;border-radius:8px;font-size:1rem;font-family:inherit;
      direction:rtl;background:#fafafa}
    .login-box input:focus{outline:none;border-color:#6c63ff;background:#fff}
    .login-box button{width:100%;padding:12px;background:#1a1a2e;color:#fff;
      border:none;border-radius:8px;font-size:1rem;font-family:inherit;
      cursor:pointer;transition:background .2s}
    .login-box button:hover{background:#6c63ff}
    .error{background:#fce4e4;color:#c0392b;border-radius:8px;padding:10px;
      margin-bottom:14px;font-size:0.9rem}
  </style>
</head>
<body>
  <div class="login-box">
    <h1>מערכת דשבורדים</h1>
    <p>הזן שם משתמש וסיסמא כדי להיכנס</p>
    {% if error %}<div class="error">{{ error }}</div>{% endif %}
    <form method="POST" action="/login">
      <input type="text" name="username" placeholder="שם משתמש" required autofocus>
      <input type="password" name="password" placeholder="סיסמא" required>
      <button type="submit">כניסה</button>
    </form>
  </div>
</body></html>"""

PORTAL_HTML = """<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>מערכת דשבורדים</title>
  <style>
    *{box-sizing:border-box;margin:0;padding:0}
    body{font-family:'Segoe UI',Arial,sans-serif;
      background:linear-gradient(135deg,#1a1a2e 0%,#16213e 50%,#0f3460 100%);
      min-height:100vh;direction:rtl;color:#e2e8f0}
    .top-bar{background:rgba(26,26,46,0.95);backdrop-filter:blur(8px);
      padding:14px 24px;display:flex;align-items:center;justify-content:space-between;
      box-shadow:0 2px 12px rgba(0,0,0,.3)}
    .top-bar h2{font-size:1.1rem;color:#fff}
    .top-bar a{background:#c0392b;color:#fff;padding:6px 16px;
      border-radius:6px;text-decoration:none;font-size:0.85rem}
    .top-bar a:hover{background:#e74c3c}
    .container{max-width:900px;margin:0 auto;padding:60px 24px}
    .portal-title{text-align:center;margin-bottom:48px}
    .portal-title h1{font-size:2.2rem;margin-bottom:8px}
    .portal-title p{color:#94a3b8;font-size:1rem}
    .cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:24px}
    .card{background:rgba(30,41,59,0.85);border:1px solid #334155;
      border-radius:16px;padding:32px 28px;text-decoration:none;color:inherit;
      transition:all .25s;display:flex;flex-direction:column;gap:14px}
    .card:hover{transform:translateY(-4px);box-shadow:0 12px 40px rgba(0,0,0,.3);
      border-color:#6c63ff;background:rgba(30,41,59,1)}
    .card-icon{font-size:2.5rem}
    .card-title{font-size:1.3rem;font-weight:bold;color:#f1f5f9}
    .card-desc{font-size:0.9rem;color:#94a3b8;line-height:1.5}
    .card-status{font-size:0.8rem;padding:4px 10px;border-radius:12px;
      display:inline-block;width:fit-content}
    .card-status.active{background:rgba(34,197,94,.15);color:#4ade80}
    .card-status.new{background:rgba(108,99,255,.18);color:#a5b4fc}
    .card-status.soon{background:rgba(234,179,8,.15);color:#fbbf24}
  </style>
</head>
<body>
  <div class="top-bar">
    <h2>מערכת דשבורדים</h2>
    <a href="/logout">התנתק</a>
  </div>
  <div class="container">
    <div class="portal-title">
      <h1>בחר דשבורד</h1>
      <p>לחץ על כרטיס כדי לפתוח את הדשבורד המבוקש</p>
    </div>
    <div class="cards">

      <a href="/posta" class="card">
        <div class="card-icon">📮</div>
        <div class="card-title">דוח פוסטה</div>
        <div class="card-desc">סריקת אתר חדשותי — איתור חשודים בפלילים</div>
        <span class="card-status active">פעיל</span>
      </a>

      <a href="/doctors" class="card">
        <div class="card-icon">🏥</div>
        <div class="card-title">סריקת רופאים</div>
        <div class="card-desc">זיהוי רופאים עם פעילות אסתטית — דשבורד ביקורת וניקוד</div>
        <span class="card-status active">פעיל</span>
      </a>

      <a href="/fraud/" class="card">
        <div class="card-icon">🔍</div>
        <div class="card-title">זיהוי זיופים</div>
        <div class="card-desc">העלאת קבלה / מסמך → ציון חשד עם הסבר. POC.</div>
        <span class="card-status new">חדש</span>
      </a>

    </div>
  </div>
</body></html>"""

NOT_FOUND_HTML = """<!DOCTYPE html><html lang="he" dir="rtl"><head><meta charset="UTF-8">
<title>404</title><style>body{font-family:'Segoe UI',Arial,sans-serif;
background:#1a1a2e;color:#e2e8f0;display:flex;align-items:center;justify-content:center;
min-height:100vh;margin:0;direction:rtl}.box{text-align:center;padding:40px}
h1{font-size:6rem;margin:0;color:#6c63ff}p{color:#94a3b8}
a{color:#fff;background:#6c63ff;padding:10px 20px;border-radius:8px;
text-decoration:none;display:inline-block;margin-top:16px}</style></head>
<body><div class="box"><h1>404</h1><p>הדף שביקשת לא נמצא.</p>
<a href="/">חזרה לדף הראשי</a></div></body></html>"""

ERROR_HTML = """<!DOCTYPE html><html lang="he" dir="rtl"><head><meta charset="UTF-8">
<title>שגיאה</title><style>body{font-family:'Segoe UI',Arial,sans-serif;
background:#1a1a2e;color:#e2e8f0;display:flex;align-items:center;justify-content:center;
min-height:100vh;margin:0;direction:rtl}.box{text-align:center;padding:40px}
h1{font-size:3rem;margin:0;color:#c0392b}p{color:#94a3b8}
a{color:#fff;background:#6c63ff;padding:10px 20px;border-radius:8px;
text-decoration:none;display:inline-block;margin-top:16px}</style></head>
<body><div class="box"><h1>שגיאה פנימית</h1><p>משהו השתבש בצד השרת. נסה שוב.</p>
<a href="/">חזרה לדף הראשי</a></div></body></html>"""


# --- routes ----------------------------------------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("logged_in"):
        return redirect(url_for("portal"))
    error = None
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        if username == WEB_USERNAME and check_password_hash(WEB_PASSWORD_HASH, password):
            session.permanent = True
            session["logged_in"] = True
            return redirect(url_for("portal"))
        error = "שם משתמש או סיסמא שגויים"
    return render_template_string(LOGIN_HTML, error=error)


@app.route("/")
def index():
    return redirect(url_for("portal" if session.get("logged_in") else "login"))


@app.route("/portal")
@login_required
def portal():
    return render_template_string(PORTAL_HTML)


@app.route("/posta")
@login_required
def posta():
    if not REPORT_FILE.exists():
        return ("<h2 style='text-align:center;padding:60px;font-family:Arial'>"
                "הדוח עדיין לא נוצר.</h2>")
    html = REPORT_FILE.read_text(encoding="utf-8-sig")
    return _inject_nav(html)


@app.route("/report")
@login_required
def report_alias():
    return redirect(url_for("posta"))


@app.route("/doctors")
@login_required
def doctors():
    if not DOCTORS_FILE.exists():
        return ("<h2 style='text-align:center;padding:60px;font-family:Arial'>"
                "דשבורד הרופאים עדיין לא הועלה.</h2>")
    html = DOCTORS_FILE.read_text(encoding="utf-8-sig")
    return _inject_nav(html)


@app.route("/api/doctors/reviews", methods=["GET"])
@login_required
def get_doctor_reviews():
    return jsonify(_read_json(DOCTORS_REVIEWS_FILE))


@app.route("/api/doctors/reviews", methods=["POST"])
@login_required
def save_doctor_reviews():
    data = request.get_json(force=True, silent=True) or {}
    if not isinstance(data, dict):
        return jsonify({"error": "invalid data"}), 400
    # Drop empty / whitespace-only keys (client bug — see audit notes).
    data = {k: v for k, v in data.items() if isinstance(k, str) and k.strip()}
    if not data:
        return jsonify({"ok": True, "total": 0, "skipped": "all-empty"}), 200
    merged = _merge_json(DOCTORS_REVIEWS_FILE, data)
    return jsonify({"ok": True, "total": len(merged)})


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# --- error handlers --------------------------------------------------
@app.errorhandler(404)
def _not_found(e):
    return render_template_string(NOT_FOUND_HTML), 404


@app.errorhandler(500)
def _server_error(e):
    app.logger.exception("Unhandled exception: %s", e)
    return render_template_string(ERROR_HTML), 500


# --- fraud-detection Blueprint --------------------------------------
# Registered last so any /fraud/* paths resolve to the blueprint and not
# to a stray Flask route. The blueprint enforces the same login as the
# rest of the app via session["logged_in"].
try:
    from fraud_detection.integrations.flask_blueprint import make_fraud_blueprint
    app.register_blueprint(
        make_fraud_blueprint(
            db_path=BASE_DIR / "data" / "store" / "fraud_detection.db",
        )
    )
except ImportError:
    app.logger.warning("fraud_detection package not importable — /fraud/* disabled")


# --- local dev -------------------------------------------------------
if __name__ == "__main__":
    print("האפליקציה רצה על http://localhost:5000")
    app.run(debug=True, host="0.0.0.0", port=5000)
