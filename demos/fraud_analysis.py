#!/usr/bin/env python3
"""
מנתח הונאות ביטוח בריאות - נתונים סינתטיים
מייצר נתונים עם דפוסי הונאה מוטמעים ומנתח אותם
"""
import random
import csv
import json
from datetime import datetime, timedelta
from collections import Counter, defaultdict

random.seed(42)

# === DATA GENERATORS ===

FIRST_NAMES = ["יוסי","דני","שרה","רחל","דוד","משה","מיכל","יעל","אורי","נועה",
"איתן","ליאת","אבי","טלי","רון","חנה","גיל","ענת","עמית","שירה",
"בני","דינה","אלון","קרן","ניר","מאיה","זיו","הילה","עידו","לירון"]
LAST_NAMES = ["כהן","לוי","מזרחי","פרץ","ביטון","אברהם","פרידמן","שמעוני","גולדשטיין","דהן",
"אזולאי","רוזנברג","מלכה","חדד","עמר","בן דוד","נחום","יוסף","סבג","אלון"]
CITIES = ["תל אביב","ירושלים","חיפה","באר שבע","ראשון לציון","פתח תקווה","נתניה",
"אשדוד","בני ברק","רמת גן","הרצליה","חולון","רחובות","אשקלון","כפר סבא"]
EMPLOYERS = ["עצמאי","חברת הייטק א","בנק לאומי","עיריית ת\"א","צה\"ל","משרד הבריאות",
"חברת ביטוח ב","אוניברסיטה","בית חולים","חברת תקשורת"]
COVERAGES = ["התייעצות מומחה","רפואה משלימה","פיזיותרפיה","אביזרים רפואיים",
"בדיקות אבחנתיות","שיקום","רפואת שיניים"]
PROVIDERS = ["ד\"ר כהן יוסף","ד\"ר לוי שרה","מכון פיזיו בריא","קליניקת שלום",
"מרכז רפואה משלימה אור","ד\"ר אברהם דוד","מכון MRI צפון",
"קליניקת גב ומפרקים","מרכז דיקור סיני","ד\"ר מזרחי רונית",
"פיזיו פלוס","קליניקת טבע","מכון שיקום הדר","ד\"ר פרידמן אלי",
"מרכז בריאות טוב","קליניקת החלמה"]

def gen_id():
    return f"{random.randint(100000000,399999999)}"

def gen_date(start="2025-01-01", end="2025-12-31"):
    s = datetime.strptime(start,"%Y-%m-%d")
    e = datetime.strptime(end,"%Y-%m-%d")
    d = s + timedelta(days=random.randint(0,(e-s).days))
    return d.strftime("%Y-%m-%d")

def gen_policy_start():
    y = random.choice([2020,2021,2022,2023,2024,2025])
    m = random.randint(1,12)
    return f"{y}-{m:02d}-01"

