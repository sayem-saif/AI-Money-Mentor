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
- Gemini API client (`google-generativeai`)
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
3. Create `.env` from `.env.example` and add your Gemini API key:
   ```env
   GEMINI_API_KEY=your_key_here
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

## Screenshots

- Dashboard screenshot: _placeholder_
- Input form screenshot: _placeholder_

## Team

- Team name: _placeholder_
- Members: _placeholder_

