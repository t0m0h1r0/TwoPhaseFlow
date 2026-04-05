"""Unified matplotlib style for all experiment scripts.

Usage::

    from twophase.experiment.style import apply_style, COLORS, MARKERS

    apply_style()          # call once at import time
    fig, ax = plt.subplots(figsize=FIGSIZE_2COL)
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402

# ── Publication-quality rcParams ──────────────────────────────────────────────

_RC = {
    # Font
    "font.size": 9,
    "axes.titlesize": 10,
    "axes.labelsize": 10,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "legend.fontsize": 8,
    # Lines
    "lines.linewidth": 1.5,
    "lines.markersize": 5,
    # Grid
    "axes.grid": False,
    # Figure
    "figure.dpi": 150,
    "savefig.dpi": 150,
    "savefig.bbox": "tight",
    # LaTeX-compatible math
    "mathtext.fontset": "cm",
    # Colorbar
    "image.cmap": "RdBu_r",
}


def apply_style() -> None:
    """Apply unified rcParams.  Idempotent — safe to call multiple times."""
    plt.rcParams.update(_RC)


# ── Standard palettes ─────────────────────────────────────────────────────────

#: Categorical colors for up to 8 series (tab10 subset).
COLORS = [
    "#1f77b4",  # blue
    "#d62728",  # red
    "#2ca02c",  # green
    "#ff7f0e",  # orange
    "#9467bd",  # purple
    "#8c564b",  # brown
    "#e377c2",  # pink
    "#7f7f7f",  # gray
]

#: Marker cycle matching COLORS.
MARKERS = ["o", "s", "^", "D", "v", "P", "X", "*"]

#: Line-style cycle for monochrome or overlay plots.
LINESTYLES = ["-", "--", "-.", ":", (0, (3, 1, 1, 1)), (0, (5, 2))]

# ── Standard figure sizes (inches) ───────────────────────────────────────────

FIGSIZE_1COL = (5, 4)        # single-column (half page)
FIGSIZE_2COL = (7, 5)        # two-column default
FIGSIZE_WIDE = (10, 4)       # wide single-row
FIGSIZE_PANEL = (3.5, 3.0)   # per-panel unit for multi-panel figures


def figsize_grid(nrows: int, ncols: int,
                 panel_w: float = 3.5, panel_h: float = 3.0) -> tuple[float, float]:
    """Compute figure size for an (nrows x ncols) subplot grid."""
    return (panel_w * ncols, panel_h * nrows)
