import streamlit as st
import requests

st.set_page_config(page_title="Research Assistant", layout="wide")

st.title("Research Assistant 🧬")
st.markdown("Welcome to your personalized research assistant powered by **Snowflake** and **Knowledge Graphs**.")

with st.sidebar:
    st.header("Settings")
    passcode = st.text_input("Snowflake MFA Passcode", type="password", help="Enter your Duo MFA token if required.")
    
    if st.button("Verify Connection"):
        with st.spinner("Connecting to Snowflake..."):
            try:
                res = requests.post("http://localhost:3001/auth", json={"passcode": passcode})
                data = res.json()
                if data.get("status") == "success":
                    st.success("Successfully authenticated with Snowflake!")
                else:
                    st.error(data.get("message", "Authentication failed."))
            except Exception as e:
                st.error(f"Cannot reach backend: {str(e)}")

    st.markdown("---")
    st.header("Chat History")
    try:
        hist_res = requests.get("http://localhost:3001/history")
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

# Chat Interface
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
                # Call backend API
                payload = {
                    "question": prompt,
                    "top_k": 5,
                    "passcode": passcode
                }
                res = requests.post("http://localhost:3001/query", json=payload)
                res.raise_for_status()
                data = res.json()
                
                # FastAPI returns a list with a single dict for some reason: [{ 'answer': ..., 'citations': ... }]
                if isinstance(data, list) and len(data) > 0:
                    data = data[0]

                answer = data.get("answer", "No answer provided.")
                citations = data.get("citations", [])
                confidence = data.get("confidence", 0.0)
                
                message_placeholder.markdown(answer)
                
                # Citation Display
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

