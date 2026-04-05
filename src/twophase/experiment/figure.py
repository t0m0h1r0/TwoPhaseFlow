"""Figure save/creation helpers.

Enforces project conventions:
  - PDF format only (publication-quality vector)
  - dpi=150, bbox_inches="tight"
  - Dual-path output for viz scripts (results/ + paper/figures/)
"""

from __future__ import annotations

import pathlib

import matplotlib.pyplot as plt
from matplotlib.figure import Figure


def save_figure(
    fig: Figure,
    path: str | pathlib.Path,
    *,
    also_to: str | pathlib.Path | None = None,
    close: bool = True,
) -> None:
    """Save figure as PDF with project-standard settings.

    Parameters
    ----------
    fig : Figure
        Matplotlib figure to save.
    path : path-like
        Primary output path.  Suffix is forced to ``.pdf``.
    also_to : path-like, optional
        Secondary output path (e.g. ``paper/figures/``).
    close : bool
        Close the figure after saving (default True).
    """
    p = pathlib.Path(path).with_suffix(".pdf")
    p.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(p, format="pdf", bbox_inches="tight", dpi=150)
    print(f"Saved figure → {p}")

    if also_to is not None:
        p2 = pathlib.Path(also_to).with_suffix(".pdf")
        p2.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(p2, format="pdf", bbox_inches="tight", dpi=150)
        print(f"Saved figure → {p2}")

    if close:
        plt.close(fig)
