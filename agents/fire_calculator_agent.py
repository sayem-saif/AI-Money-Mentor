from typing import Any, Dict

from google.adk.agents import Agent
from google.adk.tools import FunctionTool

from tools.finance_tools import calculate_fire_metrics


def calculate_fire(profile: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate SIP needs, FIRE number, years to FIRE, asset allocation, and milestones."""
    return calculate_fire_metrics(profile)


calculate_fire_tool = FunctionTool(calculate_fire)


fire_calculator_agent = Agent(
    name="fire_calculator_agent",
    model="gemini-2.0-flash",
    description="Calculates FIRE number and SIP requirements for each goal.",
    tools=[calculate_fire_tool],
    instruction=(
        "You are a finance calculation agent. "
        "Always call calculate_fire and return the resulting JSON only."
    ),
)
