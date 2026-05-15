from typing import TypedDict, List, Optional, Any
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import os, json, re
from datetime import datetime
from src.fetchers.nse_fetcher import fetch_price_data, fetch_nse_news
import structlog

load_dotenv()
logger = structlog.get_logger()

# Initialize LLM with OpenRouter
llm = ChatOpenAI(
    model=os.getenv("LLM_MODEL_ID", "google/gemini-2.0-flash"),
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1",
    temperature=0.3,
    max_tokens=500
)


class AgentState(TypedDict):
    """State container for the analysis workflow."""
    symbol: str
    price_data: Optional[dict]
    news_data: List[dict]
    cleaned_data: List[dict]
    llm_summary: Optional[dict]
    timestamp: Optional[str]
    error: Optional[str]


async def fetch_nodes(state: AgentState) -> dict:
    """Fetch price data and news for the given symbol."""
    try:
        logger.info("fetching_data", symbol=state["symbol"])
        price_data, news_data = await asyncio.gather(
            fetch_price_data(state["symbol"]),
            fetch_nse_news(state["symbol"])
        )
        return {"price_data": price_data, "news_data": news_data}
    except Exception as e:
        logger.error("fetch_failed", symbol=state["symbol"], error=str(e))
        return {"error": str(e)}


def clean_data(state: AgentState) -> dict:
    """Combine and structure fetched data for analysis."""
    combined = []
    if state.get("price_data"):
        combined.append({"type": "price", "content": state["price_data"]})
    for n in state.get("news_data", []):
        combined.append({"type": "news", "content": n})
    
    return {
        "cleaned_data": combined,
        "timestamp": datetime.utcnow().isoformat()
    }


async def generate_insight(state: AgentState) -> dict:
    """Generate AI-powered analysis summary from cleaned data."""
    if state.get("error"):
        logger.warning("skipping_analysis_due_to_error", symbol=state.get("symbol"))
        return {"llm_summary": {"status": "error", "message": state["error"]}}

    prompt = f"""
You are an NSE-focused financial analyst. Analyze this data for {state['symbol']} (NSE):
{json.dumps(state['cleaned_data'], indent=2)}

Output JSON ONLY (no markdown, no extra text):
{{
  "summary": "3-line executive summary focusing on price action & news catalysts",
  "sentiment": "Bullish | Neutral | Bearish",
  "key_catalysts": ["point1", "point2"],
  "risks": ["point1"],
  "confidence_1_to_10": 8
}}
"""
    try:
        logger.info("generating_insight", symbol=state["symbol"])
        response = await llm.ainvoke(prompt)
        json_match = re.search(r"\{.*\}", response.content, re.DOTALL)
        
        if not json_match:
            logger.warning("no_json_found", symbol=state["symbol"])
            return {"llm_summary": {"status": "error", "message": "No JSON found in response"}}
        
        parsed = json.loads(json_match.group())
        logger.info("insight_generated", symbol=state["symbol"], sentiment=parsed.get("sentiment"))
        return {"llm_summary": parsed}
    
    except Exception as e:
        logger.error("llm_failed", symbol=state["symbol"], error=str(e))
        return {"llm_summary": {"status": "error", "message": f"LLM failed: {str(e)}"}}


# Build the workflow graph
workflow = StateGraph(AgentState)
workflow.add_node("fetch", fetch_nodes)
workflow.add_node("clean", clean_data)
workflow.add_node("analyze", generate_insight)

workflow.set_entry_point("fetch")
workflow.add_edge("fetch", "clean")
workflow.add_edge("clean", "analyze")
workflow.add_edge("analyze", END)

# Compile the agent
agent = workflow.compile()
logger.info("agent_workflow_initialized")
