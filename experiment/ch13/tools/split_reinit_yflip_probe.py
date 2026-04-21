"""CHK-168 Phase 1 — operator-isolation probe for split-reinit y-flip asymmetry.

Reproduces the step-5 jump (1e-15 → 1e-6 in sym_psi_y) seen in
``ch13_04_sym_B_alpha2_split`` by dissecting one ``SplitReinitializer``
call into its constituent operators on a y-flip-symmetric input:

    stage A : dccd_compression_div          (∇·[ψ(1−ψ) n̂])
    stage B : A → clip(q − dτ·divcomp)      → q_star
    stage C : B → cn_diffusion_axis(x)      → q_B
    stage D : C → cn_diffusion_axis(y)      → q_C  (one full inner iteration)
    stage E : full SplitReinitializer.reinitialize(ψ)  (n_steps=4 + mass corr)

For each stage we report

    yflip_err = ||op(ψ) − flip_y(op(flip_y(ψ)))||_∞ / max|op(ψ)|
    xflip_err = ||op(ψ) − flip_x(op(flip_x(ψ)))||_∞ / max|op(ψ)|

as well as the x→y / y→x ordering swap at stage D to probe Yanenko (C3).

Setup matches ``experiment/ch13/config/ch13_04_sym_B_alpha2_split.yaml``:
NX=NY=64, L=1, α_grid=2, use_local_eps=true, reinit_eps_scale=1.4.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

_REPO_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_REPO_SRC) not in sys.path:
    sys.path.insert(0, str(_REPO_SRC))

from twophase.backend import Backend
from twophase.ccd.ccd_solver import CCDSolver
from twophase.config import GridConfig
from twophase.core.grid import Grid
from twophase.levelset.reinit_split import SplitReinitializer
from twophase.levelset.reinit_ops import (
    dccd_compression_div,
    cn_diffusion_axis,
    compute_gradient_normal,
    filtered_divergence,
)
from twophase.levelset.heaviside import apply_mass_correction
from twophase.simulation.initial_conditions.shapes import PerturbedCircle


# ── helpers ──────────────────────────────────────────────────────────────


def _flip(a: np.ndarray, axis: int) -> np.ndarray:
    return np.flip(a, axis=axis)


def _rel_err(a: np.ndarray, b: np.ndarray) -> float:
    denom = float(np.max(np.abs(a)))
    if denom == 0.0:
        return 0.0
    return float(np.max(np.abs(a - b))) / denom


def _sym_err(op, psi: np.ndarray, axis: int, parity: int = +1) -> float:
    """Parity-aware equivariance error.

    parity=+1: expect  op(flip(ψ)) = flip(op(ψ))   (even)
    parity=−1: expect  op(flip(ψ)) = −flip(op(ψ))  (odd)
    """
    forward = op(psi)
    flipped = _flip(op(_flip(psi, axis)), axis)
    diff = forward - parity * flipped
    denom = float(np.max(np.abs(forward)))
    if denom == 0.0:
        return 0.0
    return float(np.max(np.abs(diff))) / denom


# ── probe setup (mirrors sym_B config) ───────────────────────────────────


def build_env(N: int = 64, alpha_grid: float = 2.0):
    backend = Backend(use_gpu=False)
    gc = GridConfig(
        ndim=2,
        N=(N, N),
        L=(1.0, 1.0),
        alpha_grid=alpha_grid,
        eps_g_factor=2.0,
    )
    grid = Grid(gc, backend)
    ccd = CCDSolver(grid, backend)

    # ε: reinit_eps_scale=1.4 × nominal 1.5 / N (same as yaml)
    eps = 1.4 * 1.5 / N

    # Perturbed circle (mode=2) — analytically y-flip-symmetric about y=0.5.
    shape = PerturbedCircle(
        center=(0.5, 0.5), radius=0.25, epsilon=0.05, mode=2,
        interior_phase="liquid",
    )
    X, Y = grid.meshgrid()
    phi = shape.sdf(np.asarray(X), np.asarray(Y))
    # CLS Heaviside ψ = 0.5 · (1 − tanh(φ/(2ε)))  (interior=liquid ⇒ ψ=1)
    psi0 = 0.5 * (1.0 - np.tanh(phi / (2.0 * eps)))

    # interface-fitted grid update (α=2 stretched) — matches runner path.
    grid.update_from_levelset(psi0, eps, ccd=ccd)

    # Rebuild ψ on the new (stretched) node coords so the input is still the
    # analytic shape on the stretched mesh — this is the form the solver
    # sees at reinit call time in the real run.
    X, Y = grid.meshgrid()
    phi = shape.sdf(np.asarray(X), np.asarray(Y))
    psi0 = 0.5 * (1.0 - np.tanh(phi / (2.0 * eps)))

    return backend, grid, ccd, eps, psi0


# ── stages (closed over reinit instance) ─────────────────────────────────


def make_stage_ops(reinit: SplitReinitializer, ccd: CCDSolver, grid, eps: float):
    xp = reinit.xp
    bc = reinit._bc
    eps_d_comp = reinit._eps_d_comp
    dtau = reinit.dtau
    h = reinit._h
    cn_factors = reinit._cn_factors

    def stage_diff_x(psi):
        g, _ = ccd.differentiate(psi, 0)
        return g

    def stage_diff_y(psi):
        g, _ = ccd.differentiate(psi, 1)
        return g

    def stage_diff_x_xi(psi):  # ξ-space derivative (no metric)
        g, _ = ccd.differentiate(psi, 0, apply_metric=False)
        return g

    def stage_diff_y_xi(psi):
        g, _ = ccd.differentiate(psi, 1, apply_metric=False)
        return g

    def stage_n_hat_x(psi):
        _, n_hat, _ = compute_gradient_normal(xp, psi, ccd)
        return n_hat[0]

    def stage_n_hat_y(psi):
        _, n_hat, _ = compute_gradient_normal(xp, psi, ccd)
        return n_hat[1]

    def stage_flux_x(psi):  # ψ(1-ψ) n_hat[x]
        _, n_hat, _ = compute_gradient_normal(xp, psi, ccd)
        return psi * (1.0 - psi) * n_hat[0]

    def stage_flux_y(psi):
        _, n_hat, _ = compute_gradient_normal(xp, psi, ccd)
        return psi * (1.0 - psi) * n_hat[1]

    def stage_div_from_ax0(psi):  # filtered_divergence of flux_x along x
        _, n_hat, _ = compute_gradient_normal(xp, psi, ccd)
        flux_x = psi * (1.0 - psi) * n_hat[0]
        return filtered_divergence(xp, flux_x, 0, eps_d_comp, ccd, grid, bc)

    def stage_div_from_ax1(psi):  # filtered_divergence of flux_y along y
        _, n_hat, _ = compute_gradient_normal(xp, psi, ccd)
        flux_y = psi * (1.0 - psi) * n_hat[1]
        return filtered_divergence(xp, flux_y, 1, eps_d_comp, ccd, grid, bc)

    # ── deep probe into filt_div(flux_y, axis=1) ──────────────────
    from twophase.core.boundary import pad_ghost_cells

    def stage_gxi_y(psi):  # ξ-space deriv of flux_y along y
        _, n_hat, _ = compute_gradient_normal(xp, psi, ccd)
        flux_y = psi * (1.0 - psi) * n_hat[1]
        g_xi, _ = ccd.differentiate(flux_y, 1, apply_metric=False)
        return g_xi

    def stage_gxi_y_pad(psi):  # padded g_xi (shape N_y+3 along y)
        _, n_hat, _ = compute_gradient_normal(xp, psi, ccd)
        flux_y = psi * (1.0 - psi) * n_hat[1]
        g_xi, _ = ccd.differentiate(flux_y, 1, apply_metric=False)
        return pad_ghost_cells(xp, g_xi, 1, 1, bc)

    def stage_F_xi_y(psi):  # dissipative filter on g_xi_pad (no J)
        _, n_hat, _ = compute_gradient_normal(xp, psi, ccd)
        flux_y = psi * (1.0 - psi) * n_hat[1]
        g_xi, _ = ccd.differentiate(flux_y, 1, apply_metric=False)
        g_xi_pad = pad_ghost_cells(xp, g_xi, 1, 1, bc)
        nd = g_xi_pad.ndim
        s_c = tuple([slice(None)] * 1 + [slice(1, -1)] + [slice(None)] * (nd - 2))
        s_p1 = tuple([slice(None)] * 1 + [slice(2, None)] + [slice(None)] * (nd - 2))
        s_m1 = tuple([slice(None)] * 1 + [slice(0, -2)] + [slice(None)] * (nd - 2))
        return g_xi_pad[s_c] + eps_d_comp * (g_xi_pad[s_p1] - 2.0 * g_xi_pad[s_c] + g_xi_pad[s_m1])

    def stage_A(psi):
        return dccd_compression_div(xp, psi, ccd, grid, bc, eps_d_comp)

    def _compute_grad_normal_smooth(psi, delta_sq: float = 1e-20):
        """Candidate fix: smooth |∇ψ| regularization."""
        ndim = psi.ndim
        dpsi = []
        for ax in range(ndim):
            g1, _ = ccd.differentiate(psi, ax)
            dpsi.append(g1)
        grad_sq = sum(g * g for g in dpsi)
        safe_grad = xp.sqrt(grad_sq + delta_sq)
        n_hat = [g / safe_grad for g in dpsi]
        return dpsi, n_hat, safe_grad

    def stage_A_fixed(psi):
        _, n_hat, _ = _compute_grad_normal_smooth(psi)
        psi_1mpsi = psi * (1.0 - psi)
        div_total = xp.zeros_like(psi)
        for ax in range(grid.ndim):
            flux_ax = psi_1mpsi * n_hat[ax]
            div_total = div_total + filtered_divergence(xp, flux_ax, ax, eps_d_comp, ccd, grid, bc)
        return div_total

    def stage_n_hat_y_fixed(psi):
        _, n_hat, _ = _compute_grad_normal_smooth(psi)
        return n_hat[1]

    def stage_A_gradflux(psi, delta_sq: float = 1e-20):
        """Option 2: flux = ψ(1-ψ)·∇ψ·|∇ψ|/(|∇ψ|² + δ²). Zero exact in bulk."""
        ndim = psi.ndim
        dpsi = []
        for ax in range(ndim):
            g1, _ = ccd.differentiate(psi, ax)
            dpsi.append(g1)
        grad_sq = sum(g * g for g in dpsi)
        grad_mag = xp.sqrt(grad_sq)
        psi_1mpsi = psi * (1.0 - psi)
        denom = grad_sq + delta_sq
        div_total = xp.zeros_like(psi)
        for ax in range(ndim):
            flux_ax = psi_1mpsi * dpsi[ax] * grad_mag / denom
            div_total = div_total + filtered_divergence(xp, flux_ax, ax, eps_d_comp, ccd, grid, bc)
        return div_total

    def stage_n_hat_y_gradflux(psi, delta_sq: float = 1e-20):
        dpsi = []
        for ax in range(2):
            g1, _ = ccd.differentiate(psi, ax)
            dpsi.append(g1)
        grad_sq = sum(g * g for g in dpsi)
        grad_mag = xp.sqrt(grad_sq)
        denom = grad_sq + delta_sq
        return dpsi[1] * grad_mag / denom  # ≡ n̂_y when |∇ψ| >> δ, → 0 in bulk

    def stage_A_raisefloor(psi, floor: float = 1e-6):
        """Option 3: raise safe_grad floor to 1e-6 (preserves interface bit-exactness)."""
        ndim = psi.ndim
        dpsi = []
        for ax in range(ndim):
            g1, _ = ccd.differentiate(psi, ax)
            dpsi.append(g1)
        grad_sq = sum(g * g for g in dpsi)
        safe_grad = xp.maximum(xp.sqrt(xp.maximum(grad_sq, floor * floor)), floor)
        n_hat = [g / safe_grad for g in dpsi]
        psi_1mpsi = psi * (1.0 - psi)
        div_total = xp.zeros_like(psi)
        for ax in range(ndim):
            flux_ax = psi_1mpsi * n_hat[ax]
            div_total = div_total + filtered_divergence(xp, flux_ax, ax, eps_d_comp, ccd, grid, bc)
        return div_total

    def stage_n_hat_y_raisefloor(psi, floor: float = 1e-6):
        dpsi = []
        for ax in range(2):
            g1, _ = ccd.differentiate(psi, ax)
            dpsi.append(g1)
        grad_sq = sum(g * g for g in dpsi)
        safe_grad = xp.maximum(xp.sqrt(xp.maximum(grad_sq, floor * floor)), floor)
        return dpsi[1] / safe_grad

    def stage_B(psi):
        div_comp = dccd_compression_div(xp, psi, ccd, grid, bc, eps_d_comp)
        return np.clip(psi - dtau * div_comp, 0.0, 1.0)

    def stage_C(psi):  # B + CN-x
        q_star = stage_B(psi)
        return cn_diffusion_axis(xp, q_star, 0, eps, dtau, h[0], cn_factors[0])

    def stage_D_xy(psi):  # B + CN-x + CN-y  (Yanenko x→y)
        q_star = stage_B(psi)
        q1 = cn_diffusion_axis(xp, q_star, 0, eps, dtau, h[0], cn_factors[0])
        q2 = cn_diffusion_axis(xp, q1, 1, eps, dtau, h[1], cn_factors[1])
        return np.clip(q2, 0.0, 1.0)

    def stage_D_yx(psi):  # B + CN-y + CN-x  (reverse Yanenko for C3 probe)
        q_star = stage_B(psi)
        q1 = cn_diffusion_axis(xp, q_star, 1, eps, dtau, h[1], cn_factors[1])
        q2 = cn_diffusion_axis(xp, q1, 0, eps, dtau, h[0], cn_factors[0])
        return np.clip(q2, 0.0, 1.0)

    def stage_CNx_only(psi):  # just CN-x on raw ψ (is CN equivariant alone?)
        return cn_diffusion_axis(xp, psi, 0, eps, dtau, h[0], cn_factors[0])

    def stage_CNy_only(psi):  # just CN-y on raw ψ
        return cn_diffusion_axis(xp, psi, 1, eps, dtau, h[1], cn_factors[1])

    def stage_E(psi):
        return reinit.reinitialize(psi)

    reinit_1 = SplitReinitializer(
        backend=reinit.backend if hasattr(reinit, 'backend') else reinit.xp.__class__,
        grid=grid, ccd=ccd, eps=eps, n_steps=1, bc="zero",
        eps_d_comp=0.05, mass_correction=False,
    ) if False else None  # placeholder; patched below via closure

    def stage_E_1iter_nomc(psi):
        # reinitialize with n_steps=1, no mass_correction
        q = psi.copy()
        dtau_1 = reinit.dtau
        div_comp = dccd_compression_div(xp, q, ccd, grid, bc, eps_d_comp)
        q_star = xp.clip(q - dtau_1 * div_comp, 0.0, 1.0)
        q_new = q_star
        for ax in range(grid.ndim):
            q_new = cn_diffusion_axis(xp, q_new, ax, eps, dtau_1, h[ax], cn_factors[ax])
        return xp.clip(q_new, 0.0, 1.0)

    def _n_iter_nomc(psi, n):
        q = psi.copy()
        for _ in range(n):
            div_comp = dccd_compression_div(xp, q, ccd, grid, bc, eps_d_comp)
            q_star = xp.clip(q - reinit.dtau * div_comp, 0.0, 1.0)
            q_new = q_star
            for ax in range(grid.ndim):
                q_new = cn_diffusion_axis(xp, q_new, ax, eps, reinit.dtau, h[ax], cn_factors[ax])
            q = xp.clip(q_new, 0.0, 1.0)
        return q

    def stage_E_nomc(psi):
        return _n_iter_nomc(psi, 4)

    def stage_E_2iter_nomc(psi):
        return _n_iter_nomc(psi, 2)

    def stage_E_3iter_nomc(psi):
        return _n_iter_nomc(psi, 3)

    # Gradflux variant of compression — no floor, exact zero in bulk.
    def _dccd_comp_gradflux(psi, delta_sq=1e-20):
        ndim = psi.ndim
        dpsi = []
        for ax in range(ndim):
            g1, _ = ccd.differentiate(psi, ax)
            dpsi.append(g1)
        grad_sq = sum(g * g for g in dpsi)
        grad_mag = xp.sqrt(grad_sq)
        psi_1mpsi = psi * (1.0 - psi)
        denom = grad_sq + delta_sq
        div_total = xp.zeros_like(psi)
        for ax in range(ndim):
            flux_ax = psi_1mpsi * dpsi[ax] * grad_mag / denom
            div_total = div_total + filtered_divergence(xp, flux_ax, ax, eps_d_comp, ccd, grid, bc)
        return div_total

    def stage_E_gradflux_nomc(psi):
        q = psi.copy()
        for _ in range(4):
            div_comp = _dccd_comp_gradflux(q)
            q_star = xp.clip(q - reinit.dtau * div_comp, 0.0, 1.0)
            q_new = q_star
            for ax in range(grid.ndim):
                q_new = cn_diffusion_axis(xp, q_new, ax, eps, reinit.dtau, h[ax], cn_factors[ax])
            q = xp.clip(q_new, 0.0, 1.0)
        return q

    return {
        "diff_x_xi : ccd.differentiate(ψ,0,no-metric)": stage_diff_x_xi,
        "diff_y_xi : ccd.differentiate(ψ,1,no-metric)": stage_diff_y_xi,
        "diff_x    : ccd.differentiate(ψ,0) [with J]": stage_diff_x,
        "diff_y    : ccd.differentiate(ψ,1) [with J]": stage_diff_y,
        "n_hat_x   : ψ(1-ψ) n̂[x] ∂norm":               stage_n_hat_x,
        "n_hat_y   : ψ(1-ψ) n̂[y] ∂norm":               stage_n_hat_y,
        "flux_x    : ψ(1-ψ)·n_hat[x]":                  stage_flux_x,
        "flux_y    : ψ(1-ψ)·n_hat[y]":                  stage_flux_y,
        "div0      : filt_div(flux_x, axis=0)":         stage_div_from_ax0,
        "div1      : filt_div(flux_y, axis=1)":         stage_div_from_ax1,
        "gxi_y     : ccd.diff(flux_y,1,no-metric)":     stage_gxi_y,
        "gxi_y_pad : pad_ghost(gxi_y,'zero')":          stage_gxi_y_pad,
        "Fxi_y     : filter(gxi_y_pad) no J":           stage_F_xi_y,
        "A   : dccd_compression_div(ψ)": stage_A,
        "A_fix     : dccd_compr w/ smooth safe_grad":   stage_A_fixed,
        "n_hat_y_fix : smooth safe_grad":                stage_n_hat_y_fixed,
        "A_gradflux: ψ(1-ψ)·∇ψ·|∇ψ|/(|∇ψ|²+δ²)":         stage_A_gradflux,
        "n_hat_y_gf: gradflux form":                     stage_n_hat_y_gradflux,
        "A_raisefloor: floor 1e-14 → 1e-6":              stage_A_raisefloor,
        "n_hat_y_rf: raised floor":                      stage_n_hat_y_raisefloor,
        "B   : ψ − dτ·divcomp  (clip)": stage_B,
        "C   : B + CN-x":                 stage_C,
        "Dxy : B + CN-x + CN-y":          stage_D_xy,
        "Dyx : B + CN-y + CN-x":          stage_D_yx,
        "CNx : cn_diff_axis(x) on ψ":     stage_CNx_only,
        "CNy : cn_diff_axis(y) on ψ":     stage_CNy_only,
        "E_1iter_nomc : 1 iter, no mass_corr":              stage_E_1iter_nomc,
        "E_2iter_nomc : 2 iters, no mass_corr":             stage_E_2iter_nomc,
        "E_3iter_nomc : 3 iters, no mass_corr":             stage_E_3iter_nomc,
        "E_nomc       : 4 iters, no mass_corr":             stage_E_nomc,
        "E_gf_nomc    : 4 iters, gradflux, no mass_corr":   stage_E_gradflux_nomc,
        "E   : SplitReinitializer.reinitialize (n_steps=4)": stage_E,
    }


# ── main ─────────────────────────────────────────────────────────────────


def run_probe(alpha_grid: float) -> None:
    print()
    print("=" * 76)
    print(f"CHK-168 probe — alpha_grid = {alpha_grid}")
    print("=" * 76)
    backend, grid, ccd, eps, psi0 = build_env(N=64, alpha_grid=alpha_grid)
    h_min = [float(grid.h[ax].min()) for ax in range(grid.ndim)]
    y_sym_input = _rel_err(psi0, _flip(psi0, axis=1))
    print(f"h[x]min={h_min[0]:.3e} h[y]min={h_min[1]:.3e} "
          f"eq={h_min[0]==h_min[1]} input_y_sym={y_sym_input:.3e}")
    reinit = SplitReinitializer(
        backend=backend, grid=grid, ccd=ccd, eps=eps,
        n_steps=4, bc="zero", eps_d_comp=0.05, mass_correction=True,
    )
    stages = make_stage_ops(reinit, ccd, grid, eps)
    # Print only key stages (iter growth + full reinit)
    keys = ["A   ", "E_1iter_nomc", "E_2iter_nomc", "E_3iter_nomc",
            "E_nomc      ", "E   "]
    for name, op in stages.items():
        if not any(name.startswith(k.strip()) for k in keys):
            continue
        y = _sym_err(op, psi0, axis=1, parity=+1)
        x = _sym_err(op, psi0, axis=0, parity=+1)
        print(f"  {name:<50s} y={y:.3e}  x={x:.3e}")


def main() -> int:
    # Quick comparison: uniform vs stretched grid.
    run_probe(alpha_grid=1.0)
    run_probe(alpha_grid=2.0)
    print()

    # Full diagnostic on the α=2 stretched grid (sym_B config).
    backend, grid, ccd, eps, psi0 = build_env(N=64, alpha_grid=2.0)

    # Baseline: the input itself must be y-flip-symmetric up to floating eps.
    y_sym_input = _rel_err(psi0, _flip(psi0, axis=1))
    x_sym_input = _rel_err(psi0, _flip(psi0, axis=0))
    h_min = [float(grid.h[ax].min()) for ax in range(grid.ndim)]
    h_max = [float(grid.h[ax].max()) for ax in range(grid.ndim)]

    print("=" * 76)
    print("CHK-168 Phase 1 — split-reinit operator-isolation probe")
    print("=" * 76)
    print(f"grid: N=(64,64) L=(1,1) α=2  h[x] min/max = "
          f"{h_min[0]:.3e}/{h_max[0]:.3e}  h[y] min/max = "
          f"{h_min[1]:.3e}/{h_max[1]:.3e}")
    print(f"eps = {eps:.6e}   (1.4 × 1.5 / N)")
    print(f"input |ψ − flip_y(ψ)|_∞/max|ψ| = {y_sym_input:.3e}  (baseline)")
    print(f"input |ψ − flip_x(ψ)|_∞/max|ψ| = {x_sym_input:.3e}")
    print(f"h[0].min() == h[1].min() → {h_min[0] == h_min[1]}")

    # ── palindromic symmetry of grid metrics ───────────────────────────
    for ax in range(grid.ndim):
        h_arr = np.asarray(grid.h[ax])
        J_arr = np.asarray(grid.J[ax])
        dJ_arr = np.asarray(grid.dJ_dxi[ax])
        h_pal = float(np.max(np.abs(h_arr - h_arr[::-1]))) / float(np.max(np.abs(h_arr)))
        J_pal = float(np.max(np.abs(J_arr - J_arr[::-1]))) / float(np.max(np.abs(J_arr)))
        dJ_pal = float(np.max(np.abs(dJ_arr + dJ_arr[::-1]))) / max(1.0, float(np.max(np.abs(dJ_arr))))
        tag = "x" if ax == 0 else "y"
        print(f"axis {tag}: h palindromic err = {h_pal:.3e}, J palindromic err = {J_pal:.3e}, dJ anti-palindromic err = {dJ_pal:.3e}")
    print()

    reinit = SplitReinitializer(
        backend=backend, grid=grid, ccd=ccd, eps=eps,
        n_steps=4, bc="zero", eps_d_comp=0.05, mass_correction=True,
    )
    stages = make_stage_ops(reinit, ccd, grid, eps)

    # parity table (expected parity under y-flip , x-flip) for each stage.
    # scalar ψ-like: (+, +); ∂/∂x output: (+, -); ∂/∂y output: (-, +);
    # flux_y component (vector y-comp scaled by scalar): (-, +); etc.
    parity_map = {
        "diff_x_xi": (+1, -1),
        "diff_y_xi": (-1, +1),
        "diff_x   ": (+1, -1),
        "diff_y   ": (-1, +1),
        "n_hat_x  ": (+1, -1),
        "n_hat_y  ": (-1, +1),
        "flux_x   ": (+1, -1),
        "flux_y   ": (-1, +1),
        "div0     ": (+1, +1),  # divergence contribution along ax=0 (y-EVEN, x-EVEN)
        "div1     ": (+1, +1),
        "gxi_y    ": (+1, +1),  # ∂(flux_y ODD)/∂ξ_y → EVEN under y-flip
        "gxi_y_pad": (+1, +1),
        "Fxi_y    ": (+1, +1),
        "n_hat_y_fix": (-1, +1),
        "n_hat_y_gf": (-1, +1),
        "n_hat_y_rf": (-1, +1),
    }
    print(f"{'stage':<50s} {'yflip_err':>12s} {'xflip_err':>12s}  note")
    print("-" * 76)
    parity_map = {k.strip(): v for k, v in parity_map.items()}
    for name, op in stages.items():
        key = name.split(":")[0].strip()
        py, px = parity_map.get(key, (+1, +1))
        y = _sym_err(op, psi0, axis=1, parity=py)
        x = _sym_err(op, psi0, axis=0, parity=px)
        mark = ""
        if y > 1e-10 and x < 1e-12:
            mark = "  ← ASYMMETRIC IN Y ONLY"
        elif y > 1e-10 and x > 1e-10:
            mark = "  ← ASYMMETRIC (both)"
        print(f"{name:<50s} {y:12.3e} {x:12.3e}{mark}")

    # ── location diagnostic for largest asymmetric stage ─────────────
    print()
    print("=== location of max y-flip error in n_hat_y (ODD parity) ===")
    op = stages["n_hat_y   : ψ(1-ψ) n̂[y] ∂norm"]
    forward = op(psi0)
    flipped = _flip(op(_flip(psi0, axis=1)), axis=1)
    diff = forward + flipped  # ODD parity: expect forward == -flipped
    ij = np.unravel_index(int(np.argmax(np.abs(diff))), diff.shape)
    print(f"max|diff| = {np.max(np.abs(diff)):.3e} at node (i,j) = {ij}")
    print(f"forward[{ij}]            = {forward[ij]:+.6e}")
    print(f"flipped[{ij}]            = {flipped[ij]:+.6e}")
    print(f"|ψ|[{ij}]                = {psi0[ij]:+.6e}  (interior=liquid, ψ=1)")
    _, n_hat, safe_g = compute_gradient_normal(np, psi0, ccd)
    dpsi_y = n_hat[1] * safe_g
    print(f"∂ψ/∂y[{ij}]             = {dpsi_y[ij]:+.6e}")
    print(f"|∇ψ|[{ij}] (safe_grad)  = {safe_g[ij]:+.6e}")
    print(f"dpsi_y at mirror {(ij[0], psi0.shape[1]-1-ij[1])}: "
          f"{dpsi_y[ij[0], psi0.shape[1]-1-ij[1]]:+.6e}")
    print(f"safe_grad at mirror: "
          f"{safe_g[ij[0], psi0.shape[1]-1-ij[1]]:+.6e}")

    # Also: how many cells hit the 1e-14 safe_grad floor?
    floor_mask = (safe_g == 1e-14)
    print(f"safe_grad hits 1e-14 floor at {int(floor_mask.sum())} / {safe_g.size} nodes")

    return 0


if __name__ == "__main__":
    sys.exit(main())
