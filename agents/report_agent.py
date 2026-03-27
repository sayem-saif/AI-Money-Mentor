from typing import Any, Dict

from google.adk.agents import Agent
from google.adk.tools import FunctionTool

from tools.finance_tools import build_final_report


def generate_report(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Generate final Money Mentor report with score, priorities, and roadmap."""
    profile = payload.get("profile", {})
    fire_data = payload.get("fire_data", {})
    gaps = payload.get("gaps", [])
    return build_final_report(profile, fire_data, gaps)


generate_report_tool = FunctionTool(generate_report)


report_agent = Agent(
    name="report_agent",
    model="gemini-2.0-flash",
    description="Generates a full financial advisory report and health score.",
    tools=[generate_report_tool],
    instruction=(
        "You are a report generator for AI Money Mentor. "
        "Call generate_report and return JSON only."
    ),
)
