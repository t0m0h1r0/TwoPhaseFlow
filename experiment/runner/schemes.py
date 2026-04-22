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


# ── Hydrostatic NS (ch12-style IPC projection) ───────────────────────────────

class _HydrostaticNSScheme:
    """IPC projection for hydrostatic equilibrium (rho=1, gravity=-1 in y).

    Convergence metric: L∞ pressure error vs p_exact = ρ|g|(1-y).
    """

    def __init__(self, N: int, domain: dict,
                 n_steps: int = 100, rho: float = 1.0,
                 g_y: float = -1.0, dt_scale: float = 0.1):
        self._N = N
        self._domain = domain
        self._n_steps = n_steps
        self._rho = rho
        self._g_y = g_y
        self._dt_scale = dt_scale

    def compute_errors(self, test_fn=None) -> dict:
        import numpy as _np
        from twophase.backend import Backend
        from twophase.config import GridConfig
        from twophase.core.grid import Grid
        from twophase.ccd.ccd_solver import CCDSolver
        from twophase.ppe.ppe_builder import PPEBuilder
        from twophase.tools.experiment.gpu import sparse_solve_2d

        backend = Backend()
        xp = backend.xp
        N = self._N
        Lx = float(self._domain.get("Lx", 1.0))
        h = Lx / N
        dt = self._dt_scale * h

        gc = GridConfig(ndim=2, N=(N, N), L=(Lx, Lx))
        grid = Grid(gc, backend)
        ccd = CCDSolver(grid, backend, bc_type="wall")
        ppe_builder = PPEBuilder(backend, grid, bc_type="wall")

        X, Y = grid.meshgrid()
        rho = xp.full_like(X, self._rho)

        u = xp.zeros_like(X)
        v = xp.zeros_like(X)
        p = self._rho * abs(self._g_y) * (1.0 - Y)   # exact IC

        def wall_bc(arr):
            arr[0, :] = 0; arr[-1, :] = 0
            arr[:, 0] = 0; arr[:, -1] = 0

        def solve_ppe(rhs):
            triplet, shape = ppe_builder.build(rho)
            data, rows, cols = [backend.to_device(a) for a in triplet]
            A = backend.sparse.csr_matrix((data, (rows, cols)), shape=shape)
            return sparse_solve_2d(backend, A, rhs.ravel()).reshape(rhs.shape)

        u_max_final = 0.0
        for _ in range(self._n_steps):
            dp_dx, _ = ccd.differentiate(p, 0)
            dp_dy, _ = ccd.differentiate(p, 1)
            u_star = u - dt / rho * dp_dx
            v_star = v + dt * self._g_y - dt / rho * dp_dy
            wall_bc(u_star); wall_bc(v_star)
            du_dx, _ = ccd.differentiate(u_star, 0)
            dv_dy, _ = ccd.differentiate(v_star, 1)
            phi = solve_ppe((du_dx + dv_dy) / dt)
            dphi_dx, _ = ccd.differentiate(phi, 0)
            dphi_dy, _ = ccd.differentiate(phi, 1)
            u = u_star - dt / rho * dphi_dx
            v = v_star - dt / rho * dphi_dy
            wall_bc(u); wall_bc(v)
            p = p + phi
            u_max_final = float(xp.max(xp.sqrt(u**2 + v**2)))
            if _np.isnan(u_max_final) or u_max_final > 1e6:
                break

        p_exact = self._rho * abs(self._g_y) * (1.0 - Y)
        p_shifted = p - xp.mean(p) + xp.mean(p_exact)
        s = slice(2, -2)
        p_err = float(xp.max(xp.abs(p_shifted[s, s] - p_exact[s, s])))
        return {"N": N, "h": h, "p_err_inf": p_err, "u_inf_final": u_max_final}


@register_scheme("hydrostatic_ns")
def _build_hydrostatic_ns(N: int, domain: dict, n_steps: int = 100,
                           rho: float = 1.0, g_y: float = -1.0,
                           dt_scale: float = 0.1, **_):
    return _HydrostaticNSScheme(N=N, domain=domain, n_steps=n_steps,
                                rho=rho, g_y=g_y, dt_scale=dt_scale)


# ── Curvature CCD vs CD2 (exp11_03) ──────────────────────────────────────────

