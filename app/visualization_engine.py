"""Auto-select visualizations using Plotly based on question intent and dataframe shape."""
from typing import Optional

import plotly.express as px
import pandas as pd


def auto_plot(df: pd.DataFrame, question: str):
    if df is None or df.empty:
        return None

    q = question.lower()
    # Time series
    if "month" in ",".join(df.columns).lower() or "month" in q or "trend" in q:
        # try to find a datetime-like column
        time_cols = [c for c in df.columns if "date" in c or "month" in c]
        if time_cols:
            x = time_cols[0]
            y = [c for c in df.columns if c not in [x]][0]
            fig = px.line(df, x=x, y=y, title="Trend")
            return fig

    # Distribution / pie
    if df.shape[1] == 2 and (df.iloc[:, 1].dtype == 'int64' or df.iloc[:, 1].dtype == 'float64'):
        fig = px.bar(df, x=df.columns[0], y=df.columns[1], title="Distribution")
        return fig

    # Fallback: display first two numeric columns
    numeric = df.select_dtypes(include=['number']).columns.tolist()
    if len(numeric) >= 1 and len(df.columns) >= 2:
        fig = px.bar(df, x=df.columns[0], y=numeric[0], title="Auto chart")
        return fig

    return None
