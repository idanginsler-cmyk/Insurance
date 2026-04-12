"""
עזרים לטקסט עברי ופורמט מספרים
"""


def format_currency(amount: int | float) -> str:
    """פורמט סכום בשקלים: 52,750 ₪"""
    return f"{amount:,.0f} ₪"


def format_date_hebrew(date_str: str) -> str:
    """המרת תאריך לפורמט עברי"""
    return date_str  # כבר בפורמט DD/MM/YYYY


def severity_badge(level: str) -> str:
    """תג חומרה עם צבע (לשימוש עם rich)"""
    badges = {
        "נמוך": "[green]● נמוך[/green]",
        "בינוני": "[yellow]● בינוני[/yellow]",
        "גבוה": "[red]● גבוה[/red]",
        "קריטי": "[bold red]◆ קריטי[/bold red]",
    }
    return badges.get(level, level)


def fraud_score_color(score: int) -> str:
    """צבע לציון הונאה (1-10)"""
    if score <= 3:
        return f"[green]{score}/10[/green]"
    elif score <= 6:
        return f"[yellow]{score}/10[/yellow]"
    else:
        return f"[red]{score}/10[/red]"


def print_section_header(title: str):
    """הדפסת כותרת סקשן"""
    try:
        from rich.console import Console
        from rich.panel import Panel
        console = Console()
        console.print(Panel(title, border_style="blue"))
    except ImportError:
        print(f"\n{'=' * 50}")
        print(f"  {title}")
        print(f"{'=' * 50}\n")
