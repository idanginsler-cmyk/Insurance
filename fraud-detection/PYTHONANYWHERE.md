# פריסה ל־PythonAnywhere

מדריך לפריסת ה־POC על חשבון PythonAnywhere — כולל free tier. אחרי שתסיים,
תקבל URL קבוע בצורת `https://<שם-משתמש>.pythonanywhere.com/` שתוכל לפתוח
מכל מקום ולהעלות אליו קבצים.

## דרישות

- חשבון PythonAnywhere (free או beginner). free tier מספיק.
- לא נדרש credit card.

## מגבלות free tier שכדאי לדעת

- 100MB דיסק (החבילה תופסת ~50MB עם הספריות + מודלי tesseract).
- רק שרת web אחד.
- outbound network חסום פרט ל־allowlist (github בתוכו, אז אפשר לעדכן git).
- אין uvicorn ארוך־רץ — רצים דרך WSGI שלהם. כבר טיפלנו בזה (`a2wsgi`).
- CPU מוגבל — אבחון של מסמך יחיד עם OCR ייקח אצלם 3–8 שניות.

---

## שלב 1 — Bash console: שכפל את הריפו והרץ setup

ב־PythonAnywhere → **Consoles** → **Bash**:

```bash
git clone https://github.com/idanginsler-cmyk/Insurance.git ~/Insurance
cd ~/Insurance/fraud-detection
bash scripts/setup_pythonanywhere.sh
```

הסקריפט:
1. מתקין את כל ה־Python deps עם `--user`.
2. מוריד את `heb.traineddata` ו־`eng.traineddata` ל־`~/tessdata`.
3. מדפיס את הסניפט שצריך להדביק בשלב הבא.

**שמור את הסניפט** — הוא יודפס בסוף הסקריפט עם הנתיבים של *החשבון שלך*.

---

## שלב 2 — Web tab: הגדר Web App חדש

PythonAnywhere → **Web** → **Add a new web app**:

1. **Domain**: השאר ברירת מחדל (`<username>.pythonanywhere.com`)
2. **Framework**: בחר **Manual configuration**
3. **Python version**: 3.11 (או 3.10 אם 3.11 לא זמין)
4. סיים.

---

## שלב 3 — ערוך את קובץ ה־WSGI

בלשונית Web, גלול ל־**Code** → לחץ על:
```
WSGI configuration file: /var/www/<username>_pythonanywhere_com_wsgi.py
```

זה יפתח עורך טקסט. **מחק הכל** ושים את התוכן שהסקריפט הדפיס. זה ייראה
בערך ככה (החלף את `<username>` בשם המשתמש שלך):

```python
import sys, os
PROJECT = '/home/<username>/Insurance/fraud-detection'
if PROJECT not in sys.path:
    sys.path.insert(0, PROJECT)
os.environ.setdefault('TESSDATA_PREFIX', '/home/<username>/tessdata')

from wsgi import application
```

לחץ **Save**.

---

## שלב 4 — Reload + פתח את האתר

חזור ללשונית Web → לחץ על הכפתור הירוק **Reload <username>.pythonanywhere.com**.

המתן ~10 שניות, ואז פתח:

```
https://<username>.pythonanywhere.com/
```

תראה את דף ההעלאה בעברית. תוכל להעלות קובץ, לקבל ציון, ולראות את כל
הסיגנלים — בדיוק כמו ב־CLI.

---

## פתרון תקלות

### "Something went wrong :-(" / Server error
- חזור ל־Web tab → גלול לתחתית ל־**Error log**, פתח את הקובץ ותקרא את ה־traceback.
- 90% מהפעמים זה אחד מאלה:
  - ImportError → לא הרצת את `setup_pythonanywhere.sh` (חזור לשלב 1).
  - מסלול שגוי ב־WSGI file → ודא שה־`PROJECT` הוא הנתיב המדויק.
  - tesseract לא מוצא heb → ודא ש־`TESSDATA_PREFIX` מצביע על `~/tessdata`.

### העלאות גדולות נחתכות
PythonAnywhere חוסם בקשות מעל 100MB ב־free tier. הקטן את הקובץ.

### "Disk quota exceeded" אחרי תקופה
ה־DB של מסמכים שנשמרו (`data/store/fraud_detection.db`) ימשיך לגדול. נקה
מדי פעם:
```bash
rm ~/Insurance/fraud-detection/data/store/fraud_detection.db
```

### עדכון לגרסה חדשה
```bash
cd ~/Insurance
git pull
cd fraud-detection
pip3.11 install --user --upgrade -e .
# חזור ל־Web tab → Reload
```

---

## מה עובד / לא עובד ב־PythonAnywhere לעומת Codespaces

| יכולת | PA free | Codespaces |
|---|---|---|
| URL ציבורי קבוע | ✅ | ✅ (ארעי) |
| OCR בעברית (Tesseract heb) | ✅ אחרי setup | ✅ |
| pdf2image (poppler) | ⚠ poppler מותקן אבל גרסה ישנה | ✅ |
| upload גדול (>100MB) | ❌ | ✅ |
| persistence של מאגר | ✅ עד שהדיסק מתמלא | ❌ נמחק עם הקודספייס |
| CPU לעיבוד מהיר | ⚠ איטי | ✅ |
| עלות | חינם | חינם עד 120 שעות/חודש |

---

## אבטחה (חשוב)

- ה־POC ללא auth, ללא הצפנה במנוחה, ללא audit log.
- כל מי שיש לו את ה־URL יכול להעלות.
- **אסור להעלות מסמכים עם נתוני לקוח אמיתיים.** רק קבצי דמו.
- אם רוצה להגביל גישה: PA free tier לא תומך ב־HTTP basic auth ברמת השרת.
  אפשרות פשוטה: להוסיף בדיקת `X-API-Key` בתוך ה־FastAPI middleware (אני
  יכול להוסיף את זה אם תרצה).
