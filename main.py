"""
NSE AI Stock Analyst - FastAPI Backend
Main application entry point with async database, CRUD APIs, and background scheduler.
"""
from fastapi import FastAPI, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, func
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, AsyncSessionLocal, async_sessionmaker
from sqlalchemy.orm import declarative_base, sessionmaker
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import asyncio
import os
import json
import structlog

from src.agent.workflow import agent

# Configure structlog
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///stock_insights.db")
engine = create_async_engine(DATABASE_URL, echo=False)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)
Base = declarative_base()


# Database Models
class Watchlist(Base):
    __tablename__ = "watchlist"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(10), unique=True, nullable=False, index=True)
    added_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)


class StockInsight(Base):
    __tablename__ = "stock_insights"
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(10), nullable=False, index=True)
    summary_json = Column(Text, nullable=False)
    fetched_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_scheduled = Column(Boolean, default=False)


# Pydantic Schemas
class WatchlistCreate(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=10, description="Stock symbol (e.g., RELIANCE)")
    
    class Config:
        json_schema_extra = {"example": {"symbol": "RELIANCE"}}


class WatchlistResponse(BaseModel):
    symbol: str
    added_at: datetime
    last_updated: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class InsightResponse(BaseModel):
    symbol: str
    data: Dict[str, Any]
    fetched_at: datetime
    
    class Config:
        from_attributes = True


# Background task manager
class BackgroundScheduler:
    def __init__(self):
        self.running = False
        self.task = None
    
    async def start(self, get_db):
        """Start the background scheduler."""
        self.running = True
        interval_hours = int(os.getenv("UPDATE_INTERVAL_HOURS", 4))
        logger.info("scheduler_started", interval_hours=interval_hours)
        
        while self.running:
            try:
                await self.run_scheduled_analysis(get_db)
            except Exception as e:
                logger.error("scheduled_analysis_failed", error=str(e))
            
            await asyncio.sleep(interval_hours * 3600)
    
    async def stop(self):
        """Stop the background scheduler."""
        self.running = False
        if self.task:
            self.task.cancel()
        logger.info("scheduler_stopped")
    
    async def run_scheduled_analysis(self, get_db):
        """Run analysis for all active watchlist symbols."""
        db = next(get_db())
        try:
            result = await db.execute(
                "SELECT symbol FROM watchlist WHERE is_active = TRUE"
            )
            symbols = [row[0] for row in result.fetchall()]
            
            logger.info("scheduled_analysis_starting", count=len(symbols))
            
            for symbol in symbols:
                try:
                    await analyze_stock(symbol, db, scheduled=True)
                    logger.info("scheduled_analysis_complete", symbol=symbol)
                except Exception as e:
                    logger.error("scheduled_analysis_symbol_failed", symbol=symbol, error=str(e))
        finally:
            await db.close()


scheduler = BackgroundScheduler()


# Dependency for DB session
async def get_db():
    async with async_session_maker() as session:
        yield session


async def analyze_stock(symbol: str, db: AsyncSession, scheduled: bool = False) -> Dict[str, Any]:
    """Run the AI analysis workflow and store results."""
    logger.info("analyzing_stock", symbol=symbol, scheduled=scheduled)
    
    # Run agent workflow
    result = await agent.ainvoke({"symbol": symbol})
    summary = result.get("llm_summary", {})
    
    # Upsert into database
    stmt = """
        INSERT INTO stock_insights (symbol, summary_json, fetched_at, is_scheduled)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(symbol) DO UPDATE SET
            summary_json = excluded.summary_json,
            fetched_at = excluded.fetched_at,
            is_scheduled = excluded.is_scheduled
    """
    await db.execute(
        stmt,
        (symbol, json.dumps(summary), datetime.utcnow(), scheduled)
    )
    await db.commit()
    
    return summary


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown events."""
    # Startup
    logger.info("application_starting")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Start background scheduler
    scheduler.task = asyncio.create_task(scheduler.start(get_db))
    
    yield
    
    # Shutdown
    await scheduler.stop()
    await engine.dispose()
    logger.info("application_shutdown")


# Initialize FastAPI app
app = FastAPI(
    title="NSE AI Stock Analyst",
    description="AI-powered stock analysis for NSE (India) using LangGraph and Google Gemini",
    version="2.0.0",
    lifespan=lifespan
)

# Mount static files and serve frontend
app.mount("/static", StaticFiles(directory="templates"), name="static")


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the frontend dashboard."""
    return FileResponse("templates/index.html")


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "running",
        "database": "connected",
        "scheduler": "active" if scheduler.running else "inactive"
    }


