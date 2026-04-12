# הוראות התקנה

## דרישות מקדימות

- Python 3.10 ומעלה
- חשבון OpenAI ו/או Anthropic (למפתחות API)
- גישה לאינטרנט (להורדת חבילות ולתקשורת עם APIs)

## התקנה שלב אחר שלב

### 1. שכפול הריפוזיטורי

```bash
git clone <repo-url>
cd Insurance
```

### 2. יצירת סביבה וירטואלית

```bash
python -m venv venv
```

**הפעלה:**
- Linux / Mac: `source venv/bin/activate`
- Windows (PowerShell): `venv\Scripts\Activate.ps1`
- Windows (CMD): `venv\Scripts\activate.bat`

### 3. התקנת תלויות

```bash
pip install -r requirements.txt
```

### 4. הגדרת מפתחות API

```bash
cp .env.example .env
```

ערוך את קובץ `.env` והכנס את המפתחות שלך. **לפחות מפתח אחד** (OpenAI או Anthropic) נדרש להרצת הדמואים במצב חי.

> **מצב Mock:** כל הדמואים תומכים בהרצה ללא מפתחות API - יוצגו תוצאות לדוגמה מוכנות מראש. מצוין למקרה של בעיות רשת או הגבלות ארגוניות.

### 5. הרצת דמו לבדיקה

```bash
python demos/demo_1_policy_analyzer.py
```

## פתרון בעיות נפוצות

### שגיאת SSL / Proxy ארגוני
אם אתם מאחורי פרוקסי ארגוני:
```bash
pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt
```

### שגיאת הרשאות API
- ודאו שהמפתחות בקובץ `.env` תקינים
- ודאו שיש credit בחשבון ה-API
- הדמואים יעברו אוטומטית למצב mock אם אין חיבור

### בעיות עם עברית בטרמינל
- Windows: השתמשו ב-Windows Terminal (לא CMD הישן)
- ודאו שהטרמינל תומך ב-UTF-8
- VS Code: הטרמינל המובנה תומך בעברית כברירת מחדל
