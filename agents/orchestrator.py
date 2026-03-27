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
    return deduped


def _run_openrouter_model(user_data: Dict[str, Any]) -> Dict[str, Any]:
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

    system_prompt = (
        "You are AI Money Mentor. Generate valid JSON only with keys: health_score, score_breakdown, "
        "fire_data, goals_sip, gaps, roadmap, priority_actions, summary. No markdown."
    )
    user_prompt = f"{MODEL_INSTRUCTION_PREFIX}Input payload: {json.dumps(user_data, ensure_ascii=False)}"
    payload = {
        "model": model_name,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }

    key_errors: list[str] = []
    for index, api_key in enumerate(openrouter_api_keys, start=1):
        print(f"[Orchestrator] Trying OpenRouter key #{index}...")
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
