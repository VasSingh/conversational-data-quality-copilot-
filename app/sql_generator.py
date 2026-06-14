"""NL -> SQL generator with two modes:

- OpenAI-backed generator (used when OPENAI_API_KEY is set). The prompt requests
  a DuckDB-compatible SQL query and nothing else.
- Local rule-based generator as fallback (deterministic, no API key required).

The local generator is intentionally conservative and returns readable SQL suitable
for demo purposes. For production use, extend prompt engineering and validation.
"""
from typing import Dict, Optional
import os
import re
import datetime

try:
    import openai
except Exception:
    openai = None


def _clean_sql(text: str) -> str:
    # Remove markdown fences and surrounding text
    text = text.strip()
    text = re.sub(r"```sql\n|```\n", "", text, flags=re.IGNORECASE)
    # Try to extract the first SQL-looking statement
    m = re.search(r"(SELECT|WITH)\b[\s\S]+", text, flags=re.IGNORECASE)
    return m.group(0).strip() if m else text


def _generate_sql_with_openai(question: str, filters: Dict) -> Optional[str]:
    """Call OpenAI to generate SQL. Returns None on failure.

    The model is asked to return only SQL text (no commentary). We perform basic
    sanitization and fallback to local generator on errors.
    """
    if openai is None:
        return None

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None

    openai.api_key = api_key
    model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")

    system = (
        "You are an assistant that translates natural language into valid DuckDB SQL. "
        "Respond with SQL only, no explanation or markdown fences. Use the tables: dq_exceptions, entities, remediation."
    )

    # Build a short user prompt describing filters and the question
    filter_text = ""
    if filters:
        if filters.get("countries") and filters.get("countries") != ["All"]:
            filter_text += f" Only include countries: {', '.join(filters.get('countries'))}."
        if filters.get("industries") and filters.get("industries") != ["All"]:
            filter_text += f" Only include industries: {', '.join(filters.get('industries'))}."

    user = f"Translate the following question into a single DuckDB SQL query. Question: {question}.{filter_text}"

    try:
        resp = openai.ChatCompletion.create(
            model=model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            max_tokens=800,
            temperature=0.0,
        )
        content = resp.choices[0].message.content
        sql = _clean_sql(content)
        # Basic safety: ensure it's a SELECT/WITH statement
        if not re.match(r"^(SELECT|WITH)\b", sql, flags=re.IGNORECASE):
            return None
        return sql
    except Exception:
        return None


def _generate_sql_local(question: str, filters: Dict = None) -> str:
    """Improved local, rule-based SQL generator covering common intents.

    This generator looks for keywords and patterns and produces readable SQL.
    It is intentionally conservative and returns aggregate queries where appropriate.
    """
    q = (question or "").lower()
    filters = filters or {}

    where_clauses = []
    if filters.get("countries") and filters.get("countries") != ["All"]:
        vals = ",".join([f"'{c}'" for c in filters.get("countries")])
        where_clauses.append(f"country IN ({vals})")

    if filters.get("industries") and filters.get("industries") != ["All"]:
        vals = ",".join([f"'{i}'" for i in filters.get("industries")])
        where_clauses.append(f"entity_id IN (SELECT entity_id FROM entities WHERE industry IN ({vals}))")

    where = ""
    if where_clauses:
        where = "WHERE " + " AND ".join(where_clauses)

    # Date range detection: "last N months" or "last 12 months"
    m = re.search(r"last (\d{1,2}) months", q)
    date_filter = ""
    if m:
        months = int(m.group(1))
        # Use SQL interval subtraction compatible with DuckDB
        date_filter = f"exception_date >= current_date - INTERVAL '{months} months'"
    elif "last 12 months" in q or "last year" in q:
        date_filter = "exception_date >= current_date - INTERVAL '1 year'"

    if date_filter:
        if where:
            where = where + " AND " + date_filter
        else:
            where = "WHERE " + date_filter

    # Intent matching
    if any(x in q for x in ["country", "countries"]) and any(x in q for x in ["top", "highest", "most", "count"]):
        return f"SELECT country, COUNT(*) AS exceptions FROM dq_exceptions {where} GROUP BY country ORDER BY exceptions DESC"

    if any(x in q for x in ["rule", "rules"]) and any(x in q for x in ["most", "top", "highest", "count"]):
        return f"SELECT rule_name, COUNT(*) AS cnt FROM dq_exceptions {where} GROUP BY rule_name ORDER BY cnt DESC"

    if "trend" in q or "trend" in q or "months" in q or re.search(r"last \d+ months", q):
        # monthly trend
        return f"SELECT date_trunc('month', exception_date) AS month, COUNT(*) AS exceptions FROM dq_exceptions {where} GROUP BY month ORDER BY month"

    if any(x in q for x in ["unresolved", "open", "not resolved"]) or ("critical" in q and "unresolved" in q):
        return f"SELECT * FROM dq_exceptions WHERE status != 'resolved' AND severity IN ('Critical','High') ORDER BY exception_date DESC"

    if "sla" in q or "breach" in q or "sla breach" in q:
        return (
            "SELECT r.owner_team, SUM(CASE WHEN r.resolution_days > r.sla_target THEN 1 ELSE 0 END) AS breaches, "
            "COUNT(*) as total FROM remediation r GROUP BY r.owner_team ORDER BY breaches DESC"
        )

    if "entities" in q and any(x in q for x in ["with", "have", "that"]):
        return f"SELECT e.* FROM entities e JOIN dq_exceptions d ON e.entity_id = d.entity_id {where} ORDER BY d.exception_date DESC LIMIT 100"

    # Default safe query
    return "SELECT country, COUNT(*) AS exceptions FROM dq_exceptions GROUP BY country ORDER BY exceptions DESC"


def generate_sql(question: str, filters: Dict = None) -> str:
    """Public entrypoint. Try OpenAI first, then local generator as fallback."""
    # Attempt OpenAI generation if available
    sql = _generate_sql_with_openai(question, filters or {})
    if sql:
        return sql

    # Fallback to local deterministic generator
    return _generate_sql_local(question, filters or {})

