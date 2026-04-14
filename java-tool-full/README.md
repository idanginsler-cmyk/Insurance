# 🔍 מנתח הונאות מלא - Java

**גרסה מלאה** עם 11 טאבים אינטראקטיביים.

## מה הכלי עושה

קורא CSV של תביעות ומייצר דשבורד HTML עם:

1. **📊 סקירה** - סטטיסטיקות + התראות חמורות
2. **🚨 כל ההתראות** - 19+ התראות מדורגות
3. **🎯 דירוג מבוטחים** - ציון סיכון 1-100 לכל מבוטח
4. **🏥 נותני שירות** - ריכוז, מעסיק דומיננטי, סיכון
5. **📍 גיאוגרפי** - התפלגות ערים, חריגים
6. **📋 כיסויים** - סכומים וממוצעים
7. **📅 טרנדים חודשיים** - זיהוי ריצת סוף שנה
8. **💰 כספי** - Top 10 יקרים, פערים, היסטוגרמה
9. **👥 אשכולות משפחתיים** - משפחות חשודות
10. **🎭 פרופילי הונאה** - הממקסם, הרוכב, הצמוד, המפצל
11. **📋 Watchlist** - רשימת מעקב + פעולות מומלצות

## 📧 איך להעביר לעבודה

1. פתח: https://github.com/idanginsler-cmyk/Insurance/blob/main/java-tool-full/FraudAnalyzer.java
2. לחץ **"Raw"** (למעלה מימין)
3. Ctrl+A → Ctrl+C
4. שלח במייל לעצמך (בגוף המייל)

## 🖥️ בעבודה

1. צור תיקייה `C:\fraud-full`
2. ב-VS Code: **File → New File**
3. הדבק את הקוד, שמור בשם `FraudAnalyzer.java`
4. שים את ה-CSV שלך בתיקייה בשם `claims.csv`

## ▶️ הרצה (Java 22)

```
java FraudAnalyzer.java
```

או עם שמות מותאמים:
```
java FraudAnalyzer.java my-claims.csv my-report.html
```

## ✅ תוצאה
יווצר `fraud-report.html` - פתח בדפדפן ותראה את הדשבורד המלא!

## 📁 פורמט CSV נדרש
```
claim_id,date,insured_name,insured_id,age,city,employer,policy_type,policy_start,policy_num,coverage,provider,amount_claimed,amount_paid
```

## 🔒 אבטחה
- ✅ אפס חיבורים לאינטרנט
- ✅ אפס ספריות חיצוניות
- ✅ רק Java Standard Library
- ✅ כל הנתונים נשארים במחשב שלך
