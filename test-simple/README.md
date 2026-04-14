# 🧪 ניסיון פשוט - Hello World ב-Java

בדיקה אם אתה יכול להריץ Java ולפתוח דף HTML.

## מה הקוד עושה
1. מדפיס הודעה בטרמינל
2. יוצר קובץ HTML פשוט
3. פותח אותו אוטומטית בדפדפן

---

## 📧 שלב 1: העבר במייל

### קובץ 1: `Hello.class.b64` (טקסט Base64)
- לך ל: https://github.com/idanginsler-cmyk/Insurance/blob/main/test-simple/Hello.class.b64
- לחץ **Raw**
- Ctrl+A → Ctrl+C
- שלח לעצמך במייל

### קובץ 2: `decode.bat` (סקריפט המרה)
- להלן התוכן - העתק למייל:

```
@echo off
certutil -decode Hello.class.b64 Hello.class > /dev/null
echo Done! Run: java Hello
pause
```

---

## 🖥️ שלב 2: בעבודה

1. צור תיקייה `C:\test-java`
2. שמור שם את שני הקבצים מהמייל:
   - `Hello.class.b64` (הדבק את הטקסט הארוך)
   - `decode.bat` (הדבק את 4 השורות)
3. לחץ כפולה על `decode.bat`
4. יווצר `Hello.class`

## ▶️ שלב 3: הרץ

בטרמינל CMD (לא PowerShell!):
```
cd C:\test-java
java Hello
```

## ✅ מה אמור לקרות

תראה בטרמינל:
```
שלום! הקוד רץ בהצלחה!
נוצר קובץ: hello.html
פותח בדפדפן...
```

ודפדפן ייפתח עם הודעה ירוקה "✅ הקוד עבד!"

## 🐞 אם לא עובד

- **"java is not recognized"** → אין Java, לבקש מ-IT
- **"UnsupportedClassVersionError"** → גרסת Java ישנה, להגיד לי
- **הקובץ HTML לא נפתח אוטומטית** → פתח ידנית את `hello.html`