def generate_claims(n=2000):
    claims = []
    people = []
    # Generate 400 unique people
    for _ in range(400):
        people.append({
            "name": f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}",
            "id": gen_id(),
            "age": random.randint(22,75),
            "city": random.choice(CITIES),
            "employer": random.choice(EMPLOYERS),
            "policy_type": random.choice(["פרטי","קבוצתי"]),
            "policy_start": gen_policy_start(),
            "policy_num": f"POL-{random.randint(100000,999999)}"
        })

    # NORMAL CLAIMS (1600)
    for i in range(1600):
        p = random.choice(people)
        cov = random.choice(COVERAGES)
        provider = random.choice(PROVIDERS)
        amount = random.randint(80,3000)
        claims.append({
            "claim_id": f"CLM-{10000+i}",
            "date": gen_date(),
            "insured_name": p["name"],
            "insured_id": p["id"],
            "age": p["age"],
            "city": p["city"],
            "employer": p["employer"],
            "policy_type": p["policy_type"],
            "policy_start": p["policy_start"],
            "policy_num": p["policy_num"],
            "coverage": cov,
            "provider": provider,
            "amount_claimed": amount,
            "amount_paid": int(amount * random.uniform(0.7,1.0)),
            "fraud_flag": False,
            "fraud_type": ""
        })

    # === FRAUD PATTERN 1: MAX UTILIZER (50 claims) ===
    fraud_person1 = people[0].copy()
    fraud_person1["name"] = "אברהם סבג"
    fraud_person1["id"] = "111111111"
    for i in range(50):
        cov = random.choice(["רפואה משלימה","פיזיותרפיה","התייעצות מומחה"])
        claims.append({
            "claim_id": f"CLM-{11600+i}",
            "date": gen_date(),
            "insured_name": fraud_person1["name"],
            "insured_id": fraud_person1["id"],
            "age": 45,
            "city": "תל אביב",
            "employer": "עצמאי",
            "policy_type": "פרטי",
            "policy_start": "2024-06-01",
            "policy_num": "POL-111111",
            "coverage": cov,
            "provider": "מרכז רפואה משלימה אור",
            "amount_claimed": random.choice([200,200,200,250,200]),
            "amount_paid": 200,
            "fraud_flag": True,
            "fraud_type": "ניצול_מקסימלי"
        })

    # === FRAUD PATTERN 2: PROVIDER RING (80 claims) ===
    ring_provider = "קליניקת שלום"
    ring_employer = "חברת הייטק א"
    for i in range(80):
        p = random.choice([pp for pp in people if pp["employer"]==ring_employer] or [people[1]])
        claims.append({
            "claim_id": f"CLM-{11650+i}",
            "date": gen_date("2025-09-01","2025-11-30"),
            "insured_name": p["name"],
            "insured_id": p["id"],
            "age": p["age"],
            "city": p["city"],
            "employer": ring_employer,
            "policy_type": "קבוצתי",
            "policy_start": p["policy_start"],
            "policy_num": p["policy_num"],
            "coverage": "רפואה משלימה",
            "provider": ring_provider,
            "amount_claimed": random.choice([350,350,350,400,350]),
            "amount_paid": 350,
            "fraud_flag": True,
            "fraud_type": "טבעת_נותן_שירות"
        })

    # === FRAUD PATTERN 3: END OF YEAR RUSH (40 claims) ===
    for i in range(40):
        p = random.choice(people)
        claims.append({
            "claim_id": f"CLM-{11730+i}",
            "date": gen_date("2025-11-15","2025-12-31"),
            "insured_name": p["name"],
            "insured_id": p["id"],
            "age": p["age"],
            "city": p["city"],
            "employer": p["employer"],
            "policy_type": p["policy_type"],
            "policy_start": p["policy_start"],
            "policy_num": p["policy_num"],
            "coverage": random.choice(["רפואה משלימה","פיזיותרפיה"]),
            "provider": random.choice(PROVIDERS),
            "amount_claimed": random.randint(800,2500),
            "amount_paid": random.randint(700,2200),
            "fraud_flag": True,
            "fraud_type": "ריצת_סוף_שנה"
        })

    # === FRAUD PATTERN 4: NEW POLICY IMMEDIATE CLAIMS (30) ===
    for i in range(30):
        claims.append({
            "claim_id": f"CLM-{11770+i}",
            "date": gen_date("2025-02-01","2025-03-15"),
            "insured_name": f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}",
            "insured_id": gen_id(),
            "age": random.randint(30,55),
            "city": random.choice(CITIES),
            "employer": "עצמאי",
            "policy_type": "פרטי",
            "policy_start": "2025-01-15",
            "policy_num": f"POL-NEW{random.randint(100,999)}",
            "coverage": random.choice(["פיזיותרפיה","אביזרים רפואיים","בדיקות אבחנתיות"]),
            "provider": random.choice(PROVIDERS),
            "amount_claimed": random.randint(1500,4000),
            "amount_paid": random.randint(1200,3500),
            "fraud_flag": True,
            "fraud_type": "תביעה_מיידית"
        })

    # === FRAUD PATTERN 5: ROUND AMOUNTS (30) ===
    for i in range(30):
        p = random.choice(people)
        claims.append({
            "claim_id": f"CLM-{11800+i}",
            "date": gen_date(),
            "insured_name": p["name"],
            "insured_id": p["id"],
            "age": p["age"],
            "city": p["city"],
            "employer": p["employer"],
            "policy_type": p["policy_type"],
            "policy_start": p["policy_start"],
            "policy_num": p["policy_num"],
            "coverage": "רפואה משלימה",
            "provider": "מרכז דיקור סיני",
            "amount_claimed": random.choice([500,1000,1500,2000]),
            "amount_paid": random.choice([500,1000,1500,2000]),
            "fraud_flag": True,
            "fraud_type": "סכום_עגול"
        })

    # === FRAUD PATTERN 6: FAMILY CLUSTER (40) ===
    family_last = "גולדשטיין"
    family_addr = "הרצליה"
    family_provider = "קליניקת טבע"
    for i in range(40):
        fname = random.choice(FIRST_NAMES)
        claims.append({
            "claim_id": f"CLM-{11830+i}",
            "date": gen_date("2025-03-01","2025-05-31"),
            "insured_name": f"{fname} {family_last}",
            "insured_id": f"22{random.randint(1000000,9999999)}",
            "age": random.randint(18,70),
            "city": family_addr,
            "employer": "עצמאי",
            "policy_type": "פרטי",
            "policy_start": "2024-01-01",
            "policy_num": f"POL-GLD{random.randint(10,99)}",
            "coverage": "רפואה משלימה",
            "provider": family_provider,
            "amount_claimed": random.choice([300,350,300,350]),
            "amount_paid": 300,
            "fraud_flag": True,
            "fraud_type": "אשכול_משפחתי"
        })

    random.shuffle(claims)
    return claims


