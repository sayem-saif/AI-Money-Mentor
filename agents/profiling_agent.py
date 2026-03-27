from typing import Any, Dict

from google.adk.agents import Agent
from google.adk.tools import FunctionTool

from tools.finance_tools import validate_and_structure_profile


def profile_user(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and structure raw user financial inputs into a consistent profile."""
    return validate_and_structure_profile(user_data)


profile_user_tool = FunctionTool(profile_user)


profiling_agent = Agent(
    name="profiling_agent",
    model="gemini-2.0-flash",
    description="Validates user data and builds a clean financial profile.",
    tools=[profile_user_tool],
    instruction=(
        "You are a profiling specialist for Indian personal finance. "
        "Call profile_user with raw user data and return valid JSON only. "
        "No markdown and no extra commentary."
    ),
)