class _CurvatureCCDScheme:
    """CCD curvature vs 2nd-order FD (CD2) on circle or sinusoidal interface."""

    def __init__(self, N: int, domain: dict, interface: str = "circle",
                 R: float = 0.25, eps_scale: float = 1.5):
        self._N = N
        self._domain = domain
        self._interface = interface
        self._R = R
        self._eps_scale = eps_scale

    def compute_errors(self, test_fn=None) -> dict:
        import numpy as _np
        from twophase.backend import Backend
        from twophase.config import GridConfig
        from twophase.core.grid import Grid
        from twophase.ccd.ccd_solver import CCDSolver
        from twophase.levelset.curvature import CurvatureCalculator
        from twophase.levelset.heaviside import heaviside

        backend = Backend()
        xp = backend.xp
        N = self._N
        Lx = float(self._domain.get("Lx", 1.0))
        h = Lx / N
        eps = self._eps_scale * h

        gc = GridConfig(ndim=2, N=(N, N), L=(Lx, Lx))
        grid = Grid(gc, backend)
        ccd = CCDSolver(grid, backend, bc_type="wall")
        X, Y = grid.meshgrid()

        if self._interface == "circle":
            R = self._R
            phi = R - xp.sqrt((X - 0.5) ** 2 + (Y - 0.5) ** 2)
            kappa_exact_scalar = 1.0 / R
            kappa_ref_arr = None
        else:  # sinusoidal
            A = 0.05
            y_if = 0.5 + A * xp.sin(2 * _np.pi * X)
            phi = y_if - Y
            f_p = A * 2 * _np.pi * xp.cos(2 * _np.pi * X)
            f_pp = -A * (2 * _np.pi) ** 2 * xp.sin(2 * _np.pi * X)
            kappa_ref_arr = -f_pp / (1 + f_p**2) ** 1.5
            kappa_exact_scalar = None

        psi = heaviside(xp, phi, eps)
        kappa_ccd = CurvatureCalculator(backend, ccd, eps).compute(psi)

        near = xp.abs(phi) < 3 * h
        if not bool(xp.any(near)):
            return {"N": N, "h": h, "ccd_Li": float("nan")}

        if kappa_exact_scalar is not None:
            ccd_Li = float(xp.max(xp.abs(kappa_ccd[near] - kappa_exact_scalar)))
        else:
            ccd_Li = float(xp.max(xp.abs(kappa_ccd[near] - kappa_ref_arr[near])))

        result = {"N": N, "h": h, "ccd_Li": ccd_Li}

        # CD2 curvature (circle only, for comparison panel)
        if self._interface == "circle":
            phi_x = xp.zeros_like(phi); phi_y = xp.zeros_like(phi)
            phi_x[1:-1, :] = (phi[2:, :] - phi[:-2, :]) / (2 * h)
            phi_y[:, 1:-1] = (phi[:, 2:] - phi[:, :-2]) / (2 * h)
            phi_xx = xp.zeros_like(phi); phi_yy = xp.zeros_like(phi); phi_xy = xp.zeros_like(phi)
            phi_xx[1:-1, :] = (phi[2:, :] - 2 * phi[1:-1, :] + phi[:-2, :]) / h**2
            phi_yy[:, 1:-1] = (phi[:, 2:] - 2 * phi[:, 1:-1] + phi[:, :-2]) / h**2
            phi_xy[1:-1, 1:-1] = (phi[2:, 2:] - phi[2:, :-2] - phi[:-2, 2:] + phi[:-2, :-2]) / (4 * h**2)
            gm = xp.sqrt(phi_x**2 + phi_y**2 + 1e-12)
            kappa_cd2 = -(phi_y**2 * phi_xx - 2 * phi_x * phi_y * phi_xy + phi_x**2 * phi_yy) / gm**3
            result["cd2_Li"] = float(xp.max(xp.abs(kappa_cd2[near] - kappa_exact_scalar)))

        return result


@register_scheme("curvature_ccd")
def _build_curvature_ccd(N: int, domain: dict, interface: str = "circle",
                          R: float = 0.25, eps_scale: float = 1.5, **_):
    return _CurvatureCCDScheme(N=N, domain=domain, interface=interface,
                               R=R, eps_scale=eps_scale)


# ── RC / C-RC bracket (exp11_05) ─────────────────────────────────────────────

class _RCBracketScheme:
    """Standard RC vs C/RC face gradient bracket (periodic, p=cos2πx·cos2πy)."""

    def __init__(self, N: int, domain: dict):
        self._N = N
        self._domain = domain

    def compute_errors(self, test_fn=None) -> dict:
        import numpy as _np
        from twophase.backend import Backend
        from twophase.config import GridConfig
        from twophase.core.grid import Grid
        from twophase.ccd.ccd_solver import CCDSolver

        backend = Backend()
        xp = backend.xp
        N = self._N
        Lx = float(self._domain.get("Lx", 1.0))
        h = Lx / N
        k = 2 * _np.pi

        gc = GridConfig(ndim=2, N=(N, N), L=(Lx, Lx))
        grid = Grid(gc, backend)
        ccd = CCDSolver(grid, backend, bc_type="periodic")
        X, Y = grid.meshgrid()

        p = xp.cos(k * X) * xp.cos(k * Y)
        _, d2p_dx2 = ccd.differentiate(p, axis=0)

        x_face = X[:-1, :] + h / 2
        dp_exact = -k * xp.sin(k * x_face) * xp.cos(k * Y[:-1, :])

        dp_std = (p[1:, :] - p[:-1, :]) / h
        dp_crc = (p[1:, :] - p[:-1, :]) / h - h / 24.0 * (d2p_dx2[1:, :] - d2p_dx2[:-1, :])

        err_std = float(xp.max(xp.abs(dp_std - dp_exact)))
        err_crc = float(xp.max(xp.abs(dp_crc - dp_exact)))
        return {"N": N, "h": h, "err_std": err_std, "err_crc": err_crc}


@register_scheme("rc_bracket")
def _build_rc_bracket(N: int, domain: dict, **_):
    return _RCBracketScheme(N=N, domain=domain)


# ── DC Poisson Dirichlet (exp11_09) ──────────────────────────────────────────

class _DCPoissonDirichletScheme:
    """Defect-correction Poisson with Dirichlet BC; p*=sin(πx)sin(πy)."""

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
            fd_laplacian_dirichlet_2d, max_abs_error,
            sparse_solve_2d, zero_dirichlet_boundary,
        )

        backend = Backend()
        xp = backend.xp
        N = self._N
        Lx = float(self._domain.get("Lx", 1.0))
        h = Lx / N

        gc = GridConfig(ndim=2, N=(N, N), L=(Lx, Lx))
        grid = Grid(gc, backend)
        ccd = CCDSolver(grid, backend, bc_type="wall")
        X, Y = grid.meshgrid()

        p_exact = xp.sin(_np.pi * X) * xp.sin(_np.pi * Y)
        rhs = -2.0 * _np.pi**2 * p_exact
        zero_dirichlet_boundary(rhs)
        L_L = fd_laplacian_dirichlet_2d(N, h, backend)

        p = xp.zeros_like(rhs)
        for _ in range(self._k_dc):
            Lp = xp.zeros_like(p)
            for ax in range(2):
                _, d2p = ccd.differentiate(p, ax)
                Lp += d2p
            d = rhs - Lp
            zero_dirichlet_boundary(d)
            dp = sparse_solve_2d(backend, L_L, d)
            p = p + dp
            zero_dirichlet_boundary(p)

        err = max_abs_error(backend, p, p_exact)
        return {"N": N, "h": h, "Li": float(err)}


