
import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "email_assistant.db"

st.set_page_config(
    page_title="AI Email Assistant",
    page_icon="📧",
    layout="wide",
)


@st.cache_data(ttl=10)
def load_audit_data():
    """Read audit records without changing the database."""

    if not DB_PATH.exists():
        return pd.DataFrame()

    with sqlite3.connect(DB_PATH) as connection:
        return pd.read_sql_query(
            """
            SELECT
                status,
                category,
                urgency,
                needs_reply,
                error_type,
                created_at,
                updated_at
            FROM email_processing
            ORDER BY updated_at DESC
            """,
            connection,
        )


st.title("📧 AI Email Assistant")
st.caption("Processing analytics and audit history")
st.caption(
    "Demo mode: current records are synthetic test data, "
    "not actual Gmail processing results."
)

if st.button("Refresh dashboard"):
    st.cache_data.clear()
    st.rerun()

df = load_audit_data()

if df.empty:
    st.info(
        "No audit records found yet. Run the email processor "
        "to populate the dashboard."
    )
    st.stop()

# Normalize stored values for reliable reporting.
df["status"] = df["status"].fillna("unknown")
df["category"] = df["category"].fillna("Unclassified")
df["urgency"] = df["urgency"].fillna("Unknown")
df["needs_reply"] = df["needs_reply"].map(
    {1: "Yes", 0: "No"}
).fillna("Unknown")

total = len(df)
processed = int((df["status"] == "processed").sum())
failed = int((df["status"] == "failed").sum())
high_urgency = int((df["urgency"] == "high").sum())

st.subheader("Processing overview")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total tracked", total)
col2.metric("Processed", processed)
col3.metric("Failed", failed)
col4.metric("High urgency", high_urgency)

st.divider()

left, right = st.columns(2)

with left:
    st.subheader("Emails by category")
    category_counts = df["category"].value_counts()
    st.bar_chart(category_counts)

with right:
    st.subheader("Emails by urgency")
    urgency_counts = df["urgency"].value_counts()
    st.bar_chart(urgency_counts)

left, right = st.columns(2)

with left:
    st.subheader("Processing status")
    st.bar_chart(df["status"].value_counts())

with right:
    st.subheader("Reply requirement")
    st.bar_chart(df["needs_reply"].value_counts())

st.divider()

st.subheader("Audit history")

status_options = ["All"] + sorted(df["status"].unique().tolist())
selected_status = st.selectbox("Filter by status", status_options)

history = df.copy()

if selected_status != "All":
    history = history[history["status"] == selected_status]

display_columns = [
    "status",
    "category",
    "urgency",
    "needs_reply",
    "error_type",
    "created_at",
    "updated_at",
]

st.dataframe(
    history[display_columns],
    use_container_width=True,
    hide_index=True,
)

st.caption(
    "Read-only dashboard. Email content, message IDs, and draft IDs "
    "are not displayed."
)

