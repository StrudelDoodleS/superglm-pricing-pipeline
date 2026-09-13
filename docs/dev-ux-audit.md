# Developer usability audit

Audited the package at `a35a87a` on 2026-09-13, including the model-recipe work.
The question was whether a developer can follow a value through the system and
find the owner of a change without opening every function.

## Findings and changes

| Finding | Why it caused confusion | Change in this pass |
|---|---|---|
| 38 of 76 Python files had no module docstring. | Opening a file did not explain its job or its callers. | Every module now states its purpose. Package docstrings point to the main owners. |
| Core notebook types lacked class explanations. | A spec, a registered reference, a built candidate and a loaded candidate looked like overlapping model wrappers. | Added object meanings, producer/consumer relationships and lifecycle distinctions to class docstrings. |
| CLI-to-notebook mapping was spread across parser, config, service, renderer and templates. | An argument name alone did not reveal which cell changed. | Added the full argument/token/destination table and a worked runtime-module trace in [scaffold-trace.md](scaffold-trace.md). Added handoff docstrings at the corresponding functions. |
| Other flows had the same missing connections. | Developers had to infer how fit outputs reached SQL or edit files became child packages. | Added [package-flows.md](package-flows.md) covering data, fitting, publication, edits, monitoring and reporting. |
| The maintainer guide omitted recipe and spline publication owners. | New code could end up in the wrong module. | Updated the ownership map and linked the [module index](module-index.md). |
| `file_lock.py` imported `typing.Iterator`. | The alias is deprecated and produced Ruff UP035. | Import `Iterator` from `collections.abc`; retain the supported `contextlib.contextmanager` decorator. |

The decorator warning reported during this audit was not reproduced at runtime.
A local lock completed with deprecation warnings treated as errors. Python's
[typing documentation](https://docs.python.org/3.14/library/typing.html#typing.Iterator)
identifies the deprecated alias; the
[contextlib documentation](https://docs.python.org/3.14/library/contextlib.html#contextlib.contextmanager)
continues to document the decorator.

## Structural follow-up implemented

The follow-up refactor starts at `2d4719f`, the documentation pass above.
It moves existing definitions into focused owners and removes three editor
functions that only forwarded arguments. It adds no model record classes.

| Area | Before | Current ownership |
|---|---|---|
| Monitoring | One 2,404-line module | A 202-line workflow; separate baseline checks, reconstruction, evidence, invariants and persistence; shared records in `contracts`. |
| Editor publication | One 1,589-line module | A 355-line workflow; parent verification, replay, export and retry checks each have an owner. Three forwarding functions removed. |
| Report evidence | One 1,208-line module | A 498-line collection/normalization workflow; records, shared value checks and interaction normalization separated. |
| Notebook API | 1,286 lines with configuration validation mixed into operations | 1,065 lines of notebook operations; `models/pricing.py` owns `PricingModelSpec` and its validation. The notebook import is unchanged. |
| Scaffold handoff | Service copied eleven fields into renderer keywords | Service passes `ResolvedScaffoldOptions` unchanged; the renderer maps `options.<field>` directly to template tokens. |

Start at the workflow module and follow its named calls. Existing public imports
remain explicit re-exports, including old serialized record paths. Each group
has one-way dependencies; verification and record modules do not import their
workflow. Tests patch helpers at their new implementation owners.

`publishing/sqlserver.py` has 1,719 lines, 23 functions and one class. Keeping a
transaction readable in one place is useful, so splitting it purely to hit a
line limit would be counterproductive. `reporting/_underwriter_html.py` has
2,555 lines but only two top-level functions; much of it is embedded presentation
code. Its file size is a different problem from mixed model-lifecycle logic.

The small scaffold files demonstrate that size is only part of the issue.
`scaffold/commands.py` had 188 lines and ten functions, yet the argument handoff
was still hard to follow. Explicit mappings and named consumers matter even in
small modules.

The notebook API still has several lifecycle operations in one file. Further
splitting should make a specific operation easier to follow without forcing
analysts to learn more entry points. SQL transactions and embedded HTML remain
with their current owners.

## Keep future changes traceable

- A module docstring states its responsibility and names the next owner when it delegates work.
- A handoff function says what the input represents, what it returns and who consumes that result.
- An argument's path remains explicit through parsing, validation, conversion and its final use.
- Class docstrings explain the record's role; they do not repeat every annotated field.
- Comments explain a constraint or conversion that the code cannot explain by itself.
- Public names and signatures remain stable during internal extractions. Existing workflow tests verify the handoffs.

Use short descriptions such as "write the edited model and its hashes". Avoid
phrases such as "governed artifact plumbing" that leave the operation unspecified.

## Documentation-pass verification

- All 76 Python modules and all 117 publicly named top-level classes have purpose docstrings.
- The 70 existing file-lock, scaffold, CLI, resource and recipe-notebook tests passed.
- A temporary project confirmed that a CLI runtime-module override reaches all six generated notebooks and overrides the TOML default. Every generated code cell parsed successfully.
- AST comparison across the 67 changed Python files found no executable changes beyond the `Iterator` import replacement and removal of a redundant exception-class `pass`.
- New documentation links and whitespace checks passed.
- No new Ruff lint or formatting findings. The changed files already had 19 lint findings; 18 remain after the deprecated import fix. Two pre-existing formatting failures remain in `data/fremtpl.py` and `tools/db_diagrams.py`.

The full model-fitting suite was not repeated for this documentation pass.
Existing SQL migration and notebook-template bytes were preserved.

## Structural-refactor verification

- All 92 Python modules and 117 publicly named top-level classes have purpose docstrings.
- Mechanical AST comparison found 184 unchanged moved definitions and values. The only two changed editor bodies call the same checked operations directly after removal of the forwarding functions.
- The scaffold's 67 focused tests passed. Six configurations across all six notebooks produced the same 36 rendered outputs byte for byte, including remote/local settings, non-ASCII labels and token-shaped text.
- Existing monitoring, reporting, editor and notebook regressions passed in focused runs. Compatibility tests exercise original serialized class paths.
- The first full run exposed a missing handoff in the portable report exporter: its explicit embedded-source inventory needed the three new evidence modules. Updated the list, regenerated the artifact and passed all 28 portable-report tests.
- The independent xhigh review found no remaining issues after redirecting recipe construction to the new spec owner. It checked 25 baseline serialized classes, 194 runtime type hints, the public exports and 101 focused cases.
- Changed-code Ruff lint and formatting, `uv lock --check`, and wheel/source-distribution builds passed. All current documentation links resolve and the module index covers every source file exactly once.
- Final full suite: **1,640 passed, 4 skipped** in 153.65 seconds, including distribution-content checks and clean-wheel execution outside the checkout. Three skips require an explicitly configured live SQL Server; the fourth requires optional CatBoost. No live SQL Server verification was performed.
