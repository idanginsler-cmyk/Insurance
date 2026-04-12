"""
מחולל נתוני ביטוח סינתטיים בעברית
כל הנתונים בדויים לחלוטין - אין כאן מידע אמיתי
"""
import random
from datetime import datetime, timedelta


def generate_policy() -> dict:
    """יצירת פוליסת ביטוח בריאות סינתטית"""
    return {
        "policy_number": f"HLT-2025-{random.randint(10000, 99999)}",
        "type": "ביטוח בריאות פרטי - תוכנית בריאות פלוס",
        "insured": {
            "name": "ישראל ישראלי",
            "id": "000-000-000",
            "birth_date": "15/03/1980",
            "age": 45,
        },
        "start_date": "01/01/2025",
        "end_date": "31/12/2025",
        "premium_monthly": 850,
        "coverages": [
            {"name": "אשפוז כירורגי", "max_amount": 500000, "deductible": 2500, "waiting_months": 6},
            {"name": "ניתוחים בישראל", "max_amount": 300000, "deductible": 1500, "waiting_months": 6},
            {"name": "התייעצות עם מומחים", "max_amount": 2000, "deductible": 150, "waiting_months": 3},
            {"name": "בדיקות אבחנתיות", "max_amount": 15000, "deductible": 300, "waiting_months": 3},
            {"name": "תרופות שלא בסל", "max_amount": 100000, "deductible": 200, "waiting_months": 12},
            {"name": "רפואה משלימה", "max_amount": 3000, "deductible": 50, "waiting_months": 3},
        ],
        "exclusions": [
            "טיפולי שיניים",
            "ניתוחים קוסמטיים",
            "ספורט אתגרי",
            "מצבים רפואיים קודמים (24 חודשים)",
            "טיפולים בחו\"ל",
        ],
    }


def generate_claim() -> dict:
    """יצירת תביעת ביטוח סינתטית"""
    claim_types = [
        {
            "type": "אשפוז + ניתוח",
            "description": "ניתוח כריתת תוספתן לפרוסקופי עקב דלקת חריפה",
            "hospital": "בית החולים הדוגמה",
            "amount": 52750,
            "items": [
                ("בדיקת CT בטן", 2500),
                ("בדיקות דם", 800),
                ("ניתוח לפרוסקופי", 35000),
                ("הרדמה כללית", 8000),
                ("אשפוז 3 ימים", 4500),
                ("תרופות", 1200),
                ("ביקור מעקב", 750),
            ],
        },
        {
            "type": "ביקור מומחה",
            "description": "התייעצות עם קרדיולוג - כאבים בחזה",
            "hospital": "מרפאת מומחים",
            "amount": 1200,
            "items": [
                ("ביקור קרדיולוג", 850),
                ("א.ק.ג", 350),
            ],
        },
        {
            "type": "בדיקות אבחנתיות",
            "description": "MRI ברך שמאל - חשד לקרע מניסקוס",
            "hospital": "מכון הדמיה",
            "amount": 3200,
            "items": [
                ("MRI ברך", 3200),
            ],
        },
    ]
    claim = random.choice(claim_types)
    claim["claim_number"] = f"CLM-2025-{random.randint(10000, 99999)}"
    claim["date"] = (datetime.now() - timedelta(days=random.randint(1, 60))).strftime("%d/%m/%Y")
    claim["insured"] = "ישראל ישראלי"
    claim["policy_number"] = f"HLT-2025-{random.randint(10000, 99999)}"
    return claim


