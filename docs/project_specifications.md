# Conversational Data Quality Copilot — Project Specification

## Purpose
This project builds a production-ready, demo-friendly Conversational Data Quality (CDQ) Copilot: a tool that lets data stewards and analysts ask natural‑language questions about data quality and receive SQL, visualizations, narratives, root‑cause analysis, and remediation recommendations. The app demonstrates how lightweight local analytics (DuckDB + CSVs) and optional LLM augmentation (OpenAI) can be combined to deliver immediate, explainable insights for data quality monitoring and investigation.

## Scope
- Interactive Streamlit frontend for conversational queries and filter controls.
- NL→SQL translation with two modes: a deterministic local rule-based generator and an optional OpenAI-backed generator (when `OPENAI_API_KEY` is provided).
- In-memory DuckDB execution of CSV-backed tables: `entities`, `dq_exceptions`, `remediation`.
- Automatic visualization (Plotly), narrative generation, and root-cause analysis (top rules, trends, severity, remediation performance).
- Synthetic data generator for reproducible demos and smoke tests.
- Defensive engineering to handle differences in returned results (Series vs DataFrame), and robust error logging to avoid breaking the UI.

## Rules & Business Logic
- Data tables and key fields:
  - `entities(entity_id, legal_name, country, industry, ...)`
  - `dq_exceptions(exception_id, entity_id, rule_name, severity, country, exception_date, status, ...)`
  - `remediation(entity_id, owner_team, resolution_days, sla_target, ...)`
- Common analytical rules implemented in the local SQL generator:
  - Top countries / rules by exception count.
  - Monthly trends using `date_trunc('month', exception_date)` and `INTERVAL` arithmetic.
  - Unresolved critical/high exceptions.
  - SLA breach summary by owner/team.
  - Entity-level exception lookups and top affected entities for specific rules (e.g., "Hierarchy Conflict").
- Heuristics for NL parsing: keyword-based intent matching (time ranges, `top`/`highest`, `trend`, `unresolved`, `sla`, `entities`, `rules`).

## Tools & Libraries Used
- Python 3.10+ (tested with 3.14 in this workspace)
- Streamlit — interactive application UI
- DuckDB — fast in-memory SQL engine for analytics over CSVs
- pandas — DataFrame operations and glue code
- plotly — interactive visualizations
- openai (optional) — LLM-powered NL→SQL generation when `OPENAI_API_KEY` is set
- faker / numpy — synthetic dataset creation
- pytest (recommended) — for unit tests (not yet fully implemented)

## Architecture and Design Choices (Theory)
- Local-first deterministic behavior: The app prioritizes a rule-based SQL generator to ensure demos and core functionality work without external API keys. This makes demos reproducible, auditable, and safe from network or billing variability.
- Optional LLM augmentation: When available, the OpenAI path can produce more flexible SQL for freeform requests. The system sanitizes and validates the model output (ensuring SQL-only, verifying it begins with SELECT/WITH) before execution.
- DuckDB over CSVs: DuckDB offers a zero‑dependency, high-performance SQL engine that can query CSVs directly and materialize them into memory for fast analytics. This provides production‑like SQL behavior without a full database server.
- Defensive DataFrame handling: SQL queries can return different shapes (single-row Series vs multi-row DataFrame). The app normalizes these shapes and uses positional access (`.iloc`) when appropriate to avoid KeyError and preserve the UX.
- Explainability-first UX: All flows return explicit SQL, a tabular result, a visual chart, a short executive narrative, and clear recommendations — enabling users to verify the chain of reasoning rather than relying on black‑box outputs.

## Key Features
- Conversational NL→SQL: Ask questions in plain English and receive generated SQL and results.
- Dual NL→SQL strategy: OpenAI-backed generator with sanitization, and a local fallback generator for deterministic outputs.
- Automatic visualization: `visualization_engine.auto_plot()` chooses an appropriate Plotly chart (time-series, bar chart) based on result schema.
- Rule-level analysis: `root_cause_engine.analyze_rule()` provides severity distribution, trend, top affected entities, and remediation metrics for a specific rule.
- Narrative & recommendations: `narrative_generator.generate_narrative()` builds a concise executive summary; `root_cause_engine.recommendations()` offers pragmatic next steps.
- Synthetic data generator: script to create `entities.csv`, `dq_exceptions.csv`, and `remediation.csv` with controlled biases for demo scenarios.

## How to Run (Quick Start)
1. Create and activate a virtual environment:
   - Windows (PowerShell):
     ```powershell
     python -m venv cdq_copilot_env
     .\cdq_copilot_env\Scripts\Activate.ps1
     ```
2. Install dependencies:
   ```powershell
   python -m pip install -r requirements.txt
   ```
3. Generate synthetic data (optional):
   ```powershell
   python -c "from app import synthetic_data; synthetic_data.ensure_data('data')"
   ```
4. Run Streamlit app:
   ```powershell
   python -m streamlit run app/streamlit_app.py --server.port 8501
   ```
5. (Optional) To use the OpenAI generator, set `OPENAI_API_KEY` in your environment before starting Streamlit.

## Benefits
- Fast, reproducible demos without external API dependencies.
- Explanations at every step (SQL, visual, narrative) increase trust and adoption among data stewards.
- Lightweight architecture suitable for PoCs, embedded analytics, and teaching SQL-backed observability patterns.
- Extensible: the local generator and root-cause engines are easily extended with new heuristics or ML models (e.g., a risk scorer).

## Limitations & Next Steps
- The local NL→SQL generator is rule-based and may not cover all phrasing; LLM augmentation improves coverage but requires API keys and output validation.
- No production-grade auth, persistence, or CI in the current repo — these would be required for deployment.
- Suggested next additions:
  - Implement a lightweight ML risk scoring service and integrate it into the UI.
  - Add unit tests and a GitHub Actions workflow for critical modules (`sql_generator`, `root_cause_engine`, `narrative_generator`).
  - Add role-based auth and simple persistence (Postgres or DuckDB persisted file) for multi-user operation.

## File Map (important locations)
- `app/streamlit_app.py` — Streamlit UI
- `app/chatbot.py` — orchestration: NL→SQL→execute→visualize→narrative
- `app/sql_generator.py` — OpenAI + local SQL generation
- `app/visualization_engine.py` — auto-charting logic
- `app/root_cause_engine.py` — rule-level analysis & recommendations
- `app/narrative_generator.py` — executive narrative builder
- `app/synthetic_data.py` — synthetic dataset creation
- `docs/` — documentation and specifications

## Contact & Maintenance Notes
- Keep `OPENAI_API_KEY` out of source control; use environment variables or a secrets manager.
- Re-run the synthetic data generator after schema changes to keep examples consistent.
- When adding LLM features, maintain strict sanitization of model output and prefer `temperature=0` for deterministic SQL.

---

If you want, I can also:
- produce a shorter one-page executive summary for stakeholders,
- add changelog and contributor instructions to `docs/CONTRIBUTING.md`, or
- implement the ML risk scorer next. Which would you like me to do?