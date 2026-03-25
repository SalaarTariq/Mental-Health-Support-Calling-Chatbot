"""
CalmLink — Twilio Call Tools
Handles outbound crisis calls to psychiatrists.
"""

import logging
from xml.sax.saxutils import escape as xml_escape

from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

from backend.config import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER

logger = logging.getLogger(__name__)

# Singleton Twilio client — avoids re-creating on every call
_twilio_client: Client | None = None


def _get_twilio_client() -> Client:
    """Return a cached Twilio client instance."""
    global _twilio_client
    if _twilio_client is None:
        _twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    return _twilio_client


def trigger_crisis_call(to_number: str, patient_name: str = "A patient") -> dict:
    """
    Place an outbound Twilio call to a psychiatrist when a crisis is detected.

    Args:
        to_number: The psychiatrist's phone number (E.164 format).
        patient_name: The patient's name for the voice message.

    Returns:
        dict with "success" (bool), "call_sid" (str|None), "error" (str|None).
    """
    # FIX: xml_escape prevents TwiML injection — the old code used raw f-strings
    safe_name = xml_escape(patient_name)

    twiml = (
        '<Response>'
        '<Say voice="alice">'
        f'Urgent: This is CalmLink, your mental health monitoring system. '
        f'Your patient, {safe_name}, has expressed thoughts indicating a crisis '
        f'and may need immediate support. '
        f'Please reach out to them as soon as possible. '
        f'Repeating: your patient {safe_name} needs urgent assistance.'
        '</Say>'
        '<Pause length="2"/>'
        '<Say voice="alice">'
        f'Again, your patient {safe_name} has triggered a crisis alert. '
        f'Please contact them immediately.'
        '</Say>'
        '</Response>'
    )

    try:
        client = _get_twilio_client()
        call = client.calls.create(
            twiml=twiml,
            to=to_number,
            from_=TWILIO_PHONE_NUMBER,
        )
        logger.info(
            "Crisis call initiated | to=%s | call_sid=%s", to_number, call.sid
        )
        return {"success": True, "call_sid": call.sid, "error": None}

    except TwilioRestException as e:
        logger.error("Twilio API error during crisis call: %s", e)
        return {"success": False, "call_sid": None, "error": f"Twilio error: {e.msg}"}

    except Exception as e:
        logger.error("Unexpected error during crisis call: %s", e, exc_info=True)
        return {"success": False, "call_sid": None, "error": str(e)}
