"""
CalmLink — AI Agent
Empathetic mental-health chatbot with real-time crisis detection.
Uses Groq (cloud LLM) via LangChain for both conversation and safety analysis.
"""

import logging

from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from backend.config import GROQ_API_KEY, GROQ_MODEL, EMERGENCY_CONTACT
from backend.tools import trigger_crisis_call

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Crisis-detection keyword list (checked BEFORE LLM for speed + reliability)
# These are phrases that should ALWAYS trigger a crisis flag, regardless of
# what the LLM thinks. This acts as a safety net.
# ---------------------------------------------------------------------------
CRISIS_PHRASES = [
    # Suicidal ideation
    "i want to kill myself",
    "i want to die",
    "i don't want to live",
    "i dont want to live",
    "i do not want to live",
    "kill myself",
    "end my life",
    "end it all",
    "take my own life",
    "wish i was dead",
    "wish i were dead",
    "better off dead",
    "want to be dead",
    "suicide",
    "suicidal",
    "no reason to live",
    "not worth living",
    "can't go on",
    "cant go on",
    "i give up on life",
    "i'm going to kill myself",
    "im going to kill myself",
    "planning to end",
    "thinking about ending it",
    "no point in living",
    "life is not worth",
    "life isn't worth",
    # Self-harm
    "hurt myself",
    "harm myself",
    "cut myself",
    "cutting myself",
    "self harm",
    "self-harm",
    # Hopelessness / extreme distress
    "nobody cares",
    "no one cares",
    "everyone would be better off without me",
    "world would be better without me",
    "i can't take it anymore",
    "i cant take it anymore",
    "i cannot take this anymore",
]

# System prompt that defines the AI agent's personality and safety behavior
SYSTEM_PROMPT = """You are CalmLink, a compassionate and empathetic mental health support assistant. Your role is to:

1. Listen carefully and respond with genuine empathy and warmth.
2. Validate the user's feelings without judgment.
3. Offer gentle coping suggestions when appropriate (breathing exercises, grounding techniques, journaling).
4. NEVER diagnose conditions or prescribe medication.
5. NEVER dismiss or minimize the user's feelings.
6. If the user expresses suicidal thoughts, self-harm, or extreme distress, respond with immediate care and let them know help is being arranged.

Important safety rules:
- You are NOT a replacement for professional help. Encourage professional support when appropriate.
- Always maintain a calm, warm, and supportive tone.
- Keep responses concise but caring — do not overwhelm with long paragraphs.
- If the user seems to be in crisis, acknowledge their pain and reassure them that someone who can help is being contacted right now.
"""

# Separate prompt used to classify whether a message indicates crisis
CRISIS_CLASSIFIER_PROMPT = """You are a mental health crisis classifier. Analyze the following patient message and determine if it indicates a mental health CRISIS.

A CRISIS means the patient is expressing:
- Suicidal ideation or intent (wanting to die, planning to end their life)
- Active self-harm or intent to self-harm
- Severe emotional breakdown requiring immediate professional intervention
- Expressions of complete hopelessness combined with intent to act

Respond with EXACTLY one word: CRISIS or SAFE

Do NOT classify general sadness, frustration, or venting as CRISIS. Only flag genuine danger.

Patient message: "{message}"

Classification:"""


