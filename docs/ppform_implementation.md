# Exact spline publication

The approved change preserves supported one-dimensional spline main effects as
polynomial segments from SuperGLM. Interactions and LSS are outside this change.
Existing binned packages remain readable. Ordered categoricals remain exact
lookups over declared levels.

## Contract

New spline exports use `continuous_kind="ppform"`. An explicit `"binned"`
choice retains band exports. No fallback is allowed when exact export fails.
The staging term type is `SPLINE_PPOLY_1D`.

For spline rows, `STG_RATE_CELL` carries nullable `spline_a`, `spline_b`,
`spline_c`, `spline_d`, `spline_lower`, `spline_upper`, and
`spline_upper_inclusive`. NULL lower/upper bounds represent unbounded tails;
tails must be constant. Finite intervals evaluate the normalized coordinate
`u=(x-lower)/(upper-lower)` and log effect `a+u*(b+u*(c+u*d))`.
The displayed multiplier is `exp(a)` and is not a band multiplier.
After validating that displayed value, the importer writes neutral 1/0 values
to legacy cell multiplier/log columns for spline terms. These cells carry term
identity only. The true log effect is in the spline coefficients; this avoids
overflowing legacy DECIMAL columns with otherwise valid polynomial anchors.

Store these rows once in `pricing.PRICING_SPLINE_SEGMENT`, keyed by package,
term and segment order, with the input feature name, level label, bounds,
coefficients and weight. Existing compiled cell rows retain term identity,
but spline terms must never enter categorical or band lookup scoring.
Expose all effects through `pricing.V_FINAL_MODEL_RELATIVITY`, with an explicit
representation and shared model/run/dataset lineage and transforms. V044 adds
spline rows with NULL fixed relativity and separate coefficients. Candidate
and deployed filters include these rows. The original spline-only view remains
compatible, but Power BI does not need it for a complete model.

Coefficient values and exact bounds participate in publication content and
model equivalence hashes. Preserve existing hashes for legacy frames without
spline columns. Reject malformed/partial coefficients, invalid intervals,
gaps/overlaps, nonconstant tails, unsupported terms and contradictory receipts.
SQL accepts prepared feature values, as before. Clip/error boundary behaviour
comes from the exported segments; unsupported extension is rejected upstream.

## Tasks and verification

- [x] Import/export: parse all seven workbook columns, preserve coefficients,
  validate segments and receipt type, fingerprint exact spline values. Add
  regression tests for coefficient-only changes and malformed exports.
- [x] Persistence/scoring: migrate SQL Server staging and segment storage,
  implement SQLite storage, expose segments and evaluate SQL polynomials on
  the log scale. Test boundaries, tails and package isolation. Keep old rating
  lookups compatible and document the new table/view.
- [x] Consumers: make workbook reporting evaluate polynomials. Ensure manual
  editing cannot reinterpret an exact curve as band multipliers. Test guards
  and existing editor flows.
- [x] Integration: expose representation choice in analyst builds, update
  docs and run the saved freMTPL model through exact export and local
  publication. Compare persisted segments with Python at observations,
  knots and tails. Run focused regression suites and SQL syntax checks.

SQL Server execution needs an available server; syntax checks and local
numerical checks do not substitute for a live SQL Server integration run.

## Verification results

The freMTPL 10,000-policy example was fitted and published locally with 17
polynomial segments across four spline terms. Reconstructed predictions from
the stored segments and categorical/offset effects matched the Python model
with maximum absolute percentage difference below `8e-13`. The policy whose
binned prediction differed by 32.08% now matches at floating-point precision.
The comparison is in
`state/fremtpl_frequency/demo-ppform-10000-seed-42/exact_spline_run.xlsx`.

Tests cover native exports, transformed notebook builds, legacy binned builds,
coefficient-only identities, malformed workbook columns, large spline anchors,
ordered bounds and tails, SQL insertion and scoring expressions, editor
re-exports, package lineage and rendered SQL Server migration syntax.
The SQL expression tests translate SQL Server input-conversion functions to
SQLite equivalents; they do not execute the complete stored procedure on SQL
Server. The migration has not been applied to a live server.

An existing report HTML test requires the optional Plotly dependency, which is
not installed in this environment. It is excluded from the focused suite;
polynomial report parsing and numerical curve evaluation are covered.

The combined-view follow-up adds V044 and V045. The final view contains all
26 freMTPL effect rows: eight categorical entries, one per-unit exposure factor,
and 17 spline segments. `representation` describes how to evaluate each row.
The candidate and deployed views inherit the same complete representation.

Native prediction tests fit a mixed spline/numeric/categorical model with a
scaled exposure offset, stage its actual export, and execute the publisher's
relational INSERTs and active procedure's match, summary and breakdown queries
with documented SQLite dialect translations. Predictions agree with Python at
observations, knots, adjacent values, tails and fractional exposures. Tests also
cover saved transforms, invalid inputs, package isolation and discrete offsets.
This caught and fixed per-unit offsets being treated as category lookups. V045
uses `LOG(input) + log_coefficient` for these positive per-unit inputs and blocks
fallback to a category/default row. Numeric coefficients retain `input * beta`.
An explicit workbook header comment identifies continuous offsets. The importer
stores that representation in term metadata, which the procedure and combined
view read. A discrete category named `per_unit` remains a lookup. New imports
with that label and no representation marker require a fresh package export;
existing published packages keep their stored behavior.
These tests do not execute T-SQL control flow or validate SQL Server DECIMAL
rounding, query planning, or a live deployment.

The follow-up verification covers native prediction comparisons, combined
views, deployment filters, offline upgrades, notebook builds, packaged
migrations, and rendered SQL Server syntax. The refreshed local freMTPL package
is version 2. Its 10,000 predictions retain the maximum percentage difference
below `8e-13`. `final_model_relativities.xlsx` contains its 26 combined-view rows.

Final verification passed 277 tests, with the one optional Plotly-dependent
HTML report check deselected. Ruff, formatting and whitespace checks passed.
