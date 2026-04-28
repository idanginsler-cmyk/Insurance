from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    CLEAN = "clean"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class OCRLine(BaseModel):
    text: str
    bbox: tuple[int, int, int, int] | None = None  # x0,y0,x1,y1
    confidence: float | None = None


class OCRResult(BaseModel):
    text: str
    lines: list[OCRLine] = Field(default_factory=list)
    engine: str
    lang: str


class HashSet(BaseModel):
    phash: str
    dhash: str
    ahash: str
    whash: str


class ReceiptFields(BaseModel):
    provider: Optional[str] = None
    issue_date: Optional[str] = None  # ISO date string
    amount: Optional[float] = None
    currency: Optional[str] = None
    receipt_number: Optional[str] = None
    raw_text: str = ""


class MetadataReport(BaseModel):
    producer: Optional[str] = None
    creator: Optional[str] = None
    software: Optional[str] = None        # EXIF Software tag
    creation_date: Optional[str] = None
    modified_date: Optional[str] = None
    eof_count: Optional[int] = None       # PDFs only
    incremental_updates: Optional[int] = None
    has_exif: bool = False
    suspicions: list[str] = Field(default_factory=list)
    raw: dict = Field(default_factory=dict)


class DuplicateMatch(BaseModel):
    document_id: str
    claim_id: Optional[str] = None
    match_type: str  # "phash_exact" | "phash_near" | "text_fingerprint" | "embedding"
    similarity: float
    distance: Optional[int] = None
    matched_at: Optional[datetime] = None
    note: Optional[str] = None


class FraudSignal(BaseModel):
    name: str
    weight: float
    triggered: bool
    detail: str = ""


class FraudScore(BaseModel):
    score: float = 0.0          # 0..100
    level: RiskLevel = RiskLevel.CLEAN
    reasons: list[str] = Field(default_factory=list)
    signals: list[FraudSignal] = Field(default_factory=list)
    duplicates: list[DuplicateMatch] = Field(default_factory=list)


class TypographyAnomaly(BaseModel):
    char: str
    line_index: int
    char_index: int
    bbox: tuple[int, int, int, int]
    metric: str            # "height" | "baseline" | "kerning" | "sharpness" | "brightness"
    z_score: float
    detail: str = ""


class TypographyReport(BaseModel):
    lines_analyzed: int = 0
    chars_analyzed: int = 0
    anomalies: list[TypographyAnomaly] = Field(default_factory=list)
    suspicion_score: float = 0.0   # 0..1, normalized
    source: str = "none"           # "tesseract_chars" | "ocr_words_split" | "none"


class DocumentRecord(BaseModel):
    document_id: str
    claim_id: Optional[str] = None
    file_path: str
    file_type: str
    sha256: str
    hashes: HashSet
    fields: ReceiptFields
    metadata: MetadataReport
    typography: Optional[TypographyReport] = None
    ingested_at: datetime
    embedding_id: Optional[int] = None