@register_scheme("dc_poisson_dirichlet")
def _build_dc_poisson_dirichlet(N: int, domain: dict, k_dc: int = 3, **_):
    return _DCPoissonDirichletScheme(N=N, domain=domain, k_dc=k_dc)


# ── Variable-density PPE — smooth rho (exp11_12) ─────────────────────────────

class _VarroPPESmoothScheme:
    """Variable-density DC PPE; rho=1+A·sin(πx)cos(πy); p*=sin(πx)sin(πy)."""

    def __init__(self, N: int, domain: dict, A: float = 0.8, k_dc: int = 3):
        self._N = N
        self._domain = domain
        self._A = A
        self._k_dc = k_dc

    def compute_errors(self, test_fn=None) -> dict:
        import numpy as _np
        from twophase.backend import Backend
        from twophase.config import GridConfig
        from twophase.core.grid import Grid
        from twophase.ccd.ccd_solver import CCDSolver
        from twophase.tools.experiment.gpu import (
            fd_varrho_dirichlet_2d, max_abs_error,
            sparse_solve_2d, zero_dirichlet_boundary,
        )

        backend = Backend()
        xp = backend.xp
        N = self._N
        Lx = float(self._domain.get("Lx", 1.0))
        h = Lx / N
        A = self._A

        gc = GridConfig(ndim=2, N=(N, N), L=(Lx, Lx))
        grid = Grid(gc, backend)
        ccd = CCDSolver(grid, backend, bc_type="wall")
        X, Y = grid.meshgrid()

        p_exact = xp.sin(_np.pi * X) * xp.sin(_np.pi * Y)
        rho = 1.0 + A * xp.sin(_np.pi * X) * xp.cos(_np.pi * Y)

        pi = _np.pi
        sinx = xp.sin(pi * X); cosx = xp.cos(pi * X)
        siny = xp.sin(pi * Y); cosy = xp.cos(pi * Y)
        drho_dx = A * pi * cosx * cosy
        drho_dy = -A * pi * sinx * siny
        rhs = (-2 * pi**2 * sinx * siny) / rho - (drho_dx * pi * cosx * siny + drho_dy * pi * sinx * cosy) / rho**2
        zero_dirichlet_boundary(rhs)

        L_L = fd_varrho_dirichlet_2d(N, h, rho, backend)
        p = xp.zeros_like(rhs)
        for _ in range(self._k_dc):
            Lp = xp.zeros_like(p)
            for ax in range(2):
                dp_ax, d2p_ax = ccd.differentiate(p, ax)
                drho_ax, _ = ccd.differentiate(rho, ax)
                Lp += d2p_ax / rho - (drho_ax / rho**2) * dp_ax
            d = rhs - Lp
            zero_dirichlet_boundary(d)
            dp = sparse_solve_2d(backend, L_L, d)
            p = p + dp
            zero_dirichlet_boundary(p)

        err = max_abs_error(backend, p, p_exact)
        return {"N": N, "h": h, "Li": float(err)}


@register_scheme("varrho_ppe_smooth")
def _build_varrho_ppe_smooth(N: int, domain: dict, A: float = 0.8, k_dc: int = 3, **_):
    return _VarroPPESmoothScheme(N=N, domain=domain, A=A, k_dc=k_dc)


# ── Mixed partial CCD (exp11_23) ─────────────────────────────────────────────

class _MixedPartialCCDScheme:
    """Sequential CCD mixed partial d²f/dxdy on f=sin(2πx)cos(2πy)."""

    def __init__(self, N: int, domain: dict, bc_type: str = "periodic"):
        self._N = N
        self._domain = domain
        self._bc_type = bc_type

    def compute_errors(self, test_fn=None) -> dict:
        import numpy as _np
        from twophase.backend import Backend
        from twophase.config import GridConfig
        from twophase.core.grid import Grid
        from twophase.ccd.ccd_solver import CCDSolver

        backend = Backend()
        xp = backend.xp
        N = self._N
        Lx = float(self._domain.get("Lx", 1.0))
        h = Lx / N

        gc = GridConfig(ndim=2, N=(N, N), L=(Lx, Lx))
        grid = Grid(gc, backend)
        ccd = CCDSolver(grid, backend, bc_type=self._bc_type)
        X, Y = grid.meshgrid()

        k = 2 * _np.pi
        f = xp.sin(k * X) * xp.cos(k * Y)
        fxy_exact = -(k**2) * xp.cos(k * X) * xp.sin(k * Y)

        d1x, _ = ccd.differentiate(f, axis=0)
        d1xy, _ = ccd.differentiate(d1x, axis=1)
        d1y, _ = ccd.differentiate(f, axis=1)
        d1yx, _ = ccd.differentiate(d1y, axis=0)

        s = slice(2, -2) if self._bc_type == "wall" else slice(None)
        xy_Li = float(xp.max(xp.abs(d1xy[s, s] - fxy_exact[s, s])))
        yx_Li = float(xp.max(xp.abs(d1yx[s, s] - fxy_exact[s, s])))
        comm_Li = float(xp.max(xp.abs(d1xy[s, s] - d1yx[s, s])))

        return {"N": N, "h": h, "xy_Li": xy_Li, "yx_Li": yx_Li, "comm_Li": comm_Li}


@register_scheme("mixed_partial_ccd")
def _build_mixed_partial_ccd(N: int, domain: dict, bc_type: str = "periodic", **_):
    return _MixedPartialCCDScheme(N=N, domain=domain, bc_type=bc_type)


# ── Reinit interface shift (exp11_31) ─────────────────────────────────────────

