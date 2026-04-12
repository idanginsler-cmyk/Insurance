"""
הגדרות משותפות - טעינת API keys ואתחול לקוחות
תומך במצב mock כשאין מפתחות API
"""
import os
from pathlib import Path

# טעינת משתני סביבה מ-.env
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent.parent / ".env"
    load_dotenv(env_path)
except ImportError:
    pass

# מפתחות API
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# האם יש מפתחות API תקינים?
HAS_OPENAI = bool(OPENAI_API_KEY) and not OPENAI_API_KEY.startswith("sk-...")
HAS_ANTHROPIC = bool(ANTHROPIC_API_KEY) and not ANTHROPIC_API_KEY.startswith("sk-ant-...")
MOCK_MODE = not (HAS_OPENAI or HAS_ANTHROPIC)


def get_openai_client():
    """יצירת לקוח OpenAI"""
    if not HAS_OPENAI:
        return None
    from openai import OpenAI
    return OpenAI(api_key=OPENAI_API_KEY)


def get_anthropic_client():
    """יצירת לקוח Anthropic"""
    if not HAS_ANTHROPIC:
        return None
    from anthropic import Anthropic
    return Anthropic(api_key=ANTHROPIC_API_KEY)


def call_llm(prompt: str, system: str = "", model: str = "auto") -> str:
    """
    שליחת פרומפט ל-LLM - בוחר אוטומטית את המודל הזמין.
    במצב mock מחזיר תשובה לדוגמה.
    """
    if MOCK_MODE:
        return None  # המתקשר יטפל במצב mock

    if model == "auto":
        if HAS_ANTHROPIC:
            model = "anthropic"
        elif HAS_OPENAI:
            model = "openai"

    if model == "anthropic" and HAS_ANTHROPIC:
        client = get_anthropic_client()
        messages = [{"role": "user", "content": prompt}]
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=system,
            messages=messages,
        )
        return response.content[0].text

    elif model == "openai" and HAS_OPENAI:
        client = get_openai_client()
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
        )
        return response.choices[0].message.content

    return None


def print_mode_banner():
    """הדפסת באנר מצב - mock או חי"""
    try:
        from rich.console import Console
        from rich.panel import Panel
        console = Console()
        if MOCK_MODE:
            console.print(Panel(
                "[yellow]מצב הדגמה (Mock Mode)[/yellow]\n"
                "לא נמצאו מפתחות API - מציג תוצאות לדוגמה.\n"
                "להרצה עם AI אמיתי, הגדירו מפתחות בקובץ .env",
                title="⚙️ מצב",
                border_style="yellow",
            ))
        else:
            provider = "Anthropic Claude" if HAS_ANTHROPIC else "OpenAI GPT-4"
            console.print(Panel(
                f"[green]מצב חי (Live Mode)[/green]\n"
                f"משתמש ב: {provider}",
                title="⚙️ מצב",
                border_style="green",
            ))
    except ImportError:
        if MOCK_MODE:
            print("=" * 50)
            print("מצב הדגמה (Mock Mode) - תוצאות לדוגמה")
            print("=" * 50)
        else:
            print("=" * 50)
            print("מצב חי (Live Mode)")
            print("=" * 50)
