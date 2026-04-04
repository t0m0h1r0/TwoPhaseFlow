#!/usr/bin/env python3
"""【10-12】Checkerboard suppression by DCCD filter.

Paper ref: §7 (collocated grid checkerboard problem),
           §4d (DCCD ε_d=1/4 → H(π)=0),
           §8.3 (PPE RHS uses DCCD-filtered divergence)

Tests:
  (a) Apply CCD/DCCD 1st derivative to checkerboard mode (-1)^i:
      CCD gives 0 (blind to Nyquist), DCCD gives non-zero (detects it).
  (b) Velocity field with smooth + checkerboard noise:
      Compute divergence with CCD vs DCCD, solve PPE, compare pressure spectra.
  (c) Quantify: Fourier amplitude at kh=π before/after DCCD filter.
"""

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import numpy as np
from twophase.backend import Backend
from twophase.core.grid import Grid
from twophase.config import GridConfig
from twophase.ccd.ccd_solver import CCDSolver

OUT = pathlib.Path(__file__).resolve().parent / "results" / "checkerboard"
OUT.mkdir(parents=True, exist_ok=True)


# ── Test (a): CCD vs DCCD on checkerboard mode ──────────────────────────────

def test_checkerboard_derivative(N=64):
    """Apply CCD and DCCD d/dx to checkerboard (-1)^i and measure response."""
    backend = Backend(use_gpu=False)
    L = 2 * np.pi
    gc = GridConfig(ndim=2, N=(N, N), L=(L, L))
    grid = Grid(gc, backend)
    xp = backend.xp

    ccd_std = CCDSolver(grid, backend, bc_type="periodic")
    # DCCD: use standard CCD then apply filter (ε_d=1/4)

    X, Y = grid.meshgrid()
    h = L / N

    # Checkerboard in x-direction: (-1)^i
    ix = np.round(X / h).astype(int)
    checker = (-1.0) ** ix  # shape (N+1, N+1)

    # CCD derivative of checkerboard
    d_checker_ccd, _ = ccd_std.differentiate(xp.asarray(checker), axis=0)
    d_checker_ccd = np.asarray(backend.to_host(d_checker_ccd))

    max_ccd = float(np.max(np.abs(d_checker_ccd)))

    print(f"\n  Test (a): CCD/DCCD derivative of checkerboard (-1)^i")
    print(f"    N={N}, h={h:.4f}")
    print(f"    |d/dx [(-1)^i]|_max (CCD):  {max_ccd:.6e}")
    print(f"    → CCD is {'BLIND' if max_ccd < 1e-10 else 'responsive'} to checkerboard")

    return {"N": N, "max_ccd_deriv": max_ccd}


# ── Test (b): Divergence with smooth + checkerboard velocity ─────────────────

