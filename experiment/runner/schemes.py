"""Scheme factory registry — wraps library operator classes into scheme adapters.

Each factory function is registered via @register_scheme and called by handlers as:

    adapter = SCHEME_REGISTRY["ccd"](N=64, domain={"Lx": 1.0, "Ly": 1.0}, bc_type="wall")
    errors = adapter.compute_errors(test_fn)

Adapters expose a uniform interface per experiment category:
  - SpatialSchemeAdapter: compute_errors(test_fn) → dict
  - TimeIntegratorAdapter: run(n_steps, dt, ic) → dict  [future]
  - AdvectionAdapter: advect(q0, vel, dt, n_steps) → array  [future]
"""

from __future__ import annotations

import numpy as np

from .registry import register_scheme


# ── CCD spatial differentiation ───────────────────────────────────────────────

class _CCDAdapter:
    """Adapter exposing CCDSolver.differentiate via compute_errors(test_fn)."""

    def __init__(self, ccd, grid, backend, *, bc_type: str,
                 diff_axes: tuple[int, ...], h: float, N: int):
        self.ccd = ccd
        self.grid = grid
        self.backend = backend
        self.bc_type = bc_type
        self.diff_axes = diff_axes
        self.h = h
        self.N = N

    def compute_errors(self, test_fn) -> dict:
        """Evaluate test_fn on grid, differentiate, return L∞ errors."""
        xp = self.backend.xp
        X, Y = self.grid.meshgrid()
        f_exact, (fx_ex, fy_ex), (fxx_ex, fyy_ex) = test_fn(X, Y, xp)
        s = slice(2, -2) if self.bc_type == "wall" else slice(None)

        result: dict = {"N": self.N, "h": self.h}

        # Single-axis: use short names (d1_Li, d2_Li); multi-axis: d1x_Li, d1y_Li, …
        single = len(self.diff_axes) == 1

        if 0 in self.diff_axes:
            d1x, d2x = self.ccd.differentiate(f_exact, axis=0)
            sfx = "" if single else "x"
            result[f"d1{sfx}_Li"] = float(xp.max(xp.abs(d1x[s, s] - fx_ex[s, s])))
            result[f"d2{sfx}_Li"] = float(xp.max(xp.abs(d2x[s, s] - fxx_ex[s, s])))

        if 1 in self.diff_axes:
            d1y, d2y = self.ccd.differentiate(f_exact, axis=1)
            result["d1y_Li"] = float(xp.max(xp.abs(d1y[s, s] - fy_ex[s, s])))
            result["d2y_Li"] = float(xp.max(xp.abs(d2y[s, s] - fyy_ex[s, s])))

        return result


@register_scheme("ccd")
def _build_ccd(N: int, domain: dict, bc_type: str = "periodic",
               alpha_grid: float = 1.0, nonuniform_init: bool = False,
               diff_axes=None, **_):
    """Build a CCDSolver and return a _CCDAdapter."""
    from twophase.backend import Backend
    from twophase.config import GridConfig
    from twophase.core.grid import Grid
    from twophase.ccd.ccd_solver import CCDSolver

    backend = Backend()
    Lx = float(domain.get("Lx", 1.0))
    Ly = float(domain.get("Ly", 1.0))
    gc = GridConfig(ndim=2, N=(N, N), L=(Lx, Ly), alpha_grid=alpha_grid)
    grid = Grid(gc, backend)

    if nonuniform_init and alpha_grid > 1.0:
        # Fit grid to a circular interface at domain centre (standard non-uniform probe)
        ccd_tmp = CCDSolver(grid, backend, bc_type="wall")
        X0, Y0 = np.meshgrid(
            np.linspace(0, Lx, N + 1),
            np.linspace(0, Ly, N + 1),
            indexing="ij",
        )
        R = min(Lx, Ly) * 0.25
        phi_init = np.sqrt((X0 - Lx / 2) ** 2 + (Y0 - Ly / 2) ** 2) - R
        grid.update_from_levelset(phi_init, eps=0.05, ccd=ccd_tmp)
        h_eff = float(
            sum(float(backend.to_host(grid.h[ax]).mean()) for ax in range(2)) / 2
        )
    else:
        h_eff = Lx / N

    ccd = CCDSolver(grid, backend, bc_type=bc_type)

    axes = tuple(diff_axes) if diff_axes is not None else (0, 1)
    return _CCDAdapter(ccd, grid, backend, bc_type=bc_type,
                       diff_axes=axes, h=h_eff, N=N)


# ── AB2 ODE time integrator ──────────────────────────────────────────────────

class _AB2OdeAdapter:
    """Adams-Bashforth 2nd-order scalar ODE integrator (Euler startup)."""

    def __init__(self, ode: str = "decay"):
        if ode != "decay":
            raise ValueError(f"Unknown ODE '{ode}'. Supported: 'decay' (dq/dt=-q, q(0)=1).")
        self.ode = ode

    def run(self, n_steps: int, T_final: float = 1.0) -> dict:
        dt = T_final / n_steps
        q = 1.0
        f_prev = None
        for step in range(n_steps):
            f_n = -q
            if step == 0:
                q = q + dt * f_n          # Euler startup
            else:
                q = q + dt * (1.5 * f_n - 0.5 * f_prev)
            f_prev = f_n
        return {"n": n_steps, "dt": dt, "q_final": q}


@register_scheme("ab2_ode")
def _build_ab2_ode(ode: str = "decay", **_):
    return _AB2OdeAdapter(ode=ode)


