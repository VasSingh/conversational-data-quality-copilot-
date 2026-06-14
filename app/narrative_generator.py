"""Generate concise executive narratives from analysis outputs."""
from typing import Dict, Any

import pandas as pd
import logging

logger = logging.getLogger(__name__)


def generate_narrative(question: str, df: pd.DataFrame, analysis: Dict[str, Any]) -> str:
    try:
        parts = []
        country = analysis.get('country')

        # High-level summary from df
        if df is not None and not df.empty:
            # If a Series was returned, convert to a single-row DataFrame for consistent handling
            if isinstance(df, pd.Series):
                try:
                    df = pd.DataFrame([df])
                except Exception:
                    df = df.to_frame().T

            # Safely compute exception totals when the column exists
            cols = list(getattr(df, 'columns', []))
            if 'exceptions' in cols:
                try:
                    total = int(df['exceptions'].sum())
                    # Determine a human-friendly top label
                    if 'country' in cols:
                        top_country = df.iloc[0]["country"]
                    elif len(cols) >= 1:
                        top_country = df.iloc[0, 0]
                    else:
                        top_country = 'N/A'

                    # top_exceptions: use iloc lookup to avoid label/key issues
                    top_exceptions = int(df['exceptions'].iloc[0])
                    pct = round(top_exceptions / total * 100, 1) if total else 0.0
                    parts.append(f"{top_country} represented {pct}% of exceptions ({top_exceptions}).")
                except Exception:
                    parts.append(f"Returned {len(df)} records for the query.")
            else:
                parts.append(f"Returned {len(df)} records for the query.")
        else:
            parts.append("No results were returned for the query.")

        # Add root cause highlights
        top_rules = analysis.get('top_rules')
        if top_rules is not None and not top_rules.empty:
            try:
                top = top_rules.iloc[0]['rule_name']
                parts.append(f"The most frequent rule failure was '{top}', suggesting upstream data or validation issues.")
            except Exception:
                logger.info("Unable to read top_rules for narrative; top_rules shape: %s", getattr(top_rules, 'shape', str(type(top_rules))))

        gr = analysis.get('growth_rate')
        if gr is not None:
            parts.append(f"Recent growth rate in exceptions is {round(gr,1)}%.")

        avg_res = analysis.get('avg_resolution_days')
        if avg_res is not None:
            parts.append(f"Average remediation time is {round(avg_res,1)} days.")

        if country:
            parts.append(f"Focus recommended on {country} operations and source-system validations.")

        return " ".join(parts)
    except Exception as e:
        try:
            logger.exception("generate_narrative error: %s", str(e))
            if df is None:
                logger.info("narrative df is None")
            elif isinstance(df, pd.Series):
                logger.info("narrative df is Series; index=%s; to_dict=%s", list(df.index), df.to_dict())
            elif isinstance(df, pd.DataFrame):
                try:
                    logger.info("narrative df is DataFrame; shape=%s; columns=%s; head=%s", df.shape, list(df.columns), df.head(5).to_json(orient='records', date_format='iso'))
                except Exception:
                    logger.info("narrative df DataFrame logging failed")
        except Exception:
            pass
        return f"Unable to generate narrative due to internal error: {str(e)}"
