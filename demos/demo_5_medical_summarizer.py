#!/usr/bin/env python3
"""
דמו 5: סיכום מסמכים רפואיים + מיפוי לכיסוי ביטוחי
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from demos.utils.config import call_llm, print_mode_banner, MOCK_MODE
from demos.utils.insurance_data import generate_medical_report

MOCK_RESULT = """
🏥 ניתוח מסמך רפואי

═══ פרטי מטופל ═══
שם: שרה כהן (בדוי) | גיל: 58 | אשפוז: 6 ימים

═══ אבחנות ═══

| # | אבחנה                              | ICD-10 | חומרה |
|---|-------------------------------------|--------|-------|
| 1 | אוטם שריר הלב חריף (NSTEMI)        | I21.4  | גבוהה |
| 2 | סוכרת סוג 2 לא מאוזנת              | E11.65 | בינונית|
| 3 | יתר לחץ דם לא מאוזן                | I10    | בינונית|

═══ טיפולים שבוצעו ═══
• צנתור לבבי (Coronary Angiography)
• PCI + הצבת סטנט מצופה תרופה (DES) ב-LAD
• אקו לב - EF 45%

═══ תרופות בשחרור (8 תרופות) ═══
1. Aspirin 100mg - קבוע
2. Clopidogrel 75mg - 12 חודשים
3. Atorvastatin 80mg - הגדלת מינון
4. Metoprolol 25mg x2 - חדש
5. Ramipril 2.5mg - חדש
6. Metformin 1000mg x2 - ללא שינוי
7. Empagliflozin 10mg - חדש
8. Pantoprazole 20mg - חדש

═══ מצבים רפואיים קודמים (Pre-existing) ═══
⚠️ סוכרת סוג 2 - מאובחנת מ-2018
⚠️ יתר לחץ דם - מאובחן מ-2015
⚠️ היפרליפידמיה - מאובחנת מ-2016

═══ רלוונטיות לכיסוי ביטוחי ═══

| טיפול/פרוצדורה         | סיווג          | הערות לכיסוי                    |
|------------------------|---------------|--------------------------------|
| צנתור + PCI + סטנט      | אשפוז כירורגי | מכוסה - ניתוח חירום, ללא אכשרה  |
| אשפוז 6 ימים           | אשפוז          | מכוסה                          |
| אקו לב                 | בדיקה אבחנתית | מכוסה                          |
| Clopidogrel 12 חודשים   | תרופה          | ⚠️ לבדוק אם בסל הבריאות       |
| Empagliflozin           | תרופה          | ⚠️ לבדוק אם בסל הבריאות       |
| שיקום לבבי              | שיקום          | מכוסה - עד 50,000 ₪            |

💡 המלצה: לאשר כיסוי מלא לאשפוז ולפרוצדורות.
   לבדוק כיסוי תרופתי עבור Clopidogrel ו-Empagliflozin.
   ⚠️ מצבים קודמים: אם הפוליסה פעילה מעל 24 חודשים - אין חריגה.
"""


def main():
    print_mode_banner()

    try:
        from rich.console import Console
        from rich.panel import Panel
        console = Console()
        console.print(Panel("דמו 5: ניתוח מסמך רפואי + מיפוי לכיסוי ביטוחי", style="bold magenta"))
    except ImportError:
        print("\n=== דמו 5: ניתוח מסמך רפואי ===\n")

    medical_report = generate_medical_report()
    print(f"\n📄 מנתח סיכום רפואי ({len(medical_report)} תווים)...\n")

    if MOCK_MODE:
        print(MOCK_RESULT)
        return

    system = "אתה רופא בודק תביעות בחברת ביטוח בריאות ישראלית עם ניסיון של 15 שנה."
    prompt = f"""נתח את הסיכום הרפואי הבא וחלץ מידע מובנה:

1. **אבחנות** - טבלה עם: אבחנה, קוד ICD-10, חומרה
2. **טיפולים שבוצעו** - רשימה ממוספרת
3. **תרופות בשחרור** - שם, מינון, חדש/קיים
4. **מצבים רפואיים קודמים** - רשימה עם תאריכי אבחון
5. **רלוונטיות לכיסוי ביטוחי** - טבלה: טיפול, סיווג, הערות לכיסוי
6. **המלצה** - מה לאשר ומה לבדוק

{medical_report}"""

    result = call_llm(prompt, system)
    print(result or MOCK_RESULT)


if __name__ == "__main__":
    main()
