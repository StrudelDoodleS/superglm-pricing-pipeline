"""Export bounded rows from the dedicated demo database for inspection."""

from datetime import UTC, datetime

import pandas as pd
from demo_sql_runtime import DATABASE, ROOT
from openpyxl.styles import Alignment, Font, PatternFill
from sqlalchemy import text


def export_sql_tables(engine, limit=20):
    """Write table/view rows, counts, descriptions and complete JSON sidecars."""
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    directory = ROOT / ".local" / "sql_extracts" / stamp
    directory.mkdir(parents=True, exist_ok=False)
    json_root = directory / "json"
    json_root.mkdir()
    workbook = directory / "sql_tables.xlsx"
    extracts = {}
    index = []
    quote = engine.dialect.identifier_preparer.quote
    with engine.connect() as connection:
        actual = connection.execute(text("SELECT DB_NAME()")).scalar_one()
        if actual != DATABASE:
            raise ValueError("This exporter is only for the dedicated demo database.")
        objects = (
            connection.execute(
                text("""
            SELECT SCHEMA_NAME(obj.schema_id) AS schema_name, obj.name,
                   obj.type_desc, CAST(description.value AS NVARCHAR(4000)) AS description
            FROM sys.objects AS obj
            LEFT JOIN sys.extended_properties AS description
              ON description.major_id = obj.object_id
             AND description.minor_id = 0 AND description.class = 1
             AND description.name = 'MS_Description'
            WHERE obj.type IN ('U', 'V') AND obj.is_ms_shipped = 0
              AND SCHEMA_NAME(obj.schema_id) IN ('pricing', 'mlops', 'pricing_stg', 'dbo')
            ORDER BY SCHEMA_NAME(obj.schema_id), obj.name
        """)
            )
            .mappings()
            .all()
        )
        for number, obj in enumerate(objects, 1):
            sql_name = f"{quote(obj['schema_name'])}.{quote(obj['name'])}"
            total = connection.execute(text(f"SELECT COUNT_BIG(*) FROM {sql_name}")).scalar_one()
            df = pd.read_sql_query(text(f"SELECT TOP ({int(limit)}) * FROM {sql_name}"), connection)
            sheet = f"{number:02}_{obj['name']}"[:31]
            for column in df.columns:
                for row_number, value in df[column].items():
                    if isinstance(value, (bytes, bytearray, memoryview)):
                        df.at[row_number, column] = "0x" + bytes(value).hex().upper()
                    elif isinstance(value, str) and column.endswith("_json"):
                        filename = f"{sheet}_{row_number + 1}_{column}.json"
                        (json_root / filename).write_text(value, encoding="utf-8")
                        if len(value) > 3000:
                            df.at[row_number, column] = (
                                f"Full JSON: json/{filename}\nPreview: {value[:1500]}\n[truncated]"
                            )
            extracts[sheet] = df
            index.append(
                {
                    "object": f"{obj['schema_name']}.{obj['name']}",
                    "type": obj["type_desc"],
                    "total rows": total,
                    "exported rows": len(df),
                    "sheet": sheet,
                    "description": obj["description"],
                }
            )
    notes = pd.DataFrame(
        [
            {
                "item": "Source",
                "description": "Actual rows from local SQL Server, PricingNotebookDemo.",
            },
            {
                "item": "Data",
                "description": "Synthetic burn cost, Tweedie p=1.5, with two source snapshots.",
            },
            {
                "item": "Scope",
                "description": f"At most {limit} rows per table or view, without a guaranteed row order. The tables sheet reports full counts.",
            },
            {
                "item": "Recipe",
                "description": "recipe_gzip is the stored binary payload. recipe_json is decoded by SQL Server when selected and is not persisted.",
            },
            {
                "item": "JSON",
                "description": "Complete exported JSON values are in the json directory beside this workbook. Long cells explicitly show a truncated preview.",
            },
        ]
    )
    with pd.ExcelWriter(workbook, engine="openpyxl") as writer:
        notes.to_excel(writer, sheet_name="read_me", index=False)
        pd.DataFrame(index).to_excel(writer, sheet_name="tables", index=False)
        for sheet, df in extracts.items():
            df.to_excel(writer, sheet_name=sheet, index=False)
        for sheet in writer.book.worksheets:
            sheet.freeze_panes = "A2"
            sheet.auto_filter.ref = sheet.dimensions
            for cell in sheet[1]:
                cell.font = Font(bold=True, color="FFFFFF")
                cell.fill = PatternFill("solid", fgColor="16384B")
            for column in sheet.columns:
                longest = max(len(str(c.value or "").split("\n")[0]) for c in column)
                sheet.column_dimensions[column[0].column_letter].width = min(
                    max(15, longest + 2), 55
                )
                for cell in column:
                    cell.alignment = Alignment(vertical="top", wrap_text=True)
    return workbook
