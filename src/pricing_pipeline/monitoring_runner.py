"""Run a generated monitoring script with an execution log and scheduler exit code.

The model project's monitoring.py owns its data query and connection settings.
Its main block calls run_monitoring_script(run, log_directory=...). Notebook 07
calls the same run function directly and retains ordinary Python tracebacks.
"""

from __future__ import annotations

import logging
import sys
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import uuid4

if TYPE_CHECKING:
    from pricing_pipeline.modeling.monitoring.batch import MonitoringReport


def run_monitoring_script(run: Callable[[], MonitoringReport], *, log_directory: str | Path) -> int:
    """Execute one complete monitoring run and return its process exit status.

    Write a separate UTC-dated log for each invocation. Return 0 after a report,
    1 on a workflow failure, 2 if logging cannot start, and 130 on interruption.
    The generated script passes this value to SystemExit for Task Scheduler/cron.
    """
    try:
        directory = Path(log_directory).expanduser().resolve()
        directory.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S_%fZ")
        path = directory / f"monitoring_{timestamp}_{uuid4().hex[:8]}.log"
        file_handler = logging.FileHandler(path, mode="x", encoding="utf-8")
    except (OSError, ValueError) as exc:
        print(f"Cannot create monitoring log in {log_directory}: {exc}", file=sys.stderr)
        return 2

    logger = logging.getLogger("pricing_pipeline.monitoring")
    previous_level, previous_propagation = logger.level, logger.propagate
    console_handler = logging.StreamHandler(sys.stderr)
    formatter = logging.Formatter("%(asctime)sZ %(levelname)s %(message)s")
    formatter.converter = time.gmtime
    for handler in (file_handler, console_handler):
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    started = time.perf_counter()
    try:
        logger.info("Monitoring log: %s", path)
        report = run()
        from pricing_pipeline.modeling.monitoring.batch import MonitoringReport

        if not isinstance(report, MonitoringReport):
            raise TypeError(
                "monitoring.run() must return the MonitoringReport from run_monitoring(...)"
            )
        logger.info(
            "Monitoring complete: manifest %s; %d observations; %.2f seconds",
            report.manifest_id,
            len(report.runs),
            time.perf_counter() - started,
        )
        logger.info("SQL observations:\n%s", report.runs.to_string(index=False))
        return 0
    except KeyboardInterrupt:
        logger.error("Monitoring interrupted after %.2f seconds", time.perf_counter() - started)
        return 130
    except Exception:
        logger.exception("Monitoring failed after %.2f seconds", time.perf_counter() - started)
        return 1
    finally:
        for handler in (file_handler, console_handler):
            logger.removeHandler(handler)
            handler.close()
        logger.setLevel(previous_level)
        logger.propagate = previous_propagation
