"""Small array predicates shared by GPU hot paths."""

from __future__ import annotations


def all_arrays_exact_zero(xp, arrays) -> bool:
    """Return True when every supplied array is exactly zero."""
    zero_flags = xp.stack([
        xp.max(xp.abs(xp.asarray(array)))
        for array in arrays
    ])
    return not bool(xp.any(zero_flags))