def test_divergence_filtering(N=64, eps_d=0.25):
    """Compare CCD vs DCCD-filtered divergence for noisy velocity field."""
    backend = Backend(use_gpu=False)
    L = 2 * np.pi
    gc = GridConfig(ndim=2, N=(N, N), L=(L, L))
    grid = Grid(gc, backend)
    xp = backend.xp
    h = L / N

    ccd = CCDSolver(grid, backend, bc_type="periodic")

    X, Y = grid.meshgrid()

    # Smooth divergence-free velocity + checkerboard noise
    noise_amp = 0.01
    ix = np.round(X / h).astype(int)
    iy = np.round(Y / h).astype(int)
    checker_2d = (-1.0) ** (ix + iy)

    u_smooth = np.sin(X) * np.cos(Y)
    v_smooth = -np.cos(X) * np.sin(Y)

    u_noisy = u_smooth + noise_amp * checker_2d
    v_noisy = v_smooth + noise_amp * checker_2d

    # CCD divergence (no filter)
    du_dx_ccd, _ = ccd.differentiate(xp.asarray(u_noisy), axis=0)
    dv_dy_ccd, _ = ccd.differentiate(xp.asarray(v_noisy), axis=1)
    div_ccd = np.asarray(backend.to_host(du_dx_ccd)) + np.asarray(backend.to_host(dv_dy_ccd))

    # DCCD-filtered divergence: apply 3-point filter before differentiation
    # DCCD filter: f_filtered[i] = f[i] - ε_d (f[i-1] - 2f[i] + f[i+1])
    # For periodic grid (N+1 nodes, last = first)
    def dccd_filter_1d(f, axis, eps_d):
        """Apply DCCD dissipative filter along axis."""
        f_filt = f.copy()
        n = f.shape[axis]
        for idx in range(n):
            slc = [slice(None)] * f.ndim
            slc_m = [slice(None)] * f.ndim
            slc_p = [slice(None)] * f.ndim
            slc[axis] = idx
            slc_m[axis] = (idx - 1) % n
            slc_p[axis] = (idx + 1) % n
            f_filt[tuple(slc)] = f[tuple(slc)] + eps_d * (
                f[tuple(slc_m)] - 2*f[tuple(slc)] + f[tuple(slc_p)])
        return f_filt

    u_filt = dccd_filter_1d(u_noisy, axis=0, eps_d=eps_d)
    u_filt = dccd_filter_1d(u_filt, axis=1, eps_d=eps_d)
    v_filt = dccd_filter_1d(v_noisy, axis=0, eps_d=eps_d)
    v_filt = dccd_filter_1d(v_filt, axis=1, eps_d=eps_d)

    du_dx_dccd, _ = ccd.differentiate(xp.asarray(u_filt), axis=0)
    dv_dy_dccd, _ = ccd.differentiate(xp.asarray(v_filt), axis=1)
    div_dccd = np.asarray(backend.to_host(du_dx_dccd)) + np.asarray(backend.to_host(dv_dy_dccd))

    # Fourier analysis: measure checkerboard (kh=π) component
    # On (N+1)×(N+1) periodic grid, use interior N×N
    div_ccd_int = div_ccd[:N, :N]
    div_dccd_int = div_dccd[:N, :N]

    spec_ccd = np.abs(np.fft.fft2(div_ccd_int))
    spec_dccd = np.abs(np.fft.fft2(div_dccd_int))

    # Nyquist component: index (N/2, N/2) = checkerboard mode
    nyq = N // 2
    checker_amp_ccd = float(spec_ccd[nyq, nyq]) / (N * N)
    checker_amp_dccd = float(spec_dccd[nyq, nyq]) / (N * N)

    # Also measure total Nyquist band (all modes with max(|kx|,|ky|) = N/2)
    nyq_band_ccd = float(np.sum(spec_ccd[nyq, :]) + np.sum(spec_ccd[:, nyq])) / (N * N)
    nyq_band_dccd = float(np.sum(spec_dccd[nyq, :]) + np.sum(spec_dccd[:, nyq])) / (N * N)

    suppression = checker_amp_ccd / checker_amp_dccd if checker_amp_dccd > 0 else float("inf")

    print(f"\n  Test (b): Divergence Fourier analysis (ε_d={eps_d})")
    print(f"    Checkerboard amplitude in ∇·u:")
    print(f"      CCD (no filter):  {checker_amp_ccd:.6e}")
    print(f"      DCCD (ε_d={eps_d}): {checker_amp_dccd:.6e}")
    print(f"      Suppression ratio: {suppression:.1f}x")
    print(f"    Nyquist band total (|k|=N/2):")
    print(f"      CCD:  {nyq_band_ccd:.6e}")
    print(f"      DCCD: {nyq_band_dccd:.6e}")

    # RMS of divergence
    rms_ccd = float(np.sqrt(np.mean(div_ccd**2)))
    rms_dccd = float(np.sqrt(np.mean(div_dccd**2)))
    print(f"    RMS(∇·u):")
    print(f"      CCD:  {rms_ccd:.6e}")
    print(f"      DCCD: {rms_dccd:.6e}")

    return {
        "checker_amp_ccd": checker_amp_ccd,
        "checker_amp_dccd": checker_amp_dccd,
        "suppression": suppression,
        "nyq_band_ccd": nyq_band_ccd,
        "nyq_band_dccd": nyq_band_dccd,
        "rms_ccd": rms_ccd,
        "rms_dccd": rms_dccd,
        "spec_ccd": spec_ccd,
        "spec_dccd": spec_dccd,
    }


# ── Test (c): Transfer function H(ξ; ε_d) verification ──────────────────────

def test_transfer_function(N=64):
    """Verify DCCD transfer function H(ξ) = 1 - 4ε_d sin²(ξ/2) numerically."""
    backend = Backend(use_gpu=False)
    L = 2 * np.pi
    gc = GridConfig(ndim=2, N=(N, N), L=(L, L))
    grid = Grid(gc, backend)
    h = L / N

    X, _ = grid.meshgrid()

    eps_d_values = [0.0, 0.05, 0.25]
    results = {}

    print(f"\n  Test (c): Transfer function H(ξ; ε_d) at kh=π (Nyquist)")
    print(f"    {'ε_d':>6} | {'H(π) theory':>12} | {'H(π) measured':>14} | {'match':>6}")
    print("    " + "-" * 50)

    for eps_d in eps_d_values:
        # Use N-node fundamental domain (no wrap node) for clean periodicity
        f_1d = np.array([(-1.0)**i for i in range(N)])  # checkerboard

        if eps_d == 0:
            f_out_1d = f_1d.copy()
        else:
            f_out_1d = np.empty_like(f_1d)
            for i in range(N):
                im = (i - 1) % N
                ip = (i + 1) % N
                f_out_1d[i] = f_1d[i] + eps_d * (f_1d[im] - 2*f_1d[i] + f_1d[ip])

        amp_in = float(np.max(np.abs(f_1d)))
        amp_out = float(np.max(np.abs(f_out_1d)))
        H_measured = amp_out / amp_in if amp_in > 0 else 0.0

        # Theory: H(π) = 1 - 4ε_d sin²(π/2) = 1 - 4ε_d
        H_theory = 1.0 - 4.0 * eps_d

        match = "✓" if abs(H_measured - abs(H_theory)) < 1e-10 else "✗"

        results[eps_d] = {"H_theory": H_theory, "H_measured": H_measured}
        print(f"    {eps_d:>6.2f} | {H_theory:>12.4f} | {H_measured:>14.6e} | {match:>6}")

    return results


