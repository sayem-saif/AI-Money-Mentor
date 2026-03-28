import os
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from flask_cors import CORS

from agents import run_orchestration, run_orchestration_with_model
from agents.fire_calculator_agent import calculate_fire
from agents.portfolio_xray_agent import run_portfolio_xray
from agents.tax_wizard_agent import run_tax_wizard
from tools.finance_tools import compute_health_score_quick, recalculate_fire_projection, validate_and_structure_profile

load_dotenv(override=True)

app = Flask(__name__)
CORS(app)

AUDIT_LOG_FILE = Path("audit_trail.jsonl")


def _append_audit_log(endpoint: str, status: str, payload: Dict[str, Any], response: Dict[str, Any]) -> None:
    AUDIT_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "endpoint": endpoint,
        "status": status,
        "input": payload,
        "output_summary": {
            "health_score": response.get("health_score") if isinstance(response, dict) else None,
            "keys": list(response.keys())[:15] if isinstance(response, dict) else [],
        },
    }
    with AUDIT_LOG_FILE.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def _read_audit_logs(limit: int = 100) -> list[Dict[str, Any]]:
    if not AUDIT_LOG_FILE.exists():
        return []
    rows: list[Dict[str, Any]] = []
    with AUDIT_LOG_FILE.open("r", encoding="utf-8") as handle:
        for line in handle:
            text = line.strip()
            if not text:
                continue
            try:
                rows.append(json.loads(text))
            except json.JSONDecodeError:
                continue
    return rows[-limit:][::-1]


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
        deterministic_fallback = (
            os.getenv("ALLOW_DETERMINISTIC_FALLBACK", "true").strip().lower() == "true"
        )
        has_openrouter_keys = bool(
            os.getenv("OPENROUTER_API_KEY", "").strip() or os.getenv("OPENROUTER_API_KEYS", "").strip()
        )

        if use_model_mode:
            print("[API] Using OpenRouter model orchestration mode...")
            if not has_openrouter_keys:
                if deterministic_fallback:
                    print("[API] OpenRouter keys missing. Falling back to deterministic local orchestration...")
                    report = run_orchestration(payload)
                    report["model_provider"] = "deterministic-fallback"
                    report["model_used"] = "local-python-tools"
                    report["fallback_reason"] = "OPENROUTER_API_KEY/OPENROUTER_API_KEYS missing"
                else:
                    raise RuntimeError("OPENROUTER_API_KEY/OPENROUTER_API_KEYS missing and fallback disabled")
            else:
                try:
                    report = run_orchestration_with_model(payload)
                    if not _is_model_response_usable(report):
                        print("[API] Model output schema mismatch detected, repairing response...")
                        report = _repair_with_deterministic_schema(report, payload)
                except Exception as model_exc:
                    print(f"[API] Model chain failed: {model_exc}")
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
        _append_audit_log("/api/analyze", "success", payload, report)
        return jsonify(report)
    except Exception as exc:
        print(f"[API] Analysis failed: {exc}")
        _append_audit_log("/api/analyze", "error", payload, {"error": str(exc)})
        return (
            jsonify(
                {
                    "error": "We could not complete your analysis right now. Please retry in a moment.",
                    "details": str(exc),
                }
            ),
            500,
        )


@app.route("/api/tax-wizard", methods=["POST"])
def tax_wizard() -> Any:
    payload: Dict[str, Any] = request.get_json(silent=True) or {}
    if not payload:
        return jsonify({"error": "Request body must be valid JSON."}), 400
    try:
        result = run_tax_wizard(payload)
        _append_audit_log("/api/tax-wizard", "success", payload, result)
        return jsonify(result)
    except Exception as exc:
        _append_audit_log("/api/tax-wizard", "error", payload, {"error": str(exc)})
        return jsonify({"error": "Failed to run tax wizard.", "details": str(exc)}), 500


@app.route("/api/portfolio-xray", methods=["POST"])
def portfolio_xray() -> Any:
    payload: Dict[str, Any] = request.get_json(silent=True) or {}
    if not payload:
        return jsonify({"error": "Request body must be valid JSON."}), 400
    try:
        result = run_portfolio_xray(payload)
        _append_audit_log("/api/portfolio-xray", "success", payload, result)
        return jsonify(result)
    except Exception as exc:
        _append_audit_log("/api/portfolio-xray", "error", payload, {"error": str(exc)})
        return jsonify({"error": "Failed to run portfolio x-ray.", "details": str(exc)}), 500


@app.route("/api/audit-log", methods=["GET"])
def audit_log() -> Any:
    limit_raw = request.args.get("limit", "50")
    try:
        limit = max(1, min(500, int(limit_raw)))
    except ValueError:
        limit = 50
    return jsonify({"logs": _read_audit_logs(limit)})


@app.route("/api/recalculate", methods=["POST"])
def recalculate() -> Any:
    payload: Dict[str, Any] = request.get_json(silent=True) or {}
    profile_input = payload.get("profile")
    if not isinstance(profile_input, dict):
        return jsonify({"error": "profile object is required for recalculation."}), 400

    retirement_age = float(payload.get("retirement_age", 60))
    expected_returns = float(payload.get("expected_returns", 11))
    target_monthly_corpus_draw = float(payload.get("target_monthly_corpus_draw", 100000))

    try:
        profile = validate_and_structure_profile(profile_input)
        # Requirement alignment: keep the recalculation path FIRE-focused.
        _ = calculate_fire(profile)
        fire_projection = recalculate_fire_projection(
            profile=profile,
            retirement_age=retirement_age,
            expected_returns=expected_returns,
            target_monthly_corpus_draw=target_monthly_corpus_draw,
        )
        score = compute_health_score_quick(profile, fire_projection)
        result = {
            "fire_data": fire_projection,
            "health_score": score["health_score"],
            "score_breakdown": score["score_breakdown"],
        }
        _append_audit_log("/api/recalculate", "success", payload, result)
        return jsonify(result)
    except Exception as exc:
        _append_audit_log("/api/recalculate", "error", payload, {"error": str(exc)})
        return jsonify({"error": "Failed to recalculate.", "details": str(exc)}), 500


@app.errorhandler(404)
def handle_404(error: Any) -> Any:
    if request.path.startswith("/api/"):
        return jsonify({"error": "API endpoint not found.", "path": request.path}), 404
    return error


@app.errorhandler(405)
def handle_405(error: Any) -> Any:
    if request.path.startswith("/api/"):
        return jsonify({"error": "Method not allowed for this API endpoint.", "path": request.path}), 405
    return error


@app.errorhandler(500)
def handle_500(error: Any) -> Any:
    if request.path.startswith("/api/"):
        return jsonify({"error": "Internal server error."}), 500
    return error


if __name__ == "__main__":
    api_key = os.getenv("OPENROUTER_API_KEY", "")
    if not api_key:
        print("[Startup] Warning: OPENROUTER_API_KEY is not set in .env")
    app.run(host="0.0.0.0", port=5000, debug=True)
