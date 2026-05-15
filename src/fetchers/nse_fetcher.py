import yfinance as yf
import feedparser
import re
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential
from typing import Dict, List, Any, Optional
import structlog

logger = structlog.get_logger()


def normalize_symbol(symbol: str) -> str:
    """Normalize NSE stock symbol by adding .NS suffix if missing."""
    symbol = symbol.strip().upper()
    return symbol if ".NS" in symbol else f"{symbol}.NS"


@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=2, max=10))
async def fetch_price_data(symbol: str) -> Dict[str, Any]:
    """
    Fetch current price data and historical metrics for a given NSE symbol.
    
    Args:
        symbol: Stock ticker symbol (e.g., 'RELIANCE')
    
    Returns:
        Dictionary containing price metrics, market cap, PE ratio, etc.
    """
    sym = normalize_symbol(symbol)
    logger.info("fetching_price_data", symbol=sym)
    
    # Run blocking yfinance call in thread pool
    loop = asyncio.get_event_loop()
    ticker = await loop.run_in_executor(None, lambda: yf.Ticker(sym))
    info = await loop.run_in_executor(None, lambda: ticker.info)
    hist = await loop.run_in_executor(None, lambda: ticker.history(period="5d"))
    
    if hist.empty:
        logger.warning("no_historical_data", symbol=sym)
        return {
            "symbol": sym,
            "current_price": info.get("currentPrice"),
            "currency": info.get("currency", "INR"),
            "market_cap": info.get("marketCap"),
            "pe_ratio": info.get("trailingPE"),
            "52w_high": info.get("fiftyTwoWeekHigh"),
            "52w_low": info.get("fiftyTwoWeekLow"),
            "last_close": None,
            "change_pct": 0
        }
    
    last_close = hist["Close"].iloc[-1]
    first_close = hist["Close"].iloc[0]
    change_pct = round(((last_close - first_close) / first_close) * 100, 2) if len(hist) > 1 else 0
    
    return {
        "symbol": sym,
        "current_price": info.get("currentPrice"),
        "currency": info.get("currency", "INR"),
        "market_cap": info.get("marketCap"),
        "pe_ratio": info.get("trailingPE"),
        "52w_high": info.get("fiftyTwoWeekHigh"),
        "52w_low": info.get("fiftyTwoWeekLow"),
        "last_close": float(last_close),
        "change_pct": change_pct
    }


@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=2, max=10))
async def fetch_nse_news(symbol: str, days: int = 3) -> List[Dict[str, Any]]:
    """
    Fetch recent news articles for a given NSE symbol using Google News RSS.
    
    Args:
        symbol: Stock ticker symbol
        days: Number of days to look back (currently unused, reserved for future filtering)
    
    Returns:
        List of unique news articles with title, source, link, and snippet
    """
    sym = normalize_symbol(symbol).replace(".NS", "")
    queries = [f"{sym} NSE news", f"{sym} India stock analysis", f"{sym} SEBI filing"]
    articles: List[Dict[str, Any]] = []
    
    logger.info("fetching_news", symbol=sym, queries=len(queries))
    
    for q in queries:
        rss_url = f"https://news.google.com/rss/search?q={re.sub(r'\s+', '+', q)}&hl=en-IN&gl=IN&ceid=IN:en"
        try:
            feed = await asyncio.to_thread(feedparser.parse, rss_url)
            for entry in feed.entries[:5]:
                articles.append({
                    "title": entry.get("title"),
                    "source": entry.get("source", {}).get("title", "Google News"),
                    "link": entry.get("link"),
                    "published": entry.get("published"),
                    "snippet": entry.get("summary", "")[:200]
                })
        except Exception as e:
            logger.warning("news_fetch_failed", query=q, error=str(e))
            continue
    
    # Deduplicate articles by title hash
    seen = set()
    unique = []
    for art in articles:
        h = hash(art["title"])
        if h not in seen:
            seen.add(h)
            unique.append(art)
    
    logger.info("news_fetched", symbol=sym, count=len(unique))
    return unique[:10]
