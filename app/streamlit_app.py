import os
import sys
import logging

# Ensure project root is on sys.path so `from app import ...` works when Streamlit
# runs the script from a different working directory.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import streamlit as st

from app import chatbot
from app.synthetic_data import ensure_data
from app import narrative_generator as _narr
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info("Imported modules: chatbot=%s, narrative_generator=%s", getattr(chatbot, '__file__', 'n/a'), getattr(_narr, '__file__', 'n/a'))


def main():
    st.set_page_config(page_title="Conversational Data Quality Copilot", layout="wide")
    st.title("Conversational Data Quality Copilot")

    data_dir = os.path.join(os.getcwd(), "data")
    ensure_data(data_dir)

    # Sidebar
    with st.sidebar:
        st.header("Examples")
        examples = [
            "Show countries with the highest exception counts",
            "Which rules generate the most exceptions?",
            "Show exception trends over the last 12 months",
            "Which entities have unresolved critical issues?",
            "Which teams have the highest SLA breach rates?",
        ]
        for ex in examples:
            if st.button(ex):
                st.session_state.question = ex

        st.markdown("---")
        st.header("Filters")
        countries = st.multiselect("Country", options=["All", "Germany", "France", "Switzerland", "United Kingdom", "India", "United States", "Singapore", "Japan"], default=["All"])
        industries = st.multiselect("Industry", options=["All", "Banking", "Insurance", "Asset Management", "Technology", "Manufacturing"], default=["All"])

    # Main
    if "question" not in st.session_state:
        st.session_state.question = ""

    q = st.text_area("Ask a question about data quality", value=st.session_state.question, height=100)
    if st.button("Run"):
        if not q.strip():
            st.warning("Please enter a question.")
        else:
            with st.spinner("Processing…"):
                result = chatbot.answer_question(q, filters={"countries": countries, "industries": industries})

            sql = result.get("sql")
            df = result.get("df")
            fig = result.get("fig")
            narrative = result.get("narrative")
            recommendations = result.get("recommendations")

            st.subheader("Generated SQL")
            with st.expander("SQL", expanded=True):
                st.code(sql)

            st.subheader("Results")
            if df is not None and not df.empty:
                st.dataframe(df.head(100))
            else:
                st.write("No results returned.")

            if fig is not None:
                st.plotly_chart(fig, use_container_width=True)

            st.subheader("Executive Narrative")
            st.write(narrative)

            st.subheader("Recommended Actions")
            for r in recommendations:
                st.write("- ", r)

            # Debug expander: show which module files are loaded and df info
            with st.expander("Debug: module & dataframe info", expanded=False):
                st.write("chatbot module:", getattr(chatbot, '__file__', 'n/a'))
                st.write("narrative_generator module:", getattr(_narr, '__file__', 'n/a'))
                try:
                    st.write("Result df type:", type(df).__name__)
                    if df is not None:
                        if hasattr(df, 'shape'):
                            st.write("shape:", df.shape)
                        try:
                            st.write(df.head(10))
                        except Exception:
                            st.write(str(df))
                except Exception:
                    st.write("No df info available")

            # Rule-level analysis (if available)
            if result.get("rule_analysis"):
                ra = result.get("rule_analysis")
                st.markdown("---")
                st.subheader(f"Rule Breakdown: {ra.get('rule_name')}")

                st.markdown("**Top affected entities**")
                top_entities = ra.get('top_entities')
                if top_entities is not None and not top_entities.empty:
                    st.dataframe(top_entities.head(50))
                else:
                    st.write("No top entities found for this rule.")

                st.markdown("**Severity distribution**")
                sev = ra.get('severity')
                if sev is not None and not sev.empty:
                    st.dataframe(sev)
                else:
                    st.write("No severity data.")

                st.markdown("**Trend (monthly)**")
                trend = ra.get('trend')
                if trend is not None and not trend.empty:
                    import plotly.express as px
                    fig2 = px.line(trend, x='month', y='cnt', title=f"{ra.get('rule_name')} - Monthly Exceptions")
                    st.plotly_chart(fig2, use_container_width=True)
                else:
                    st.write("No trend data.")

                st.markdown("**Remediation summary**")
                rem = ra.get('remediation') or {}
                st.write(f"Average resolution days: {rem.get('avg_resolution')}")
                st.write(f"SLA breaches: {rem.get('sla_breaches')} of {rem.get('total_remediations')}")


if __name__ == "__main__":
    main()
