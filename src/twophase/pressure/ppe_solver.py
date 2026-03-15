"""
PPE linear solver (BiCGSTAB).

Implements §7.4 of the paper.

Solves the sparse linear system

    A p = rhs

assembled by :class:`~twophase.pressure.ppe_builder.PPEBuilder`.

The solver uses scipy's BiCGSTAB implementation with an ILU(0)
preconditioner from ``scipy.sparse.linalg``.  On GPU (CuPy), it falls
back to the CuPy equivalent.

Convergence is declared when ``‖r‖₂ / ‖b‖₂ < tol``.
"""

from __future__ import annotations
import numpy as np
from typing import Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from ..backend import Backend
    from ..config import SimulationConfig


class PPESolver:
    """BiCGSTAB solver for the PPE sparse system.

    Parameters
    ----------
    backend : Backend
    config  : SimulationConfig (provides tol and maxiter)
    """

    def __init__(self, backend: "Backend", config: "SimulationConfig"):
        self.backend = backend
        self.xp = backend.xp
        self.tol = config.bicgstab_tol
        self.maxiter = config.bicgstab_maxiter

    def solve(
        self,
        triplet: Tuple,
        A_shape: Tuple[int, int],
        rhs,
        n_dof: int,
        field_shape,
        p_init=None,
    ):
        """Solve A p = rhs.

        Parameters
        ----------
        triplet    : (data, row, col) COO arrays on host
        A_shape    : (n, n)
        rhs        : array, shape ``field_shape`` (will be flattened)
        n_dof      : total number of pressure unknowns
        field_shape: shape of the pressure field
        p_init     : optional warm-start array, shape ``field_shape``

        Returns
        -------
        p : array, shape ``field_shape``
        """
        import scipy.sparse as sp
        import scipy.sparse.linalg as spla
        import numpy as np_host

        data, rows, cols = triplet
        A = sp.csr_matrix((data, (rows, cols)), shape=A_shape)

        rhs_host = self.backend.to_host(rhs).ravel().astype(float)
        # Fix RHS: p[0] = 0 → set rhs[0] = 0
        rhs_host[0] = 0.0

        # Warm-start initial guess
        x0 = None
        if p_init is not None:
            x0 = self.backend.to_host(p_init).ravel().astype(float)

        # ILU(0) preconditioner
        try:
            ilu = spla.spilu(A.tocsc(), fill_factor=1)
            M = spla.LinearOperator(A_shape, ilu.solve)
        except Exception:
            M = None

        p_flat, info = spla.bicgstab(
            A, rhs_host,
            x0=x0,
            M=M,
            rtol=self.tol,
            maxiter=self.maxiter,
        )

        if info != 0:
            import warnings
            warnings.warn(
                f"PPE BiCGSTAB did not converge (info={info}). "
                "Consider increasing bicgstab_maxiter or loosening tol.",
                RuntimeWarning,
                stacklevel=2,
            )

        p_arr = np_host.reshape(p_flat, field_shape)
        return self.backend.to_device(p_arr)
