#!/usr/bin/env python3
"""
דמו 7: סוכן רב-שלבי - תהליך עיבוד תביעה מלא
מדגים את הקונספט של AI Agent שמבצע מספר שלבים אוטונומיים
"""
import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from demos.utils.config import call_llm, print_mode_banner, MOCK_MODE
from demos.utils.insurance_data import generate_claim, generate_policy
from demos.utils.hebrew_utils import format_currency


def print_step(step_num: int, title: str, status: str = "running"):
    """הדפסת שלב בתהליך"""
    icons = {"running": "⏳", "done": "✅", "warning": "⚠️", "error": "❌"}
    icon = icons.get(status, "•")
    try:
        from rich.console import Console
        console = Console()
        color = {"running": "yellow", "done": "green", "warning": "orange3", "error": "red"}
        console.print(f"  [{color.get(status, 'white')}]{icon} שלב {step_num}: {title}[/]")
    except ImportError:
        print(f"  {icon} שלב {step_num}: {title}")


MOCK_WORKFLOW = """
🤖 סוכן עיבוד תביעות - הדגמת תהליך רב-שלבי

═══════════════════════════════════════════════

📥 תביעה חדשה התקבלה: CLM-2025-44291

  ✅ שלב 1: חילוץ נתונים מטופס התביעה
     → מבוטח: ישראל ישראלי
     → סוג: אשפוז + ניתוח כריתת תוספתן
     → סכום: 52,750 ₪
     → תאריך: 01/03/2025

  ✅ שלב 2: שליפת פוליסה מהמערכת
     → פוליסה: HLT-2025-88421
     → סטטוס: פעילה
     → תוכנית: בריאות פלוס

  ✅ שלב 3: בדיקת כיסוי
     → אשפוז כירורגי: מכוסה (עד 500,000 ₪) ✅
     → ניתוח: מכוסה (עד 300,000 ₪) ✅
     → בדיקות: מכוסה (עד 15,000 ₪) ✅

  ⚠️ שלב 4: בדיקת תקופת אכשרה
     → פוליסה החלה: 01/01/2025
     → אירוע: 01/03/2025 (חודשיים)
     → אכשרה לאשפוז: 6 חודשים
     → ⚠️ בתוך תקופת אכשרה!
     → 🔍 בדיקה: ניתוח חירום? כן → פטור מאכשרה ✅

  ✅ שלב 5: חישוב סכום
     → סכום מבוקש: 52,750 ₪
     → השתתפות עצמית: 2,950 ₪
     → לתשלום: 49,800 ₪

  ✅ שלב 6: בדיקת הונאה
     → ציון הונאה: 1/10 (נקי)
     → אין דגלים אדומים
     → תביעה ראשונה של המבוטח

  ✅ שלב 7: הכנת החלטה
     → המלצה: לאשר
     → סכום: 49,800 ₪
     → טיוטת מכתב אישור הוכנה

═══════════════════════════════════════════════

📊 סיכום תהליך:
   שלבים שבוצעו: 7/7
   זמן עיבוד: ~15 שניות
   תוצאה: ✅ אישור תביעה
   סכום לתשלום: 49,800 ₪
   דורש אישור אנושי: כן (מעל 10,000 ₪)

═══════════════════════════════════════════════

💡 מה ראינו כאן:
   הסוכן ביצע 7 שלבים אוטונומיים:
   1. חילוץ מידע מטופס (NLP)
   2. שליפה ממערכת (API/Database)
   3. בדיקת כיסוי (חוקים עסקיים)
   4. בדיקת אכשרה (לוגיקה + חריג חירום)
   5. חישוב כספי (מתמטיקה)
   6. בדיקת הונאה (Pattern matching)
   7. יצירת מסמך (NLG)

   בעולם האמיתי - כל שלב יתחבר למערכת אמיתית.
   הסוכן מחליף תהליך שלוקח 30-60 דקות ב-15 שניות.
   ⚠️ עדיין דורש אישור אנושי סופי!
"""


def run_mock_workflow():
    """הרצת תהליך mock עם אנימציה"""
    try:
        from rich.console import Console
        from rich.panel import Panel
        console = Console()
        use_rich = True
    except ImportError:
        use_rich = False

    steps = [
        (1, "חילוץ נתונים מטופס התביעה"),
        (2, "שליפת פוליסה מהמערכת"),
        (3, "בדיקת כיסוי"),
        (4, "בדיקת תקופת אכשרה"),
        (5, "חישוב סכום לתשלום"),
        (6, "בדיקת חשד הונאה"),
        (7, "הכנת החלטה וטיוטת מכתב"),
    ]

    print("\n📥 תביעה חדשה התקבלה: CLM-2025-44291\n")

    for num, title in steps:
        print_step(num, title, "running")
        time.sleep(0.5)
        status = "warning" if num == 4 else "done"
        print_step(num, title, status)

    print(MOCK_WORKFLOW)


def main():
    print_mode_banner()

    try:
        from rich.console import Console
        from rich.panel import Panel
        console = Console()
        console.print(Panel(
            "דמו 7: סוכן רב-שלבי - עיבוד תביעה מקצה לקצה",
            style="bold yellow",
        ))
    except ImportError:
        print("\n=== דמו 7: סוכן רב-שלבי ===\n")

    print("\n🤖 סוכן עיבוד תביעות מופעל...\n")

    if MOCK_MODE:
        run_mock_workflow()
        return

    # מצב חי - שליחת כל השלבים ל-AI
    claim = generate_claim()
    policy = generate_policy()

    system = """אתה סוכן AI לעיבוד תביעות ביטוח בריאות.
עליך לבצע את השלבים הבאים ולהציג את התוצאה של כל שלב:

שלב 1: חילוץ נתונים מהתביעה
שלב 2: בדיקת פוליסה
שלב 3: בדיקת כיסוי לכל פריט
שלב 4: בדיקת תקופת אכשרה (הפוליסה החלה ב-01/01/2025)
שלב 5: חישוב סכום (מבוקש - השתתפות עצמית)
שלב 6: בדיקת הונאה (דגלים אדומים)
שלב 7: המלצה סופית + טיוטת מכתב

לכל שלב הצג: ✅ או ⚠️ ותוצאה קצרה.
בסוף הצג סיכום: שלבים, זמן, תוצאה, סכום."""

    claim_text = f"""
תביעה: {claim['claim_number']}
מבוטח: {claim['insured']}
תאריך: {claim['date']}
סוג: {claim['type']}
תיאור: {claim['description']}
סכום: {format_currency(claim['amount'])}
פירוט: {', '.join(f'{name} ({format_currency(cost)})' for name, cost in claim['items'])}
"""

    policy_text = f"""
פוליסה: {policy['policy_number']}
תחילה: {policy['start_date']}
כיסויים: {', '.join(f"{c['name']} (עד {format_currency(c['max_amount'])})" for c in policy['coverages'])}
"""

    prompt = f"עבד את התביעה הבאה:\n{claim_text}\n\nפוליסה:\n{policy_text}"

    for num, title in [(1, "חילוץ"), (2, "פוליסה"), (3, "כיסוי"),
                        (4, "אכשרה"), (5, "חישוב"), (6, "הונאה"), (7, "החלטה")]:
        print_step(num, title, "running")

    result = call_llm(prompt, system)
    print("\n" + (result or MOCK_WORKFLOW))


if __name__ == "__main__":
    main()
