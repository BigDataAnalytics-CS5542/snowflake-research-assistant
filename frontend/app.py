import os
from pathlib import Path

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:3001").rstrip("/")


def _show_snowflake_mfa_ui() -> bool:
    """Hide Duo/passcode UI when `SNOWFLAKE_PRIVATE_KEY` is set (key-pair auth)."""
    pk = (os.getenv("SNOWFLAKE_PRIVATE_KEY") or "").strip()
    return not bool(pk)


st.set_page_config(page_title="Research Assistant", layout="wide")

st.title("Research Assistant 🧬")
st.markdown("Welcome to your personalized research assistant powered by **Snowflake** and **Knowledge Graphs**.")

with st.sidebar:
    if _show_snowflake_mfa_ui():
        with st.expander("Snowflake MFA (password + Duo)", expanded=False):
            st.caption(
                "Use this **only** if you sign in with **Snowflake password + Duo** (not key-pair). "
                "After you **start or restart** the backend, send a **fresh** 6-digit code once, then chat."
            )
            mfa_code = st.text_input("Duo / MFA code", type="password", key="mfa_passcode", label_visibility="visible")
            if st.button("Send code to backend", key="mfa_submit"):
                if not mfa_code.strip():
                    st.warning("Enter your current MFA code.")
                else:
                    try:
                        res = requests.post(
                            f"{BACKEND_URL}/auth",
                            json={"passcode": mfa_code.strip()},
                            timeout=60,
                        )
                        data = res.json()
                        if data.get("status") == "success":
                            st.success("Snowflake session ready. You can chat below.")
                        else:
                            st.error(data.get("message", "Authentication failed."))
                    except Exception as e:
                        st.error(f"Cannot reach backend: {e}")

        st.markdown("---")

    st.header("Chat History")
    try:
        hist_res = requests.get(f"{BACKEND_URL}/history")
        hist_data = hist_res.json()
        if hist_data:
            for entry in reversed(hist_data):
                ts = entry.get("timestamp", "")[:19].replace("T", " ")
                with st.expander(f"{ts} — {entry.get('query', '')[:60]}"):
                    st.markdown(f"**Q:** {entry.get('query', '')}")
                    st.markdown(f"**A:** {entry.get('answer', '')}")
                    chunks = entry.get("chunks", [])
                    if chunks:
                        st.caption(f"{len(chunks)} citation(s)")
        else:
            st.caption("No history yet. Ask a question to get started.")
    except Exception:
        st.caption("Could not load history.")

# ── Chat Interface ────────────────────────────────────────────────────────────

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Ask a question about your research papers..."):
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        message_placeholder = st.empty()

        with st.spinner("Analyzing papers..."):
            try:
                payload = {
                    "question": prompt,
                    "top_k": 5,
                    "passcode": "",
                }
                res = requests.post(f"{BACKEND_URL}/query", json=payload)
                res.raise_for_status()
                data = res.json()

                if isinstance(data, list) and len(data) > 0:
                    data = data[0]

                answer = data.get("answer", "No answer provided.")
                citations = data.get("citations", [])
                confidence = data.get("confidence", 0.0)

                message_placeholder.markdown(answer)

                if citations:
                    with st.expander("View Citations & Confidence"):
                        st.write(f"**Confidence Score:** {confidence}")
                        for chunk in citations:
                            st.markdown("---")
                            st.write(f"**Score:** {round(chunk.get('score', 0), 3)}")
                            st.write(f"- Chunk ID: `{chunk.get('chunk_id')}` from Paper `{chunk.get('title')}`")
                            st.write(f"- Section: `{chunk.get('section')}`")
                            st.write(f"> {chunk.get('text')}")

            except Exception as e:
                answer = f"Error connecting to backend: {e}"
                message_placeholder.error(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})