def generate_medical_report() -> str:
    """יצירת סיכום רפואי סינתטי"""
    return """
סיכום רפואי - מכתב שחרור (מסמך סינתטי)

מטופל: שרה כהן (שם בדוי), בת 58
תאריך אשפוז: 10/02/2025 - 16/02/2025

רקע: סוכרת סוג 2 (מ-2018), יתר לחץ דם (מ-2015), היפרליפידמיה.
תרופות קבועות: Metformin 1000mg x2, Amlodipine 5mg, Atorvastatin 40mg, Aspirin 100mg.

אבחנות:
1. NSTEMI - אוטם שריר הלב חריף (ICD-10: I21.4)
2. סוכרת סוג 2 לא מאוזנת (ICD-10: E11.65, HbA1c: 8.9%)
3. יתר לחץ דם לא מאוזן (ICD-10: I10)

מהלך: צנתור לבבי - היצרות 85% ב-LAD. בוצע PCI + הצבת DES בהצלחה.
אקו לב: EF 45%.

טיפול בשחרור: Aspirin, Clopidogrel (12 חודשים), Atorvastatin 80mg,
Metoprolol 25mg x2, Ramipril 2.5mg, Metformin, Empagliflozin 10mg.

המלצות: שיקום לבבי, מעקב קרדיולוג, הפסקת עישון, דיאטה.
אי-כושר: 30 יום.
""".strip()


def generate_suspicious_claims() -> list:
    """יצירת רשימת תביעות עם דפוסים חשודים"""
    return [
        {
            "claim_number": "CLM-2025-11111",
            "insured": "דוד לוי (בדוי)",
            "policy_start": "01/12/2024",
            "claim_date": "15/01/2025",
            "type": "ניתוח ברך",
            "amount": 85000,
            "description": "ניתוח החלפת מפרק ברך ימין",
            "flags": ["תביעה 45 יום אחרי תחילת פוליסה", "ניתוח אלקטיבי"],
            "fraud_score": 7,
        },
        {
            "claim_number": "CLM-2025-22222",
            "insured": "רחל כהן (בדוי)",
            "policy_start": "01/01/2023",
            "claim_date": "20/02/2025",
            "type": "אשפוז",
            "amount": 42000,
            "description": "אשפוז עקב כאבי בטן חריפים",
            "flags": ["תביעה שלישית ב-6 חודשים", "אותו בית חולים"],
            "fraud_score": 5,
        },
        {
            "claim_number": "CLM-2025-33333",
            "insured": "משה אברהם (בדוי)",
            "policy_start": "01/06/2024",
            "claim_date": "01/03/2025",
            "type": "בדיקות + ביקור מומחה",
            "amount": 4500,
            "description": "בדיקת MRI גב + ביקור אורתופד",
            "flags": [],
            "fraud_score": 1,
        },
        {
            "claim_number": "CLM-2025-44444",
            "insured": "יעל שמעון (בדוי)",
            "policy_start": "15/01/2025",
            "claim_date": "10/02/2025",
            "type": "ניתוח אף",
            "amount": 65000,
            "description": "ניתוח אף - תיקון מחיצה + אסתטיקה",
            "flags": ["26 יום אחרי תחילת פוליסה", "מרכיב קוסמטי", "סכום גבוה"],
            "fraud_score": 8,
        },
    ]


def generate_underwriting_application() -> dict:
    """יצירת בקשה לביטוח עם שאלון בריאות סינתטי"""
    return {
        "applicant": {
            "name": "אבי לוי (בדוי)",
            "id": "000-000-002",
            "age": 52,
            "gender": "זכר",
            "occupation": "מהנדס תוכנה",
            "smoking": "לשעבר (הפסיק לפני 3 שנים)",
            "bmi": 28.5,
            "height_cm": 175,
            "weight_kg": 87,
        },
        "requested_insurance": {
            "type": "ביטוח חיים + בריאות",
            "life_amount": 1000000,
            "health_plan": "פלוס",
        },
        "health_questionnaire": {
            "chronic_conditions": ["יתר לחץ דם - מטופל מ-2020"],
            "medications": ["Amlodipine 5mg יומי"],
            "surgeries": ["כריתת שקדים (1995)"],
            "family_history": ["אב - אוטם שריר הלב בגיל 60", "אם - סוכרת סוג 2"],
            "hospitalizations_5y": [],
            "mental_health": "לא",
            "disabilities": "לא",
        },
        "recent_tests": {
            "blood_pressure": "135/85",
            "cholesterol_total": 220,
            "hdl": 45,
            "ldl": 145,
            "hba1c": 5.8,
            "ecg": "תקין",
        },
    }
