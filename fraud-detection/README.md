# Fraud Detection POC

POC לזיהוי זיופים והגשות כפולות במסמכי תביעות ביטוח (קבלות, חשבוניות, מרשמים)
בעברית. ממוקד ב־**שכבת ה־Phase 1 שזיהינו במחקר** — duplicate detection +
metadata heuristics, שם ה־ROI הגבוה ביותר וההתחייבות הרגולטורית הנמוכה ביותר.

## מה המערכת עושה

1. **Ingestion** — קולטת PDF/JPG/PNG, מרנדרת עמוד ראשון, מחשבת SHA-256.
2. **Perceptual hashing** — pHash, dHash, aHash, wHash (כל אחד 64-bit) לזיהוי
   חזותי של אותה תמונה גם אחרי dimming, scaling, JPEG recompression.
3. **Metadata forensics** — EXIF Software, PDF Producer/Creator, ספירת `%%EOF`
   (incremental updates), פער בין CreationDate ל־ModDate, blacklist/whitelist
   של כלי הפקה.
4. **OCR** — Tesseract (`heb+eng`) או EasyOCR (`he+en`), לפי מה שמותקן.
5. **Field extraction** — ספק, תאריך (DD/MM/YYYY ישראלי), סכום (כולל זיהוי ₪),
   מספר קבלה. רגקס + עוגני מילות מפתח בעברית.
6. **Text fingerprinting** — חתימה קנונית `provider|date|amount|receipt#`
   להתאמה מדויקת + Jaccard על טוקנים נורמליים להתאמה רכה (שורד גם
   re-photograph של אותה קבלה).
7. **Optional CLIP embeddings** — לדמיון סמנטי מעבר ל־hash. מושבת כברירת
   מחדל כי דורש torch ~2GB.
8. **Ensemble scoring** — ציון 0–100 + רמת סיכון + רשימת הסיבות
   (חובת explainability לפי רגולטור שוק ההון).

## מה המערכת *לא* עושה (בכוונה — מחוץ ל־scope של POC)

- מודלי forensics עמוקים (TruFor, Noiseprint, MVSS-Net) — דורשים GPU.
- AI-generated detection (DIRE, AIDE, Sentry).
- Cross-claim graph analysis.
- תמיכה בכתב יד רפואי.
- UI לאד'סטרים (יש CLI ו־REST API בלבד).
- Authentication/authorization, audit log, HA, rate limiting.

## התקנה

```bash
cd fraud-detection
python -m venv .venv && source .venv/bin/activate
pip install -e .

# לפחות מנוע OCR אחד (אופציונלי לבדיקות בסיסיות):
sudo apt install -y tesseract-ocr tesseract-ocr-heb   # Ubuntu/Debian
pip install pytesseract
# או:
pip install easyocr            # כבד יותר, כולל מודל עברי

# לרינדור PDF:
sudo apt install -y poppler-utils
pip install pdf2image

# לבדיקת זמינות:
make info
```

## שימוש

### CLI

```bash
# נתח מסמך בודד
fraud-detection analyze receipt.pdf --claim claim_42

# הזרם תיק תביעה שלם (כל מסמך נבדק מול הקודמים)
fraud-detection ingest receipt1.pdf receipt2.pdf receipt3.pdf --claim claim_42

# הצג מאגר
fraud-detection list --claim claim_42

# JSON גולמי
fraud-detection analyze receipt.pdf --json
```

### REST API

```bash
make run-api
# → http://localhost:8000/docs (Swagger UI)

curl -F "file=@receipt.pdf" -F "claim_id=claim_42" -F "persist=true" \
    http://localhost:8000/v1/analyze
```

### דמו מקצה־לקצה עם דאטה סינתטי

```bash
make demo
```

יוצר 4 קבלות סינתטיות (אותנטית, הגשה־חוזרת ביט־לביט, סכום מזויף 600→1600,
ספק לא קשור), מזין אותן, ובסוף מנתח את ה־resubmission. הציפייה: phash_exact
match על המסמך הראשון, רמה HIGH/CRITICAL.

## ארכיטקטורה

```
ingestion/loader.py        PDF/image → Document (image, sha256, pdf_raw)
forensics/perceptual_hash  Document → HashSet (pHash, dHash, ahash, wHash)
forensics/metadata         Document → MetadataReport (producer, eof_count, suspicions)
ocr/{tesseract,easyocr}    Image → OCRResult (text, lines, confidence)
extraction/fields          OCRResult → ReceiptFields (provider, date, amount, ...)
duplicates/store           SQLite-backed DocumentStore
duplicates/matcher         Record → list[DuplicateMatch]  (5 strategies, scoped by claim)
scoring/ensemble           DuplicateMatch[] + MetadataReport → FraudScore (0–100, level, reasons)
pipeline.py                ties it all together
cli.py                     Typer CLI
api/server.py              FastAPI server
```

## טסטים

```bash
make test
```

הטסטים מייצרים תמונות סינתטיות לבד — אין צורך במסמכי דוגמה. מכוסים: hashing,
extraction (סכום, תאריך, מס׳ קבלה, ספק, fingerprint), metadata, store,
ופייפליין מקצה־לקצה.

## גבולות ידועים של ה־POC

- Field extraction מבוסס regex — ב־production צריך layout-aware model
  (LayoutLMv3, Donut, Azure Document Intelligence).
- אין קישור ל־CIPER, Sapiens, או מערכת תביעות אמיתית — רק SQLite מקומי.
- אין compliance עם תיקון 13 לחוק הגנת הפרטיות — אין הצפנה במנוחה,
  אין audit log, אין PII vault.
- האדג׳סטר רואה רק CLI/JSON — אין UI עם heatmap.
- אין קישור ל־vendor forensic (Veridox/Verisk) — נקודת הרחבה ברורה.

## הצעדים הבאים (אם רוצים להפוך את ה־POC לפרודקשן)

1. החלפת ingestion ל־Azure Document Intelligence Read v4 (חזק לעברית RTL).
2. הוספת שכבת layout/font consistency check (kerning, baseline) — תופסת
   "1" שהוסף לפני "600".
3. הפעלת CLIP embeddings ב־FAISS index (cross-claim near-duplicate search
   על מיליוני מסמכים).
4. אינטגרציה ל־vendor forensic כשכבה Phase 3.
5. Adjuster UI עם heatmap, similar-doc panel, rationale per signal.
6. Audit trail מלא, encryption at rest, role-based access.
