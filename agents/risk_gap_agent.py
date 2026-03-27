from typing import Any, Dict, List

from google.adk.agents import Agent
from google.adk.tools import FunctionTool

from tools.finance_tools import analyze_financial_gaps


def analyze_gaps(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Analyze risk and planning gaps from profile and FIRE outputs."""
    profile = payload.get("profile", {})
    fire_data = payload.get("fire_data", {})
    return analyze_financial_gaps(profile, fire_data)


analyze_gaps_tool = FunctionTool(analyze_gaps)


risk_gap_agent = Agent(
    name="risk_gap_agent",
    model="gemini-2.0-flash",
    description="Finds insurance, tax, emergency fund, and retirement gaps.",
    tools=[analyze_gaps_tool],
    instruction=(
        "You are a risk and gap analyzer. "
        "Call analyze_gaps with profile and fire_data, then return valid JSON only."
    ),
)
