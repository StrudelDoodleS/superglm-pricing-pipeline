# Generic analyst notebooks

The approved design is prototype C with a flat `PricingModelSpec`, short
comments, `df`, dataset details saved during ingestion, and a shared
`apply_transforms` declaration. The generated example uses the scaffold's
model, target, feature, and key placeholders. It makes no insurance-specific
exposure or transformation choice for the analyst.

## Implementation

- [x] Add `PricingDataset` and fixed `Log`, `Log1p`, and `Clip` transforms.
  Save data and provenance together with verification before loading. Preserve
  source columns and reject invalid domains, overwritten inputs, and ambiguous
  transform dependencies. Test persistence, mutation, and preparation errors.
- [x] Extend the flat spec to accept `dataset` and `transforms`. Keep legacy
  dataset and offset fields compatible. Derive offset descriptions from the
  shared transform declaration. Validate prepared data before a model build.
- [x] Carry transform recipes through candidate artifacts and publication
  receipts. Add workbook preparation instructions and persist the same recipes
  in existing SQL package metadata. Preserve recipes through editor and
  monitoring paths. SQL scoring continues to accept prepared feature values.
- [x] Generate generic ingestion and training notebooks with the approved
  layout. Explain fitting and publishing immediately above each operation.
  Retain existing remote-write controls and package/deployment separation.
- [x] Execute a generated local ingestion/training/publication workflow and
  run relevant persistence, export, editor, monitoring, and scaffold checks.

## Files

Data helpers live in `data/dataset.py` and `data/transforms.py`; analyst entry
points remain in `notebook.py`. `modeling/standard_superglm.py` passes verified
recipes to the workbook exporter, publication metadata, and candidate bundle.
Generated notebook resources remain under `resources/scaffold/notebooks`.

No migration is needed for transform descriptions because package metadata is
already persisted and included in publication identity. This change does not
translate arbitrary Python into SQL, rename rating-table units, or activate a
published package.

## Verification

537 focused tests pass, including generated default and transformed local
workflows through publication. Ruff and whitespace checks pass. Review fixes
cover repeated configuration-cell execution, copied dataset axes, nullable
integer clipping, and clear rejection of unsupported persisted cell values.
SQL Server execution was not exercised against a live server.
