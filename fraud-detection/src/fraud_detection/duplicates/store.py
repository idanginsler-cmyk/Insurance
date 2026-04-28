from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Iterator, Optional

import numpy as np

from ..models import (
    DocumentRecord, HashSet, MetadataReport, ReceiptFields, TypographyReport,
)


SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    document_id   TEXT PRIMARY KEY,
    claim_id      TEXT,
    file_path     TEXT NOT NULL,
    file_type     TEXT NOT NULL,
    sha256        TEXT NOT NULL,
    phash         TEXT NOT NULL,
    dhash         TEXT NOT NULL,
    ahash         TEXT NOT NULL,
    whash         TEXT NOT NULL,
    provider      TEXT,
    issue_date    TEXT,
    amount        REAL,
    currency      TEXT,
    receipt_number TEXT,
    raw_text      TEXT,
    metadata_json TEXT,
    typography_json TEXT,
    ingested_at   TEXT NOT NULL,
    embedding     BLOB
);

CREATE INDEX IF NOT EXISTS idx_documents_claim       ON documents(claim_id);
CREATE INDEX IF NOT EXISTS idx_documents_sha256      ON documents(sha256);
CREATE INDEX IF NOT EXISTS idx_documents_provider    ON documents(provider);
CREATE INDEX IF NOT EXISTS idx_documents_amount      ON documents(amount);
CREATE INDEX IF NOT EXISTS idx_documents_receipt_no  ON documents(receipt_number);
CREATE INDEX IF NOT EXISTS idx_documents_issue_date  ON documents(issue_date);
"""


def _row_to_record(row: sqlite3.Row) -> DocumentRecord:
    keys = row.keys()
    typography = None
    if "typography_json" in keys and row["typography_json"]:
        typography = TypographyReport.model_validate_json(row["typography_json"])
    return DocumentRecord(
        document_id=row["document_id"],
        claim_id=row["claim_id"],
        file_path=row["file_path"],
        file_type=row["file_type"],
        sha256=row["sha256"],
        hashes=HashSet(
            phash=row["phash"], dhash=row["dhash"],
            ahash=row["ahash"], whash=row["whash"],
        ),
        fields=ReceiptFields(
            provider=row["provider"],
            issue_date=row["issue_date"],
            amount=row["amount"],
            currency=row["currency"],
            receipt_number=row["receipt_number"],
            raw_text=row["raw_text"] or "",
        ),
        metadata=MetadataReport.model_validate_json(row["metadata_json"] or "{}"),
        typography=typography,
        ingested_at=datetime.fromisoformat(row["ingested_at"]),
    )


class DocumentStore:
    """SQLite-backed document store with optional in-memory embedding index.

    All queries scoped by claim_id when provided — the most common
    insurance use case is "find duplicates within this claim file".
    """

    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA)
        # Forward-compatible upgrade for DBs created before typography:
        try:
            self._conn.execute("ALTER TABLE documents ADD COLUMN typography_json TEXT")
        except sqlite3.OperationalError:
            pass
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    # --- writes ------------------------------------------------------

    def add(
        self,
        record: DocumentRecord,
        embedding: Optional[np.ndarray] = None,
    ) -> None:
        emb_blob = embedding.tobytes() if embedding is not None else None
        self._conn.execute(
            """
            INSERT OR REPLACE INTO documents (
                document_id, claim_id, file_path, file_type, sha256,
                phash, dhash, ahash, whash,
                provider, issue_date, amount, currency, receipt_number,
                raw_text, metadata_json, typography_json,
                ingested_at, embedding
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                record.document_id, record.claim_id, record.file_path,
                record.file_type, record.sha256,
                record.hashes.phash, record.hashes.dhash,
                record.hashes.ahash, record.hashes.whash,
                record.fields.provider, record.fields.issue_date,
                record.fields.amount, record.fields.currency,
                record.fields.receipt_number, record.fields.raw_text,
                record.metadata.model_dump_json(),
                record.typography.model_dump_json() if record.typography else None,
                record.ingested_at.isoformat(),
                emb_blob,
            ),
        )
        self._conn.commit()

    # --- reads -------------------------------------------------------

    def get(self, document_id: str) -> DocumentRecord | None:
        row = self._conn.execute(
            "SELECT * FROM documents WHERE document_id = ?", (document_id,)
        ).fetchone()
        return _row_to_record(row) if row else None

    def by_sha256(self, sha256: str) -> list[DocumentRecord]:
        rows = self._conn.execute(
            "SELECT * FROM documents WHERE sha256 = ?", (sha256,)
        ).fetchall()
        return [_row_to_record(r) for r in rows]

    def iter_records(
        self,
        claim_id: str | None = None,
        exclude_id: str | None = None,
    ) -> Iterator[DocumentRecord]:
        sql = "SELECT * FROM documents WHERE 1=1"
        params: list = []
        if claim_id:
            sql += " AND claim_id = ?"
            params.append(claim_id)
        if exclude_id:
            sql += " AND document_id != ?"
            params.append(exclude_id)
        for row in self._conn.execute(sql, params):
            yield _row_to_record(row)

    def get_embedding(self, document_id: str) -> Optional[np.ndarray]:
        row = self._conn.execute(
            "SELECT embedding FROM documents WHERE document_id = ?", (document_id,)
        ).fetchone()
        if row and row["embedding"]:
            return np.frombuffer(row["embedding"], dtype=np.float32)
        return None

    def count(self) -> int:
        return self._conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]

    # --- candidate filters ------------------------------------------

    def candidates_by_field(
        self,
        provider: str | None = None,
        amount: float | None = None,
        receipt_number: str | None = None,
        claim_id: str | None = None,
        exclude_id: str | None = None,
    ) -> list[DocumentRecord]:
        clauses, params = ["1=1"], []
        if provider:
            clauses.append("provider = ?")
            params.append(provider)
        if amount is not None:
            clauses.append("amount = ?")
            params.append(amount)
        if receipt_number:
            clauses.append("receipt_number = ?")
            params.append(receipt_number)
        if claim_id:
            clauses.append("claim_id = ?")
            params.append(claim_id)
        if exclude_id:
            clauses.append("document_id != ?")
            params.append(exclude_id)

        sql = f"SELECT * FROM documents WHERE {' AND '.join(clauses)}"
        return [_row_to_record(r) for r in self._conn.execute(sql, params).fetchall()]
