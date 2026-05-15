# 📊 NSE AI Stock Analyst - Project Documentation

**Version:** 2.0.0 (FastAPI + Async Architecture)  
**Target Market:** NSE (India)  
**Tech Stack:** Python 3.10+, FastAPI, LangGraph, Google Gemini (via OpenRouter), SQLite (Async), Alpine.js + HTMX

---

## 🎯 Project Overview

An AI-powered stock market intelligence agent that automatically fetches real-time data from NSE, aggregates news from multiple sources, and generates professional financial analysis reports using Large Language Models (LLMs).

### Key Features
- **Automated Data Collection:** Fetches live price data (yfinance) and news (Google News RSS) for NSE stocks
- **AI-Powered Analysis:** Uses Google Gemini via OpenRouter to generate executive summaries, sentiment scores, catalysts, and risk assessments
- **Dynamic Watchlist:** CRUD API endpoints to manage monitored stocks (no hardcoded lists)
- **Background Scheduler:** Automatically analyzes watchlist stocks every 4 hours (configurable)
- **Modern Frontend:** Real-time dashboard built with HTMX + Alpine.js + Tailwind CSS
- **Async Architecture:** Non-blocking I/O operations using FastAPI + asyncio + SQLAlchemy 2.0

---

## 📁 Project Structure

```
stock_saa_crawler/
├── .env                      # Environment variables (API keys, config)
├── requirements.txt          # Python dependencies
├── main.py                   # FastAPI application entry point
├── start_system.bat          # Windows startup script
├── start_system.sh           # Linux/Mac startup script
├── templates/
│   └── index.html            # Frontend dashboard (HTMX + Alpine.js)
└── src/
    ├── fetchers/
    │   ├── __init__.py
    │   └── nse_fetcher.py    # Async data fetching (price + news)
    └── agent/
        ├── __init__.py
        └── workflow.py       # LangGraph agent workflow
```

---

## 🛠️ Technology Decisions

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| **Backend Framework** | FastAPI | Native async support, automatic validation, superior performance vs Flask |
| **Database ORM** | SQLAlchemy 2.0 (Async) | Type-safe, async-compatible, modern API |
| **Database** | SQLite (aiosqlite) | Lightweight, zero-config, perfect for single-user SaaS |
| **AI Orchestrator** | LangGraph | Stateful workflows, multi-step reasoning, easy to extend |
| **LLM Provider** | OpenRouter (Google Gemini) | Cost-effective, high-quality, supports multiple models |
| **Frontend** | HTMX + Alpine.js | Zero-build, reactive UI without React/Vue complexity |
| **Styling** | Tailwind CSS | Utility-first, rapid prototyping |
| **Logging** | structlog | Structured JSON logging for production monitoring |
| **Scheduler** | asyncio (native) | No external dependencies, integrates with async event loop |

---

## 📦 Installation & Setup