class _ReinitShiftScheme:
    """Zero-level and centroid shift after reinit on circular interface."""

    def __init__(self, N: int, domain: dict, n_calls: int = 1, eps_coeff: float = 1.5):
        self._N = N
        self._domain = domain
        self._n_calls = n_calls
        self._eps_coeff = eps_coeff

    def compute_errors(self, test_fn=None) -> dict:
        import numpy as _np
        from twophase.backend import Backend
        from twophase.config import GridConfig
        from twophase.core.grid import Grid
        from twophase.ccd.ccd_solver import CCDSolver
        from twophase.levelset.reinitialize import Reinitializer
        from twophase.levelset.heaviside import heaviside

        backend = Backend()
        xp = backend.xp
        N = self._N
        Lx = float(self._domain.get("Lx", 1.0))
        h = Lx / N
        eps = self._eps_coeff * h

        gc = GridConfig(ndim=2, N=(N, N), L=(Lx, Lx))
        grid = Grid(gc, backend)
        ccd = CCDSolver(grid, backend, bc_type="wall")
        X, Y = grid.meshgrid()

        phi0 = 0.25 - xp.sqrt((X - 0.5)**2 + (Y - 0.5)**2)
        psi0 = heaviside(xp, phi0, eps)

        reinit = Reinitializer(backend, grid, ccd, eps, n_steps=5,
                               bc="zero", unified_dccd=False,
                               mass_correction=False, method="split")

        def zero_cross(psi):
            j = N // 2
            col = _np.asarray(backend.to_host(psi[:, j]))
            for i in range(len(col) - 1):
                if (col[i] - 0.5) * (col[i + 1] - 0.5) <= 0:
                    xi = float(backend.to_host(X[i, j]))
                    xi1 = float(backend.to_host(X[i + 1, j]))
                    t = (0.5 - col[i]) / (col[i + 1] - col[i])
                    return xi + t * (xi1 - xi)
            return float("nan")

        def centroid(psi):
            s = float(xp.sum(psi))
            if s < 1e-30:
                return float("nan"), float("nan")
            return float(xp.sum(psi * X) / s), float(xp.sum(psi * Y) / s)

        z0 = zero_cross(psi0)
        xc0, yc0 = centroid(psi0)

        psi = psi0.copy()
        for _ in range(self._n_calls):
            psi = reinit.reinitialize(psi)

        zn = zero_cross(psi)
        xcn, ycn = centroid(psi)
        zshift = abs(zn - z0) if not (_np.isnan(z0) or _np.isnan(zn)) else float("nan")
        cshift = float(_np.sqrt((xcn - xc0)**2 + (ycn - yc0)**2))

        return {"N": N, "h": h, "zero_shift": zshift, "centroid_shift": cshift}


@register_scheme("reinit_shift")
def _build_reinit_shift(N: int, domain: dict, n_calls: int = 1,
                         eps_coeff: float = 1.5, **_):
    return _ReinitShiftScheme(N=N, domain=domain, n_calls=n_calls, eps_coeff=eps_coeff)


# ── TVD-RK3 ODE integrator (exp11_14) ────────────────────────────────────────

class _TVDrk3OdeAdapter:
    """Shu-Osher SSP TVD-RK3 on dq/dt=-q, q(0)=1. run() → {q_final, dt, n}."""

    def run(self, n_steps: int, T_final: float = 1.0) -> dict:
        from twophase.backend import Backend
        from twophase.time_integration.tvd_rk3 import tvd_rk3

        backend = Backend()
        xp = backend.xp
        dt = T_final / n_steps
        q = xp.array([[1.0]])
        for _ in range(n_steps):
            q = tvd_rk3(xp, q, dt, lambda q: -q)
        return {"n": n_steps, "dt": dt, "q_final": float(q[0, 0])}


@register_scheme("tvd_rk3_ode")
def _build_tvd_rk3_ode(**_):
    return _TVDrk3OdeAdapter()


# ── TVD-RK3 scalar advection (exp11_14 panel b) ──────────────────────────────

class _TVDrk3AdvectionAdapter:
    """TVD-RK3 1D advection of sin(2πx) at fixed N=256; err=L2 after T=1."""

    def __init__(self, N: int = 256):
        self._N = N

    def run(self, n_steps: int, T_final: float = 1.0) -> dict:
        import numpy as _np
        from twophase.backend import Backend
        from twophase.config import GridConfig
        from twophase.core.grid import Grid
        from twophase.ccd.ccd_solver import CCDSolver
        from twophase.time_integration.tvd_rk3 import tvd_rk3

        backend = Backend()
        xp = backend.xp
        N = self._N
        gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
        grid = Grid(gc, backend)
        ccd = CCDSolver(grid, backend, bc_type="periodic")
        X, _ = grid.meshgrid()
        q0 = xp.sin(2 * _np.pi * X)

        dt = T_final / n_steps
        q = q0.copy()
        rhs_fn = lambda q: -1.0 * ccd.differentiate(q, 0)[0]
        for _ in range(n_steps):
            q = tvd_rk3(xp, q, dt, rhs_fn)

        err = float(xp.sqrt(xp.mean((q - q0)**2)))
        return {"n": n_steps, "dt": dt, "q_final": err}


@register_scheme("tvd_rk3_advection")
def _build_tvd_rk3_advection(N: int = 256, **_):
    return _TVDrk3AdvectionAdapter(N=N)


# ── Cross-viscous LTE (exp11_30) ──────────────────────────────────────────────

