# CalmLink — Mental Health Support Calling Chatbot

CalmLink is an AI-powered mental health support chatbot that provides empathetic conversations and automatically detects crisis situations (suicidal ideation, self-harm, extreme distress). When a crisis is detected, CalmLink immediately places a Twilio phone call to the patient's registered psychiatrist so they can intervene.

## Architecture

```
Patient (Browser)
    |
    v
Streamlit Frontend (frontend.py)
    |  POST /ask
    v
FastAPI Backend (backend/main.py)
    |
    v
CalmLinkAgent (backend/ai_agent.py)
    |-- Keyword-based crisis check (fast, deterministic safety net)
    |-- LLM-based crisis classifier (Groq — catches nuanced language)
    |-- Empathetic response generator (Groq via LangChain)
    |
    +-- If crisis detected:
        +-- Twilio Call (backend/tools.py) -> Psychiatrist's phone
```

## Prerequisites

1. **Python 3.11+**
2. **Groq API key** (free at https://console.groq.com)
3. **Twilio account** with a verified phone number (https://console.twilio.com)

## Setup

```bash
# 1. Clone the repo
git clone <repo-url>
cd Mental-Health-Support-Calling-Chatbot

# 2. Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -e .
# or with uv:
uv pip install -e .

# 4. Configure environment variables
cp .env.example .env
# Edit .env with your real Twilio credentials, Groq API key, and phone numbers
```

## Running

You need two terminals:

**Terminal 1 — Backend:**
```bash
python main.py
# Backend starts on http://localhost:8000
```

**Terminal 2 — Frontend:**
```bash
streamlit run frontend.py
# Opens browser at http://localhost:8501
```

## How to Test the Crisis Flow

1. Start the backend and frontend as described above.
2. Open the Streamlit UI in your browser.
3. In the sidebar, enter a patient name and (optionally) a psychiatrist phone number.
4. Send a normal message first, e.g.: *"I've been feeling sad lately"* — you should get an empathetic response with NO crisis trigger.
5. Send a crisis message, e.g.: *"I don't want to live anymore"* — you should see:
   - The AI responds with immediate care and comfort
   - A yellow/red banner appears: "Your psychiatrist has been notified"
   - The psychiatrist's phone rings with a Twilio call saying the patient needs help
6. Other test phrases that should trigger crisis detection:
   - "I want to kill myself"
   - "I'm thinking about ending it all"
   - "Nobody cares, I want to die"
   - "I've been cutting myself"

## File Structure

```
├── main.py                  # Entry point — starts the backend server
├── frontend.py              # Streamlit chat UI
├── backend/
│   ├── __init__.py
│   ├── main.py              # FastAPI app, routes, session management
│   ├── ai_agent.py          # CalmLinkAgent — LLM chat + crisis detection
│   ├── config.py            # Environment variable loading
│   └── tools.py             # Twilio calling functions
├── .env.example             # Template for environment variables
├── .gitignore
├── pyproject.toml           # Python project metadata & dependencies
└── README.md
```

## Safety Notes

- CalmLink uses a **two-layer crisis detection** system: fast keyword matching (deterministic) + LLM-based classification (nuanced). This means dangerous phrases are NEVER missed even if the LLM is uncertain.
- The system always shows crisis hotline information in the UI.
- If the Twilio call fails, the patient is immediately told to call emergency services directly.
- CalmLink is NOT a replacement for professional mental health care. It is a support tool.
