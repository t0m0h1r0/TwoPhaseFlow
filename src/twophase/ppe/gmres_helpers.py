"""Small compatibility helpers for backend-native Krylov solvers."""

from __future__ import annotations


def backend_supports_gmres(linear_algebra) -> bool:
    """Return whether ``linear_algebra`` exposes GMRES and LinearOperator."""
    return hasattr(linear_algebra, "LinearOperator") and hasattr(linear_algebra, "gmres")


def backend_supports_cg(linear_algebra) -> bool:
    """Return whether ``linear_algebra`` exposes CG and LinearOperator."""
    return hasattr(linear_algebra, "LinearOperator") and hasattr(linear_algebra, "cg")


def solve_gmres(
    linear_algebra,
    operator,
    rhs,
    *,
    x0,
    preconditioner,
    restart,
    maxiter: int,
    tolerance: float,
):
    """Call SciPy/CuPy GMRES using the supported tolerance keyword."""
    try:
        return linear_algebra.gmres(
            operator,
            rhs,
            x0=x0,
            M=preconditioner,
            restart=restart,
            maxiter=maxiter,
            atol=0.0,
            rtol=tolerance,
        )
    except TypeError:
        return linear_algebra.gmres(
            operator,
            rhs,
            x0=x0,
            M=preconditioner,
            restart=restart,
            maxiter=maxiter,
            tol=tolerance,
        )


def solve_cg(
    linear_algebra,
    operator,
    rhs,
    *,
    x0,
    preconditioner,
    maxiter: int,
    tolerance: float,
):
    """Call SciPy/CuPy CG using the supported tolerance keyword."""
    try:
        return linear_algebra.cg(
            operator,
            rhs,
            x0=x0,
            M=preconditioner,
            maxiter=maxiter,
            atol=0.0,
            rtol=tolerance,
        )
    except TypeError:
        return linear_algebra.cg(
            operator,
            rhs,
            x0=x0,
            M=preconditioner,
            maxiter=maxiter,
            tol=tolerance,
        )
