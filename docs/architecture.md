# Architecture

## Overview
The system is a lightweight Python backend with a Streamlit frontend. Data is stored as CSVs and queried using DuckDB in-memory for fast analytical queries.

## Components
- Streamlit App: UI for chat, filters, displays and visualizations.
- SQL Generator: rule-based generator mapping NL to SQL templates.
- Root Cause Engine: analytical routines to compute contributing rules and trends.
- Narrative Generator: templates for executive summaries.
- Synthetic Data Generator: creates realistic datasets for demos.

## Data Flow
1. User enters natural language query in Streamlit.
2. SQL generator builds a query.
3. DuckDB executes SQL against CSV-backed tables.
4. Results are visualized and analyzed for root cause and narrative generation.