# === ANALYSIS ENGINE ===

def analyze(claims):
    results = {"alerts": [], "stats": {}}

    # Basic stats
    total = len(claims)
    total_claimed = sum(c["amount_claimed"] for c in claims)
    total_paid = sum(c["amount_paid"] for c in claims)
    results["stats"] = {
        "total_claims": total,
        "total_claimed": total_claimed,
        "total_paid": total_paid,
        "unique_insured": len(set(c["insured_id"] for c in claims)),
        "unique_providers": len(set(c["provider"] for c in claims)),
    }

    # 1. HIGH FREQUENCY per insured
    by_person = defaultdict(list)
    for c in claims:
        by_person[c["insured_id"]].append(c)
    avg_claims = total / len(by_person)
    for pid, pclaims in by_person.items():
        if len(pclaims) >= avg_claims * 4:
            results["alerts"].append({
                "type": "תדירות_חריגה",
                "severity": "גבוה",
                "title": f"{pclaims[0]['insured_name']} - {len(pclaims)} תביעות",
                "detail": f"ממוצע: {avg_claims:.0f} תביעות. מבוטח זה: {len(pclaims)}. סה\"כ נתבע: {sum(x['amount_claimed'] for x in pclaims):,} ₪",
                "insured": pclaims[0]["insured_name"],
                "count": len(pclaims),
            })

    # 2. PROVIDER CONCENTRATION
    by_provider = defaultdict(list)
    for c in claims:
        by_provider[c["provider"]].append(c)
    for prov, pclaims in by_provider.items():
        pct = len(pclaims)/total*100
        if pct > 5:
            employers = Counter(c["employer"] for c in pclaims)
            top_emp = employers.most_common(1)[0]
            results["alerts"].append({
                "type": "ריכוז_נותן_שירות",
                "severity": "גבוה" if pct > 8 else "בינוני",
                "title": f"{prov} - {len(pclaims)} תביעות ({pct:.1f}%)",
                "detail": f"מעסיק דומיננטי: {top_emp[0]} ({top_emp[1]} תביעות, {top_emp[1]/len(pclaims)*100:.0f}%)",
                "provider": prov,
                "count": len(pclaims),
            })

    # 3. SAME AMOUNT from provider
    for prov, pclaims in by_provider.items():
        amounts = [c["amount_claimed"] for c in pclaims]
        if len(amounts) >= 10:
            most_common_amt, cnt = Counter(amounts).most_common(1)[0]
            if cnt/len(amounts) > 0.6:
                results["alerts"].append({
                    "type": "סכום_אחיד",
                    "severity": "בינוני",
                    "title": f"{prov} - {cnt}/{len(amounts)} תביעות בסכום {most_common_amt} ₪",
                    "detail": f"{cnt/len(amounts)*100:.0f}% מהתביעות באותו סכום בדיוק",
                    "provider": prov,
                })

    # 4. ROUND AMOUNTS
    round_claims = [c for c in claims if c["amount_claimed"] % 500 == 0 and c["amount_claimed"] >= 500]
    if len(round_claims)/total > 0.03:
        by_prov_round = Counter(c["provider"] for c in round_claims)
        top = by_prov_round.most_common(3)
        results["alerts"].append({
            "type": "סכומים_עגולים",
            "severity": "בינוני",
            "title": f"{len(round_claims)} תביעות בסכומים עגולים (כפולות 500)",
            "detail": f"נותני שירות: {', '.join(f'{p[0]} ({p[1]})' for p in top)}",
        })

    # 5. END OF YEAR RUSH
    eoy = [c for c in claims if c["date"] >= "2025-11-01"]
    other_months = [c for c in claims if c["date"] < "2025-11-01"]
    monthly_avg = len(other_months) / 10 if other_months else 1
    eoy_monthly = len(eoy) / 2
    if eoy_monthly > monthly_avg * 1.5:
        results["alerts"].append({
            "type": "ריצת_סוף_שנה",
            "severity": "בינוני",
            "title": f"עלייה של {eoy_monthly/monthly_avg*100-100:.0f}% בתביעות נוב-דצמ",
            "detail": f"ממוצע חודשי: {monthly_avg:.0f}. נוב-דצמ ממוצע: {eoy_monthly:.0f}",
        })

    # 6. NEW POLICY QUICK CLAIMS
    quick = []
    for c in claims:
        try:
            ps = datetime.strptime(c["policy_start"],"%Y-%m-%d")
            cd = datetime.strptime(c["date"],"%Y-%m-%d")
            if (cd - ps).days <= 60 and (cd - ps).days >= 0:
                quick.append(c)
        except:
            pass
    if len(quick) > 20:
        results["alerts"].append({
            "type": "תביעה_מיידית",
            "severity": "גבוה",
            "title": f"{len(quick)} תביעות תוך 60 יום מתחילת פוליסה",
            "detail": f"סה\"כ סכום: {sum(c['amount_claimed'] for c in quick):,} ₪. ממוצע: {sum(c['amount_claimed'] for c in quick)//len(quick):,} ₪",
        })

    # 7. FAMILY CLUSTERS (same last name + city + provider)
    by_family = defaultdict(list)
    for c in claims:
        last = c["insured_name"].split()[-1] if " " in c["insured_name"] else ""
        key = f"{last}|{c['city']}|{c['provider']}"
        by_family[key].append(c)
    for key, fclaims in by_family.items():
        parts = key.split("|")
        unique_ids = len(set(c["insured_id"] for c in fclaims))
        if unique_ids >= 3 and len(fclaims) >= 8:
            results["alerts"].append({
                "type": "אשכול_משפחתי",
                "severity": "גבוה",
                "title": f"משפחת {parts[0]} - {unique_ids} מבוטחים, {len(fclaims)} תביעות",
                "detail": f"עיר: {parts[1]}, נותן שירות: {parts[2]}",
            })

    # Sort by severity
    sev_order = {"גבוה":0,"בינוני":1,"נמוך":2}
    results["alerts"].sort(key=lambda x: sev_order.get(x["severity"],9))

    # Monthly distribution
    monthly = defaultdict(int)
    for c in claims:
        m = c["date"][:7]
        monthly[m] += 1
    results["monthly"] = dict(sorted(monthly.items()))

    # Coverage distribution
    cov_dist = Counter(c["coverage"] for c in claims)
    results["coverage_dist"] = dict(cov_dist.most_common())

    # Top providers
    prov_dist = Counter(c["provider"] for c in claims)
    results["top_providers"] = dict(prov_dist.most_common(10))

    return results


