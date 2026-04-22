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
