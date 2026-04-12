#!/usr/bin/env python3
"""
דמו 1: ניתוח פוליסת ביטוח עם AI
מחלץ כיסויים, סכומים, חריגות ותנאים מפוליסה
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from demos.utils.config import call_llm, print_mode_banner, MOCK_MODE
from demos.utils.insurance_data import generate_policy
from demos.utils.hebrew_utils import format_currency

# תוצאה לדוגמה למצב mock
MOCK_RESULT = """
📋 ניתוח פוליסת ביטוח בריאות - HLT-2025-88421

┌─────────────────────────────────────────────────────┐
│ פרטי פוליסה                                         │
├─────────────────────────────────────────────────────┤
│ מספר: HLT-2025-88421                                │
│ סוג: ביטוח בריאות פרטי - תוכנית בריאות פלוס         │
│ תוקף: 01/01/2025 - 31/12/2025                      │
│ פרמיה חודשית: 850 ₪                                 │
└─────────────────────────────────────────────────────┘

📊 כיסויים עיקריים:

| כיסוי                    | סכום מקסימלי | השתתפות עצמית | אכשרה    |
|--------------------------|-------------|--------------|----------|
| אשפוז כירורגי            | 500,000 ₪   | 2,500 ₪      | 6 חודשים |
| ניתוחים בישראל           | 300,000 ₪   | 1,500 ₪      | 6 חודשים |
| התייעצות עם מומחים       | 2,000 ₪     | 150 ₪        | 3 חודשים |
| בדיקות אבחנתיות          | 15,000 ₪    | 300 ₪        | 3 חודשים |
| תרופות שלא בסל           | 100,000 ₪   | 200 ₪        | 12 חודשים|
| רפואה משלימה             | 3,000 ₪     | 50 ₪         | 3 חודשים |

🚫 חריגות עיקריות:
1. טיפולי שיניים (למעט תאונה)
2. ניתוחים קוסמטיים
3. ספורט אתגרי (ללא הרחבה)
4. מצבים רפואיים קודמים - 24 חודשים ראשונים
5. טיפולים בחו"ל (ללא הרחבה)

⚠️ נקודות לתשומת לב:
• תקופת אכשרה של 12 חודשים לתרופות - ארוכה מהממוצע בשוק
• חריגת pre-existing של 24 חודשים - סטנדרטי
• השתתפות עצמית באשפוז (2,500 ₪) - בטווח הבינוני
• אין כיסוי לטיפולי שיניים - שכיח בפוליסות בסיסיות
"""


def main():
    print_mode_banner()

    try:
        from rich.console import Console
        from rich.table import Table
        from rich.panel import Panel
        console = Console()
        use_rich = True
    except ImportError:
        use_rich = False

    # יצירת נתוני פוליסה סינתטיים
    policy = generate_policy()

    if use_rich:
        console.print(Panel("דמו 1: ניתוח פוליסת ביטוח עם AI", style="bold blue"))
        console.print(f"\n[bold]מנתח פוליסה:[/bold] {policy['policy_number']}")
        console.print(f"[bold]מבוטח:[/bold] {policy['insured']['name']}")
        console.print(f"[bold]פרמיה:[/bold] {format_currency(policy['premium_monthly'])}/חודש\n")
    else:
        print("\n=== דמו 1: ניתוח פוליסת ביטוח עם AI ===")
        print(f"מנתח פוליסה: {policy['policy_number']}")
        print(f"מבוטח: {policy['insured']['name']}")
        print(f"פרמיה: {format_currency(policy['premium_monthly'])}/חודש\n")

    if MOCK_MODE:
        print(MOCK_RESULT)
        return

    # מצב חי - שליחה ל-AI
    policy_text = f"""
פוליסת ביטוח בריאות מספר {policy['policy_number']}
סוג: {policy['type']}
תוקף: {policy['start_date']} - {policy['end_date']}
פרמיה חודשית: {policy['premium_monthly']} ₪

כיסויים:
"""
    for cov in policy["coverages"]:
        policy_text += f"- {cov['name']}: עד {format_currency(cov['max_amount'])}, "
        policy_text += f"השתתפות עצמית {format_currency(cov['deductible'])}, "
        policy_text += f"אכשרה {cov['waiting_months']} חודשים\n"

    policy_text += "\nחריגות:\n"
    for exc in policy["exclusions"]:
        policy_text += f"- {exc}\n"

    system = "אתה מומחה ביטוח בריאות ישראלי עם 20 שנות ניסיון."
    prompt = f"""נתח את פוליסת הביטוח הבאה וצור סיכום מובנה:

1. פרטי הפוליסה
2. טבלת כיסויים (כיסוי, סכום, השתתפות עצמית, אכשרה)
3. חריגות עיקריות
4. נקודות לתשומת לב - סעיפים חריגים או שכדאי לשים אליהם לב

{policy_text}"""

    print("שולח לניתוח AI...")
    result = call_llm(prompt, system)
    if result:
        print("\n" + result)
    else:
        print("שגיאה בתקשורת עם AI. מציג תוצאה לדוגמה:")
        print(MOCK_RESULT)


if __name__ == "__main__":
    main()