# === MAIN ===
if __name__ == "__main__":
    print("מייצר 1,870 תביעות סינתטיות...")
    claims = generate_claims()

    # Save CSV
    csv_path = "/home/user/Insurance/demos/claims_2025.csv"
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=claims[0].keys())
        w.writeheader()
        w.writerows(claims)
    print(f"נשמר CSV: {csv_path}")

    # Analyze
    print("מנתח דפוסי הונאה...")
    results = analyze(claims)

    # Save JSON
    json_path = "/home/user/Insurance/demos/fraud_results.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"נשמר JSON: {json_path}")

    # Print summary
    print(f"\n{'='*50}")
    print(f"סה\"כ תביעות: {results['stats']['total_claims']:,}")
    print(f"סה\"כ נתבע: {results['stats']['total_claimed']:,} ₪")
    print(f"סה\"כ שולם: {results['stats']['total_paid']:,} ₪")
    print(f"מבוטחים ייחודיים: {results['stats']['unique_insured']}")
    print(f"נותני שירות: {results['stats']['unique_providers']}")
    print(f"\n🚨 התראות: {len(results['alerts'])}")
    for a in results["alerts"]:
        icon = "🔴" if a["severity"]=="גבוה" else "🟡"
        print(f"  {icon} [{a['type']}] {a['title']}")
        print(f"     {a['detail']}")
