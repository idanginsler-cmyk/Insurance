# 📧 איך להעביר ולהפעיל בעבודה

## רעיון: כל הקבצים כטקסט → העברה במייל → המרה חזרה בעבודה

## שלב 1: בבית/בנייד - העתק את הקבצים הבאים כטקסט

### 3 קבצי Base64 (טקסט בלבד):
1. `FraudAnalyzer.class.b64`
2. `Claim.class.b64`
3. `Alert.class.b64`

### 1 קובץ המרה:
- `decode.bat` (קובץ Windows רגיל)

### איך להעתיק:
1. לך לכל קובץ ב-GitHub
2. לחץ **"Raw"**
3. **Ctrl+A** → **Ctrl+C**
4. שלח לעצמך במייל (גוף המייל)

**תעשה את זה 4 פעמים** - מייל אחד לכל קובץ, או הכל במייל אחד עם הפרדה ברורה.

## שלב 2: בעבודה

### צור תיקייה
לדוגמה: `C:\fraud-tool`

### שמור את 4 הקבצים
בתוך `C:\fraud-tool`, צור 4 קבצים חדשים:
1. `FraudAnalyzer.class.b64` (הדבק את התוכן)
2. `Claim.class.b64` (הדבק את התוכן)
3. `Alert.class.b64` (הדבק את התוכן)
4. `decode.bat` (הדבק את התוכן)

### לחץ פעמיים על decode.bat
זה יעשה את ההמרה אוטומטית ב-3 שניות. יווצרו:
- `FraudAnalyzer.class`
- `FraudAnalyzer$Claim.class`
- `FraudAnalyzer$Alert.class`

### שים את ה-CSV
העתק את `claims.csv` לאותה תיקייה.

### הרץ!
פתח Command Prompt (cmd.exe) בתיקייה ותקליד:
```
java FraudAnalyzer
```

יווצר `fraud-report.html` - פתח בדפדפן!

## למה זה יעבוד
✅ **Base64** - טקסט פשוט, עובר בכל מייל
✅ **certutil** - כלי של Windows, תמיד מותקן, לא דורש הרשאות
✅ **decode.bat** - קובץ Batch, רץ ב-CMD (לא דורש הרשאות PowerShell)
✅ **java** - יש לך Runtime, רק מריץ `.class` ללא קמפול
