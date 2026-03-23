import os
from collections import Counter
from pathlib import Path

import pandas as pd
import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:3001").rstrip("/")


def _show_snowflake_mfa_ui() -> bool:
    """Hide Duo/passcode UI when `SNOWFLAKE_PRIVATE_KEY` is set (key-pair auth)."""
    pk = (os.getenv("SNOWFLAKE_PRIVATE_KEY") or "").strip()
    return not bool(pk)


# ── Cached data fetchers ─────────────────────────────────────────────────────

@st.cache_data(ttl=30)
def fetch_history():
    try:
        res = requests.get(f"{BACKEND_URL}/history", timeout=10)
        res.raise_for_status()
        return res.json()
    except Exception:
        return []


@st.cache_data(ttl=30)
def fetch_metrics():
    try:
        res = requests.get(f"{BACKEND_URL}/metrics", timeout=10)
        res.raise_for_status()
        return res.json()
    except Exception:
        return None


@st.cache_data(ttl=30)
def fetch_metrics_history():
    try:
        res = requests.get(f"{BACKEND_URL}/metrics/history", timeout=10)
        res.raise_for_status()
        return res.json()
    except Exception:
        return []


@st.cache_data(ttl=60)
def fetch_snowflake_health():
    try:
        res = requests.get(f"{BACKEND_URL}/health/snowflake", timeout=10)
        res.raise_for_status()
        return res.json()
    except Exception:
        return None


# ── Dashboard rendering ──────────────────────────────────────────────────────

def render_dashboard():
    st.header("Metrics Dashboard")

    metrics = fetch_metrics()
    metrics_history = fetch_metrics_history()
    health = fetch_snowflake_health()

    # ── Summary KPI row ──────────────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)

    if metrics:
        col1.metric("Total Queries", metrics.get("total_queries", 0))
        col2.metric("Avg Latency", f"{metrics.get('avg_latency_ms', 0)} ms")
        col3.metric("Avg Confidence", f"{metrics.get('avg_confidence', 0)}")
    else:
        col1.metric("Total Queries", "N/A")
        col2.metric("Avg Latency", "N/A")
        col3.metric("Avg Confidence", "N/A")

    corpus_size = "N/A"
    if health and health.get("tables"):
        for t in health["tables"]:
            if t.get("name") == "PAPERS" and t.get("schema") == "RAW":
                corpus_size = t.get("row_count", "N/A")
                break
    col4.metric("Papers in Corpus", corpus_size)

    if not metrics_history:
        st.info("No query data yet. Ask a question in the Chat tab to start seeing metrics.")
        _render_corpus_info(health)
        return

    # Build DataFrame from per-query metrics
    df = pd.DataFrame(metrics_history)
    df["TIMESTAMP"] = pd.to_datetime(df["TIMESTAMP"], errors="coerce")
    df["CONFIDENCE"] = pd.to_numeric(df.get("CONFIDENCE", pd.Series(dtype=float)), errors="coerce").fillna(0)
    df["LATENCY_MS"] = pd.to_numeric(df.get("LATENCY_MS", pd.Series(dtype=int)), errors="coerce").fillna(0)
    df["NUM_ITERATIONS"] = pd.to_numeric(df.get("NUM_ITERATIONS", pd.Series(dtype=int)), errors="coerce").fillna(0)
    df = df.sort_values("TIMESTAMP")

    # ── Latency over time ────────────────────────────────────────────────────
    st.subheader("Query Latency Over Time")
    chart_df = df.set_index("TIMESTAMP")[["LATENCY_MS"]].rename(columns={"LATENCY_MS": "Latency (ms)"})
    st.line_chart(chart_df)

    # ── Two-column layout: confidence + tool usage ───────────────────────────
    left, right = st.columns(2)

    with left:
        st.subheader("Confidence Distribution")
        bins = pd.cut(
            df["CONFIDENCE"],
            bins=[0, 0.2, 0.4, 0.6, 0.8, 1.0],
            labels=["0–0.2", "0.2–0.4", "0.4–0.6", "0.6–0.8", "0.8–1.0"],
            include_lowest=True,
        )
        dist = bins.value_counts().sort_index()
        st.bar_chart(dist)

    with right:
        st.subheader("Tool Usage Breakdown")
        all_tools = []
        for tc in df["TOOL_CALLS"]:
            if isinstance(tc, list):
                all_tools.extend(tc)
            elif isinstance(tc, str):
                try:
                    parsed = pd.io.json.loads(tc)
                    if isinstance(parsed, list):
                        all_tools.extend(parsed)
                except Exception:
                    pass
        if all_tools:
            tool_counts = Counter(all_tools)
            tool_df = pd.Series(tool_counts).sort_values(ascending=False)
            st.bar_chart(tool_df)
        else:
            st.caption("No tool usage data available.")

    # ── Recent queries table ─────────────────────────────────────────────────
    st.subheader("Recent Queries")
    display_df = df[["TIMESTAMP", "QUESTION", "CONFIDENCE", "LATENCY_MS", "NUM_ITERATIONS"]].copy()
    display_df.columns = ["Timestamp", "Question", "Confidence", "Latency (ms)", "Iterations"]
    display_df["Question"] = display_df["Question"].str[:80]
    display_df = display_df.sort_values("Timestamp", ascending=False).head(20)
    st.dataframe(display_df, use_container_width=True, hide_index=True)

    # ── Snowflake table inventory ────────────────────────────────────────────
    _render_corpus_info(health)