class CalmLinkAgent:
    """
    Manages conversation state and crisis detection for one patient session.
    """

    def __init__(self, patient_name: str = "Patient", psychiatrist_phone: str = ""):
        self.patient_name = patient_name
        # Use patient's psychiatrist number, or fall back to the global emergency contact
        self.psychiatrist_phone = psychiatrist_phone or EMERGENCY_CONTACT
        self.conversation_history: list = []
        self.crisis_triggered = False

        # Use Groq cloud LLM (fast inference via LangChain)
        self.chat_llm = ChatGroq(
            model=GROQ_MODEL,
            api_key=GROQ_API_KEY,
            temperature=0.7,  # Slightly creative for empathetic responses
        )
        self.classifier_llm = ChatGroq(
            model=GROQ_MODEL,
            api_key=GROQ_API_KEY,
            temperature=0.0,  # Deterministic for safety classification
        )

    def _check_crisis_keywords(self, message: str) -> bool:
        """
        Fast keyword-based crisis check. Runs BEFORE the LLM classifier as a
        safety net — ensures dangerous phrases are NEVER missed even if the LLM
        hallucinates a 'SAFE' classification.
        """
        msg_lower = message.lower().strip()
        for phrase in CRISIS_PHRASES:
            if phrase in msg_lower:
                logger.warning("Crisis keyword detected: '%s'", phrase)
                return True
        return False

    def _check_crisis_llm(self, message: str) -> bool:
        """
        LLM-based crisis classification for nuanced messages that keywords might miss.
        Returns True if the LLM thinks the message indicates a crisis.
        """
        try:
            prompt = CRISIS_CLASSIFIER_PROMPT.format(message=message)
            response = self.classifier_llm.invoke([HumanMessage(content=prompt)])
            classification = response.content.strip().upper()
            logger.info("LLM crisis classification: %s", classification)
            # Accept any response starting with "CRISIS"
            return classification.startswith("CRISIS")
        except Exception as e:
            # FIX: If the classifier fails, err on the side of caution
            logger.error("Crisis classifier failed: %s — defaulting to safe", e)
            return False

    def _trigger_crisis_response(self) -> dict:
        """
        Initiate the Twilio call to the patient's psychiatrist.
        Returns the call result dict.
        """
        if not self.psychiatrist_phone:
            logger.error("No psychiatrist phone number configured!")
            return {"success": False, "call_sid": None, "error": "No psychiatrist phone number on file"}

        logger.warning(
            "CRISIS TRIGGERED for patient '%s' — calling psychiatrist at %s",
            self.patient_name,
            self.psychiatrist_phone,
        )
        result = trigger_crisis_call(
            to_number=self.psychiatrist_phone,
            patient_name=self.patient_name,
        )
        self.crisis_triggered = True
        return result

    def _generate_response(self, user_message: str, is_crisis: bool) -> str:
        """
        Generate an empathetic AI response using the LLM with full conversation context.
        """
        messages = [SystemMessage(content=SYSTEM_PROMPT)]

        # Add conversation history for context (keep last 20 turns to avoid token overflow)
        for turn in self.conversation_history[-20:]:
            if turn["role"] == "user":
                messages.append(HumanMessage(content=turn["content"]))
            else:
                messages.append(AIMessage(content=turn["content"]))

        # Add the current message
        messages.append(HumanMessage(content=user_message))

        # If crisis, prepend a system nudge so the LLM responds appropriately
        if is_crisis:
            messages.append(
                SystemMessage(
                    content=(
                        "IMPORTANT: The patient has just expressed something indicating a crisis. "
                        "Their psychiatrist is being called right now. Acknowledge their pain, "
                        "tell them help is on the way, and provide immediate comfort. "
                        "Do NOT be dismissive. Be direct that you've arranged for their doctor to call them."
                    )
                )
            )

        try:
            response = self.chat_llm.invoke(messages)
            return response.content.strip()
        except Exception as e:
            logger.error("LLM response generation failed: %s", e)
            # Fallback: a safe, pre-written empathetic response
            if is_crisis:
                return (
                    "I hear you, and I want you to know that what you're feeling matters. "
                    "I've contacted your psychiatrist and they will be calling you very soon. "
                    "You are not alone in this. Please stay with me."
                )
            return (
                "I'm here to listen and support you. Could you tell me more about "
                "what you're going through? Remember, you don't have to face this alone."
            )

    def process_message(self, user_message: str) -> dict:
        """
        Main entry point: process a patient message and return the response.

        Returns:
            dict with keys:
                - reply (str): The AI's empathetic response
                - crisis_detected (bool): Whether crisis was flagged
                - call_initiated (bool): Whether a Twilio call was placed
                - call_sid (str|None): Twilio call SID if call was placed
                - error (str|None): Error message if call failed
        """
        # Store user message in conversation history
        self.conversation_history.append({"role": "user", "content": user_message})

        # --- CRISIS DETECTION (two-layer: keywords first, then LLM) ---
        is_crisis = self._check_crisis_keywords(user_message)
        if not is_crisis:
            is_crisis = self._check_crisis_llm(user_message)

        # --- TRIGGER CALL if crisis detected ---
        call_result = {"success": False, "call_sid": None, "error": None}
        if is_crisis:
            call_result = self._trigger_crisis_response()

        # --- GENERATE EMPATHETIC RESPONSE ---
        reply = self._generate_response(user_message, is_crisis)

        # If crisis, append the call status to the reply so the patient knows
        if is_crisis and call_result["success"]:
            reply += (
                "\n\n---\n"
                "I've reached out to your psychiatrist. They will be calling you shortly. "
                "Please stay on the line or keep this chat open. You are not alone."
            )
        elif is_crisis and not call_result["success"]:
            reply += (
                "\n\n---\n"
                "I tried to reach your psychiatrist but encountered an issue. "
                "If you are in immediate danger, please call your local emergency services "
                "or a crisis hotline right away."
            )

        # Store AI response in conversation history
        self.conversation_history.append({"role": "assistant", "content": reply})

        return {
            "reply": reply,
            "crisis_detected": is_crisis,
            "call_initiated": call_result["success"],
            "call_sid": call_result.get("call_sid"),
            "error": call_result.get("error"),
        }