### Prerequisites
- Python 3.10 or higher
- OpenRouter API key ([Get one here](https://openrouter.ai))

### Quick Start

#### Windows
```bash
start_system.bat
```

#### Linux/Mac
```bash
chmod +x start_system.sh
./start_system.sh
```

### Manual Setup
```bash
# 1. Create virtual environment
python -m venv venv

# 2. Activate environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
# Edit .env file and add your OPENROUTER_API_KEY

# 5. Run the application
python main.py
# Or use uvicorn directly:
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

---

## 🔐 Environment Variables (.env)

```env
# Required
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxx     # Your OpenRouter API key
LLM_MODEL_ID=google/gemini-2.0-flash          # Model to use (see OpenRouter docs)

# Database
DATABASE_URL=sqlite+aiosqlite:///stock_insights.db

# Scheduler
UPDATE_INTERVAL_HOURS=4                       # How often to auto-analyze watchlist

# Server
HOST=0.0.0.0
PORT=8000
SECRET_KEY=change_this_to_random_string       # For session security
```

---

## 🌐 API Endpoints

### Health Check
```http
GET /api/health
```
**Response:** `{"status": "running", "database": "connected", "scheduler": "active"}`

---

### Watchlist Management

#### Add Symbol
```http
POST /api/watchlist
Content-Type: application/json

{"symbol": "RELIANCE"}
```
**Response:** `{"symbol": "RELIANCE", "added_at": "2024-01-15T10:30:00"}`

#### Get All Symbols
```http
GET /api/watchlist
```
**Response:**
```json
[
  {"symbol": "RELIANCE", "added_at": "...", "last_updated": "..."},
  {"symbol": "TCS", "added_at": "...", "last_updated": "..."}
]
```

#### Remove Symbol
```http
DELETE /api/watchlist/{symbol}
```
**Status:** `204 No Content`

---

### Analysis

#### Trigger Analysis
```http
GET /api/analyze/{symbol}
```
**Response:**
```json
{
  "symbol": "RELIANCE",
  "data": {
    "summary": "Reliance Industries shows bullish momentum...",
    "sentiment": "Bullish",
    "key_catalysts": ["Q3 earnings beat", "New retail expansion"],
    "risks": ["Crude oil volatility"],
    "confidence_1_to_10": 8
  },
  "status": "success"
}
```

#### Get All Insights
```http
GET /api/insights
```
**Response:** Array of all stored analysis results

---

### Frontend Dashboard
```http
GET /
```
Serves the interactive dashboard at `http://localhost:8000`

### Interactive API Docs
```http
GET /docs
```
Swagger UI for testing APIs directly in browser

---

## 🤖 Agent Workflow (LangGraph)

The analysis pipeline consists of three sequential nodes:

### 1. **Fetch Node** (`fetch_nodes`)
- Calls `fetch_price_data()` for current market metrics
- Calls `fetch_nse_news()` for recent news articles
- Runs both in parallel using `asyncio.gather()`
- Handles retries with exponential backoff (tenacity)

### 2. **Clean Node** (`clean_data`)
- Combines price and news data into unified structure
- Adds timestamp for tracking
- Validates data presence

### 3. **Analyze Node** (`generate_insight`)
- Constructs prompt with cleaned data
- Invokes LLM via OpenRouter
- Parses JSON response
- Extracts: summary, sentiment, catalysts, risks, confidence score

**Graph Flow:**
```
Entry → Fetch → Clean → Analyze → END
```

---

## 🗄️ Database Schema

### Table: `watchlist`
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| symbol | VARCHAR(10) | Stock symbol (unique) |
| added_at | DATETIME | When added to watchlist |
| is_active | BOOLEAN | Enable/disable monitoring |

### Table: `stock_insights`
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| symbol | VARCHAR(10) | Stock symbol (indexed) |
| summary_json | TEXT | JSON blob of LLM analysis |
| fetched_at | DATETIME | Last analysis timestamp |
| is_scheduled | BOOLEAN | True if auto-scheduled |

---

## 🎨 Frontend Architecture

**File:** `templates/index.html`

### Technologies
- **Alpine.js:** Reactive state management (watchlist, insights)
- **HTMX:** Dynamic content updates (optional, used for indicators)
- **Tailwind CSS:** Styling via CDN
- **Vanilla JS:** API calls, date formatting

### Features
- Real-time watchlist CRUD operations
- Sentiment badges (Bullish/Neutral/Bearish)
- Confidence score display
- Key catalysts and risks lists
- Auto-refresh every 60 seconds
- Manual refresh button
- Responsive design (mobile-friendly)

---

## 🔄 Background Scheduler

**Implementation:** Native `asyncio` loop (no APScheduler dependency)

**Behavior:**
1. On app startup, scheduler task begins
2. Every `UPDATE_INTERVAL_HOURS` (default: 4):
   - Queries active watchlist symbols
   - Runs analysis for each symbol sequentially
   - Logs success/failure per symbol
3. On app shutdown, scheduler cancels gracefully

**Code Location:** `main.py` → `BackgroundScheduler` class

---

## 🧪 Testing & Debugging

### Test Individual Components

#### Test Fetcher
```python
import asyncio
from src.fetchers.nse_fetcher import fetch_price_data, fetch_nse_news

async def test():
    price = await fetch_price_data("RELIANCE")
    print(price)
    news = await fetch_nse_news("RELIANCE")
    print(news)

asyncio.run(test())
```

#### Test Agent Workflow
```python
from src.agent.workflow import agent

result = await agent.ainvoke({"symbol": "TCS"})
print(result["llm_summary"])
```

### View Logs
Logs are output as structured JSON to stdout. Use `jq` for pretty printing:
```bash
python main.py | jq
```

---

## 🚀 Performance Considerations

1. **Async I/O:** All network calls (yfinance, RSS, LLM) are non-blocking
2. **Connection Pooling:** SQLAlchemy async engine manages DB connections efficiently
3. **Retry Logic:** Exponential backoff prevents API rate limiting
4. **Caching:** Consider adding Redis/cachetools for frequently accessed symbols
5. **Batch Processing:** Scheduler processes symbols sequentially to avoid LLM rate limits

---

## 🔒 Security Best Practices

- ✅ API keys stored in `.env` (never commit to Git)
- ✅ Input validation via Pydantic models
- ✅ SQL injection prevention (parameterized queries)
- ✅ CORS configured for production deployment
- ⚠️ Add authentication for multi-user deployments
- ⚠️ Rate limit API endpoints in production

---

## 📈 Future Enhancements

### Priority 1 (Recommended Next Steps)
- [ ] **User Authentication:** JWT-based auth for multi-user support
- [ ] **Email Alerts:** Send daily digests via SMTP/SendGrid
- [ ] **Advanced Charts:** Integrate Plotly/Chart.js for price history
- [ ] **Portfolio Tracking:** Track buy/sell prices and P&L

### Priority 2
- [ ] **Multi-Model Support:** Allow users to choose LLM (Gemini, Llama, Mistral)
- [ ] **Backtesting:** Historical analysis mode
- [ ] **Export Reports:** PDF/CSV download functionality
- [ ] **Webhooks:** Notify external systems on sentiment changes

### Priority 3
- [ ] **Docker Containerization:** One-command deployment
- [ ] **PostgreSQL Migration:** For production-scale workloads
- [ ] **WebSocket Updates:** Real-time push notifications
- [ ] **Mobile App:** React Native frontend

---

## 🐛 Troubleshooting

### Common Issues

**1. "ModuleNotFoundError: No module named 'src'"**
- Ensure you're running from project root directory
- Check that `__init__.py` files exist in `src/`, `src/fetchers/`, `src/agent/`

**2. "OPENROUTER_API_KEY not found"**
- Verify `.env` file exists in project root
- Check key format (should start with `sk-or-v1-`)

**3. "yfinance returns empty data"**
- NSE symbols must have `.NS` suffix (auto-added by `normalize_symbol()`)
- Market may be closed (NSE operates 9:15 AM - 3:30 PM IST)

**4. "Scheduler not running"**
- Check logs for "scheduler_started" message
- Verify `UPDATE_INTERVAL_HOURS` is set correctly

**5. "LLM returns invalid JSON"**
- Increase `max_tokens` in `workflow.py`
- Try a different model (e.g., `google/gemini-pro`)

---

## 📞 Support & Contribution

This project is designed to be extended by other LLM agents and developers. Key modification points:

- **Add new data sources:** Extend `src/fetchers/` with new modules
- **Customize analysis prompts:** Edit `generate_insight()` in `workflow.py`
- **Add API endpoints:** Follow existing patterns in `main.py`
- **Enhance UI:** Modify `templates/index.html`

---

## 📄 License

MIT License - Free for personal and commercial use.

---

**Generated for:** Qwen Coder and other LLM development assistants  
**Last Updated:** 2024  
**Maintainer:** Human Developer + AI Collaboration
