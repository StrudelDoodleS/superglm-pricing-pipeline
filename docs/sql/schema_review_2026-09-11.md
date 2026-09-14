# Schema review, 11 September 2026

This review covers the packaged migration chain through V042, SQL Server
publication and deployment code, and the local SQLite implementation. It does
not inventory a live SQL Server database or external SQL and BI consumers.

## Changes made

- V039 describes all 52 surviving tables and views, including the two migration
  administration tables. Each description explains its purpose, row meaning,
  and use. All 16 SQL Server view definitions also contain the explanation.
  SQLite definitions contain corresponding comments.
- V039 removes `PRICING_PACKAGE_POINTER`. The current deployment selection
  already lives in `PRICING_MODEL_DEPLOYMENT`. The migration rejects unmatched
  pointers and recorded SQL dependencies before dropping the table. Runtime
  deployment, reset, and diagram code no longer use it.
- Existing public view names remain compatible. Descriptions identify the
  internal relativity view, preferred analyst views, and the published-view
  alias. V039 preserves their result definitions.

The dataset and split link tables remain. They currently enforce relationships
and supply validation lineage. Removing them would require changing that data
model and migrating the references; they are not unused tables.

## Bugs fixed

### Deployment switches within the same millisecond could fail

Deployment timestamps have millisecond precision and the closing timestamp
must be strictly later than the opening timestamp. Two rapid switches could
violate that constraint. Separate clock reads also left a gap between intervals.

The writer now uses one server timestamp for both boundaries, at least one
millisecond later than the previous start. Tests cover initial deployment,
normal clock progression, equal timestamps, and a clock moving backward.

### SQL NULL comparisons could admit an invalid monitoring baseline

The SQL Server fit-contract guard compared nullable baseline identifiers using
`<>`. SQL NULL semantics could let an incomplete baseline pass. V040 requires
an actual matching successful run and published package using `NOT EXISTS`.
The observation guard also verifies the referenced baseline identity and status.

### A baseline run could change after a monitoring contract referenced it

The contract itself was immutable, but the referenced run's model, package,
or status could still change. V040 protects those fields and prevents deletion
of referenced baselines. SQLite has equivalent guards. Unrelated annotations
remain editable.

### A table comment could prevent a local constraint upgrade

The SQLite upgrader searched the whole stored table definition for
`MANUAL_EDIT`. A comment containing that word made it skip the model-kind
constraint upgrade. The upgrader now ignores comments and inspects the actual
`model_kind` check. Legacy-upgrade tests cover the commented definitions.

Review also caught table rebuilds dropping the newly installed SQLite lineage
triggers. The upgrader now restores missing triggers within the rebuild
transaction. The legacy-upgrade test checks that baseline changes and deletion
are rejected immediately after the first upgrade.

## Follow-up fixes

### Completed monitoring observations now reject extra evidence rows

The existing immutable child-table triggers block updates and deletions, but
not inserts. A direct insert of an extra monitoring relativity point increased
the monitoring view from 19 to 20 rows while the stored result digest stayed
unchanged. The retry path checks the stored signature rather than recomputing
the child evidence. This was reproduced against SQLite; the SQL Server trigger
definitions have the same insertion gap.

V041 adds `evidence_sealed`. The writer assembles the parent and children,
then seals the observation in the same transaction. Sealed observations reject
further child inserts as well as updates and deletions. The parent permits only
the initial seal transition; it cannot be reopened or changed while sealing.
Monitoring views exclude unsealed observations, and retries refuse to reuse
them. Existing observations are sealed on upgrade, but this does not verify
that their historical child evidence was untampered.

### Numeric scoring no longer exponentiates individual effects prematurely

`PREDICT_RATE_PACKAGE` computes `EXP(input * coefficient)` for each numeric
term before adding the log contributions. With contributions `1000` and
`-1000`, the combined multiplier is 1, but the intermediate `EXP(1000)` exceeds
SQL FLOAT's range. The call can fail even when no breakdown was requested.

V042 keeps numeric contributions on the log scale during matching and
exponentiates the combined contribution for scoring. A requested breakdown
returns `NULL` for an individual numeric multiplier outside the documented
positive SQL FLOAT range, while retaining its `log_coefficient`. Ordinary
numeric multipliers and other exported rating values retain their behavior.
The guard uses Microsoft's [documented FLOAT limits](https://learn.microsoft.com/en-us/sql/t-sql/data-types/float-and-real-transact-sql).

This fixes intermediate overflow when effects cancel. A combined score that
itself exceeds the numeric range still cannot be returned as a finite FLOAT.
The procedure's expressions are regression-tested; full procedure execution
has not been exercised on SQL Server.

## Other interpretation traps

- `V_FINAL_MODEL_RELATIVITY` includes all package statuses. "Final" does not
  identify an approval, deployment, or latest version.
- `V_CURRENT_DATASET_CV_FOLD` selects the most recently registered manifest,
  not the latest data-as-at date. Its training-fold labels do not encode exact
  row membership for holdout or custom splits.
- `V_CURRENT_RATE_PACKAGE` is used by the current scoring procedure even though
  Python does not directly query it. Removing views based only on Python
  reference counts would break scoring.

## Verification boundary

All 449 focused tests pass after the follow-up fixes. These include monitoring
sealing, rollback, retry and upgrade behavior, numeric cancellation, and exact
breakdown range boundaries. Ruff and the whitespace checks pass. The model
tests emit warnings about their weighting and editor fixtures.

Checks exercise deployment behavior, SQLite upgrades and persistence, and
actual relational migration-guard queries using SQLite's SQL NULL semantics.
Migration syntax and custom-schema rendering are checked with the repository's
SQL Server parser tests. The combined script now exceeds SQLFluff's document
size limit, so that check parses the same GO batches as the migration runner.
View definitions were compared with their previous
versions after removing comments and whitespace.

These checks do not prove SQL Server trigger execution, locking, permissions,
or migration rollback on a live server. Apply and exercise V039 through V042 in a
disposable SQL Server database before deployment. Existing evidence
is not retrospectively certified by the new guards.
