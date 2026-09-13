"""Turn completed builds into SQL rating packages and deploy selected packages.

``publish`` validates and dispatches; ``sqlite`` and ``sqlserver`` own the
transactions; ``deployment`` changes the active package. Supported callers
use ``pricing_pipeline.notebook``.
"""
