"""
CalmLink — FastAPI Backend
Serves the chat API and manages per-session AI agent instances.
"""

import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.config import BACKEND_HOST, BACKEND_PORT, validate_config
from backend.ai_agent import CalmLinkAgent

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# In-memory session store: session_id -> CalmLinkAgent
# In production, replace with Redis or a database-backed session store.
# ---------------------------------------------------------------------------
sessions: dict[str, CalmLinkAgent] = {}


# ---------------------------------------------------------------------------
# App lifecycle — validate config on startup
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Validate required env vars before accepting requests."""
    validate_config()
    logger.info("CalmLink backend starting — config OK")
    yield
    logger.info("CalmLink backend shutting down")


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(
    title="CalmLink API",
    description="Mental health support chatbot with crisis detection and Twilio calling",
    version="1.0.0",
    lifespan=lifespan,
)

# FIX: Add CORS so the Streamlit frontend (port 8501) can reach us
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten in production
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------
class ChatRequest(BaseModel):
    """Incoming chat message from the frontend."""
    message: str
    session_id: str = "default"
    patient_name: str = "Patient"
    psychiatrist_phone: str = ""  # Optional override per-request


class ChatResponse(BaseModel):
    """Structured response back to the frontend."""
    reply: str
    crisis_detected: bool = False
    call_initiated: bool = False
    call_sid: str | None = None
    error: str | None = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.post("/ask", response_model=ChatResponse)
async def ask(req: ChatRequest):
    """
    Main chat endpoint.
    Receives a patient message, runs it through the AI agent (empathetic reply
    + crisis detection), and returns a structured response.
    """
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    # Get or create a session-scoped agent so conversation history is preserved
    agent = sessions.get(req.session_id)
    if agent is None:
        agent = CalmLinkAgent(
            patient_name=req.patient_name,
            psychiatrist_phone=req.psychiatrist_phone,
        )
        sessions[req.session_id] = agent
        logger.info("New session created: %s", req.session_id)

    # Process the message through the AI agent
    result = agent.process_message(req.message)

    return ChatResponse(
        reply=result["reply"],
        crisis_detected=result["crisis_detected"],
        call_initiated=result["call_initiated"],
        call_sid=result.get("call_sid"),
        error=result.get("error"),
    )


@app.get("/health")
async def health():
    """Simple health check endpoint."""
    return {"status": "ok", "service": "calmlink"}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host=BACKEND_HOST,
        port=BACKEND_PORT,
        reload=True,
    )
