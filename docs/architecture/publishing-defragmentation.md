# Publishing Defragmentation Design

**Date:** 2026-08-28
**Baseline:** `superglm-pricing-pipeline` v0.2.1

## Purpose

Make model publication readable from start to finish without weakening any
governance rule. This is a defragmentation of the existing workflow, not a new
publication system.

A maintainer should be able to open one module and follow:

```text
validate build
-> verify artifacts and identity
-> find an exact retry or equivalent publication
-> prepare rating tables
-> write package and lineage
-> verify persisted output
-> return the result
```

## Compatibility boundary

Preserve every actual capability:

- RAW, ROUTINE_EDIT, EDITOR_EDIT and MANUAL_EDIT publication;
- semantic deduplication and exact-retry handling;
- manifest, split, parent and deployment lineage;
- immutable publication receipts and artifact verification;
- trusted manual-policy replay;
- rating-table normalization and Python/SQL parity checks;
- SQLite local mode and SQL Server remote mode;
- publication locking, transactions and concurrency-safe retries;
- package deployment and monitoring consumers; and
- current confidentiality boundaries.

Keep these supported surfaces unchanged:

- documented exports from `pricing_pipeline.notebook`;
- the installed `pricing-pipeline` and `python -m pricing_pipeline` commands;
- `pricing-pipeline init` TOML output and defaults;
- `pricing-pipeline scaffold` directory and file creation;
- all six generated notebook filenames and bytes;
- model-source, manifest and equivalence identities; and
- current SQL schema semantics, views, triggers and stored procedures.

Internal `pricing_pipeline.publishing` imports are not public. They may move or
disappear without compatibility shims. Pre-release database rows that depend on
obsolete nullable digests or old payload formats are not supported; reset the
experimental database before adopting this release. This slice does not squash
or redesign the current SQL schema.

## Chosen structure

Use vertical workflows with concrete backend modules. Do not introduce a
generic repository framework.

```text
publishing/
  publish.py          one visible publication entry and result types
  identity.py         canonical receipts, fingerprints and equivalence
  rating_tables.py    workbook parsing, normalized frames and content hashes
  sqlserver.py        explicit SQL Server transaction and writes
  sqlite.py           explicit SQLite transaction and writes
  editor.py           trusted editor/manual preparation and replay
  metadata.py         SuperGLM publication metadata
  lineage.py          model-run, manifest, split and metric evidence
  deployment.py       explicit deployment transition
```

Small constants may live beside the operation that uses them. Do not retain a
tiny module merely to hold one name, lifecycle value or forwarding import.

The target is at most ten purposeful publishing modules and approximately
5,000-5,800 physical Python lines. The target is a readability guard, not a
reason to hide Python logic inside SQL or generated files.

## Publication data flow

`publish.py` accepts one immutable publication request produced from an
`ApprovedModelBuild`. It performs common validation and preparation once, then
selects the concrete SQLite or SQL Server writer explicitly.

The request contains data, not callbacks:

- the approved build and normalized rating-table frames;
- canonical content and equivalence identities;
- optional parent package/run identities;
- immutable lineage and metric records; and
- optional concrete draft-verification data for Python/SQL parity.

The existing `draft_validator` and `package_lineage_writer` callback pattern is
removed. Backend code executes named stages directly inside one transaction.

Each backend writer reads top-to-bottom:

1. acquire the backend-specific publication lock;
2. resolve an exact retry or semantic equivalent;
3. reserve the next model/package version when required;
4. write normalized package, term, cell and compiled-cell rows;
5. write model-run, dataset, split and metric lineage;
6. execute the explicit persisted-package verification;
7. mark the package published and remove disposable staging rows; and
8. commit and return the common publication result.

SQLite and SQL Server may use different SQL. They share canonical preparation
and result types, not a class hierarchy. A small amount of visible SQL-specific
duplication is preferable to an opaque adapter framework.

## Model-kind flows

RAW and ROUTINE_EDIT builds enter `publish.py` directly.

`editor.py` performs the additional trusted work required for EDITOR_EDIT and
MANUAL_EDIT:

1. load and verify the signed submission;
2. reload the immutable parent artifact;
3. validate parent, champion and source lineage;
4. replay and verify a manual policy when applicable;
5. produce an `ApprovedModelBuild` plus explicit verification evidence; and
6. call the same publication entry used by RAW and ROUTINE_EDIT.

The common publisher does not know how an editor UI works and does not accept
editor-specific callbacks.

## Module consolidation

The implementation should remove the current fragmentation rather than merely
rename it:

- merge the tiny naming, lifecycle, version and lock helpers into their owning
  workflows;
- combine publication receipt construction and SuperGLM metadata in
  `metadata.py` while retaining their canonical bytes;
- separate workbook parsing and hashing from database staging;
- replace duplicated local/remote identity-conflict checks with one pure
  implementation;
- replace duplicated local model-run construction with common lineage records;
- reduce `editor_candidate.py` to a readable editor/manual preparation flow;
  and
- delete obsolete internal facades and branches for old experimental payloads.

Do not move SQL into resource files solely to reduce the Python line count.

## Errors and transactions

Validate files, hashes, request fields and model identity before opening the
write transaction where possible. Inside the transaction, any conflict or
verification failure rolls back every new durable row.

Retries are successful only when the complete immutable request identity
matches the stored publication. A matching semantic model may reuse the
existing package according to the current deduplication rules. A partial match
or changed release intent raises a specific publication conflict.

Cleanup uses context managers and `finally` blocks rather than broad nested
`try`/callback structures. Error messages retain the current confidentiality
rules and never include row-level model data.

## Verification

Do not create a large new test matrix. Use the existing publication, editor,
manual-adjustment, SQLite, migration and notebook suites as the contract.

Add only focused characterization where extraction would otherwise be unsafe:

- one common-flow test showing all model kinds reach the same publisher;
- one SQLite/SQL Server preparation-parity test without requiring a live SQL
  Server; and
- one test proving obsolete internal compatibility is gone while supported
  notebook imports remain.

Release gates:

- exact existing init/scaffold golden hashes remain unchanged;
- focused publishing and SQLite suites pass;
- packaged migration and clean-wheel tests pass;
- the complete locked suite passes;
- changed Python files pass Ruff and formatting checks; and
- an independent review finds no Critical or Important regression.

## Acceptance criteria

- The main publication sequence is visible in one module without nested local
  functions or callable hooks.
- All four model kinds and both databases preserve their current outcomes.
- Supported notebook and CLI APIs remain unchanged.
- Init and scaffold outputs remain byte-for-byte identical.
- Publishing contains no obsolete internal compatibility facade.
- Publishing is at most ten purposeful modules and no orchestration module
  exceeds 800 lines without a documented SQL-specific reason.
- Publishing source is below 6,000 physical Python lines without relocating
  logic merely to satisfy the count.
