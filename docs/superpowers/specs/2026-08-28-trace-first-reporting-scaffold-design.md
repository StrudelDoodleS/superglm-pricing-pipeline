# Trace-first reporting and scaffold design

## Goal

Make reporting and scaffold generation easy to trace from their supported public
entry points to the code that performs each step. Preserve every user-facing
capability while removing private compatibility routes and hidden orchestration.

The success measure is followability, not minimum line count. Concrete rendering,
SQL, and safety code may remain large when it has one clear owner and does not hide
the workflow.

## Usability contract

The refactor preserves:

- `pricing-pipeline init` and `pricing-pipeline scaffold`;
- generated scaffold TOML and notebook bytes;
- `pricing_pipeline.reporting.build_scored_model_report()`;
- `pricing_pipeline.reporting.build_underwriter_report()`;
- existing arguments, result objects, diagnostics, privacy behaviour and HTML;
- model-neutral reporting without importing SuperGLM;
- optional SuperGLM and rating-workbook evidence;
- the generated portable standalone report; and
- existing sanitized error and minimum-cell-size rules.

Private implementation imports are not compatibility promises. In particular,
`reporting._core`, `reporting.underwriter`, dynamic module attributes and
`scaffold.legacy` may be removed after all repository callers use the final owners.

## Non-goals

- Redesigning HTML, CSS, JavaScript or report appearance.
- Adding report features, diagnostics or adapters.
- Changing notebook contents, scaffold defaults or CLI flags.
- Introducing a repository framework, plugin registry or generic callback layer.
- Creating a new test matrix for behaviour already covered by existing tests.

## Reporting architecture

The supported path is deliberately linear:

```text
build_scored_model_report / build_underwriter_report
    -> validate and normalize inputs once
    -> collect optional model evidence
    -> calculate named diagnostic sections
    -> assemble one payload
    -> invoke the existing HTML renderer
```

Final functional owners:

- `report.py`: both public entry points and the top-to-bottom workflow;
- `inputs.py`: options, input normalization and boundary validation;
- `evidence.py`: model-neutral evidence contracts and collection;
- `adapters/superglm.py`: SuperGLM evidence only;
- `adapters/rating_workbook.py`: workbook evidence only;
- `diagnostics.py`: metrics, importance, relativities, interactions, distributions,
  curves and double-lift calculations;
- `movement.py`: prediction-movement calculations; and
- the existing HTML/style modules: rendering assets only.

`report.py` must read as the workflow and contain no dynamic dispatch, nested
orchestration functions or model-library imports on the generic path. A small
SuperGLM convenience branch may import its adapter only when the caller supplies a
fitted model.

Diagnostics consume normalized arrays and normalized evidence. They do not load
models, read workbooks, write files or render HTML. Evidence adapters do not assemble
the report. The HTML renderer receives a completed JSON-safe payload and does not
calculate model statistics.

`reporting.__init__` uses direct imports for the two supported entry points and their
public option/result types. It does not use `__getattr__` or compatibility aliases.

## Scaffold architecture

The existing supported path remains:

```text
cli.main
    -> scaffold.commands.run_init / run_scaffold
    -> scaffold.config resolves configuration once
    -> scaffold.service validates destinations and writes files
    -> scaffold.render renders packaged notebook resources
```

`scaffold.legacy` is deleted. Configuration merging and validation have one public
owner in `scaffold.config`; commands translate CLI arguments, while the service owns
filesystem safety and creation. Named symlink/type guards remain at the write
boundary so the main creation path stays readable.

## Errors and privacy

Validation happens at public or adapter boundaries. Internal calculation functions
receive valid normalized inputs rather than repeating the same guards. Error messages
remain analyst-actionable but never include row-level data, identifiers configured as
comparison units, raw predictions or feature values.

Partial artifacts are not left behind: report output is written only after payload
construction succeeds, and scaffold safety checks run before managed writes.

## Verification

Use the existing reporting, adapter, browser/runtime, portable exporter, CLI,
scaffold-golden and packaged-resource tests as the behavioural contract. Update
imports and ownership assertions rather than duplicating cases.

Required gates:

- the generic report path imports and runs without SuperGLM;
- both supported report entry points retain their signatures and result fields;
- diagnostics and privacy payload assertions remain green;
- the portable generated script is current and its standalone tests pass;
- scaffold TOML and all notebook golden hashes are unchanged;
- obsolete private modules are absent and have no repository callers;
- changed Python passes Ruff and formatting checks; and
- the complete locked test suite passes.

No live browser or model server is required beyond the repository's existing report
runtime tests. No new behavioural test is added unless an extraction exposes a
previously untested regression.

## Acceptance criteria

A maintainer can identify the implementation of scaffold generation or report
generation from its public entry point in a few direct calls. Every functional module
has one stated responsibility, the happy paths are linear, model-specific code stays
inside adapters, rendering stays separate from calculations, and no legacy facade or
hidden compatibility path remains.
