# Project Memory - Stock Research Platform

> קובץ זכרון לפרויקט. עדכן בכל סשן כדי לשמור רציפות.

## Context

**מטרה**: אתר למחקר מניות - ניתוח טכני, פונדמנטלי, קריאת דוחות כספיים (עם LLM), סנטימנט, וציון משולב.

**שוק יעד**: ארה"ב (SEC EDGAR + yfinance). ת"א - עתיד.

**סטטוס**: MVP לניתוח מניה בודדת - הושלם ונדחף לענף.

**ענף Git**: `claude/stock-analysis-platform-PCff9`

**Commit אחרון**: `d3fda67` - "Add stock research platform MVP (single-stock)"

## Stack

| שכבה | טכנולוגיה |
|---|---|
| Backend | Python 3.11 + FastAPI + Uvicorn |
| Data | yfinance (מחירים/יסודות/חדשות), SEC EDGAR (דוחות) |
| LLM | Anthropic Claude (`claude-sonnet-4-6`) |
| Frontend | HTML + vanilla JS + lightweight-charts |
| Deploy | אין עדיין (לוקאלי בלבד) |

## מבנה הקוד

```
stock-platform/
├── backend/
│   ├── main.py                FastAPI app + SafeJSONResponse (NaN sanitizer)
│   ├── data/
│   │   ├── prices.py          get_history() + get_quote() מ-yfinance
│   │   ├── fundamentals.py    get_fundamentals() - valuation/profit/growth/bs/div
│   │   ├── filings.py         SEC EDGAR: ticker_to_cik, list_filings, fetch_filing_text
│   │   └── news.py            get_news() מ-yfinance
│   ├── analysis/
│   │   ├── technical.py       SMA/EMA/RSI/MACD/Bollinger + enrich() + technical_snapshot()
│   │   ├── llm.py             summarize_filing() + news_sentiment() עם Claude
│   │   └── scoring.py         technical/fundamental/sentiment/combined scores
│   └── requirements.txt
├── frontend/
│   ├── index.html             SPA עם 4 tabs
│   ├── app.js                 מחובר לבקאנד ב-same-origin
│   └── styles.css             dark theme
├── .env.example               ANTHROPIC_API_KEY + SEC_USER_AGENT
├── .gitignore
├── README.md
└── MEMORY.md                  (הקובץ הזה)
```

## API Endpoints

| Endpoint | Status |
|---|---|
| `GET /api/health` | ✅ |
| `GET /api/stock/{ticker}/overview` | ✅ |
| `GET /api/stock/{ticker}/prices?period=1y&interval=1d` | ✅ |
| `GET /api/stock/{ticker}/technical` | ✅ |
| `GET /api/stock/{ticker}/fundamentals` | ✅ |
| `GET /api/stock/{ticker}/filings` | ✅ |
| `GET /api/stock/{ticker}/filings/latest-summary?form=10-Q` | ✅ (דורש מפתח Anthropic) |
| `GET /api/stock/{ticker}/news?analyze=true` | ✅ |
| `GET /api/stock/{ticker}/score?include_sentiment=true` | ✅ |

## החלטות ארכיטקטוניות

1. **Same-origin frontend**: ה-FastAPI מגיש את ה-frontend ישירות (`StaticFiles` + `FileResponse`). אין CORS ב-prod, אין bundler. פשטות > תחכום.
2. **Caching**: `lru_cache` עם bucket לפי זמן - מחירים 15 דק', פונדמנטלים 6 שעות, דוחות EDGAR 6 שעות, חדשות 30 דק'.
3. **LLM graceful degradation**: `llm.llm_available()` מחזיר False אם אין `ANTHROPIC_API_KEY`. כל endpoint ממשיך לעבוד בלי LLM, רק מחזיר `{"error": "no_api_key"}` במקום סיכום.
4. **NaN sanitizer**: `SafeJSONResponse` מנקה `float('nan')` ו-`inf` לפני serialize - yfinance מחזיר NaN ב-dicts.
5. **Robust yfinance access**: `getattr` עם try/except על `FastInfo`. API של yfinance משתנה בין גרסאות.
6. **Composite score weights**: Fundamental 45%, Technical 35%, Sentiment 20%. עריכה ב-`analysis/scoring.py::combined_score`.
7. **Disclaimer**: כל מסך ציון כולל "Research tool only. Not investment advice." בגלל רגולציה ישראלית על ייעוץ השקעות.

## מה נבדק

- ✅ Syntax check על כל קבצי ה-Python
- ✅ יבוא מודולים נקי ב-venv
- ✅ שרת עולה ומגיב ל-`/api/health`
- ✅ כל ה-endpoints מחזירים JSON תקין (גם כשאין רשת)
- ❌ בדיקה חיה עם נתוני AAPL אמיתיים - **הסנדבוקס חסם Yahoo/SEC (403)**. צריך לוודא בסביבה עם אינטרנט.

## מה נותר לעשות

### לפני שימוש
- [ ] הרצה מקומית עם מפתח Anthropic ובדיקה של AAPL end-to-end
- [ ] ודא שסיכום 10-Q של Claude מייצר JSON תקין (prompt התפתחותי)

### תכונות בשלב הבא (לפי עדיפות)
- [ ] **Watchlist** - שמירת רשימת מניות + dashboard השוואתי
- [ ] **התראות** - RSI/MACD/price crosses + earnings dates
- [ ] **השוואה לעמיתים** - peers בענף (יחסים + גרף)
- [ ] **Scanner** - דירוג מאות מניות (S&P500) לפי ציון משולב, עם sort/filter
- [ ] **Backtesting** - רצף אחורי של האסטרטגיה על ציון המשולב
- [ ] **תמיכה ב-ת"א** - מקור נתונים נוסף (TASE API / scraping)
- [ ] **User accounts + persistence** - DB (SQLite בהתחלה, Postgres אח"כ)

### חובות טכניים
- [ ] Rate limiting על endpoints יקרים (LLM)
- [ ] Error boundaries טובים יותר ב-frontend
- [ ] טסטים (pytest לבקאנד, Playwright ל-UI)
- [ ] Dockerfile + docker-compose לפריסה

## הערות חשובות לסשן הבא

1. ה-repo הוא בעיקרו **פרויקט ביטוח** - כל תוכן המניות ב-`stock-platform/` כתיקייה נפרדת.
2. אם יש שאלות על ה-UI - יש `demo.html` שנראה בלי שרת.
3. ב-yfinance מתחלפים שדות בגרסאות - אם משהו חוזר `null` בצורה לא הגיונית בסביבה חיה, בדוק את `fast_info` vs `info` API.
4. ה-API Key של Anthropic נטען מ-`.env` דרך `python-dotenv` (שנקרא בתוך `main.py`).
5. כדי להפעיל: `cd stock-platform/backend && uvicorn main:app --reload`. פתח `http://localhost:8000/`.
