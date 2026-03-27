from typing import Any, Dict

from google.adk.agents import Agent
from google.adk.tools import FunctionTool

from tools.finance_tools import compare_tax_regimes


def run_tax_wizard(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Compare old vs new regime and suggest tax actions."""
    return compare_tax_regimes(payload)


run_tax_wizard_tool = FunctionTool(run_tax_wizard)


tax_wizard_agent = Agent(
    name="tax_wizard_agent",
    model="gemini-2.0-flash",
    description="Tax optimization assistant for old vs new regime comparison.",
    tools=[run_tax_wizard_tool],
    instruction=(
        "You are a tax wizard agent. "
        "Call run_tax_wizard and return structured JSON only."
    ),
)
