"""Generate notebooks from CLI arguments or explicit Python options.

CLI path: cli.build_parser -> commands.run_scaffold ->
commands._raw_scaffold_options -> config.resolve_scaffold_options ->
service.scaffold_resolved_pricing_model -> render.render_notebooks -> files.

``render_notebooks`` contains the argument-to-template-token mapping.
Templates live in ``pricing_pipeline.resources.scaffold/notebooks``.
See ``docs/scaffold-trace.md`` in the source repository for worked examples.
"""
