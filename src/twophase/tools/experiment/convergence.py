"""
Convergence analysis utilities.

Extracted from experiment scripts where grid-refinement convergence
rate computation was duplicated across ch12 unit tests.
"""

from __future__ import annotations
import numpy as np
from typing import List, Dict, Sequence, Optional


def compute_convergence_rates(
    errors: Sequence[float],
    spacings: Sequence[float],
) -> List[float]:
    """Compute pairwise log-log convergence rates.

    rate_i = log(e_{i-1} / e_i) / log(h_{i-1} / h_i)

    Parameters
    ----------
    errors   : sequence of error norms (coarse → fine)
    spacings : sequence of grid spacings (coarse → fine)

    Returns
    -------
    rates : list of float (length = len(errors) - 1)
    """
    rates = []
    for i in range(1, len(errors)):
        if errors[i] > 0 and errors[i - 1] > 0 and spacings[i] != spacings[i - 1]:
            log_h = np.log(spacings[i - 1] / spacings[i])
            log_e = np.log(errors[i - 1] / errors[i])
            rates.append(log_e / log_h)
        else:
            rates.append(float('nan'))
    return rates


def convergence_table(
    results: List[Dict],
    h_key: str = "h",
    error_keys: Optional[List[str]] = None,
) -> str:
    """Format a convergence table as a string.

    Parameters
    ----------
    results    : list of dicts, each with h_key and error fields
    h_key      : key for grid spacing
    error_keys : keys to include (default: all numeric keys except h_key)

    Returns
    -------
    table : formatted string with N, h, errors, and convergence rates
    """
    if not results:
        return "(empty)"

    if error_keys is None:
        error_keys = [k for k in results[0] if k != h_key and isinstance(results[0][k], (int, float))]

    spacings = [r[h_key] for r in results]
    lines = []

    # Header
    cols = [f"{'h':>10s}"]
    for k in error_keys:
        cols.append(f"{k:>12s}")
        cols.append(f"{'rate':>6s}")
    lines.append(" | ".join(cols))
    lines.append("-" * len(lines[0]))

    # Rows
    for i, r in enumerate(results):
        row = [f"{r[h_key]:10.4e}"]
        for k in error_keys:
            row.append(f"{r[k]:12.4e}")
            if i == 0:
                row.append(f"{'—':>6s}")
            else:
                errs = [res[k] for res in results]
                rates = compute_convergence_rates(errs[:i + 1], spacings[:i + 1])
                row.append(f"{rates[-1]:6.2f}")
        lines.append(" | ".join(row))

    return "\n".join(lines)


def error_norms(exact, computed):
    """Compute L-inf and L2 error norms.

    Parameters
    ----------
    exact, computed : arrays of same shape

    Returns
    -------
    dict with 'Linf' and 'L2' keys
    """
    diff = np.asarray(exact) - np.asarray(computed)
    return {
        "Linf": float(np.max(np.abs(diff))),
        "L2": float(np.sqrt(np.mean(diff ** 2))),
    }
