import os
from typing import Any, Dict

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from flask_cors import CORS

from agents import run_orchestration

load_dotenv()

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
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        print("[Startup] Warning: GEMINI_API_KEY is not set in .env")
    app.run(host="0.0.0.0", port=5000, debug=True)