# ── Young-Laplace / curvature convergence ────────────────────────────────────

class _YoungLaplaceAdapter:
    """Measures Δp = κ (We=1) for a circular droplet of radius R."""

    def __init__(self, R: float = 0.25, We: float = 1.0, eps_scale: float = 1.5):
        self.R = R
        self.We = We
        self.eps_scale = eps_scale

    def compute_errors(self, test_fn=None) -> dict:
        raise NotImplementedError("YoungLaplaceAdapter uses compute_dp, not compute_errors.")

    def compute_dp(self, N: int, domain: dict) -> dict:
        from twophase.backend import Backend
        from twophase.config import GridConfig
        from twophase.core.grid import Grid
        from twophase.ccd.ccd_solver import CCDSolver
        from twophase.levelset.curvature import CurvatureCalculator
        from twophase.levelset.heaviside import heaviside

        backend = Backend()
        xp = backend.xp
        Lx = float(domain.get("Lx", 1.0))
        Ly = float(domain.get("Ly", 1.0))
        gc = GridConfig(ndim=2, N=(N, N), L=(Lx, Ly))
        grid = Grid(gc, backend)
        ccd = CCDSolver(grid, backend, bc_type="wall")
        h = Lx / N
        eps = self.eps_scale * h
        X, Y = grid.meshgrid()

        phi = self.R - xp.sqrt((X - Lx / 2) ** 2 + (Y - Ly / 2) ** 2)
        psi = heaviside(xp, phi, eps)
        curv_calc = CurvatureCalculator(backend, ccd, eps)
        kappa = curv_calc.compute(psi)

        near = xp.abs(phi) < 3 * h
        kappa_mean = float(xp.mean(kappa[near])) if bool(xp.any(near)) else float("nan")
        Dp_exact = (1.0 / self.R) / self.We
        Dp_measured = kappa_mean / self.We
        rel_err = abs(Dp_measured - Dp_exact) / Dp_exact

        return {"N": N, "h": h, "Dp": Dp_measured, "Dp_exact": Dp_exact, "rel_err": rel_err}


class _YoungLaplaceScheme:
    """Wraps _YoungLaplaceAdapter to look like a CCD-style scheme adapter."""

    def __init__(self, R: float = 0.25, We: float = 1.0, eps_scale: float = 1.5,
                 N: int = 32, domain: dict | None = None):
        self._adapter = _YoungLaplaceAdapter(R=R, We=We, eps_scale=eps_scale)
        self._N = N
        self._domain = domain or {"Lx": 1.0, "Ly": 1.0}

    def compute_errors(self, test_fn=None) -> dict:
        return self._adapter.compute_dp(self._N, self._domain)


@register_scheme("young_laplace")
def _build_young_laplace(N: int, domain: dict, R: float = 0.25,
                          We: float = 1.0, eps_scale: float = 1.5, **_):
    return _YoungLaplaceScheme(R=R, We=We, eps_scale=eps_scale, N=N, domain=domain)


# ── PPE Neumann + defect-correction (exp11_11) ───────────────────────────────

class _PPENeumannScheme:
    """CCD defect-correction PPE with all-Neumann BC + gauge pin.

    Test: p* = cos(π x)·cos(π y).  Returns L∞ error of the corrected solution.
    """

    def __init__(self, N: int, domain: dict, k_dc: int = 3):
        self._N = N
        self._domain = domain
        self._k_dc = k_dc

    def compute_errors(self, test_fn=None) -> dict:
        import numpy as _np
        from twophase.backend import Backend
        from twophase.config import GridConfig
        from twophase.core.grid import Grid
        from twophase.ccd.ccd_solver import CCDSolver
        from twophase.tools.experiment.gpu import (
            fd_laplacian_neumann_2d, max_abs_error, pin_gauge, sparse_solve_2d,
        )

        backend = Backend()
        xp = backend.xp
        N = self._N
        Lx = float(self._domain.get("Lx", 1.0))
        gc = GridConfig(ndim=2, N=(N, N), L=(Lx, Lx))
        grid = Grid(gc, backend)
        ccd = CCDSolver(grid, backend, bc_type="wall")
        h = Lx / N
        X, Y = grid.meshgrid()

        p_exact = xp.cos(_np.pi * X) * xp.cos(_np.pi * Y)
        rhs = -2 * _np.pi**2 * p_exact

        L = fd_laplacian_neumann_2d(N, h, backend)
        pin_dof = 0
        pin_val = float(_np.asarray(backend.to_host(p_exact.ravel()[0])))
        L_pinned, _ = pin_gauge(L, rhs.ravel(), pin_dof, pin_val, backend)

        p = xp.zeros_like(rhs)
        for _ in range(self._k_dc):
            Lp = xp.zeros_like(p)
            for ax in range(2):
                _, d2p = ccd.differentiate(p, ax)
                Lp += d2p
            d = rhs - Lp
            d.ravel()[pin_dof] = pin_val - p.ravel()[pin_dof]
            dp = sparse_solve_2d(backend, L_pinned, d)
            p = p + dp

        err = max_abs_error(backend, p, p_exact)
        return {"N": N, "h": h, "Li": float(err)}


@register_scheme("ppe_neumann")
def _build_ppe_neumann(N: int, domain: dict, k_dc: int = 3, **_):
    return _PPENeumannScheme(N=N, domain=domain, k_dc=k_dc)
