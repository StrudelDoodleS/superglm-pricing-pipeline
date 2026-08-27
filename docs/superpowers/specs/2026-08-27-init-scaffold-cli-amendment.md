# Installed Init and Scaffold CLI Amendment

**Date:** 2026-08-27
**Parent design:** `2026-08-26-installable-pricing-pipeline-design.md`

## Purpose

Give a non-technical analyst one obvious way to start a standalone model
repository:

```text
install framework -> init -> edit pricing_model.toml -> scaffold
```

This amendment supersedes the parent design only where it previously made
`scaffold` create `pricing_model.toml` or required `uv.lock` merely to create
local scaffold files.

## Supported commands

The installed distribution exposes one parser through both forms:

```bash
uv run pricing-pipeline init
uv run pricing-pipeline scaffold

python -m pricing_pipeline init
python -m pricing_pipeline scaffold
```

The console command is the documented form. The module form is the fallback
when the package is already installed but `uv` is unavailable.

## Recommended uv workflow

```bash
mkdir claim_frequency
cd claim_frequency
uv init --bare --python 3.14
uv add "airflow-superglm-builder @ git+ssh://git@HOST/TEAM/REPOSITORY.git" --tag v0.2.0
uv run pricing-pipeline init
```

The analyst edits `pricing_model.toml`, then runs:

```bash
uv run pricing-pipeline scaffold
```

Examples install the base framework only. A private runtime-provider package
owns its SQL driver and authentication dependencies. `ipykernel` is a model
repository development dependency, not an implicit framework requirement.

## Python-only fallback

`python -m pricing_pipeline` works only after the framework has been installed
in that interpreter. It may initialize and scaffold a repository and use local
SQLite/read-only workflows without `uv.lock`.

The absence of `uv.lock` is never silently treated as governed evidence.
Environment verification, governed notebook execution, publication, and
deployment refuse with an actionable message until the repository has a
verified supported lock and environment.

## `init` contract

`pricing-pipeline init [--root PATH]`:

1. resolves the model root independently of the current working directory;
2. requires a regular, non-symlink `pyproject.toml` at that root;
3. creates only `pricing_model.toml`;
4. never creates notebooks, SQL, groupings, README, Git files, directories, or
   a lockfile;
5. never overwrites and has no `--force` option;
6. uses the same directory-anchored, no-follow, atomic no-clobber rules as the
   standalone scaffold; and
7. prints the absolute created path, the fields that require attention, and
   the exact scaffold command.

If `pricing_model.toml` already exists as a regular file, `init` leaves it
byte-for-byte unchanged. A syntactically valid file produces an idempotent
"already initialized" result and the next command. Invalid TOML, a symlink,
reparse point, non-file entry, or concurrent replacement fails without
mutation.

The generated TOML is syntactically valid, contains explanatory comments, and
uses the exact reserved sentinel `"<EDIT_ME>"` for required analyst-supplied
strings (and `["<EDIT_ME>"]` for required lists). The validator rejects that
sentinel in every field, so an untouched template can never scaffold. The file
begins with:

```toml
schema_version = 2
template_version = "standalone-v1"
scaffold_state = "draft"
```

It contains the parent design's `[model]`, `[source]`, `[roles]`,
`[validation]`, `[notebook_defaults]`, and `[manual_edit_defaults]` sections.
It contains no credentials and links to the installed runtime-provider
documentation.

## Configuration state

`scaffold_state` is one of:

- `draft`: created by `init`; only `init`, `scaffold`, and help/diagnostic
  commands may use the repository;
- `current`: the configured scaffold completed successfully; or
- `manual_pending`: an upgrade requires explicit analyst reconciliation.

The analyst does not manually change `draft` to `current`. The scaffold owns
that transition. All other model commands encountering `draft` explain which
fields remain invalid and tell the analyst to rerun `scaffold`.

## `scaffold` contract

`pricing-pipeline scaffold [--root PATH]`:

1. requires an existing `pricing_model.toml`; when absent it exits without
   mutation and tells the analyst to run `pricing-pipeline init`;
2. strictly validates every configured section, field, placeholder, relative
   path, feature/role relationship, runtime-provider alias, and validation
   variant before writing;
3. preflights the complete managed output tree;
4. creates the README, `.gitignore`, `.env.example`, `model_spec.py`, documented
   empty `groupings.toml`, `sql/model_data.sql`, and notebooks `01` through
   `06` from installed resources;
5. creates no nested `pricing_models/` or framework source copy;
6. changes `scaffold_state` to `current` only as the final journalled atomic
   transition after every managed output is durable; and
7. is a byte- and mtime-preserving no-op when the current scaffold already
   matches.

Any validation, collision, lock, write, or durability failure leaves the
configuration in `draft`; it can never expose a project as `current`. A handled
failure rolls back newly created managed files. A process crash may leave only
a journalled recoverable draft, which every other model command refuses until
`scaffold` performs recovery. Existing custom content is never overwritten.

## Runtime provider documentation

Add a dedicated installed and repository documentation page describing the
private runtime adapter. The adapter's minimum callable contract is:

```python
def get_engine(database=None):
    """Return a SQLAlchemy Engine."""
```

It may additionally expose `get_schema_names()`, `get_runtime_settings()` (or
legacy `get_settings()`), and `ensure_database(database)`. The private runtime
package owns SQL driver/authentication dependencies and obtains credentials
from its normal secret provider.

`pricing_model.toml` selects only a harmless host-registered
`runtime_provider` alias. It does not contain an arbitrary module import path
for governed remote writes. The documentation explains the host mapping from
that alias to the trusted private runtime module.

## Error and output rules

- Successful creation and idempotent reuse return `0`.
- User/configuration/precondition errors return `2` with the field and absolute
  path, but never a credential or secret value.
- Unexpected internal failures return `1`.
- Commands print concise next actions suitable for copying from a terminal.
- Optional command implementations are imported only after subcommand
  selection, so `init`, `scaffold`, and `--help` do not require SQL, notebook,
  reporting, or cloud extras.

## Verification

Tests must prove:

- console and `python -m` forms use the same parser and return codes;
- CLI help and `init` work from a clean wheel with optional imports blocked;
- `init` creates exactly one file and is idempotent without overwriting;
- malformed existing TOML, symlink/reparse-point ancestors and leaves,
  concurrent creation, and output collisions cause no mutation;
- missing config directs the user to `init`;
- incomplete placeholders produce field-specific scaffold errors;
- a handled scaffold failure preserves `draft` and rolls back newly created
  managed files, while a crash leaves only the tested recoverable journal;
- successful scaffold writes the exact golden standalone tree and transitions
  to `current` last;
- retries preserve bytes and mtimes;
- Python-only local scaffolding works without `uv.lock`;
- governed commands refuse an absent or unverified lock; and
- base installation does not pull `ipykernel`, `pyodbc`, or Azure packages.

## Deliberate non-goals for this slice

This amendment does not implement schema, report, package-inspection,
governed-notebook supervisor, environment-attestation, or deployment commands.
It establishes the shared installed parser and the standalone `init` and
`scaffold` lifecycle those later commands consume.