@app.post("/api/watchlist", status_code=status.HTTP_201_CREATED, response_model=WatchlistResponse)
async def add_to_watchlist(item: WatchlistCreate, db: AsyncSession = Depends(get_db)):
    """Add a stock symbol to the watchlist."""
    symbol = item.symbol.upper().strip()
    
    # Check if exists
    result = await db.execute(
        "SELECT * FROM watchlist WHERE symbol = ?",
        (symbol,)
    )
    existing = result.fetchone()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Symbol {symbol} already in watchlist"
        )
    
    # Insert new symbol
    await db.execute(
        "INSERT INTO watchlist (symbol, added_at, is_active) VALUES (?, ?, ?)",
        (symbol, datetime.utcnow(), True)
    )
    await db.commit()
    
    logger.info("watchlist_added", symbol=symbol)
    
    return WatchlistResponse(symbol=symbol, added_at=datetime.utcnow())


@app.get("/api/watchlist", response_model=List[WatchlistResponse])
async def get_watchlist(db: AsyncSession = Depends(get_db)):
    """Get all active watchlist symbols."""
    result = await db.execute(
        "SELECT symbol, added_at FROM watchlist WHERE is_active = TRUE ORDER BY added_at DESC"
    )
    rows = result.fetchall()
    
    # Get last updated time for each symbol from insights
    watchlist = []
    for symbol, added_at in rows:
        insight_result = await db.execute(
            "SELECT fetched_at FROM stock_insights WHERE symbol = ? ORDER BY fetched_at DESC LIMIT 1",
            (symbol,)
        )
        insight_row = insight_result.fetchone()
        last_updated = insight_row[0] if insight_row else None
        
        watchlist.append({
            "symbol": symbol,
            "added_at": added_at,
            "last_updated": last_updated
        })
    
    return watchlist


@app.delete("/api/watchlist/{symbol}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_from_watchlist(symbol: str, db: AsyncSession = Depends(get_db)):
    """Remove a symbol from the watchlist."""
    symbol = symbol.upper().strip()
    
    result = await db.execute(
        "DELETE FROM watchlist WHERE symbol = ?",
        (symbol,)
    )
    
    if result.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Symbol {symbol} not found in watchlist"
        )
    
    await db.commit()
    logger.info("watchlist_removed", symbol=symbol)


@app.get("/api/analyze/{symbol}")
async def analyze_endpoint(symbol: str, db: AsyncSession = Depends(get_db)):
    """Trigger immediate AI analysis for a symbol."""
    symbol = symbol.upper().strip()
    summary = await analyze_stock(symbol, db, scheduled=False)
    
    return {
        "symbol": symbol,
        "data": summary,
        "status": "success"
    }


@app.get("/api/insights", response_model=List[InsightResponse])
async def get_all_insights(db: AsyncSession = Depends(get_db)):
    """Get all stored insights."""
    result = await db.execute(
        "SELECT symbol, summary_json, fetched_at FROM stock_insights ORDER BY fetched_at DESC"
    )
    rows = result.fetchall()
    
    insights = []
    for symbol, summary_json, fetched_at in rows:
        try:
            data = json.loads(summary_json)
        except json.JSONDecodeError:
            data = {"error": "Invalid JSON"}
        
        insights.append({
            "symbol": symbol,
            "data": data,
            "fetched_at": fetched_at
        })
    
    return insights


if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host=host, port=port)
