from typing import Any, Dict

from google.adk.agents import Agent

from .fire_calculator_agent import calculate_fire, fire_calculator_agent
from .profiling_agent import profile_user, profiling_agent
from .report_agent import generate_report, report_agent
from .risk_gap_agent import analyze_gaps, risk_gap_agent


money_mentor_orchestrator = Agent(
    name="money_mentor_orchestrator",
    model="gemini-2.0-flash",
    description="Orchestrates profiling, FIRE calculation, risk analysis, and final reporting.",
    sub_agents=[profiling_agent, fire_calculator_agent, risk_gap_agent, report_agent],
    instruction=(
        "You are the AI Money Mentor orchestrator. "
        "1) Call profiling_agent to structure user input. "
        "2) Call fire_calculator_agent with profile. "
        "3) Call risk_gap_agent with profile + fire_data. "
        "4) Call report_agent with all outputs. "
        "Return valid JSON only."
    ),
)


def run_orchestration(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """Deterministic orchestration path used by Flask API for reliability in demos."""
    print("[Orchestrator] Step 1/4: Profiling agent running...")
    profile = profile_user(user_data)

    print("[Orchestrator] Step 2/4: FIRE calculator agent running...")
    fire_data = calculate_fire(profile)

    print("[Orchestrator] Step 3/4: Risk and gap analyzer agent running...")
    gaps = analyze_gaps({"profile": profile, "fire_data": fire_data})

    print("[Orchestrator] Step 4/4: Report generator agent running...")
    report = generate_report({"profile": profile, "fire_data": fire_data, "gaps": gaps})

    report["profile"] = profile
    return report