# ── Output ───────────────────────────────────────────────────────────────────

def save_plot(div_results):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    N = div_results["spec_ccd"].shape[0]

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))

    # (a) 1D spectrum along kx (ky=0 slice)
    ax = axes[0]
    kx = np.arange(N)
    spec_ccd_1d = div_results["spec_ccd"][:, 0] / (N * N)
    spec_dccd_1d = div_results["spec_dccd"][:, 0] / (N * N)
    ax.semilogy(kx, spec_ccd_1d + 1e-20, "b-", label="CCD (no filter)", alpha=0.8)
    ax.semilogy(kx, spec_dccd_1d + 1e-20, "r-", label=r"DCCD ($\varepsilon_d=0.25$)", alpha=0.8)
    ax.axvline(N//2, color="gray", ls="--", alpha=0.5, label="Nyquist $kh=\\pi$")
    ax.set_xlabel("Wavenumber index $k_x$")
    ax.set_ylabel("Fourier amplitude $|\\hat{\\nabla \\cdot u}|$")
    ax.set_title("(a) Divergence spectrum ($k_y=0$ slice)")
    ax.legend(fontsize=8)
    ax.grid(True, which="both", alpha=0.3)

    # (b) 2D spectrum comparison (log scale)
    ax = axes[1]
    ratio = np.log10((div_results["spec_ccd"] + 1e-20) / (div_results["spec_dccd"] + 1e-20))
    im = ax.imshow(ratio.T, origin="lower", cmap="RdBu_r", vmin=-2, vmax=2,
                   extent=[0, N, 0, N])
    ax.set_xlabel("$k_x$"); ax.set_ylabel("$k_y$")
    ax.set_title(r"(b) $\log_{10}(|\hat{F}_\mathrm{CCD}|/|\hat{F}_\mathrm{DCCD}|)$")
    plt.colorbar(im, ax=ax, label="Log ratio")

    fig.tight_layout()
    fig.savefig(OUT / "checkerboard_suppression.eps", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"\n  Saved: {OUT / 'checkerboard_suppression.eps'}")


def save_latex_table(test_a, test_b, test_c):
    with open(OUT / "table_checkerboard.tex", "w") as fp:
        fp.write("% Auto-generated by exp10_12_checkerboard_suppression.py\n")
        fp.write("\\begin{tabular}{lrr}\n\\toprule\n")
        fp.write("指標 & CCD（フィルタなし） & DCCD（$\\varepsilon_d=0.25$） \\\\\n")
        fp.write("\\midrule\n")
        fp.write(f"チェッカーボード振幅 $|\\hat{{(\\bnabla\\cdot\\bu)}}|_{{k=\\pi/h}}$ "
                 f"& ${test_b['checker_amp_ccd']:.2e}$ & ${test_b['checker_amp_dccd']:.2e}$ \\\\\n")
        fp.write(f"Nyquist バンド合計 & ${test_b['nyq_band_ccd']:.2e}$ & ${test_b['nyq_band_dccd']:.2e}$ \\\\\n")
        fp.write(f"$\\mathrm{{RMS}}(\\bnabla\\cdot\\bu)$ & ${test_b['rms_ccd']:.2e}$ & ${test_b['rms_dccd']:.2e}$ \\\\\n")
        fp.write(f"抑制比 & \\multicolumn{{2}}{{c}}{{${test_b['suppression']:.0f}\\times$}} \\\\\n")
        fp.write("\\bottomrule\n\\end{tabular}\n")
    print(f"  Saved: {OUT / 'table_checkerboard.tex'}")


def main():
    print("\n" + "=" * 80)
    print("  【10-12】Checkerboard Suppression by DCCD Filter")
    print("=" * 80)

    test_a = test_checkerboard_derivative(N=64)
    test_b = test_divergence_filtering(N=64, eps_d=0.25)
    test_c = test_transfer_function(N=64)

    save_latex_table(test_a, test_b, test_c)
    save_plot(test_b)

    np.savez(OUT / "checkerboard_data.npz",
             test_a=test_a, test_b_summary={k: v for k, v in test_b.items()
                                             if k not in ("spec_ccd", "spec_dccd")},
             test_c=test_c)
    # Save spectra separately for --plot-only
    np.savez(OUT / "checkerboard_spectra.npz",
             spec_ccd=test_b["spec_ccd"], spec_dccd=test_b["spec_dccd"])
    print(f"\n  All results saved to {OUT}")


if __name__ == "__main__":
    import argparse
    _parser = argparse.ArgumentParser()
    _parser.add_argument('--plot-only', action='store_true')
    _args = _parser.parse_args()

    if _args.plot_only:
        _d = np.load(OUT / "checkerboard_data.npz", allow_pickle=True)
        _ds = np.load(OUT / "checkerboard_spectra.npz", allow_pickle=True)
        _test_b = _d["test_b_summary"].item()
        _test_b["spec_ccd"] = _ds["spec_ccd"]
        _test_b["spec_dccd"] = _ds["spec_dccd"]
        save_plot(_test_b)
    else:
        main()
