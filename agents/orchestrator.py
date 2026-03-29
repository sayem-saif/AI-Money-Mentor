import json
import os
import re
import urllib.error
import urllib.request
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


MODEL_INSTRUCTION_PREFIX = (
    "Use your sub-agents in the exact sequence: profiling_agent, fire_calculator_agent, "
    "risk_gap_agent, report_agent. Return only valid JSON with keys: health_score, "
    "score_breakdown, fire_data, goals_sip, gaps, roadmap, priority_actions, summary. "
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


def _parse_json_payload(text: str) -> Dict[str, Any]:
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = text[start : end + 1]
        parsed = json.loads(candidate)
        if isinstance(parsed, dict):
            return parsed
    raise ValueError("Model output was not valid JSON.")


def _extract_chat_completion_text(response_json: Dict[str, Any]) -> str:
    choices = response_json.get("choices") or []
    if choices:
        message = choices[0].get("message", {})
        content = message.get("content")
        if isinstance(content, str):
            return content

    output_text = response_json.get("output_text")
    if isinstance(output_text, str):
        return output_text

    output = response_json.get("output") or []
    for item in output:
        for part in item.get("content", []):
            text = part.get("text")
            if isinstance(text, str) and text.strip():
                return text
    return ""


def _get_openrouter_api_keys() -> list[str]:
    """Load one or many OpenRouter keys from env, without hardcoding secrets in code."""
    keys: list[str] = []

    single = os.getenv("OPENROUTER_API_KEY", "").strip()
    if single:
        keys.append(single)

    multi = os.getenv("OPENROUTER_API_KEYS", "").strip()
    if multi:
        for item in re.split(r"[,;\n\r\t ]+", multi):
            token = item.strip()
            if token:
                keys.append(token)

    # Deduplicate while preserving order.
    deduped: list[str] = []
    seen = set()
    for key in keys:
        if key not in seen:
            deduped.append(key)
            seen.add(key)

    # Guard against template placeholders and malformed values.
    valid: list[str] = []
    rejected: list[str] = []
    for key in deduped:
        lowered = key.lower()
        if lowered.startswith("your_") or lowered.startswith("<") or lowered.endswith("_here"):
            rejected.append("placeholder value")
            continue
        if not key.startswith("sk-or-v1-"):
            rejected.append("must start with sk-or-v1-")
            continue
        valid.append(key)

    if not valid and deduped:
        raise RuntimeError(
            "OpenRouter key is not valid. Please set OPENROUTER_API_KEY to a real sk-or-v1 key in .env"
        )

    if rejected:
        print(f"[Orchestrator] Ignored {len(rejected)} invalid OpenRouter key entries.")

    return valid


def _run_openrouter_model(
    user_data: Dict[str, Any],
    *,
    system_prompt: str | None = None,
    user_prompt: str | None = None,
    temperature: float = 0.2,
) -> Dict[str, Any]:
    openrouter_api_keys = _get_openrouter_api_keys()
    if not openrouter_api_keys:
        raise RuntimeError("OPENROUTER_API_KEY or OPENROUTER_API_KEYS is required.")

    model_name = os.getenv("OPENROUTER_MODEL", "openai/gpt-oss-20b").strip() or "openai/gpt-oss-20b"
    base_url = (
        os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").strip()
        or "https://openrouter.ai/api/v1"
    )
    base_url = base_url.rstrip("/")
    endpoint = f"{base_url}/chat/completions"
    print(f"[Orchestrator] Using OpenRouter model: {model_name}")

    resolved_system_prompt = system_prompt or (
        "You are AI Money Mentor. Generate valid JSON only with keys: health_score, score_breakdown, "
        "fire_data, goals_sip, gaps, roadmap, priority_actions, summary. No markdown."
    )
    resolved_user_prompt = user_prompt or (
        f"{MODEL_INSTRUCTION_PREFIX}Input payload: {json.dumps(user_data, ensure_ascii=False)}"
    )
    payload = {
        "model": model_name,
        "temperature": temperature,
        "messages": [
            {"role": "system", "content": resolved_system_prompt},
            {"role": "user", "content": resolved_user_prompt},
        ],
    }

    key_errors: list[str] = []
    total_keys = len(openrouter_api_keys)
    for index, api_key in enumerate(openrouter_api_keys, start=1):
        print(f"[Orchestrator] Trying configured OpenRouter API key {index}/{total_keys}...")
        data = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        referer = os.getenv("OPENROUTER_SITE_URL", "").strip()
        app_title = os.getenv("OPENROUTER_APP_NAME", "AI Money Mentor").strip()
        if referer:
            headers["HTTP-Referer"] = referer
        if app_title:
            headers["X-Title"] = app_title

        req = urllib.request.Request(
            endpoint,
            data=data,
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                body = resp.read().decode("utf-8")
            response_json = json.loads(body)
            model_text = _extract_chat_completion_text(response_json)
            if not model_text:
                key_errors.append(f"key #{index}: no textual response")
                continue
            return _parse_json_payload(model_text)
        except urllib.error.HTTPError as exc:
            err_text = exc.read().decode("utf-8", errors="ignore")
            key_errors.append(f"key #{index}: HTTP {exc.code} {err_text[:180]}")
        except Exception as exc:
            key_errors.append(f"key #{index}: {exc}")

    raise RuntimeError("OpenRouter call failed for all configured keys. " + " | ".join(key_errors))


def run_orchestration_with_model(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """OpenRouter-only model orchestration path."""
    result = _run_openrouter_model(user_data)
    result["model_provider"] = "openrouter"
    result["model_used"] = os.getenv("OPENROUTER_MODEL", "openai/gpt-oss-20b")
    return result


def run_orchestration_with_model_schema_fix(
    user_data: Dict[str, Any], invalid_report: Dict[str, Any]
) -> Dict[str, Any]:
    """Second-pass OpenRouter call to repair schema while remaining API-only."""
    repair_system_prompt = (
        "You are a strict JSON schema repair assistant for AI Money Mentor. "
        "Return only valid JSON and no markdown. "
        "Mandatory top-level keys: health_score, score_breakdown, fire_data, goals_sip, gaps, roadmap, "
        "priority_actions, summary."
    )
    repair_user_prompt = (
        "The previous model output did not pass schema validation. "
        "Rewrite it into valid JSON with this structure requirements:\n"
        "- health_score: number\n"
        "- score_breakdown: object\n"
        "- fire_data: object with fire_number_inr or fire_number\n"
        "- goals_sip: array of objects each with name, target_amount, years, required_monthly_sip\n"
        "- gaps: array of objects each with gap_type, severity, current_value, recommended_value, action\n"
        "- roadmap: array of objects each with month, action\n"
        "- priority_actions: array\n"
        "- summary: string\n"
        f"Original user input: {json.dumps(user_data, ensure_ascii=False)}\n"
        f"Invalid model output to repair: {json.dumps(invalid_report, ensure_ascii=False)}"
    )

    result = _run_openrouter_model(
        user_data,
        system_prompt=repair_system_prompt,
        user_prompt=repair_user_prompt,
        temperature=0,
    )
    result["model_provider"] = "openrouter"
    result["model_used"] = os.getenv("OPENROUTER_MODEL", "openai/gpt-oss-20b")
    result["schema_repaired_by_model"] = True
    return result


def generate_gap_action_plan_with_model(
    gap: Dict[str, Any], profile: Dict[str, Any] | None = None
) -> Dict[str, Any]:
    """Generate exactly five concise, actionable steps for a specific gap using OpenRouter only."""
    safe_gap = gap if isinstance(gap, dict) else {}
    safe_profile = profile if isinstance(profile, dict) else {}

    system_prompt = (
        "You are a personal finance action planner. "
        "Return valid JSON only. No markdown, no extra text."
    )
    user_prompt = (
        "Create exactly 5 short actionable points to fix this financial gap. "
        "Keep each point under 18 words and practical for an Indian retail investor. "
        "Output strictly in this JSON format: "
        '{"title":"...","five_point_plan":["...","...","...","...","..."]}. '
        f"Gap data: {json.dumps(safe_gap, ensure_ascii=False)}. "
        f"Profile context: {json.dumps(safe_profile, ensure_ascii=False)}"
    )

    result = _run_openrouter_model(
        {"gap": safe_gap, "profile": safe_profile},
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=0.2,
    )

    plan = result.get("five_point_plan")
    if not isinstance(plan, list):
        raise ValueError("Model did not return five_point_plan array")

    cleaned_plan = [str(item).strip() for item in plan if str(item).strip()][:5]
    if len(cleaned_plan) < 5:
        raise ValueError("Model returned fewer than 5 actionable points")

    return {
        "title": str(result.get("title") or safe_gap.get("gap_type") or "How to Fix This Gap"),
        "five_point_plan": cleaned_plan,
        "model_provider": "openrouter",
        "model_used": os.getenv("OPENROUTER_MODEL", "openai/gpt-oss-20b"),
    }