def _render_corpus_info(health):
    if health and health.get("tables"):
        st.subheader("Snowflake Table Inventory")
        table_df = pd.DataFrame(health["tables"])
        table_df.columns = ["Schema", "Table", "Row Count", "Type"]
        st.dataframe(table_df, use_container_width=True, hide_index=True)


# ── Page config and sidebar ──────────────────────────────────────────────────

st.set_page_config(page_title="Research Assistant", layout="wide")

st.title("Research Assistant")
st.markdown("Personalized research assistant powered by **Snowflake** and **Knowledge Graphs**.")

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
    hist_data = fetch_history()
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

# ── Tabs ─────────────────────────────────────────────────────────────────────

tab_chat, tab_dashboard = st.tabs(["Chat", "Dashboard"])

# ── Chat tab ─────────────────────────────────────────────────────────────────

with tab_chat:
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            # Show tool call info for assistant messages
            meta = message.get("meta")
            if meta:
                tool_calls = meta.get("tool_calls", [])
                num_iter = meta.get("num_iterations", 0)
                if tool_calls:
                    st.caption(
                        f"Agent used {len(tool_calls)} tool call(s) across {num_iter} iteration(s): "
                        f"{', '.join(tool_calls)}"
                    )

    # Show citations for the last assistant response
    if st.session_state.get("last_citations"):
        with st.expander("View Citations & Confidence"):
            st.write(f"**Confidence Score:** {st.session_state.get('last_confidence', 0.0)}")
            for chunk in st.session_state["last_citations"]:
                st.markdown("---")
                st.write(f"**Score:** {round(chunk.get('score', 0), 3)}")
                st.write(f"- Chunk ID: `{chunk.get('chunk_id')}` from Paper `{chunk.get('title')}`")
                st.write(f"- Section: `{chunk.get('section')}`")
                st.write(f"> {chunk.get('text')}")

# ── Dashboard tab ────────────────────────────────────────────────────────────

with tab_dashboard:
    render_dashboard()

# ── Chat input (root scope — sticky bottom bar on both tabs) ─────────────────

if prompt := st.chat_input("Ask a question about your research papers..."):
    st.session_state.messages.append({"role": "user", "content": prompt})

    try:
        payload = {"question": prompt, "top_k": 5, "passcode": ""}
        res = requests.post(f"{BACKEND_URL}/query", json=payload)
        res.raise_for_status()
        data = res.json()

        if isinstance(data, list) and len(data) > 0:
            data = data[0]

        answer = data.get("answer", "No answer provided.")
        citations = data.get("citations", [])
        confidence = data.get("confidence", 0.0)
        tool_calls = data.get("tool_calls", [])
        num_iterations = data.get("num_iterations", 0)

        st.session_state.messages.append({
            "role": "assistant",
            "content": answer,
            "meta": {
                "tool_calls": tool_calls,
                "num_iterations": num_iterations,
            },
        })
        st.session_state["last_citations"] = citations
        st.session_state["last_confidence"] = confidence

    except Exception as e:
        st.session_state.messages.append({
            "role": "assistant",
            "content": f"Error connecting to backend: {e}",
        })

    st.rerun()