class _CrossViscousLTEAdapter:
    """Single-step FE LTE of cross-viscous term vs dt; MMS solution.

    PDE: u_t = d/dx[μ(x)·du/dy] + d/dy[μ(x)·du/dx] + f
    μ(x) = MU_BASE·(1+(mu_ratio-1)·Hε(x-0.5)), Hε smooth Heaviside.
    """

    def __init__(self, N: int = 64, mu_ratio: float = 1.0, mu_base: float = 0.01):
        self._N = N
        self._mu_ratio = mu_ratio
        self._mu_base = mu_base

    def run(self, n_steps: int, T_final: float = 1.0) -> dict:
        import numpy as _np
        from twophase.backend import Backend
        from twophase.config import GridConfig
        from twophase.core.grid import Grid
        from twophase.ccd.ccd_solver import CCDSolver

        backend = Backend()
        xp = backend.xp
        N = self._N
        dt = T_final / n_steps
        decay = 1.0
        k = 2 * _np.pi

        gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
        grid = Grid(gc, backend)
        ccd = CCDSolver(grid, backend, bc_type="periodic")
        X, Y = grid.meshgrid()

        # Smooth Heaviside viscosity
        h = 1.0 / N
        eps_mu = 2.0 * h
        H = 0.5 * (1.0 + xp.tanh((X - 0.5) / eps_mu))
        mu = self._mu_base * (1.0 + (self._mu_ratio - 1.0) * H)

        def u_exact_t(t):
            return xp.exp(-decay * t) * xp.sin(k * X) * xp.sin(k * Y)

        # MMS source: f = u_t - L_cross[u_exact]
        u0 = u_exact_t(0.0)

        du_dy0, _ = ccd.differentiate(u0, 1)
        du_dx0, _ = ccd.differentiate(u0, 0)
        mu_dudy0, _ = ccd.differentiate(mu * du_dy0, 0)
        mu_dudx0, _ = ccd.differentiate(mu * du_dx0, 1)
        L_cross_u0 = mu_dudy0 + mu_dudx0

        u_t0 = -decay * u0
        f0 = u_t0 - L_cross_u0

        u_num = u0 + dt * (L_cross_u0 + f0)
        u_ref = u_exact_t(dt)

        err = float(xp.sqrt(xp.mean((u_num - u_ref)**2)))
        return {"n": n_steps, "dt": dt, "q_final": err}


@register_scheme("cross_viscous_lte")
def _build_cross_viscous_lte(N: int = 64, mu_ratio: float = 1.0,
                              mu_base: float = 0.01, **_):
    return _CrossViscousLTEAdapter(N=N, mu_ratio=mu_ratio, mu_base=mu_base)


# ── CN viscous temporal convergence (exp11_25) ────────────────────────────────

class _CNViscousTemporalAdapter:
    """CN + CCD viscous heat equation; u=exp(-8π²νt)sin(2πx)sin(2πy)."""

    def __init__(self, N: int = 64, nu: float = 0.01):
        self._N = N
        self._nu = nu

    def run(self, n_steps: int, T_final: float = 1.0) -> dict:
        import numpy as _np
        from scipy.sparse.linalg import gmres, LinearOperator
        from twophase.backend import Backend
        from twophase.config import GridConfig
        from twophase.core.grid import Grid
        from twophase.ccd.ccd_solver import CCDSolver

        backend = Backend()
        xp = backend.xp
        N = self._N
        nu = self._nu
        dt = T_final / n_steps
        k = 2 * _np.pi

        gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
        grid = Grid(gc, backend)
        ccd = CCDSolver(grid, backend, bc_type="periodic")
        X_d, Y_d = grid.meshgrid()
        X = _np.asarray(backend.to_host(X_d))
        Y = _np.asarray(backend.to_host(Y_d))

        def u_ex(t):
            return _np.exp(-2 * k**2 * nu * t) * _np.sin(k * X) * _np.sin(k * Y)

        def lap_ccd(u):
            u_d = xp.asarray(u)
            _, d2x = ccd.differentiate(u_d, 0)
            _, d2y = ccd.differentiate(u_d, 1)
            return _np.asarray(backend.to_host(d2x + d2y))

        u = u_ex(0.0)
        shape = u.shape
        n = u.size

        for _ in range(n_steps):
            lap_n = lap_ccd(u)
            rhs = (u + 0.5 * dt * nu * lap_n).flatten()

            def matvec(v_flat):
                v = v_flat.reshape(shape)
                return (v - 0.5 * dt * nu * lap_ccd(v)).flatten()

            A_op = LinearOperator((n, n), matvec=matvec)
            u_new, _ = gmres(A_op, rhs, x0=u.flatten(), atol=1e-14,
                             restart=50, maxiter=200)
            u = u_new.reshape(shape)

        u_ref = u_ex(T_final)
        err = float(_np.sqrt(_np.mean((u - u_ref)**2)))
        return {"n": n_steps, "dt": dt, "q_final": err}


@register_scheme("cn_viscous_temporal")
def _build_cn_viscous_temporal(N: int = 64, nu: float = 0.01, **_):
    return _CNViscousTemporalAdapter(N=N, nu=nu)


# ── Kovasznay NS residual (exp12_05) ──────────────────────────────────────────

class _KovasznayNSScheme:
    """Steady NS momentum + divergence residual on Kovasznay exact flow."""

    def __init__(self, N: int, domain: dict, Re: float = 40.0):
        self._N = N
        self._domain = domain
        self._Re = Re

    def compute_errors(self, test_fn=None) -> dict:
        from twophase.backend import Backend
        from twophase.config import GridConfig
        from twophase.core.grid import Grid
        from twophase.ccd.ccd_solver import CCDSolver
        from twophase.tools.benchmarks.analytical_solutions import (
            kovasznay_velocity, kovasznay_pressure,
        )

        backend = Backend()
        xp = backend.xp
        N = self._N
        Lx = float(self._domain.get("Lx", 1.0))
        h = Lx / N
        nu = 1.0 / self._Re

        gc = GridConfig(ndim=2, N=(N, N), L=(Lx, Lx))
        grid = Grid(gc, backend)
        # Shift y to [-0.5, 0.5]
        grid.coords[1] = grid.coords[1] - 0.5
        ccd = CCDSolver(grid, backend, bc_type="wall")
        X, Y = grid.meshgrid()

        u, v = kovasznay_velocity(X, Y, self._Re)
        p = kovasznay_pressure(X, Y, self._Re)

        du_dx, d2u_dx2 = ccd.differentiate(u, 0)
        du_dy, d2u_dy2 = ccd.differentiate(u, 1)
        dv_dx, d2v_dx2 = ccd.differentiate(v, 0)
        dv_dy, d2v_dy2 = ccd.differentiate(v, 1)
        dp_dx, _ = ccd.differentiate(p, 0)
        dp_dy, _ = ccd.differentiate(p, 1)

        R_u = -(u * du_dx + v * du_dy) + nu * (d2u_dx2 + d2u_dy2) - dp_dx
        R_v = -(u * dv_dx + v * dv_dy) + nu * (d2v_dx2 + d2v_dy2) - dp_dy
        R_div = du_dx + dv_dy

        s = (slice(1, -1), slice(1, -1))
        err_mom = float(max(xp.max(xp.abs(R_u[s])), xp.max(xp.abs(R_v[s]))))
        err_div = float(xp.max(xp.abs(R_div[s])))
        return {"N": N, "h": h, "err_mom": err_mom, "err_div": err_div}


