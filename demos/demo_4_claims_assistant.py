#!/usr/bin/env python3
"""
דמו 4: עוזר תביעות - הערכה ראשונית של תביעה מול פוליסה
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from demos.utils.config import call_llm, print_mode_banner, MOCK_MODE
from demos.utils.insurance_data import generate_claim, generate_policy
from demos.utils.hebrew_utils import format_currency

MOCK_RESULT = """
📋 הערכת תביעה - CLM-2025-44291

═══ פרטי התביעה ═══
מספר: CLM-2025-44291
מבוטח: ישראל ישראלי
תאריך אירוע: 01/03/2025
סוג: אשפוז + ניתוח
סכום מבוקש: 52,750 ₪

═══ בדיקת כיסוי ═══

| פריט                   | סכום      | מכוסה? | הערות                    |
|------------------------|----------|--------|--------------------------|
| בדיקת CT בטן           | 2,500 ₪  | ✅ כן  | כיסוי בדיקות אבחנתיות   |
| בדיקות דם              | 800 ₪    | ✅ כן  | כלול באשפוז              |
| ניתוח לפרוסקופי        | 35,000 ₪ | ✅ כן  | כיסוי ניתוחים            |
| הרדמה כללית            | 8,000 ₪  | ✅ כן  | כלול בכיסוי ניתוח        |
| אשפוז 3 ימים           | 4,500 ₪  | ✅ כן  | כיסוי אשפוז כירורגי     |
| תרופות                 | 1,200 ₪  | ✅ כן  | כלול באשפוז              |
| ביקור מעקב             | 750 ₪    | ✅ כן  | כיסוי מומחים             |

═══ חישוב ═══
סכום מבוקש: 52,750 ₪
אשפוז + ניתוח - השתתפות עצמית: 2,500 ₪
בדיקת CT - השתתפות עצמית: 300 ₪
ביקור מעקב - השתתפות עצמית: 150 ₪

סה"כ השתתפות עצמית: 2,950 ₪
סה"כ לתשלום למבוטח: 49,800 ₪

═══ בדיקות נוספות ═══
⚠️ תקופת אכשרה: הפוליסה החלה ב-01/01/2025, האירוע ב-01/03/2025 (חודשיים).
   תקופת אכשרה לאשפוז כירורגי: 6 חודשים.
   אולם - זהו ניתוח חירום (דלקת תוספתן חריפה) → פטור מאכשרה! ✅

🔍 דגלי הונאה: לא זוהו דגלים חשודים ✅

═══ המלצה ═══
✅ לאשר תביעה בסך 49,800 ₪
(ניתוח חירום, מכוסה בפוליסה, ללא דגלים חשודים)
"""


def main():
    print_mode_banner()

    try:
        from rich.console import Console
        from rich.panel import Panel
        console = Console()
        use_rich = True
    except ImportError:
        use_rich = False

    claim = generate_claim()
    policy = generate_policy()

    if use_rich:
        console.print(Panel("דמו 4: עוזר תביעות - הערכה ראשונית", style="bold green"))
        console.print(f"\n[bold]תביעה:[/bold] {claim['claim_number']}")
        console.print(f"[bold]סוג:[/bold] {claim['type']}")
        console.print(f"[bold]סכום:[/bold] {format_currency(claim['amount'])}\n")
    else:
        print("\n=== דמו 4: עוזר תביעות ===")
        print(f"תביעה: {claim['claim_number']}")
        print(f"סוג: {claim['type']}")
        print(f"סכום: {format_currency(claim['amount'])}\n")

    if MOCK_MODE:
        print(MOCK_RESULT)
        return

    # בניית טקסט תביעה ופוליסה
    claim_text = f"""
תביעה {claim['claim_number']}:
מבוטח: {claim['insured']}
פוליסה: {claim['policy_number']}
תאריך: {claim['date']}
סוג: {claim['type']}
תיאור: {claim['description']}
סכום כולל: {format_currency(claim['amount'])}
פירוט:
"""
    for item_name, item_cost in claim["items"]:
        claim_text += f"  - {item_name}: {format_currency(item_cost)}\n"

    policy_text = f"""
פוליסה {policy['policy_number']}:
תוקף: {policy['start_date']} - {policy['end_date']}
כיסויים:
"""
    for cov in policy["coverages"]:
        policy_text += f"  - {cov['name']}: עד {format_currency(cov['max_amount'])}, "
        policy_text += f"השתתפות {format_currency(cov['deductible'])}, "
        policy_text += f"אכשרה {cov['waiting_months']} חודשים\n"

    system = "אתה בודק תביעות ביטוח בריאות מנוסה בחברת ביטוח ישראלית."
    prompt = f"""בצע הערכה ראשונית של התביעה מול הפוליסה:

1. בדוק לכל פריט - האם מכוסה בפוליסה
2. חשב השתתפות עצמית וסכום לתשלום
3. בדוק תקופות אכשרה
4. זהה דגלים אדומים
5. תן המלצה: לאשר / לדחות / לבדוק

תביעה:
{claim_text}

פוליסה:
{policy_text}"""

    print("מעריך תביעה...")
    result = call_llm(prompt, system)
    print("\n" + (result or MOCK_RESULT))


if __name__ == "__main__":
    main()
