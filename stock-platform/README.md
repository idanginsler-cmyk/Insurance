# Stock Research Platform

פלטפורמה למחקר מניות שמשלבת ניתוח טכני, פונדמנטלי, ניתוח דוחות כספיים וסנטימנט - עם Claude כמנוע ניתוח לדוחות.

> כלי מחקר בלבד. לא מהווה ייעוץ השקעות.

## מה יש ב-MVP

- **גרף מחירים אינטראקטיבי** (Lightweight Charts) עם SMA50/200, Bollinger, RSI, MACD
- **כרטיס פונדמנטלי** - יחסי שווי, רווחיות, צמיחה, מאזן, דיבידנד, קונצנזוס אנליסטים
- **ניתוח דוח אחרון** (10-K/10-Q מ-SEC EDGAR) באמצעות Claude - כולל highlights, סיכונים, ודגלים אדומים
- **חדשות וסנטימנט** מצטבר
- **ציון משולב** (טכני / פונדמנטלי / סנטימנט) עם disclaimer ברור

## ארכיטקטורה

```
stock-platform/
├── backend/
│   ├── main.py              FastAPI app
│   ├── data/
│   │   ├── prices.py        yfinance price history + quote
│   │   ├── fundamentals.py  yfinance fundamentals
│   │   ├── filings.py       SEC EDGAR fetcher
│   │   └── news.py          yfinance news feed
│   ├── analysis/
│   │   ├── technical.py     SMA/EMA/RSI/MACD/Bollinger
│   │   ├── llm.py           Claude summaries & sentiment
│   │   └── scoring.py       composite scoring
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── app.js
│   └── styles.css
└── .env.example
```

## התקנה והרצה

```bash
cd stock-platform
python -m venv venv
source venv/bin/activate               # Linux/Mac
pip install -r backend/requirements.txt

cp .env.example .env
# ערוך את .env - הזן ANTHROPIC_API_KEY ו-SEC_USER_AGENT (שם ואימייל)

cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

פתח את `http://localhost:8000/` - טעינה ראשונית טוענת אוטומטית AAPL.

## API

| Endpoint | תיאור |
|---|---|
| `GET /api/health` | סטטוס ובדיקת זמינות LLM |
| `GET /api/stock/{ticker}/overview` | שם, מחיר, פרופיל |
| `GET /api/stock/{ticker}/prices?period=1y&interval=1d` | נרות + אינדיקטורים |
| `GET /api/stock/{ticker}/technical` | snapshot טכני |
| `GET /api/stock/{ticker}/fundamentals` | נתונים פונדמנטליים |
| `GET /api/stock/{ticker}/filings` | רשימת דוחות מ-SEC |
| `GET /api/stock/{ticker}/filings/latest-summary?form=10-Q` | סיכום של Claude על הדוח האחרון |
| `GET /api/stock/{ticker}/news` | חדשות + ניתוח סנטימנט |
| `GET /api/stock/{ticker}/score` | ציון משולב |

## הערות חשובות

- **ללא מפתח Anthropic**: כל תכונות הניתוח שאינן-LLM עובדות (גרף, פונדמנטלי, חדשות גולמיות). סיכום דוח וסנטימנט LLM ידרשו מפתח.
- **SEC EDGAR** דורש User-Agent מזהה (שם ואימייל) ב-`.env`.
- **Cache**: מחירים 15 דק', פונדמנטלים 6 שעות, דוחות מ-EDGAR 6 שעות.
- **שוק**: ארה"ב בלבד בשלב זה (SEC + yfinance).

## צעדי המשך אפשריים

1. Watchlist / פורטפוליו רב-מניות עם השוואה
2. Backtesting של אסטרטגיות על בסיס הציון
3. התראות (price / RSI / MACD / earnings)
4. סורקר שוק - דירוג מאות מניות לפי ציון משולב
5. השוואה לעמיתים בענף
6. הוספת שוק ת"א (דורש מקור נתונים נוסף - ככל הנראה TASE API / scraping)
