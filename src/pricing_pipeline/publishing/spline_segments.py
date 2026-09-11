"""Validate the normalized polynomial segments exported by SuperGLM."""

from __future__ import annotations

import math
import re
from typing import Any

SPLINE_TERM_TYPE = "SPLINE_PPOLY_1D"
SPLINE_COLUMNS = (
    "spline_a",
    "spline_b",
    "spline_c",
    "spline_d",
    "spline_lower",
    "spline_upper",
    "spline_upper_inclusive",
)
_NUMBER = r"[-+]?(?:inf|(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?)"
_INTERVAL = re.compile(rf"^\[\s*({_NUMBER})\s*,\s*({_NUMBER})\s*([\])])$", re.IGNORECASE)


def parse_spline_interval(label: str) -> tuple[float | None, float | None, int]:
    """Read exact bounds; NULL bounds represent the constant tails."""
    match = _INTERVAL.fullmatch(str(label).strip())
    if match is None:
        raise ValueError(f"invalid spline interval bounds: {label!r}")
    lower, upper = float(match[1]), float(match[2])
    inclusive = int(match[3] == "]")
    if lower >= upper or lower == math.inf or upper == -math.inf:
        raise ValueError(f"invalid spline interval bounds: {label!r}")
    if not math.isfinite(lower) and not math.isfinite(upper):
        raise ValueError("spline interval bounds cannot both be unbounded")
    if inclusive and not math.isfinite(upper):
        raise ValueError("unbounded spline interval cannot include infinity")
    if math.isfinite(lower) and math.isfinite(upper) and not math.isfinite(upper - lower):
        raise ValueError("spline interval width must be finite")
    return (
        lower if math.isfinite(lower) else None,
        upper if math.isfinite(upper) else None,
        inclusive,
    )


def validate_spline_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Validate one complete term and attach its numerical interval bounds."""
    if not rows:
        raise ValueError("spline term has no segments")
    result = []
    for row in rows:
        row = dict(row)
        lower, upper, inclusive = parse_spline_interval(row["level_code"])
        try:
            coefficients = [float(row[column]) for column in SPLINE_COLUMNS[:4]]
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("spline coefficients must contain four finite numbers") from exc
        if not all(math.isfinite(value) for value in coefficients):
            raise ValueError("spline coefficients must contain four finite numbers")
        if (lower is None or upper is None) and any(coefficients[1:]):
            raise ValueError("unbounded spline tail must have constant coefficients")
        multiplier = float(row["multiplier"])
        if (
            not math.isfinite(multiplier)
            or multiplier <= 0
            or not math.isclose(math.log(multiplier), coefficients[0], rel_tol=1e-12, abs_tol=1e-12)
        ):
            raise ValueError("spline displayed multiplier must equal exp(a)")
        row.update(zip(SPLINE_COLUMNS[:4], coefficients, strict=True))
        row.update(spline_lower=lower, spline_upper=upper, spline_upper_inclusive=inclusive)
        if result:
            previous = result[-1]
            if (
                lower is None
                or previous["spline_upper"] is None
                or (lower != previous["spline_upper"] or previous["spline_upper_inclusive"])
            ):
                raise ValueError("spline intervals must be ordered, contiguous and nonoverlapping")
        result.append(row)
    if not any(
        row["spline_lower"] is not None and row["spline_upper"] is not None for row in result
    ):
        raise ValueError("spline must contain a finite interval")
    if result[-1]["spline_upper"] is not None and not result[-1]["spline_upper_inclusive"]:
        raise ValueError("finite spline domain must include its final endpoint")
    return result
