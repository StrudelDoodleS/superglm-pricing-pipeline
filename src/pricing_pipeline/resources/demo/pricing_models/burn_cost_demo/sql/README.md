# Source queries

Keep this model's dataset queries here, for example `training_data.sql`.
Load a query in `01_data_ingestion.ipynb` using your source SQLAlchemy engine:

```python
query = (MODEL_DIR / "sql" / "training_data.sql").read_text(encoding="utf-8")
raw_df = pd.read_sql_query(query, source_engine)
```

Replace `source_engine` with the engine connected to your source database.
Keep the snapshot-date column in the query result and set `PricingDataset(as_of=...)`
to its name.
