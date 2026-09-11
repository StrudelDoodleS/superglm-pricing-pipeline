CREATE TABLE IF NOT EXISTS pricing_stg.STG_RATING_EXPORT (
/*
Purpose: Receive the header and receipt for a workbook publication attempt.
One row: One export identifier with model metadata, hashes, and base rate.
Use: Successful publication removes the staged child rows but retains this header as a retry receipt. Its presence alone does not mean a package was published.
*/
    export_id TEXT NOT NULL PRIMARY KEY,
    model_id TEXT,
    model_name TEXT NOT NULL,
    model_version TEXT,
    base_rate REAL NOT NULL,
    effective_from_date TEXT,
    effective_to_date TEXT,
    source_file TEXT,
    publication_receipt_json TEXT,
    publication_receipt_sha256 TEXT,
    package_metadata_json TEXT,
    offset_handling TEXT,
    offset_factor_name TEXT,
    offset_source_name TEXT,
    offset_label TEXT,
    metadata_origin TEXT,
    staging_content_sha256 TEXT,
    model_equivalence_sha256 TEXT,
    created_ts TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS pricing_stg.STG_RATE_CELL (
/*
Purpose: Temporarily hold rating multipliers read from an export workbook.
One row: One workbook rating entry within an export attempt.
Use: Publication validates and copies these rows into a package, then removes them on success.
*/
    export_id TEXT NOT NULL,
    row_id INTEGER NOT NULL,
    term_name TEXT NOT NULL,
    term_type TEXT NOT NULL,
    sequence_no INTEGER NOT NULL,
    cell_key_text TEXT NOT NULL,
    multiplier REAL NOT NULL,
    log_coefficient REAL NOT NULL,
    exposure_weight REAL,
    record_count INTEGER,
    is_reference INTEGER NOT NULL DEFAULT 0,
    is_default INTEGER NOT NULL DEFAULT 0,
    spline_a REAL,
    spline_b REAL,
    spline_c REAL,
    spline_d REAL,
    spline_lower REAL,
    spline_upper REAL,
    spline_upper_inclusive INTEGER,
    PRIMARY KEY (export_id, row_id)
);

CREATE TABLE IF NOT EXISTS pricing_stg.STG_CELL_LEVEL (
/*
Purpose: Temporarily hold the feature levels that identify each staged rating entry.
One row: One level at one feature position within a staged workbook entry.
Use: Publication uses these rows to build category, band, and interaction lookup keys. Successful publication removes them.
*/
    export_id TEXT NOT NULL,
    row_id INTEGER NOT NULL,
    position_no INTEGER NOT NULL,
    feature_name TEXT NOT NULL,
    feature_value_type TEXT NOT NULL,
    level_set_name TEXT NOT NULL,
    level_set_type TEXT NOT NULL,
    level_code TEXT NOT NULL,
    level_label TEXT,
    order_index INTEGER,
    lower_bound REAL,
    upper_bound REAL,
    representative_value REAL,
    is_missing INTEGER NOT NULL DEFAULT 0,
    is_other INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (export_id, row_id, position_no)
);

CREATE TABLE IF NOT EXISTS pricing_stg.STG_TERM_METADATA (
/*
Purpose: Temporarily hold model-effect metadata from an export workbook.
One row: One metadata JSON document for a term within an export attempt.
Use: Publication uses this evidence to preserve effect types and exported model behavior. Successful publication removes it.
*/
    export_id TEXT NOT NULL,
    term_name TEXT NOT NULL,
    term_metadata_json TEXT NOT NULL,
    PRIMARY KEY (export_id, term_name),
    FOREIGN KEY (export_id) REFERENCES STG_RATING_EXPORT(export_id)
);
