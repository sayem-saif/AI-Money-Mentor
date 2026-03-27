# AI Money Mentor

AI Money Mentor is a multi-agent personal finance advisory system built for **ET AI Hackathon 2026 (Problem Statement 9)**. It takes user financial details and generates a practical roadmap with FIRE planning, SIP recommendations, risk gaps, tax-saving suggestions, and a Money Health Score.

## Architecture

```text
[Frontend Form]
   -> POST /api/analyze
      -> Orchestrator Agent
         -> Profiling Agent
         -> FIRE Calculator Agent
         -> Risk & Gap Analyzer Agent
         -> Report Generator Agent
      -> Final JSON report
   -> Dashboard Rendering
```

## Tech Stack

- Python 3.10+
- Google ADK (`google-adk`)
- Flask + Flask-CORS
- HTML, CSS, JavaScript (single page UI)
- python-dotenv

## Project Structure

```text
ai-money-mentor/
├── .env.example
├── .env
├── .gitignore
├── requirements.txt
├── README.md
├── main.py
├── agents/
│   ├── __init__.py
│   ├── orchestrator.py
│   ├── profiling_agent.py
│   ├── fire_calculator_agent.py
│   ├── risk_gap_agent.py
│   └── report_agent.py
├── tools/
│   ├── __init__.py
│   └── finance_tools.py
├── static/
│   ├── style.css
│   └── script.js
└── templates/
    └── index.html
```

## Setup Instructions

1. Clone the repository.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create `.env` from `.env.example` and add your OpenRouter settings:
   ```env
   OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
   OPENROUTER_API_KEY=your_sk-or-v1_key
   OPENROUTER_MODEL=openai/gpt-oss-20b
   OPENROUTER_SITE_URL=https://your-site.example
   OPENROUTER_APP_NAME=AI Money Mentor
   ```
4. Start the app:
   ```bash
   python main.py
   ```
5. Open `http://localhost:5000`.

## Agents

- **Orchestrator Agent**: Controls the end-to-end sequence and combines outputs.
- **Profiling Agent**: Validates and structures raw user financial input.
- **FIRE Calculator Agent**: Computes FIRE number, SIP by goal, allocation, emergency target, and 12-month milestones.
- **Risk & Gap Analyzer Agent**: Flags insurance, tax, emergency fund, spending, and retirement gaps.
- **Report Generator Agent**: Produces health score, summary, priority actions, and 12-month roadmap.

## API Endpoints

- `GET /health` -> `{ "status": "ok" }`
- `POST /api/analyze` -> full structured finance advisory report

## Model Fallback Chain

- Provider: OpenRouter only (`OPENROUTER_API_KEY` / `OPENROUTER_API_KEYS`)
- Optional multi-key rotation using `OPENROUTER_API_KEYS`
- Optional final local fallback: set `ALLOW_DETERMINISTIC_FALLBACK=true`


## Team

- Team name: Money Mentor
- MD Sayem Saif

