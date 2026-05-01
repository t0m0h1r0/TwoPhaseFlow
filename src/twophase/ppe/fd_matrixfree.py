"""Matrix-free low-order FD correction solver for defect correction.

A3 mapping
----------
Equation: the defect-correction step applies the paper's low-order operator
``L_L`` to the residual defect ``d^{(k)}``.

Discretization: this class uses the same pinned, conservative second-order
node-centered flux stencil as :class:`PPESolverFDDirect`, but applies the
operator matrix-free instead of assembling/factorizing it.

Code: ``solve`` applies an approximate ``L_L^{-1}`` through backend-native
Krylov iteration.  CG solves the control-volume-weighted SPD sign-flipped
system ``-W L_L p = -W rhs``; GMRES remains available for parity with the
matrix-free PPE infrastructure.  Direct fallback is intentionally disabled so
DC cannot silently leave the configured low-order iterative path.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .fvm_matrixfree import PPESolverFVMMatrixFree

if TYPE_CHECKING:
    from ..backend import Backend
    from ..config import SimulationConfig
    from ..core.boundary import BoundarySpec
    from ..core.grid import Grid


class PPESolverFDMatrixFree(PPESolverFVMMatrixFree):
    """Optional iterative ``L_L`` base solver for PPE defect correction."""

    scheme_names = ("fd_iterative",)
    _scheme_aliases = {
        "fd_matrixfree": "fd_iterative",
        "fd_cg": "fd_iterative",
    }

    def __init__(
        self,
        backend: "Backend",
        config: "SimulationConfig",
        grid: "Grid",
        bc_type: str = "wall",
        bc_spec: "BoundarySpec | None" = None,
    ):
        super().__init__(backend, config, grid, bc_type=bc_type, bc_spec=bc_spec)
        self.allow_direct_fallback = False
