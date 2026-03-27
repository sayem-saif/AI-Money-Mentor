import os
from typing import Any, Dict

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from flask_cors import CORS

from agents import run_orchestration, run_orchestration_with_model

load_dotenv(override=True)

app = Flask(__name__)
CORS(app)


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
