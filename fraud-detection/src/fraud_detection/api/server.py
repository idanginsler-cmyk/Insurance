from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from ..config import Config
from ..duplicates.store import DocumentStore
from ..pipeline import analyze


app = FastAPI(
    title="Fraud Detection POC",
    description="API לזיהוי זיופים במסמכי תביעות ביטוח (POC).",
    version="0.1.0",
)

# Permissive CORS so the page can be served via a tunnel (cloudflared,
# ngrok) and accessed from a phone browser on a different origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_INDEX_HTML = (Path(__file__).parent / "static" / "index.html").read_text(encoding="utf-8")


def _store() -> DocumentStore:
    return DocumentStore(Config.from_env().db_path)


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def index() -> str:
    """Mobile-friendly upload UI."""
    return _INDEX_HTML


@app.get("/health")
def health() -> dict:
    return {"ok": True, "version": app.version}


@app.post("/v1/analyze")
async def analyze_endpoint(
    file: UploadFile = File(...),
    claim_id: Optional[str] = Form(None),
    persist: bool = Form(False),
) -> dict:
    suffix = Path(file.filename or "upload").suffix or ".bin"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(await file.read())
        tmp_path = Path(tmp.name)

    store = _store()
    try:
        record, score, ocr = analyze(
            tmp_path, store, claim_id=claim_id, persist=persist
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        store.close()
        try:
            tmp_path.unlink()
        except OSError:
            pass

    return {
        "record": record.model_dump(mode="json"),
        "score":  score.model_dump(mode="json"),
        "ocr":    {"engine": ocr.engine, "chars": len(ocr.text)},
    }


@app.get("/v1/documents")
def list_documents(claim_id: Optional[str] = None) -> dict:
    store = _store()
    try:
        records = list(store.iter_records(claim_id=claim_id))
        return {
            "count": len(records),
            "items": [r.model_dump(mode="json") for r in records],
        }
    finally:
        store.close()