@register_scheme("kovasznay_ns")
def _build_kovasznay_ns(N: int, domain: dict, Re: float = 40.0, **_):
    return _KovasznayNSScheme(N=N, domain=domain, Re=Re)


# ── TGV AB2 temporal convergence (exp12_04) ───────────────────────────────────

class _TGVab2Adapter:
    """AB2 + IPC projection on TGV; L∞ velocity error vs dt at fixed N."""

    def __init__(self, N: int = 64, nu: float = 0.01, L_dom: float = 6.283185307):
        self._N = N
        self._nu = nu
        self._L = L_dom

    def run(self, n_steps: int, T_final: float = 0.5) -> dict:
        import numpy as _np
        from twophase.backend import Backend
        from twophase.config import GridConfig
        from twophase.core.grid import Grid
        from twophase.ccd.ccd_solver import CCDSolver
        from twophase.tools.benchmarks.analytical_solutions import tgv_velocity

        backend = Backend()
        xp = backend.xp
        N = self._N
        nu = self._nu
        L = self._L
        h = L / N
        dt = T_final / n_steps

        gc = GridConfig(ndim=2, N=(N, N), L=(L, L))
        grid = Grid(gc, backend)
        ccd = CCDSolver(grid, backend, bc_type="periodic")
        X, Y = grid.meshgrid()

        def fft_poisson(rhs):
            rhs_int = rhs[:-1, :-1]
            Ni = rhs_int.shape[0]
            kx = xp.fft.fftfreq(Ni, d=h) * 2 * _np.pi
            ky = xp.fft.fftfreq(Ni, d=h) * 2 * _np.pi
            KX, KY = xp.meshgrid(kx, ky, indexing="ij")
            K2 = KX**2 + KY**2; K2[0, 0] = 1.0
            p_hat = xp.fft.fft2(rhs_int) / (-K2); p_hat[0, 0] = 0.0
            p_int = xp.real(xp.fft.ifft2(p_hat))
            p = xp.zeros_like(rhs)
            p[:-1, :-1] = p_int; p[-1, :] = p[0, :]; p[:, -1] = p[:, 0]
            return p

        u, v = tgv_velocity(X, Y, 0.0, nu)
        p = -0.25 * (xp.cos(2 * X) + xp.cos(2 * Y))
        rhs_u_prev = rhs_v_prev = None

        for step in range(n_steps):
            du_dx, d2u_dx2 = ccd.differentiate(u, 0)
            du_dy, d2u_dy2 = ccd.differentiate(u, 1)
            dv_dx, d2v_dx2 = ccd.differentiate(v, 0)
            dv_dy, d2v_dy2 = ccd.differentiate(v, 1)
            rhs_u = -(u * du_dx + v * du_dy) + nu * (d2u_dx2 + d2u_dy2)
            rhs_v = -(u * dv_dx + v * dv_dy) + nu * (d2v_dx2 + d2v_dy2)
            dp_dx, _ = ccd.differentiate(p, 0)
            dp_dy, _ = ccd.differentiate(p, 1)

            if step == 0:
                u_s = u + dt * rhs_u - dt * dp_dx
                v_s = v + dt * rhs_v - dt * dp_dy
            else:
                u_s = u + dt * (1.5 * rhs_u - 0.5 * rhs_u_prev) - dt * dp_dx
                v_s = v + dt * (1.5 * rhs_v - 0.5 * rhs_v_prev) - dt * dp_dy

            rhs_u_prev, rhs_v_prev = rhs_u, rhs_v
            du_s_dx, _ = ccd.differentiate(u_s, 0)
            dv_s_dy, _ = ccd.differentiate(v_s, 1)
            phi = fft_poisson((du_s_dx + dv_s_dy) / dt)
            dphi_dx, _ = ccd.differentiate(phi, 0)
            dphi_dy, _ = ccd.differentiate(phi, 1)
            u = u_s - dt * dphi_dx
            v = v_s - dt * dphi_dy
            p = p + phi

        u_ex, v_ex = tgv_velocity(X, Y, T_final, nu)
        err = float(max(xp.max(xp.abs(u - u_ex)), xp.max(xp.abs(v - v_ex))))
        return {"n": n_steps, "dt": dt, "q_final": err}


@register_scheme("tgv_ab2")
def _build_tgv_ab2(N: int = 64, nu: float = 0.01, L_dom: float = 6.283185307, **_):
    return _TGVab2Adapter(N=N, nu=nu, L_dom=L_dom)


# ── CN interface viscous temporal (exp12_13) ──────────────────────────────────

