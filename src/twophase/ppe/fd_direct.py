"""Factorized low-order FD correction solver for defect correction.

Paper mapping
-------------
In Eq. ``eq:dc_three_step``, this class supplies the low-order correction
operator ``L_L``.  It solves the same second-order conservative FD flux form as
the legacy sparse low-order PPE path, but prepares the pinned matrix once per
outer defect-correction solve and explicitly reuses that prepared solve flow
for all correction RHSs.

Symbol mapping
--------------
``rhs`` → defect ``d^{(k)}``; ``rho`` → low-order density coefficient field;
``prepare_operator`` → factorize ``L_L``; ``solve`` → apply ``L_L^{-1}``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from .interfaces import IPPESolver
from .ppe_builder import PPEBuilder

if TYPE_CHECKING:
    from ..backend import Backend
    from ..core.boundary import BoundarySpec
    from ..core.grid import Grid
    from ..simulation.scheme_build_ctx import PPEBuildCtx


class PPESolverFDDirect(IPPESolver):
    """Pinned low-order FD direct solve with per-DC factor reuse."""

    scheme_names = ("fd_direct",)
    _scheme_aliases = {"fd_spsolve": "fd_direct"}

    @classmethod
    def _build(cls, name: str, ctx: "PPEBuildCtx") -> "PPESolverFDDirect":
        return cls(ctx.backend, ctx.grid, bc_type=ctx.bc_type, bc_spec=ctx.bc_spec)

    def __init__(
        self,
        backend: "Backend",
        grid: "Grid",
        bc_type: str = "wall",
        bc_spec: "BoundarySpec | None" = None,
    ):
        self.backend = backend
        self.xp = backend.xp
        self.bc_type = bc_type
        self.bc_spec = bc_spec
        self.ppb = PPEBuilder(backend, grid, bc_type, bc_spec)
        self._refresh_structure(grid)
        self._factor = None
        self._reuse_static_operator = False
        self._prepared_rho_token = None

    def set_static_operator_cache(self, enabled: bool) -> None:
        self._reuse_static_operator = bool(enabled)
        if not enabled:
            self._prepared_rho_token = None

    def _refresh_structure(self, grid: "Grid") -> None:
        dummy_rho = np.ones(grid.shape, dtype=np.float64)
        triplet, shape = self.ppb.build(dummy_rho)
        self._rows = triplet[1]
        self._cols = triplet[2]
        self._shape = shape

    def update_grid(self, grid: "Grid") -> None:
        self.ppb = PPEBuilder(self.backend, grid, self.bc_type, self.bc_spec)
        self._refresh_structure(grid)
        self._factor = None
        self._prepared_rho_token = None

    def invalidate_cache(self) -> None:
        self.ppb.invalidate_gpu_cache()
        self._factor = None
        self._prepared_rho_token = None

    def prepare_operator(self, rho) -> None:
        rho_dev = self.xp.asarray(rho)
        rho_token = _static_rho_token(rho_dev)
        if (
            self._reuse_static_operator
            and self._factor is not None
            and self._prepared_rho_token == rho_token
        ):
            return
        data = self.ppb.build_values(rho_dev)
        if self.backend.is_gpu():
            matrix = self.backend.sparse.csc_matrix(
                (data, (self._rows, self._cols)),
                shape=self._shape,
            )
        else:
            import scipy.sparse as sp

            matrix = sp.csc_matrix(
                (data, (self._rows, self._cols)),
                shape=self._shape,
            )
        factor = self.backend.sparse_linalg.splu(matrix)
        if self.backend.is_gpu():
            factor = _PreparedCuPySuperLUSolve(
                factor,
                rhs_shape=(self._shape[0], 1),
            )
        self._factor = factor
        self._prepared_rho_token = rho_token

    def solve(self, rhs, rho, dt: float = 0.0, p_init=None):
        if self._factor is None:
            self.prepare_operator(rho)
        rhs_vec = self.xp.asarray(rhs).ravel().copy()
        rhs_vec[self.ppb._pin_dof] = 0.0
        pressure_vec = self._factor.solve(rhs_vec)
        analysis_count = getattr(self._factor, "analysis_count", 0)
        self.last_diagnostics = {
            "ppe_fd_direct_factor_reuse": 1.0,
            "ppe_fd_direct_prepared_spsm_analysis_count": float(analysis_count),
        }
        return self.xp.asarray(pressure_vec).reshape(self.ppb.shape_field)


def _static_rho_token(rho) -> tuple:
    pointer = getattr(getattr(rho, "data", None), "ptr", None)
    dtype = getattr(getattr(rho, "dtype", None), "str", str(getattr(rho, "dtype", "")))
    return (id(rho), pointer, tuple(getattr(rho, "shape", ())), dtype)


class _PreparedCuPySuperLUSolve:
    """Explicit vector-RHS solve flow for one prepared SuperLU factorization."""

    def __init__(self, raw_factor, *, rhs_shape: tuple[int, int]):
        self.raw = raw_factor
        self.L = raw_factor.L
        self.U = raw_factor.U
        self.shape = raw_factor.shape
        self.perm_r = raw_factor.perm_r
        self.perm_c = raw_factor.perm_c
        self._perm_r_rev = raw_factor._perm_r_rev
        expected_shape = (int(self.shape[0]), 1)
        if tuple(rhs_shape) != expected_shape:
            raise RuntimeError(
                "FD direct GPU solve plan must be prepared for vector RHSs "
                f"{expected_shape}, got {rhs_shape}"
            )
        self._lower_plan = _PreparedCuPySpSMPlan(
            self.L,
            lower=True,
            transa="N",
            rhs_shape=expected_shape,
        )
        self._upper_plan = _PreparedCuPySpSMPlan(
            self.U,
            lower=False,
            transa="N",
            rhs_shape=expected_shape,
        )

    @property
    def analysis_count(self) -> int:
        return self._lower_plan.analysis_count + self._upper_plan.analysis_count

    def solve(self, rhs, trans="N"):
        """Solve a vector RHS through the explicitly prepared SpSM plans."""
        import cupy

        if not isinstance(rhs, cupy.ndarray):
            raise TypeError("rhs must be cupy.ndarray")
        if trans != "N":
            raise RuntimeError("FD direct GPU solve plan supports only trans='N'")
        if rhs.ndim != 1:
            raise RuntimeError("FD direct GPU solve plan supports only vector RHSs")
        if rhs.shape[0] != self.shape[0]:
            raise ValueError(
                f"shape mismatch (self.shape: {self.shape}, rhs.shape: {rhs.shape})"
            )

        x = rhs.astype(self.L.dtype)
        if self.perm_r is not None:
            x = x[self._perm_r_rev]
        x = self._lower_plan.solve_vector(x)
        x = self._upper_plan.solve_vector(x)
        if self.perm_c is not None:
            x = x[self.perm_c]
        if not x._f_contiguous:
            x = x.copy(order="F")
        return x


class _PreparedCuPySpSMPlan:
    """One explicitly analysed SpSM plan for a fixed A and vector RHS shape."""

    def __init__(self, matrix, *, lower: bool, transa: str, rhs_shape):
        import cupy
        import numpy as _np
        from cupyx import cusparse

        if not cusparse.check_availability("spsm"):
            raise RuntimeError("cuSPARSE SpSM is required for GPU FD direct solve plans")
        self._cusparse = cusparse
        self._cupy = cupy
        self.matrix, lower, transa = _canonical_spsm_matrix(
            cusparse,
            matrix,
            lower=lower,
            transa=transa,
        )
        if not getattr(self.matrix, "has_canonical_format", False):
            raise RuntimeError("GPU FD direct solve plan requires canonical sparse factors")
        self.rhs_shape = tuple(int(value) for value in rhs_shape)
        if self.rhs_shape != (int(self.matrix.shape[0]), 1):
            raise RuntimeError("GPU FD direct solve plan requires vector RHS shape")
        self.dtype = self.matrix.dtype
        if self.dtype.char not in "fdFD":
            raise TypeError(f"GPU FD direct solve plan does not support {self.dtype}")
        self._analysis_count = 0

        fill_mode = (
            cusparse._cusparse.CUSPARSE_FILL_MODE_LOWER
            if lower
            else cusparse._cusparse.CUSPARSE_FILL_MODE_UPPER
        )
        diag_type = cusparse._cusparse.CUSPARSE_DIAG_TYPE_NON_UNIT
        if transa == "N":
            op_a = cusparse._cusparse.CUSPARSE_OPERATION_NON_TRANSPOSE
        elif transa == "T":
            op_a = cusparse._cusparse.CUSPARSE_OPERATION_TRANSPOSE
        elif transa == "H":
            op_a = (
                cusparse._cusparse.CUSPARSE_OPERATION_TRANSPOSE
                if matrix.dtype.char in "fd"
                else cusparse._cusparse.CUSPARSE_OPERATION_CONJUGATE_TRANSPOSE
            )
        else:
            raise ValueError(f"unsupported transa {transa!r}")
        self._op_a = op_a
        self._op_b = cusparse._cusparse.CUSPARSE_OPERATION_NON_TRANSPOSE
        self._algo = cusparse._cusparse.CUSPARSE_SPSM_ALG_DEFAULT
        self._alpha_host = _np.array(1.0, dtype=self.dtype)
        self._alpha = self._alpha_host.ctypes
        self._cuda_dtype = cusparse._dtype.to_cuda_dtype(self.dtype)
        self._handle = cusparse._device.get_cusparse_handle()

        self._b_work = cupy.empty(self.rhs_shape, dtype=self.dtype, order="F")
        self._c_work = cupy.zeros(self.rhs_shape, dtype=self.dtype, order="F")
        self._mat_a = cusparse.SpMatDescriptor.create(self.matrix)
        self._mat_b = cusparse.DnMatDescriptor.create(self._b_work)
        self._mat_c = cusparse.DnMatDescriptor.create(self._c_work)
        self._descr = cusparse._cusparse.spSM_createDescr()
        self._mat_a.set_attribute(cusparse._cusparse.CUSPARSE_SPMAT_FILL_MODE, fill_mode)
        self._mat_a.set_attribute(cusparse._cusparse.CUSPARSE_SPMAT_DIAG_TYPE, diag_type)
        self._buff_size = cusparse._cusparse.spSM_bufferSize(
            self._handle,
            self._op_a,
            self._op_b,
            self._alpha.data,
            self._mat_a.desc,
            self._mat_b.desc,
            self._mat_c.desc,
            self._cuda_dtype,
            self._algo,
            self._descr,
        )
        self._buff = cupy.empty(self._buff_size, dtype=cupy.int8)
        cusparse._cusparse.spSM_analysis(
            self._handle,
            self._op_a,
            self._op_b,
            self._alpha.data,
            self._mat_a.desc,
            self._mat_b.desc,
            self._mat_c.desc,
            self._cuda_dtype,
            self._algo,
            self._descr,
            self._buff.data.ptr,
        )
        self._analysis_count = 1

    @property
    def analysis_count(self) -> int:
        return self._analysis_count

    def __del__(self):
        cusparse = getattr(self, "_cusparse", None)
        descr = getattr(self, "_descr", None)
        if cusparse is not None and descr is not None:
            try:
                cusparse._cusparse.spSM_destroyDescr(descr)
            except Exception:
                pass
            self._descr = None

    def solve_vector(self, rhs):
        if rhs.ndim != 1 or rhs.shape[0] != self.rhs_shape[0]:
            raise ValueError("GPU FD direct solve plan RHS shape mismatch")
        rhs_2d = rhs.reshape(self.rhs_shape)
        self._b_work[...] = rhs_2d
        self._c_work.fill(0)
        self._cusparse._cusparse.spSM_solve(
            self._handle,
            self._op_a,
            self._op_b,
            self._alpha.data,
            self._mat_a.desc,
            self._mat_b.desc,
            self._mat_c.desc,
            self._cuda_dtype,
            self._algo,
            self._descr,
            self._buff.data.ptr,
        )
        return self._c_work.reshape(-1).copy(order="F")


def _canonical_spsm_matrix(cusparse, matrix, *, lower: bool, transa: str):
    import cupyx.scipy.sparse as sparse

    if sparse.isspmatrix_csr(matrix):
        return matrix, lower, transa
    if sparse.isspmatrix_csc(matrix):
        if transa == "N":
            return matrix.T, not lower, "T"
        if transa == "T":
            return matrix.T, not lower, "N"
        if transa == "H":
            return matrix.conj().T, not lower, "N"
    if sparse.isspmatrix_coo(matrix):
        return matrix, lower, transa
    raise ValueError("GPU FD direct solve plan requires CSR, CSC, or COO factor")
