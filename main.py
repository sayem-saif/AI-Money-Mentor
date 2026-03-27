import os
from typing import Any, Dict

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from flask_cors import CORS

from agents import run_orchestration, run_orchestration_with_model

load_dotenv(override=True)

app = Flask(__name__)
CORS(app)


def _has_required_fields(item: Any, required: list[str]) -> bool:
    if not isinstance(item, dict):
        return False
    for key in required:
        if key not in item:
            return False
        value = item.get(key)
        if value is None:
            return False
        if isinstance(value, str) and not value.strip():
            return False
    return True


def _is_model_response_usable(report: Dict[str, Any]) -> bool:
    if not isinstance(report, dict):
        return False

    if not isinstance(report.get("health_score"), (int, float)):
        return False

    fire_data = report.get("fire_data")
    if not isinstance(fire_data, dict):
        return False
    if "fire_number_inr" not in fire_data and "fire_number" not in fire_data:
        return False

    goals = report.get("goals_sip")
    gaps = report.get("gaps")
    roadmap = report.get("roadmap")
    if not isinstance(goals, list) or not isinstance(gaps, list) or not isinstance(roadmap, list):
        return False

    # Frontend expects each goals item to include these fields.
    if goals and not all(
        _has_required_fields(goal, ["name", "target_amount", "years", "required_monthly_sip"])
        for goal in goals
    ):
        return False

    # Frontend expects gap cards to include these fields.
    if gaps and not all(
        _has_required_fields(gap, ["gap_type", "severity", "current_value", "recommended_value", "action"])
        for gap in gaps
    ):
        return False

    # Frontend expects roadmap rows with month and action.
    if roadmap and not all(_has_required_fields(step, ["month", "action"]) for step in roadmap):
        return False

    return True


def _repair_with_deterministic_schema(model_report: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    """Keep model narrative when possible, but guarantee frontend-safe schema."""
    deterministic_report = run_orchestration(payload)

    # Preserve model narrative fields if they are present and non-empty.
    if isinstance(model_report, dict):
        summary = model_report.get("summary")
        if isinstance(summary, str) and summary.strip():
            deterministic_report["summary"] = summary

        motivation = model_report.get("motivational_message")
        if isinstance(motivation, str) and motivation.strip():
            deterministic_report["motivational_message"] = motivation

        actions = model_report.get("priority_actions")
        if isinstance(actions, list) and actions:
            cleaned_actions = [str(item).strip() for item in actions if str(item).strip()]
            if cleaned_actions:
                deterministic_report["priority_actions"] = cleaned_actions[:5]

    deterministic_report["model_provider"] = "schema-repair"
    deterministic_report["model_used"] = "deterministic-guardrail"
    return deterministic_report


@app.route("/")
def index() -> str:
    return render_template("index.html")


@app.route("/health", methods=["GET"])
def health() -> Any:
    return jsonify({"status": "ok"})


@app.route("/api/analyze", methods=["POST"])
def analyze() -> Any:
    payload: Dict[str, Any] = request.get_json(silent=True) or {}
    if not payload:
        return jsonify({"error": "Request body must be valid JSON."}), 400

    required_fields = ["name", "age", "monthly_income", "monthly_expenses", "risk_appetite", "goals"]
    missing = [field for field in required_fields if field not in payload]
    if missing:
        return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400

    try:
        print("[API] Starting AI Money Mentor multi-agent analysis...")
        use_model_mode = os.getenv("USE_MODEL_AGENT", "true").strip().lower() == "true"
        if use_model_mode:
            print("[API] Using OpenRouter model orchestration mode...")
            try:
                report = run_orchestration_with_model(payload)
                if not _is_model_response_usable(report):
                    print("[API] Model output schema mismatch detected, repairing response...")
                    report = _repair_with_deterministic_schema(report, payload)
            except Exception as model_exc:
                print(f"[API] Model chain failed: {model_exc}")
                deterministic_fallback = (
                    os.getenv("ALLOW_DETERMINISTIC_FALLBACK", "false").strip().lower() == "true"
                )
                if deterministic_fallback:
                    print("[API] Falling back to deterministic local orchestration...")
                    report = run_orchestration(payload)
                    report["model_provider"] = "deterministic-fallback"
                    report["model_used"] = "local-python-tools"
                    report["fallback_reason"] = str(model_exc)
                else:
                    raise
        else:
            print("[API] Using deterministic orchestration mode...")
            report = run_orchestration(payload)
        print("[API] Analysis complete.")
        return jsonify(report)
    except Exception as exc:
        print(f"[API] Analysis failed: {exc}")
        return (
            jsonify(
                {
                    "error": "We could not complete your analysis right now. Please retry in a moment.",
                    "details": str(exc),
                }
            ),
            500,
        )


if __name__ == "__main__":
    api_key = os.getenv("OPENROUTER_API_KEY", "")
    if not api_key:
        print("[Startup] Warning: OPENROUTER_API_KEY is not set in .env")
    app.run(host="0.0.0.0", port=5000, debug=True)
