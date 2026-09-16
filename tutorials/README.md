# Tutorials

Open [SQL monitoring and table extracts](sql_monitoring/demo.ipynb) for an
executed synthetic Tweedie burn-cost example. It saves the baseline in SQL,
removes the original publication files, checks a dated SQL source, and saves a
champion observation plus three challenger packages. It runs the generated
`monitoring.py` from an unrelated directory, executes notebook 07, verifies that
retries reuse the saved packages, and exports actual SQL tables and the
challenger view to Excel. The isolated SQLite demo labels its simulated initial
deployment and local audit challengers explicitly. Output starts at
`state/sql_monitoring_demo/sql_tables.xlsx`; reruns use separate directories.

Open [PricingModelSpec prototypes](model_spec_prototypes/comparison.ipynb) to
review the A and C designs. The approved C layout is now used by the package
scaffolder: dataset details are saved during ingestion, and training uses a
flat spec with short comments and `apply_transforms`. See the
[notebook guide](../docs/notebooks/README.md). The comparison notebook retains
earlier sketches and runs its baseline on synthetic data without fitting or SQL.

Open [freMTPL claim frequency](fremtpl_frequency/demo.ipynb) for an executable
example using the library's public-data loader and pricing pipeline. It samples
10,000 policies, fits a Poisson model with a log-exposure offset, validates on
two folds, publishes a local SQLite audit package, and inspects the exported
rating workbook. It needs no SQL Server or credentials.

From the repository root, run `uv sync --locked --extra notebook`, then select
`.venv/bin/python` as the notebook kernel and run all cells. The first run
downloads the full public dataset even though fitting uses a sample. Outputs
stay under ignored `state/fremtpl_frequency/`. The notebook uses an explicitly
illustrative data-as-at date because this demo has no source reporting cutoff.

To run the same notebook from a terminal without a Jupyter server:

```bash
uv run --locked --extra notebook python - <<'PY'
import json
from pathlib import Path

path = Path("tutorials/fremtpl_frequency/demo.ipynb")
namespace = {"__name__": "__main__"}
for index, cell in enumerate(json.loads(path.read_text())["cells"]):
    if cell["cell_type"] == "code":
        exec(compile("".join(cell["source"]), f"{path}:cell-{index}", "exec"), namespace)
PY
```

Open `00_basic_sql_etl_schema_walkthrough.ipynb` in Jupyter for a conceptual
SQL/ETL/schema walkthrough. For an actual pricing model, use the seven-notebook
workflow created by `scripts/scaffold_pricing_model.py`, starting with
`01_data_ingestion.ipynb`, `02_model_exploration.ipynb`, and
`03_model_training.ipynb`.

The authoritative SQL Server schema is packaged at
`pricing_pipeline.resources.migrations`. For ERD work, use the maintained
Mermaid diagrams in `docs/sql/diagrams` or run
`uv run python scripts/render_schema_diagrams.py`; generated output is ignored
and should not be committed as runnable SQL.

Open `01_portable_underwriter_report.ipynb` for a synthetic, executable example
of copying the one-file prediction report into an unrelated project. It teaches
the frequency, severity, and burn-cost input scales and has no build, SQL, or
deployment dependency.
