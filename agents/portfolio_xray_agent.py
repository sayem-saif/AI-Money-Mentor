from typing import Any, Dict

from google.adk.agents import Agent
from google.adk.tools import FunctionTool

from tools.finance_tools import portfolio_xray


def run_portfolio_xray(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze overlap, costs, and rebalance opportunities for mutual funds."""
    return portfolio_xray(payload)


run_portfolio_xray_tool = FunctionTool(run_portfolio_xray)


portfolio_xray_agent = Agent(
    name="portfolio_xray_agent",
    model="gemini-2.0-flash",
    description="Portfolio diagnostic agent for funds overlap and efficiency.",
    tools=[run_portfolio_xray_tool],
    instruction=(
        "You are a portfolio diagnostic agent. "
        "Call run_portfolio_xray and return structured JSON only."
    ),
)
