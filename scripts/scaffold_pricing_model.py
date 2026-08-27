from __future__ import annotations

import sys

from pricing_pipeline.scaffold import legacy as _implementation

if __name__ == "__main__":
    raise SystemExit(_implementation.main())

sys.modules[__name__] = _implementation