class _CNInterfaceViscousAdapter:
    """CN viscous with jump μ; measures bulk vs interface L2 error vs dt.

    Returns q_final = bulk_l2 (primary metric for time_accuracy handler).
    """

    def __init__(self, N: int = 64, mu_base: float = 0.01, mu_ratio: float = 100.0,
                 decay: float = 1.0):
        self._N = N
        self._mu_base = mu_base
        self._mu_ratio = mu_ratio
        self._decay = decay

    def run(self, n_steps: int, T_final: float = 0.1) -> dict:
        import numpy as _np
        from scipy.sparse.linalg import gmres, LinearOperator
        from twophase.backend import Backend
        from twophase.config import GridConfig
        from twophase.core.grid import Grid
        from twophase.ccd.ccd_solver import CCDSolver

        backend = Backend()
        xp = backend.xp
        N = self._N
        dt = T_final / n_steps
        k = 2 * _np.pi
        decay = self._decay

        gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
        grid = Grid(gc, backend)
        ccd = CCDSolver(grid, backend, bc_type="periodic")
        X_d, Y_d = grid.meshgrid()
        X = _np.asarray(backend.to_host(X_d))
        Y = _np.asarray(backend.to_host(Y_d))

        h = 1.0 / N
        eps = 2.0 * h
        H = 0.5 * (1 + _np.tanh((X - 0.5) / eps))
        mu = self._mu_base * (1.0 + (self._mu_ratio - 1.0) * H)
        mu_d = xp.asarray(mu)

        def u_exact(t):
            return _np.exp(-decay * t) * _np.sin(k * X) * _np.sin(k * Y)

        def visc_op(u_np):
            u_d = xp.asarray(u_np)
            _, d2y = ccd.differentiate(u_d, 1)
            Lv = _np.asarray(backend.to_host(mu_d * d2y))
            return Lv

        u = u_exact(0.0)
        shape = u.shape
        n = u.size

        # MMS source: f = u_t - L[u]  where L[u] = mu(x)*d2u/dy2
        # u = exp(-decay*t)*sin(kx)*sin(ky) → d2u/dy2 = -k^2*u
        # f = -decay*u - mu*(-k^2)*u = u*(-decay + k^2*mu) (time-independent)
        f = u_exact(0.0) * (-decay + k**2 * mu)

        for _ in range(n_steps):
            Lv_n = visc_op(u)
            rhs = (u + 0.5 * dt * Lv_n + dt * f).flatten()

            def matvec(v_flat):
                v = v_flat.reshape(shape)
                return (v - 0.5 * dt * visc_op(v)).flatten()

            A_op = LinearOperator((n, n), matvec=matvec)
            u_new, _ = gmres(A_op, rhs, x0=u.flatten(), atol=1e-14,
                             restart=200, maxiter=1000)
            u = u_new.reshape(shape)

        u_ref = u_exact(T_final)
        err = _np.sqrt(_np.mean((u - u_ref)**2))

        bulk_mask = _np.abs(X - 0.5) > 6 * eps
        intf_mask = _np.abs(X - 0.5) < 3 * eps
        bulk_l2 = float(_np.sqrt(_np.mean(((u - u_ref)[bulk_mask])**2))) if bulk_mask.any() else float("nan")
        intf_l2 = float(_np.sqrt(_np.mean(((u - u_ref)[intf_mask])**2))) if intf_mask.any() else float("nan")

        return {"n": n_steps, "dt": dt, "q_final": bulk_l2, "intf_l2": intf_l2}


@register_scheme("cn_interface_viscous")
def _build_cn_interface_viscous(N: int = 64, mu_base: float = 0.01,
                                 mu_ratio: float = 100.0, decay: float = 1.0, **_):
    return _CNInterfaceViscousAdapter(N=N, mu_base=mu_base,
                                      mu_ratio=mu_ratio, decay=decay)


# ── TGV AB2 time history ──────────────────────────────────────────────────────

class _TGVab2HistoryAdapter:
    """AB2 + IPC projection on TGV; records E_k(t) and ||div||_∞ history."""

    def __init__(self, N: int = 64, nu: float = 0.01, L_dom: float = 6.283185307):
        self._N = N
        self._nu = nu
        self._L = L_dom

    def run_history(self, n_steps: int = 200, dt: float = 0.01,
                    checkpoint_interval: int = 5) -> list:
        import numpy as _np
        from twophase.backend import Backend
        from twophase.config import GridConfig
        from twophase.core.grid import Grid
        from twophase.ccd.ccd_solver import CCDSolver
        from twophase.tools.benchmarks.analytical_solutions import tgv_velocity

        backend = Backend()
        xp = backend.xp
        N, nu, L = self._N, self._nu, self._L
        h = L / N

        gc = GridConfig(ndim=2, N=(N, N), L=(L, L))
        grid = Grid(gc, backend)
        ccd = CCDSolver(grid, backend, bc_type="periodic")
        X, Y = grid.meshgrid()

        def fft_poisson(rhs):
            rhs_int = rhs[:-1, :-1]
            Ni = rhs_int.shape[0]
            kx = xp.fft.fftfreq(Ni, d=h) * 2 * _np.pi
            ky = xp.fft.fftfreq(Ni, d=h) * 2 * _np.pi
            KX, KY = xp.meshgrid(kx, ky, indexing="ij")
            K2 = KX**2 + KY**2; K2[0, 0] = 1.0
            p_hat = xp.fft.fft2(rhs_int) / (-K2); p_hat[0, 0] = 0.0
            p_int = xp.real(xp.fft.ifft2(p_hat))
            p = xp.zeros_like(rhs)
            p[:-1, :-1] = p_int; p[-1, :] = p[0, :]; p[:, -1] = p[:, 0]
            return p

        u, v = tgv_velocity(X, Y, 0.0, nu)
        p = -0.25 * (xp.cos(2 * X) + xp.cos(2 * Y))
        rhs_u_prev = rhs_v_prev = None
        history: list[dict] = []

        for step in range(n_steps):
            t = step * dt
            if step % checkpoint_interval == 0:
                E_k = float(0.5 * (xp.mean(u**2) + xp.mean(v**2)))
                E_k_exact = _np.pi**2 * _np.exp(-4 * nu * t) / L**2 * h**2 * N**2
                # Simple exact: 0.5*(u_ex^2 + v_ex^2) mean
                u_ex, v_ex = tgv_velocity(X, Y, t, nu)
                E_k_exact = float(0.5 * (xp.mean(u_ex**2) + xp.mean(v_ex**2)))
                du_dx, _ = ccd.differentiate(u, 0)
                dv_dy, _ = ccd.differentiate(v, 1)
                div_inf = float(xp.max(xp.abs(du_dx + dv_dy)))
                history.append({"t": t, "E_k": E_k, "E_k_exact": E_k_exact,
                                 "div_inf": div_inf})

            du_dx, d2u_dx2 = ccd.differentiate(u, 0)
            du_dy, d2u_dy2 = ccd.differentiate(u, 1)
            dv_dx, d2v_dx2 = ccd.differentiate(v, 0)
            dv_dy, d2v_dy2 = ccd.differentiate(v, 1)
            rhs_u = -(u * du_dx + v * du_dy) + nu * (d2u_dx2 + d2u_dy2)
            rhs_v = -(u * dv_dx + v * dv_dy) + nu * (d2v_dx2 + d2v_dy2)
            dp_dx, _ = ccd.differentiate(p, 0)
            dp_dy, _ = ccd.differentiate(p, 1)

            if step == 0:
                u_s = u + dt * rhs_u - dt * dp_dx
                v_s = v + dt * rhs_v - dt * dp_dy
            else:
                u_s = u + dt * (1.5 * rhs_u - 0.5 * rhs_u_prev) - dt * dp_dx
                v_s = v + dt * (1.5 * rhs_v - 0.5 * rhs_v_prev) - dt * dp_dy

            rhs_u_prev, rhs_v_prev = rhs_u, rhs_v
            du_s_dx, _ = ccd.differentiate(u_s, 0)
            dv_s_dy, _ = ccd.differentiate(v_s, 1)
            phi = fft_poisson((du_s_dx + dv_s_dy) / dt)
            dphi_dx, _ = ccd.differentiate(phi, 0)
            dphi_dy, _ = ccd.differentiate(phi, 1)
            u = u_s - dt * dphi_dx
            v = v_s - dt * dphi_dy
            p = p + phi

        # Final checkpoint
        t_final = n_steps * dt
        u_ex, v_ex = tgv_velocity(X, Y, t_final, nu)
        E_k = float(0.5 * (xp.mean(u**2) + xp.mean(v**2)))
        E_k_exact = float(0.5 * (xp.mean(u_ex**2) + xp.mean(v_ex**2)))
        du_dx, _ = ccd.differentiate(u, 0)
        dv_dy, _ = ccd.differentiate(v, 1)
        div_inf = float(xp.max(xp.abs(du_dx + dv_dy)))
        history.append({"t": t_final, "E_k": E_k, "E_k_exact": E_k_exact,
                         "div_inf": div_inf})
        return history


