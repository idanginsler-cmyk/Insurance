#!/usr/bin/env python3
"""
דמו 2: זיהוי הונאות ביטוח עם AI
מנתח תביעות ומזהה דפוסים חשודים
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from demos.utils.config import call_llm, print_mode_banner, MOCK_MODE
from demos.utils.insurance_data import generate_suspicious_claims
from demos.utils.hebrew_utils import format_currency

MOCK_RESULT = """
🔍 דוח זיהוי הונאות - 4 תביעות נבדקו

═══════════════════════════════════════════════════

📄 תביעה CLM-2025-11111 | דוד לוי | 85,000 ₪
   סוג: ניתוח ברך | תאריך: ינואר 2025

   🚩 דגלים אדומים:
   1. [גבוה] תביעה 45 יום בלבד אחרי תחילת פוליסה
   2. [בינוני] ניתוח אלקטיבי (לא חירום) - מעלה חשד לתכנון מראש
   3. [בינוני] סכום גבוה (85,000 ₪) לתביעה ראשונה

   ציון הונאה: 7/10 🔴
   המלצה: ⚠️ להעביר לחקירה

═══════════════════════════════════════════════════

📄 תביעה CLM-2025-22222 | רחל כהן | 42,000 ₪
   סוג: אשפוז | תאריך: פברואר 2025

   🚩 דגלים אדומים:
   1. [בינוני] תביעה שלישית ב-6 חודשים - תדירות גבוהה
   2. [נמוך] אותו בית חולים בכל התביעות

   ציון הונאה: 5/10 🟡
   המלצה: ⚠️ לבדוק - לבקש מסמכים נוספים

═══════════════════════════════════════════════════

📄 תביעה CLM-2025-33333 | משה אברהם | 4,500 ₪
   סוג: בדיקות + ביקור מומחה | תאריך: מרץ 2025

   🚩 דגלים אדומים: אין

   ציון הונאה: 1/10 🟢
   המלצה: ✅ לאשר - תביעה תקינה

═══════════════════════════════════════════════════

📄 תביעה CLM-2025-44444 | יעל שמעון | 65,000 ₪
   סוג: ניתוח אף | תאריך: פברואר 2025

   🚩 דגלים אדומים:
   1. [גבוה] 26 יום בלבד אחרי תחילת פוליסה!
   2. [גבוה] מרכיב קוסמטי - ייתכן שלא מכוסה
   3. [בינוני] סכום גבוה (65,000 ₪)

   ציון הונאה: 8/10 🔴
   המלצה: ⛔ להעביר לחקירה מיידית

═══════════════════════════════════════════════════

📊 סיכום:
   ✅ תקינות: 1 (25%)
   ⚠️ לבדיקה: 1 (25%)
   🔴 לחקירה: 2 (50%)
"""


def analyze_claims_locally(claims):
    """ניתוח תביעות מקומי - ללא AI"""
    from datetime import datetime

    for claim in claims:
        # חישוב ימים מתחילת פוליסה
        start = datetime.strptime(claim["policy_start"], "%d/%m/%Y")
        claim_date = datetime.strptime(claim["claim_date"], "%d/%m/%Y")
        days_since_start = (claim_date - start).days
        claim["days_since_policy_start"] = days_since_start

        # דגלים אוטומטיים
        if days_since_start < 60:
            if "תביעה מוקדמת" not in [f for f in claim["flags"]]:
                claim["flags"].append(f"תביעה {days_since_start} יום אחרי תחילת פוליסה")

    return claims


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

    claims = generate_suspicious_claims()

    if use_rich:
        console.print(Panel("דמו 2: זיהוי הונאות ביטוח עם AI", style="bold red"))
        console.print(f"\n[bold]בודק {len(claims)} תביעות...[/bold]\n")
    else:
        print("\n=== דמו 2: זיהוי הונאות ביטוח עם AI ===")
        print(f"בודק {len(claims)} תביעות...\n")

    if MOCK_MODE:
        print(MOCK_RESULT)
        return

    # מצב חי
    claims_text = ""
    for c in claims:
        claims_text += f"""
תביעה {c['claim_number']}:
- מבוטח: {c['insured']}
- תחילת פוליסה: {c['policy_start']}
- תאריך תביעה: {c['claim_date']}
- סוג: {c['type']}
- סכום: {format_currency(c['amount'])}
- תיאור: {c['description']}
---
"""

    system = "אתה חוקר הונאות ביטוח מנוסה. תפקידך לזהות דפוסים חשודים בתביעות."
    prompt = f"""נתח את התביעות הבאות וזהה דגלים אדומים לחשד הונאה.

לכל תביעה:
1. ציין דגלים אדומים (אם יש)
2. דרג חומרה: נמוך/בינוני/גבוה
3. תן ציון הונאה 1-10
4. המלצה: לאשר / לבדוק / להעביר לחקירה

שים לב במיוחד ל:
- תביעות סמוך לתחילת פוליסה
- תדירות תביעות גבוהה
- סכומים חריגים
- ניתוחים אלקטיביים מיד אחרי רכישת ביטוח
- מרכיבים קוסמטיים

{claims_text}"""

    print("מנתח תביעות...")
    result = call_llm(prompt, system)
    if result:
        print("\n" + result)
    else:
        print(MOCK_RESULT)


if __name__ == "__main__":
    main()
