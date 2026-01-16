import streamlit as st

st.set_page_config(page_title="Mental Health Support Calling Chatbot", page_icon=":robot_face:")
st.title("Mental Health Support Calling Chatbot")


if "messages" not in st.session_state:
    st.session_state.messages = []



user_input = st.chat_input("Ask a question about mental health support calling chatbot")
if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})


for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