@register_scheme("tgv_ab2_history")
def _build_tgv_ab2_history(N: int = 64, nu: float = 0.01,
                            L_dom: float = 6.283185307, domain=None, **_):
    return _TGVab2HistoryAdapter(N=N, nu=nu, L_dom=L_dom)


# ── Pressure filter prohibition (convergence study) ────────────────────────

class _PressureFilterScheme:
    """Compute divergence error after velocity projection from filtered/clean pressure.

    pressure p = sin(2πx)sin(2πy). After applying DCCD filter with eps_d,
    compute grad(p_filtered) and resulting div error in velocity correction.
    """

    def __init__(self, N: int, eps_d: float = 0.0, **_):
        self._N = N
        self._eps_d = eps_d

    def compute_errors(self, test_fn=None) -> dict:
        import numpy as _np
        from twophase.backend import Backend
        from twophase.config import GridConfig
        from twophase.core.grid import Grid
        from twophase.ccd.ccd_solver import CCDSolver

        backend = Backend()
        xp = backend.xp
        N = self._N
        eps_d = self._eps_d
        L = 1.0
        h = L / N

        gc = GridConfig(ndim=2, N=(N, N), L=(L, L))
        grid = Grid(gc, backend)
        ccd = CCDSolver(grid, backend, bc_type="periodic")
        X, Y = grid.meshgrid()

        p_exact = xp.sin(2 * _np.pi * X) * xp.sin(2 * _np.pi * Y)
        p = p_exact.copy()

        if eps_d > 0.0:
            # 3-point DCCD filter in x then y (periodic)
            def filter1d(f, axis):
                result = f.copy()
                if axis == 0:
                    result = (1 - 2 * eps_d) * f + eps_d * (
                        xp.roll(f, -1, axis=0) + xp.roll(f, 1, axis=0))
                else:
                    result = (1 - 2 * eps_d) * f + eps_d * (
                        xp.roll(f, -1, axis=1) + xp.roll(f, 1, axis=1))
                return result
            p = filter1d(filter1d(p, 0), 1)

        dp_dx, _ = ccd.differentiate(p, 0)
        dp_dy, _ = ccd.differentiate(p, 1)
        # Exact grad p
        dp_dx_ex = 2 * _np.pi * xp.cos(2 * _np.pi * X) * xp.sin(2 * _np.pi * Y)
        dp_dy_ex = 2 * _np.pi * xp.sin(2 * _np.pi * X) * xp.cos(2 * _np.pi * Y)

        # Velocity correction: u^{n+1} = u* - dt*grad(p). Here u* = dt*grad(p_exact).
        # div(u^{n+1}) = div(dt*(grad(p_exact) - grad(p_filtered)))
        # For filtered: div error = div(dt*(grad(p_exact) - grad(p)))
        dt = 1.0
        err_x = dp_dx_ex - dp_dx
        err_y = dp_dy_ex - dp_dy
        d_err_x_dx, _ = ccd.differentiate(err_x, 0)
        d_err_y_dy, _ = ccd.differentiate(err_y, 1)
        err_div = float(xp.max(xp.abs(d_err_x_dx + d_err_y_dy)))

        return {"N": N, "h": h, "err_div": err_div}


@register_scheme("pressure_filter")
def _build_pressure_filter(N: int = 64, eps_d: float = 0.0, **kw):
    return _PressureFilterScheme(N=N, eps_d=eps_d)
