#!/usr/bin/env python3
"""
דמו 6: עוזר חיתום - הערכת סיכונים מבקשת ביטוח
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from demos.utils.config import call_llm, print_mode_banner, MOCK_MODE
from demos.utils.insurance_data import generate_underwriting_application

MOCK_RESULT = """
📋 דוח חיתום - בקשה לביטוח חיים ובריאות

═══ פרטי מבקש ═══
שם: אבי לוי (בדוי) | גיל: 52 | מגדר: זכר
עיסוק: מהנדס תוכנה
BMI: 28.5 (עודף משקל)
עישון: לשעבר (הפסיק לפני 3 שנים)

═══ ניתוח גורמי סיכון ═══

| גורם סיכון          | ערך              | דירוג   | הערות                        |
|---------------------|------------------|---------|------------------------------|
| גיל                 | 52               | בינוני  | מעל 50 - סיכון מוגבר         |
| BMI                 | 28.5             | בינוני  | עודף משקל, לא השמנה          |
| עישון               | לשעבר (3 שנים)   | נמוך    | הפסקת עישון מפחיתה סיכון     |
| לחץ דם              | 135/85           | בינוני  | גבולי, מטופל תרופתית         |
| כולסטרול כולל       | 220              | בינוני  | מעט מעל הנורמה               |
| LDL                 | 145              | בינוני  | מוגבר, דורש מעקב             |
| HDL                 | 45               | בינוני  | נמוך - גורם סיכון           |
| HbA1c               | 5.8%             | נמוך    | טרום-סוכרת, למעקב            |
| א.ק.ג              | תקין             | נמוך    | ✅                           |
| היסטוריה משפחתית    | אב-MI בגיל 60   | בינוני  | גורם סיכון קרדיווסקולרי     |

═══ סיכום גורמי סיכון ═══
• גורמי סיכון גבוהים: 0
• גורמי סיכון בינוניים: 7
• גורמי סיכון נמוכים: 3

═══ המלצת חיתום ═══

סיווג: מוגבר (Rated)

ביטוח חיים 1,000,000 ₪:
  → לאשר עם תוספת פרמיה של 25%
  → נימוק: גיל 52, היסטוריה משפחתית קרדיווסקולרית,
    פרופיל שומנים מוגבר, עודף משקל

ביטוח בריאות תוכנית פלוס:
  → לאשר עם תוספת פרמיה של 15%
  → ללא חריגות נוספות (יל"ד מטופל ומאוזן)

═══ בדיקות נוספות מומלצות ═══
1. מבחן מאמץ - בשל גיל + גורמי סיכון קרדיווסקולריים
2. בדיקות דם חוזרות: פרופיל שומנים + HbA1c בעוד 3 חודשים

═══ נימוק ═══
המבקש בן 52 עם פרופיל סיכון קרדיווסקולרי בינוני:
יתר לחץ דם מטופל, עודף משקל, פרופיל שומנים מוגבר,
היסטוריה משפחתית של MI, ועבר עישון.
הגורמים המקלים: הפסקת עישון, HbA1c תקין, א.ק.ג תקין,
עיסוק שולחני ללא סיכון תעסוקתי.
אין מניעה לאשר ביטוח עם תוספת פרמיה מתונה.

⚠️ הערה: זוהי המלצה אוטומטית. ההחלטה הסופית בידי חתם מוסמך.
"""


def main():
    print_mode_banner()

    try:
        from rich.console import Console
        from rich.panel import Panel
        console = Console()
        console.print(Panel("דמו 6: עוזר חיתום - הערכת סיכונים", style="bold cyan"))
    except ImportError:
        print("\n=== דמו 6: עוזר חיתום ===\n")

    app = generate_underwriting_application()

    print(f"\n📋 מנתח בקשת ביטוח:")
    print(f"   שם: {app['applicant']['name']}")
    print(f"   גיל: {app['applicant']['age']}")
    print(f"   ביטוח מבוקש: {app['requested_insurance']['type']}")
    print(f"   סכום חיים: {app['requested_insurance']['life_amount']:,} ₪\n")

    if MOCK_MODE:
        print(MOCK_RESULT)
        return

    # בניית טקסט לניתוח
    app_text = f"""
פרטי מבקש:
שם: {app['applicant']['name']}
גיל: {app['applicant']['age']}, {app['applicant']['gender']}
עיסוק: {app['applicant']['occupation']}
עישון: {app['applicant']['smoking']}
BMI: {app['applicant']['bmi']} (גובה {app['applicant']['height_cm']} ס"מ, משקל {app['applicant']['weight_kg']} ק"ג)

ביטוח מבוקש: {app['requested_insurance']['type']}
סכום ביטוח חיים: {app['requested_insurance']['life_amount']:,} ₪
תוכנית בריאות: {app['requested_insurance']['health_plan']}

שאלון בריאות:
מצבים כרוניים: {', '.join(app['health_questionnaire']['chronic_conditions']) or 'אין'}
תרופות: {', '.join(app['health_questionnaire']['medications']) or 'אין'}
ניתוחים: {', '.join(app['health_questionnaire']['surgeries']) or 'אין'}
היסטוריה משפחתית: {', '.join(app['health_questionnaire']['family_history']) or 'אין'}
אשפוזים ב-5 שנים: {', '.join(app['health_questionnaire']['hospitalizations_5y']) or 'אין'}

בדיקות אחרונות:
לחץ דם: {app['recent_tests']['blood_pressure']}
כולסטרול: {app['recent_tests']['cholesterol_total']}
HDL: {app['recent_tests']['hdl']}, LDL: {app['recent_tests']['ldl']}
HbA1c: {app['recent_tests']['hba1c']}%
א.ק.ג: {app['recent_tests']['ecg']}
"""

    system = "אתה חתם ביטוח חיים ובריאות בכיר עם 20 שנות ניסיון בחברת ביטוח ישראלית."
    prompt = f"""הערך את הבקשה הבאה לביטוח חיים ובריאות:

1. נתח כל גורם סיכון בטבלה (גורם, ערך, דירוג, הערות)
2. המלץ על סיווג: סטנדרט / מוגבר / דחייה
3. אם מוגבר - כמה אחוז תוספת פרמיה ולמה
4. האם נדרשות בדיקות נוספות
5. נמק את ההחלטה

{app_text}"""

    print("מנתח בקשה...")
    result = call_llm(prompt, system)
    print(result or MOCK_RESULT)


if __name__ == "__main__":
    main()
