# Conversational Data Quality Copilot

This repository contains a production-style demo of an AI-powered conversational analytics platform for enterprise data quality.

Features
- Natural language query interface that generates SQL and executes against DuckDB.
- Automatic visualization selection using Plotly.
- Root cause analysis and executive narrative generation.
- Risk scoring and recommended remediation actions.

Installation
1. Create a Python virtual environment and activate it.

```powershell
python -m venv cdq_copilot_env
& .\cdq_copilot_env\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. Run the Streamlit app:

```bash
streamlit run app/streamlit_app.py
```

Notes
- The app generates synthetic datasets into the `data/` folder on first run.
- For production-grade natural language to SQL you can optionally provide an OpenAI API key. Set the environment variable `OPENAI_API_KEY` to enable model-backed SQL generation. If not provided the app falls back to a local rule-based SQL generator.

Screenshots
- (placeholders)

Future roadmap
- Integrate access control, larger storage (Parquet / cloud storage), fine-grained prompt engineering, audit trails, and model-backed SQL generation.
