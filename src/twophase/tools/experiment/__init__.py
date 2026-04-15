"""Experiment toolkit — unified I/O, style, and plotting for experiment scripts.

Quick start::

    from twophase.tools.experiment import (
        # Style (call once)
        apply_style,
        # I/O
        experiment_dir, experiment_argparser, save_results, load_results,
        # Plotting
        field_panel, convergence_loglog, time_history, latex_convergence_table,
        summary_text, save_figure, figsize_grid,
        # Palettes
        COLORS, MARKERS, LINESTYLES,
        FIGSIZE_1COL, FIGSIZE_2COL, FIGSIZE_WIDE,
    )

    apply_style()
"""

from .style import (
    apply_style,
    COLORS,
    MARKERS,
    LINESTYLES,
    FIGSIZE_1COL,
    FIGSIZE_2COL,
    FIGSIZE_WIDE,
    FIGSIZE_PANEL,
    figsize_grid,
)
from .io import (
    experiment_dir,
    experiment_argparser,
    save_results,
    load_results,
)
from .figure import save_figure
from .plots import (
    field_panel,
    convergence_loglog,
    time_history,
    latex_convergence_table,
    summary_text,
)
from .convergence import (
    compute_convergence_rates,
    convergence_table,
    error_norms,
)
from .gpu import (
    fd_laplacian_dirichlet_2d,
    fd_laplacian_neumann_2d,
    fd_varrho_dirichlet_2d,
    l2_norm,
    max_abs_error,
    pin_gauge,
    sparse_solve_2d,
    to_float,
    zero_dirichlet_boundary,
)

__all__ = [
    "apply_style",
    "COLORS", "MARKERS", "LINESTYLES",
    "FIGSIZE_1COL", "FIGSIZE_2COL", "FIGSIZE_WIDE", "FIGSIZE_PANEL",
    "figsize_grid",
    "experiment_dir", "experiment_argparser",
    "save_results", "load_results",
    "save_figure",
    "field_panel", "convergence_loglog", "time_history",
    "latex_convergence_table", "summary_text",
    "compute_convergence_rates", "convergence_table", "error_norms",
    "fd_laplacian_dirichlet_2d", "fd_laplacian_neumann_2d",
    "fd_varrho_dirichlet_2d", "l2_norm", "max_abs_error",
    "pin_gauge", "sparse_solve_2d", "to_float",
    "zero_dirichlet_boundary",
]
