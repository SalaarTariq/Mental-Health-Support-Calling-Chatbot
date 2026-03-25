"""
CalmLink Configuration
Loads all sensitive credentials from environment variables.
Never hardcode secrets — use a .env file locally (see .env.example).
"""

import os
from dotenv import load_dotenv

# Load .env file from project root (one level up from backend/)
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

# --- Twilio credentials (REQUIRED for crisis call feature) ---
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER", "")

# --- Default emergency contact (fallback if patient has no psychiatrist on file) ---
EMERGENCY_CONTACT = os.getenv("EMERGENCY_CONTACT", "")

# --- Groq LLM configuration ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# --- Application settings ---
BACKEND_HOST = os.getenv("BACKEND_HOST", "0.0.0.0")
BACKEND_PORT = int(os.getenv("BACKEND_PORT", "8000"))


def validate_config():
    """Validate that all required config values are set. Call at startup."""
    missing = []
    if not TWILIO_ACCOUNT_SID:
        missing.append("TWILIO_ACCOUNT_SID")
    if not TWILIO_AUTH_TOKEN:
        missing.append("TWILIO_AUTH_TOKEN")
    if not TWILIO_PHONE_NUMBER:
        missing.append("TWILIO_PHONE_NUMBER")
    if not EMERGENCY_CONTACT:
        missing.append("EMERGENCY_CONTACT")

    if not GROQ_API_KEY:
        missing.append("GROQ_API_KEY")

    if missing:
        raise EnvironmentError(
            f"Missing required environment variables: {', '.join(missing)}. "
            f"Copy .env.example to .env and fill in the values."
        )
