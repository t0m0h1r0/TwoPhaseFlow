"""I/O helpers for the experiment runner.

Thin wrappers around twophase.tools.experiment.io that handle the
list-of-dicts ↔ flat NPZ round-trip used by convergence-study handlers.
"""

from __future__ import annotations

import pathlib
from typing import Any

import numpy as np


def unpack_to_list(group: dict[str, Any]) -> list[dict[str, Any]]:
    """Convert ``{"h": array, "d1x_Li": array, ...}`` to ``[{"h": v, ...}, ...]``.

    This inverts the columnar storage that ``save_results`` uses when it
    receives a list-of-dicts (numpy stores them as arrays of scalars).
    """
    # Find the length from the first array-like value
    length = None
    for v in group.values():
        arr = np.asarray(v)
        if arr.ndim >= 1:
            length = len(arr)
            break
    if length is None:
        return []

    rows = []
    for i in range(length):
        row = {}
        for k, v in group.items():
            arr = np.asarray(v)
            if arr.ndim == 0:
                row[k] = arr.item()
            else:
                item = arr[i]
                row[k] = item.item() if hasattr(item, "item") else item
        rows.append(row)
    return rows
