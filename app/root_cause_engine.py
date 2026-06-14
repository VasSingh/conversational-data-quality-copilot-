"""Root cause analysis utilities for data quality issues."""
from typing import Dict, Any, Optional, List

import pandas as pd
import duckdb


def analyze(conn: duckdb.DuckDBPyConnection, country: Optional[str] = None) -> Dict[str, Any]:
    """Return a dictionary of analysis results (top rules, growth rate, severity distribution, resolution performance)."""
    where = ""
    if country:
        where = f"WHERE country = '{country}'"

    top_rules_q = f"SELECT rule_name, COUNT(*) AS cnt FROM dq_exceptions {where} GROUP BY rule_name ORDER BY cnt DESC LIMIT 5"
    top_rules = conn.execute(top_rules_q).df()

    # growth rate: compare last 3 months to prior 3 months
    growth_q = (
        "WITH months AS ("
        " SELECT date_trunc('month', exception_date) AS month, COUNT(*) AS cnt FROM dq_exceptions"
        f" {where} GROUP BY month ORDER BY month DESC LIMIT 6 )"
        " SELECT SUM(CASE WHEN month >= (SELECT month FROM months ORDER BY month DESC LIMIT 3) THEN cnt ELSE 0 END) AS recent, "
        " SUM(CASE WHEN month < (SELECT month FROM months ORDER BY month DESC LIMIT 3) THEN cnt ELSE 0 END) AS prior FROM months"
    )
    try:
        growth = conn.execute(growth_q).df().to_dict(orient='records')[0]
        recent = growth.get('recent') or 0
        prior = growth.get('prior') or 0
        growth_rate = ((recent - prior) / prior * 100.0) if prior and prior != 0 else None
    except Exception:
        growth_rate = None

    severity_q = f"SELECT severity, COUNT(*) AS cnt FROM dq_exceptions {where} GROUP BY severity ORDER BY cnt DESC"
    severity = conn.execute(severity_q).df()

    resolution_q = (
        "SELECT AVG(r.resolution_days) AS avg_resolution FROM remediation r "
        "JOIN dq_exceptions d ON r.entity_id = d.entity_id "
        f"{where}"
    )
    try:
        avg_resolution = conn.execute(resolution_q).fetchone()[0]
    except Exception:
        avg_resolution = None

    return {
        "top_rules": top_rules,
        "growth_rate": growth_rate,
        "severity": severity,
        "avg_resolution_days": avg_resolution,
        "country": country,
    }


def analyze_rule(conn: duckdb.DuckDBPyConnection, rule_name: str, top_n: int = 10) -> Dict[str, Any]:
    """Return analysis scoped to a specific rule_name.

    Returns:
      - top_entities: DataFrame of entities with counts
      - severity: DataFrame of severity distribution for the rule
      - trend: DataFrame of monthly counts for the rule
      - remediation: dict with avg_resolution and sla_breaches count
    """
    safe_rule = rule_name.replace("'", "''")

    top_entities_q = (
        "SELECT d.entity_id, e.legal_name, e.country, COUNT(*) as cnt "
        f"FROM dq_exceptions d LEFT JOIN entities e ON d.entity_id = e.entity_id "
        f"WHERE d.rule_name = '{safe_rule}' GROUP BY d.entity_id, e.legal_name, e.country ORDER BY cnt DESC LIMIT {top_n}"
    )
    top_entities = conn.execute(top_entities_q).df()

    severity_q = f"SELECT severity, COUNT(*) as cnt FROM dq_exceptions WHERE rule_name = '{safe_rule}' GROUP BY severity ORDER BY cnt DESC"
    severity = conn.execute(severity_q).df()

    trend_q = (
        "SELECT date_trunc('month', exception_date) AS month, COUNT(*) AS cnt "
        f"FROM dq_exceptions WHERE rule_name = '{safe_rule}' GROUP BY month ORDER BY month"
    )
    trend = conn.execute(trend_q).df()

    remediation_q = (
        "SELECT AVG(r.resolution_days) AS avg_resolution, "
        "SUM(CASE WHEN r.resolution_days > r.sla_target THEN 1 ELSE 0 END) AS sla_breaches, "
        "COUNT(*) AS total_remediations "
        "FROM remediation r JOIN dq_exceptions d ON r.entity_id = d.entity_id "
        f"WHERE d.rule_name = '{safe_rule}'"
    )
    try:
        rem_row = conn.execute(remediation_q).df().to_dict(orient='records')[0]
    except Exception:
        rem_row = {"avg_resolution": None, "sla_breaches": None, "total_remediations": None}

    return {
        "rule_name": rule_name,
        "top_entities": top_entities,
        "severity": severity,
        "trend": trend,
        "remediation": rem_row,
    }


def recommendations(analysis: Dict[str, Any]) -> List[str]:
    recs: List[str] = []
    top_rules = analysis.get('top_rules')
    country = analysis.get('country')

    if top_rules is not None and not top_rules.empty:
        top = top_rules.iloc[0]['rule_name']
        if country:
            recs.append(f"Investigate {top} failures for {country} source systems and validation rules.")
        else:
            recs.append(f"Investigate top failing rule: {top} and its upstream sources.")

    gr = analysis.get('growth_rate')
    if gr is not None and gr > 20:
        recs.append("Exception volume has grown >20% in the recent period — perform incident review.")

    avg_res = analysis.get('avg_resolution_days')
    if avg_res and avg_res > 7:
        recs.append("Average remediation time exceeds 7 days — review remediation processes and SLA compliance.")

    if not recs:
        recs.append("No immediate recommendations — monitor trends and thresholds.")

    return recs
