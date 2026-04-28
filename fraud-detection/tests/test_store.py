from datetime import datetime

from fraud_detection.duplicates.store import DocumentStore
from fraud_detection.models import (
    DocumentRecord, HashSet, MetadataReport, ReceiptFields,
)


def _record(doc_id: str, claim_id: str = "c1", amount: float = 600.0) -> DocumentRecord:
    return DocumentRecord(
        document_id=doc_id,
        claim_id=claim_id,
        file_path=f"/tmp/{doc_id}.png",
        file_type="image",
        sha256="0" * 64,
        hashes=HashSet(phash="0"*16, dhash="0"*16, ahash="0"*16, whash="0"*16),
        fields=ReceiptFields(provider="כהן", issue_date="2026-03-15",
                             amount=amount, receipt_number="123456", raw_text="hi"),
        metadata=MetadataReport(suspicions=[]),
        ingested_at=datetime.utcnow(),
    )


def test_add_and_get(tmp_db):
    store = DocumentStore(tmp_db)
    rec = _record("doc1")
    store.add(rec)
    fetched = store.get("doc1")
    assert fetched is not None
    assert fetched.fields.amount == 600.0
    assert fetched.claim_id == "c1"
    store.close()


def test_iter_records_scoped_by_claim(tmp_db):
    store = DocumentStore(tmp_db)
    store.add(_record("a", claim_id="c1"))
    store.add(_record("b", claim_id="c1"))
    store.add(_record("c", claim_id="c2"))
    c1 = list(store.iter_records(claim_id="c1"))
    assert {r.document_id for r in c1} == {"a", "b"}
    store.close()


def test_candidates_by_field(tmp_db):
    store = DocumentStore(tmp_db)
    store.add(_record("a", amount=600.0))
    store.add(_record("b", amount=600.0))
    store.add(_record("c", amount=999.0))
    matches = store.candidates_by_field(amount=600.0, exclude_id="a")
    assert {r.document_id for r in matches} == {"b"}
    store.close()
