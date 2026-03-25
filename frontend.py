"""
CalmLink — Streamlit Frontend
Patient-facing chat interface with real-time crisis feedback.
"""

import os
import uuid

import streamlit as st
import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# ---------------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="CalmLink — Mental Health Support",
    page_icon="\U0001f49a",  # Green heart
    layout="centered",
)

# ---------------------------------------------------------------------------
# Custom CSS for a calmer, more supportive UI
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    /* Softer background and fonts for a calming feel */
    .stApp {
        background-color: #f0f4f1;
    }
    .crisis-alert {
        background-color: #fff3cd;
        border-left: 5px solid #ff6b6b;
        padding: 15px;
        border-radius: 5px;
        margin: 10px 0;
        font-weight: 500;
    }
    .crisis-alert-critical {
        background-color: #f8d7da;
        border-left: 5px solid #dc3545;
        padding: 15px;
        border-radius: 5px;
        margin: 10px 0;
        font-weight: 600;
    }
    .help-banner {
        background-color: #e8f5e9;
        border-left: 5px solid #4caf50;
        padding: 12px;
        border-radius: 5px;
        margin: 10px 0;
        font-size: 0.9em;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title("\U0001f49a CalmLink")
st.caption("Your safe space to talk. A compassionate AI companion that listens.")

# Always-visible crisis helpline banner
st.markdown(
    '<div class="help-banner">'
    "<strong>If you are in immediate danger</strong>, please call your local emergency services "
    "or a crisis hotline: "
    "<strong>988 Suicide & Crisis Lifeline</strong> (US: call/text 988) | "
    "<strong>Crisis Text Line</strong> (text HOME to 741741)"
    "</div>",
    unsafe_allow_html=True,
)

st.divider()

# ---------------------------------------------------------------------------
# Session state initialization
# ---------------------------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

# ---------------------------------------------------------------------------
# Sidebar — patient info (in a real app, this would come from authentication)
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Patient Settings")
    patient_name = st.text_input("Your name", value="Patient", key="patient_name")
    psychiatrist_phone = st.text_input(
        "Psychiatrist phone (E.164)",
        value="",
        placeholder="+1XXXXXXXXXX",
        key="psychiatrist_phone",
        help="Your psychiatrist's phone number. Leave blank to use the default emergency contact.",
    )
    st.divider()
    st.caption("CalmLink v1.0 — Not a substitute for professional care.")
    if st.button("Clear Chat"):
        st.session_state.messages = []
        st.session_state.session_id = str(uuid.uuid4())
        st.rerun()

# ---------------------------------------------------------------------------
# Display conversation history
# ---------------------------------------------------------------------------
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        # Show a crisis alert badge on messages that triggered a crisis
        if msg.get("crisis_detected"):
            if msg.get("call_initiated"):
                st.markdown(
                    '<div class="crisis-alert">'
                    "\U0001f4de <strong>Your psychiatrist has been notified and will call you shortly.</strong>"
                    "</div>",
                    unsafe_allow_html=True,
                )
            elif msg.get("error"):
                st.markdown(
                    '<div class="crisis-alert-critical">'
                    "\u26a0\ufe0f <strong>We tried to reach your psychiatrist but encountered an issue. "
                    "Please call your local emergency services or 988 immediately.</strong>"
                    "</div>",
                    unsafe_allow_html=True,
                )

# ---------------------------------------------------------------------------
# Chat input
# ---------------------------------------------------------------------------
user_input = st.chat_input("How are you feeling today?")

if user_input:
    # Display user message immediately
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # Call backend
    with st.chat_message("assistant"):
        with st.spinner("Listening..."):
            try:
                res = requests.post(
                    f"{BACKEND_URL}/ask",
                    json={
                        "message": user_input,
                        "session_id": st.session_state.session_id,
                        "patient_name": patient_name,
                        "psychiatrist_phone": psychiatrist_phone,
                    },
                    timeout=60,  # LLM can be slow on first call
                )
                res.raise_for_status()
                data = res.json()

                reply = data.get("reply", "I'm here for you. Could you say more?")
                crisis_detected = data.get("crisis_detected", False)
                call_initiated = data.get("call_initiated", False)
                error = data.get("error")

                # Display the AI reply
                st.markdown(reply)

                # Show crisis feedback
                if crisis_detected and call_initiated:
                    st.markdown(
                        '<div class="crisis-alert">'
                        "\U0001f4de <strong>Your psychiatrist has been notified and will call you shortly.</strong>"
                        "</div>",
                        unsafe_allow_html=True,
                    )
                elif crisis_detected and not call_initiated:
                    st.markdown(
                        '<div class="crisis-alert-critical">'
                        "\u26a0\ufe0f <strong>We tried to reach your psychiatrist but encountered an issue. "
                        "Please call your local emergency services or 988 immediately.</strong>"
                        "</div>",
                        unsafe_allow_html=True,
                    )

                # Store in session state
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": reply,
                    "crisis_detected": crisis_detected,
                    "call_initiated": call_initiated,
                    "error": error,
                })

            except requests.ConnectionError:
                error_msg = (
                    "I'm having trouble connecting to the support service. "
                    "Please make sure the backend is running. "
                    "If you are in crisis, call 988 or your local emergency services."
                )
                st.error(error_msg)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_msg,
                })
            except requests.Timeout:
                error_msg = (
                    "The response is taking longer than expected. Please try again. "
                    "If you need immediate help, call 988 or your local emergency services."
                )
                st.error(error_msg)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_msg,
                })
            except Exception as e:
                error_msg = (
                    "Something went wrong. Please try again. "
                    "If you are in crisis, call 988 or your local emergency services."
                )
                st.error(error_msg)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_msg,
                })
