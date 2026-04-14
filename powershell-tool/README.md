# 🔍 מנתח הונאות - PowerShell

כלי עצמאי לניתוח תביעות ביטוח בריאות ב-PowerShell.
**עובד על כל מחשב Windows ללא התקנה.**

## למה PowerShell?
- ✅ **תמיד מותקן ב-Windows** - אין צורך להתקין כלום
- ✅ **סקריפט טקסט** - אפשר להעביר במייל
- ✅ **אין חיבור לאינטרנט** - הכל מקומי
- ✅ **אין קבצים בינאריים** - אבטחת מידע אוהבת

## איך להעביר לעבודה

1. פתח את קובץ `FraudAnalyzer.ps1` בדפדפן
2. העתק את כל הטקסט
3. שלח לעצמך במייל
4. בעבודה: פתח את המייל
5. העתק את הטקסט ל-VS Code
6. שמור כ-`FraudAnalyzer.ps1`

## איך להריץ

### שלב 1: תיקיית עבודה
צור תיקייה, למשל `C:\fraud-tool` ושים בה:
- `FraudAnalyzer.ps1` (הסקריפט)
- `claims.csv` (הקובץ שלך)

### שלב 2: פתח PowerShell ב-VS Code
Ctrl + ` (בקטיק)

### שלב 3: נווט לתיקייה
```powershell
cd C:\fraud-tool
```

### שלב 4: הרץ
```powershell
.\FraudAnalyzer.ps1
```

או עם שמות מותאמים:
```powershell
.\FraudAnalyzer.ps1 my-claims.csv my-report.html
```

## אם יש שגיאת Execution Policy

אם מופיעה שגיאה "running scripts is disabled":

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

(מאשר אם שואל)

או לתחילה חד-פעמית:
```powershell
powershell -ExecutionPolicy Bypass -File .\FraudAnalyzer.ps1
```

## תוצאה

יווצר קובץ `fraud-report.html` - פתח בדפדפן!

## פורמט CSV נדרש

שורה ראשונה עם כותרות:
```
claim_id,date,insured_name,insured_id,age,city,employer,policy_type,policy_start,policy_num,coverage,provider,amount_claimed,amount_paid
```

## דפוסים שנבדקים

1. **תדירות חריגה** - מבוטחים עם הרבה תביעות
2. **ריכוז נותן שירות** - ריכוז >5% מהתביעות
3. **סכום אחיד** - >60% באותו סכום
4. **סכומים עגולים** - כפולות 500₪
5. **אשכולות משפחתיים** - משפחות שכולן אצל אותו נותן שירות

## אבטחה
✅ אפס חיבורים לאינטרנט
✅ אפס מודולים חיצוניים
✅ קוד פתוח - אפשר לקרוא את כולו
✅ אפס כתיבה לרישום או למערכת
