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

## Structural work still worth doing

Counts below describe the source before this documentation pass. Functions and
classes are top-level definitions, excluding methods. These are indicators of
reading effort, not automatic reasons to split a file.

| Priority | File | Lines / functions / classes | Proposed boundary |
|---|---|---|---|
| First | `modeling/monitoring.py` | 2,378 / 45 / 10 | Separate contract types, model reconstruction, evidence extraction and SQL persistence. Keep the public monitoring calls together. |
| Next | `publishing/editor.py` | 1,569 / 38 / 5 | Separate parent/submission verification and edit replay from child-build construction. Preserve the common publication path. |
| Next | `reporting/evidence.py` | 1,186 / 51 / 11 | Separate evidence types from normalization, with interaction normalization as one focused owner. |
| Review with the next API change | `notebook.py` | 1,208 / 23 / 4 | Keep analyst entry points easy to find; move validation or conversion helpers only when they form a coherent unit. |

`publishing/sqlserver.py` has 1,719 lines, 23 functions and one class. Keeping a
transaction readable in one place is useful, so splitting it purely to hit a
line limit would be counterproductive. `reporting/_underwriter_html.py` has
2,555 lines but only two top-level functions; much of it is embedded presentation
code. Its file size is a different problem from mixed model-lifecycle logic.

The small scaffold files demonstrate that size is only part of the issue.
`scaffold/commands.py` had 188 lines and ten functions, yet the argument handoff
was still hard to follow. Explicit mappings and named consumers matter even in
small modules.

This pass documents the current architecture. It does not move functions,
rename imports, add forwarding layers or change SQL schemas. The structural
items above remain separate refactoring work.

## Keep future changes traceable

- A module docstring states its responsibility and names the next owner when it delegates work.
- A handoff function says what the input represents, what it returns and who consumes that result.
- An argument's path remains explicit through parsing, validation, conversion and its final use.
- Class docstrings explain the record's role; they do not repeat every annotated field.
- Comments explain a constraint or conversion that the code cannot explain by itself.
- Public names and signatures remain stable during internal extractions. Existing workflow tests verify the handoffs.

Use short descriptions such as "write the edited model and its hashes". Avoid
phrases such as "governed artifact plumbing" that leave the operation unspecified.

## Verification

- All 76 Python modules and all 117 publicly named top-level classes have purpose docstrings.
- The 70 existing file-lock, scaffold, CLI, resource and recipe-notebook tests passed.
- A temporary project confirmed that a CLI runtime-module override reaches all six generated notebooks and overrides the TOML default. Every generated code cell parsed successfully.
- AST comparison across the 67 changed Python files found no executable changes beyond the `Iterator` import replacement and removal of a redundant exception-class `pass`.
- New documentation links and whitespace checks passed.
- No new Ruff lint or formatting findings. The changed files already had 19 lint findings; 18 remain after the deprecated import fix. Two pre-existing formatting failures remain in `data/fremtpl.py` and `tools/db_diagrams.py`.

The full model-fitting suite was not repeated for this documentation pass.
Existing SQL migration and notebook-template bytes were preserved.
