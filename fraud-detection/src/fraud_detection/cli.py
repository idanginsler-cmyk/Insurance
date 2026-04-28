from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .config import Config
from .duplicates.store import DocumentStore
from .pipeline import analyze


app = typer.Typer(add_completion=False, help="POC לזיהוי זיופים במסמכי תביעות ביטוח")
console = Console()


def _open_store(db_path: Optional[Path]) -> DocumentStore:
    cfg = Config.from_env()
    if db_path:
        cfg.db_path = db_path
    return DocumentStore(cfg.db_path)


@app.command("analyze")
def analyze_cmd(
    file: Path = typer.Argument(..., exists=True, readable=True, help="PDF / JPG / PNG"),
    claim_id: Optional[str] = typer.Option(None, "--claim", "-c", help="מזהה תיק תביעה"),
    persist: bool = typer.Option(False, "--persist/--no-persist",
                                  help="הוסף את המסמך למאגר אחרי הניתוח"),
    db_path: Optional[Path] = typer.Option(None, "--db", help="נתיב ל-DB SQLite"),
    json_out: bool = typer.Option(False, "--json", help="פלט JSON גולמי"),
) -> None:
    """נתח מסמך בודד והדפס ציון חשד + הסברים."""
    store = _open_store(db_path)
    try:
        record, score, ocr = analyze(file, store, claim_id=claim_id, persist=persist)
    finally:
        store.close()

    if json_out:
        import json
        out = {
            "record": record.model_dump(mode="json"),
            "score": score.model_dump(mode="json"),
            "ocr": {"engine": ocr.engine, "chars": len(ocr.text)},
        }
        typer.echo(json.dumps(out, ensure_ascii=False, indent=2))
        return

    _print_human(record, score, ocr)


@app.command("ingest")
def ingest_cmd(
    files: list[Path] = typer.Argument(..., exists=True),
    claim_id: Optional[str] = typer.Option(None, "--claim", "-c"),
    db_path: Optional[Path] = typer.Option(None, "--db"),
) -> None:
    """הזרם מספר מסמכים לאותו תיק תביעה ושמור אותם במאגר.

    כל מסמך נבדק מול מה שהוזרם לפניו (ולא מול עצמו)."""
    store = _open_store(db_path)
    try:
        for f in files:
            record, score, _ = analyze(f, store, claim_id=claim_id, persist=True)
            console.print(
                f"[bold]{f.name}[/bold]  →  ציון [yellow]{score.score:.1f}[/yellow]  "
                f"רמה [cyan]{score.level.value}[/cyan]  "
                f"({len(score.duplicates)} matches)"
            )
    finally:
        store.close()


@app.command("list")
def list_cmd(
    claim_id: Optional[str] = typer.Option(None, "--claim", "-c"),
    db_path: Optional[Path] = typer.Option(None, "--db"),
) -> None:
    """רשימת מסמכים במאגר."""
    store = _open_store(db_path)
    try:
        table = Table(title="מאגר מסמכים")
        for col in ("doc_id", "claim", "provider", "date", "amount", "receipt#", "file"):
            table.add_column(col)
        for rec in store.iter_records(claim_id=claim_id):
            table.add_row(
                rec.document_id[:8],
                rec.claim_id or "-",
                rec.fields.provider or "-",
                rec.fields.issue_date or "-",
                f"{rec.fields.amount:.2f}" if rec.fields.amount else "-",
                rec.fields.receipt_number or "-",
                Path(rec.file_path).name,
            )
        console.print(table)
        console.print(f"סה\"כ: {store.count()} מסמכים")
    finally:
        store.close()


@app.command("info")
def info_cmd() -> None:
    """בדוק זמינות מנועי OCR וספריות אופציונליות."""
    from .ocr.tesseract_engine import TesseractEngine
    from .ocr.easyocr_engine import EasyOCREngine
    from .forensics.embeddings import EmbeddingEncoder

    rows = [
        ("Tesseract OCR (heb)", TesseractEngine.is_available()),
        ("EasyOCR (he)",        EasyOCREngine.is_available()),
        ("CLIP embeddings",     EmbeddingEncoder.is_available()),
    ]
    try:
        from pdf2image import convert_from_bytes  # noqa: F401
        rows.append(("pdf2image (poppler)", True))
    except Exception:
        rows.append(("pdf2image (poppler)", False))

    table = Table(title="זמינות תלויות")
    table.add_column("רכיב")
    table.add_column("זמין")
    for name, ok in rows:
        table.add_row(name, "[green]YES[/green]" if ok else "[red]NO[/red]")
    console.print(table)


def _print_human(record, score, ocr) -> None:
    color = {
        "clean":    "green",
        "low":      "blue",
        "medium":   "yellow",
        "high":     "red",
        "critical": "bright_red",
    }.get(score.level.value, "white")

    header = (
        f"[bold]{Path(record.file_path).name}[/bold]\n"
        f"ציון חשד: [bold {color}]{score.score:.1f}[/bold {color}]   "
        f"רמה: [bold {color}]{score.level.value.upper()}[/bold {color}]"
    )
    console.print(Panel.fit(header, border_style=color))

    fields_table = Table(title="שדות שזוהו", show_header=False)
    fields_table.add_column("field"); fields_table.add_column("value")
    fields_table.add_row("ספק",        record.fields.provider or "-")
    fields_table.add_row("תאריך",      record.fields.issue_date or "-")
    fields_table.add_row("סכום",       f"{record.fields.amount} {record.fields.currency or ''}".strip()
                                       if record.fields.amount else "-")
    fields_table.add_row("מס׳ קבלה",   record.fields.receipt_number or "-")
    fields_table.add_row("OCR engine", ocr.engine)
    console.print(fields_table)

    if record.metadata.suspicions:
        s = Table(title="חשדות מטא-דאטה")
        s.add_column("signal")
        for sig in record.metadata.suspicions:
            s.add_row(sig)
        console.print(s)

    if score.duplicates:
        d = Table(title="כפילויות שנמצאו")
        for col in ("doc", "type", "similarity", "note"):
            d.add_column(col)
        for m in score.duplicates:
            d.add_row(
                m.document_id[:8],
                m.match_type,
                f"{m.similarity:.2%}",
                m.note or "",
            )
        console.print(d)

    if score.reasons:
        console.print(Panel("\n".join(f"• {r}" for r in score.reasons),
                            title="סיבות עיקריות", border_style=color))


if __name__ == "__main__":
    app()
