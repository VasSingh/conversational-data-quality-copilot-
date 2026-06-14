"""Chat orchestration: NL -> SQL -> Execute -> Visualize -> Narrative
"""
from typing import Dict, Any, Optional

import duckdb
import pandas as pd
import logging

from app import sql_generator, visualization_engine, root_cause_engine, narrative_generator, synthetic_data


def _connect_db(data_dir: str = "data") -> duckdb.DuckDBPyConnection:
    conn = duckdb.connect(database=':memory:')
    # Register CSVs as DuckDB tables
    conn.execute(f"CREATE TABLE entities AS SELECT * FROM read_csv_auto('{data_dir}/entities.csv')")
    conn.execute(f"CREATE TABLE dq_exceptions AS SELECT * FROM read_csv_auto('{data_dir}/dq_exceptions.csv')")
    conn.execute(f"CREATE TABLE remediation AS SELECT * FROM read_csv_auto('{data_dir}/remediation.csv')")
    return conn


def answer_question(question: str, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Process a natural language question and return results.

    Returns a dict with keys: sql, df (pandas), fig (plotly), narrative (str), recommendations (list)
    """
    data_dir = "data"
    synthetic_data.ensure_data(data_dir)

    # Debug logging to help diagnose Series vs DataFrame issues in production
    logger = logging.getLogger(__name__)
    try:
        logger.info("Question received: %s", question)
    except Exception:
        pass

    sql = sql_generator.generate_sql(question, filters or {})

    conn = _connect_db(data_dir)
    try:
        df = conn.execute(sql).df()
    except Exception:
        # fallback: return empty dataframe
        df = pd.DataFrame()

    # Emit lightweight debug info about the dataframe to help diagnose UI crashes
    try:
        if df is None:
            logger.info("Query returned None dataframe")
        elif isinstance(df, pd.Series):
            logger.info("Result is a Series; index=%s; dtype=%s", list(df.index), str(df.dtype))
            try:
                logger.info("Series head: %s", df.head().to_dict())
            except Exception:
                pass
        elif isinstance(df, pd.DataFrame):
            logger.info("Result is DataFrame; shape=%s; columns=%s", df.shape, list(df.columns))
            try:
                logger.info("DataFrame head JSON: %s", df.head(5).to_json(orient='records', date_format='iso'))
            except Exception:
                pass
    except Exception:
        pass

    fig = visualization_engine.auto_plot(df, question)

    # Run root cause analysis for selections if applicable
    # Try to infer a country from filters or the question
    country = None
    if filters:
        cs = filters.get("countries")
        if cs and cs != ["All"]:
            country = cs[0]

    analysis = root_cause_engine.analyze(conn, country=country)

    # If the question explicitly references a rule, provide a rule-level breakdown
    rule_analysis = None
    qlow = (question or "").lower()
    if "hierarchy" in qlow and "conflict" in qlow:
        rule_analysis = root_cause_engine.analyze_rule(conn, "Hierarchy Conflict")

    # Ensure df is a DataFrame for downstream consumers
    if isinstance(df, pd.Series):
        try:
            df = pd.DataFrame([df])
        except Exception:
            df = df.to_frame().T

    try:
        narrative = narrative_generator.generate_narrative(question, df, analysis)
    except Exception as e:
        # Defensive fallback: don't let narrative generation crash the UI
        narrative = f"Unable to generate narrative: {str(e)}"

    recommendations = root_cause_engine.recommendations(analysis)

    result = {"sql": sql, "df": df, "fig": fig, "narrative": narrative, "recommendations": recommendations}
    if rule_analysis:
        result["rule_analysis"] = rule_analysis

    return result
