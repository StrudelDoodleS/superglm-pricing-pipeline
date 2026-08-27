# Tutorials

Open `00_basic_sql_etl_schema_walkthrough.ipynb` in Jupyter for a conceptual
SQL/ETL/schema walkthrough. For an actual pricing model, use the six-notebook
workflow created by `scripts/scaffold_pricing_model.py`, starting with
`01_data_ingestion.ipynb` and `02_model_training.ipynb`.

The authoritative SQL Server schema is packaged at
`pricing_pipeline.resources.migrations`. For ERD work, use the maintained
Mermaid diagrams in `docs/sql/diagrams` or run
`uv run python scripts/render_schema_diagrams.py`; generated output is ignored
and should not be committed as runnable SQL.

Open `01_portable_underwriter_report.ipynb` for a synthetic, executable example
of copying the one-file prediction report into an unrelated project. It teaches
the frequency, severity, and burn-cost input scales and has no build, SQL, or
deployment dependency.
