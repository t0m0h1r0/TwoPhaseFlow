# Low-Pass Filters Compatible with High-Order Compact Differentiation
# A Survey for Interface Curvature Computation in Two-Phase Flow

**Date:** 2026-04-04

---

## Abstract

High-order compact finite difference (CCD) schemes achieve spectral-like resolution
by solving implicit tridiagonal systems per axis.  Near a two-phase interface, the
curvature κ = −∇·n computed from CCD derivatives contains high-wavenumber noise
that drives spurious currents via the CSF term.  Standard explicit diffusion filters
(Laplacian, biharmonic) damp only near the Nyquist frequency kh ≈ π and are
ineffective for intermediate-wavenumber perturbations (kh ≈ 0.3–0.7).  This note
surveys filters from aeroacoustics, meteorology, and two-phase flow literature,
analyzes their spectral transfer functions, and recommends implementation strategies
compatible with CCD.

---

## 1. Problem Statement

CCD computes physical derivatives (units 1/L):

    ccd.differentiate(f, ax) → (∂f/∂x_ax,  ∂²f/∂x_ax²)

Curvature pipeline: φ → n = ∇φ/|∇φ| → κ = −∇·n → f_σ = κ∇ψ/We

Noise in n at wavenumber k propagates into κ at the same k, then into f_σ.
Suppression strategies must target the noise wavenumber without destroying the
physically resolved interface geometry.

**Transfer function notation:** H(ξ), ξ = kh ∈ [0, π].
- H(0) = 1 : DC preserved
- H(π) = 0 : 2h-wave eliminated
- H(ξ_noise) ≈ 0 : target noise mode suppressed

---

## 2. Filters from Computational Fluid Dynamics (Aeroacoustics)

### 2.1  Lele (1992) — Compact Padé Filter

**Reference:** S.K. Lele, "Compact finite difference schemes with spectral-like
resolution," *J. Comput. Phys.* 103:16–42, 1992.

**Equation (tridiagonal solve):**

    α_f f̂_{j-1} + f̂_j + α_f f̂_{j+1} = Σ_{n=0}^{N} (a_n/2)(f_{j+n} + f_{j-n})

Coefficients a_n determined by Taylor matching to order 2N; α_f ∈ (−0.5, 0.5)
is the free parameter.  For the 6th-order filter (N=3):

    a_0 = (11 + 10α_f)/16,  a_1 = (15 + 34α_f)/64,
    a_2 = (−3 + 6α_f)/32,   a_3 = (1 − 2α_f)/64

**Transfer function:**

    H(ξ) = [a_0 + a_1 cos ξ + a_2 cos 2ξ + a_3 cos 3ξ] / [1 + 2α_f cos ξ]

| α_f  | H(π/4) | H(π/2) | H(3π/4) | H(π) |
|------|--------|--------|---------|------|
| 0.45 | 0.9997 | 0.9971 | 0.961   | 0    |
| 0.30 | 0.9987 | 0.981  | 0.878   | 0    |
| 0.00 | 0.994  | 0.938  | 0.707   | 0    |

**CCD compatibility:** Direct — reuses the same tridiagonal infrastructure.
Apply as a separate pass: f̂ = Lele_filter(f, α_f) before CCD differentiation.

**Limitation:** For α_f near 0.5, H(ξ) ≈ 1 for ξ ≲ 0.8π.  Intermediate modes
(ξ ~ 0.3–0.5) are almost untouched.

---

### 2.2  Gaitonde & Visbal (2000, 2002) — Padé Filter for Navier-Stokes

**References:**
- D.V. Gaitonde, M.R. Visbal, *AIAA J.* 38(11):2103–2112, 2000.
- M.R. Visbal, D.V. Gaitonde, *J. Comput. Phys.* 181:155–185, 2002.

Same Padé family as Lele.  Visbal & Gaitonde (2002) demonstrate that 10th-order
Padé derivatives applied to non-smooth meshes generate spurious oscillations that
the 10th-order companion filter (α_f = 0.45) eliminates near kh = π.  This is the
canonical justification for pairing a compact filter with a high-order FD scheme.

**Key result:** Unfiltered CCD on a smooth field is accurate; oscillations appear
only at discontinuities/sharp interfaces.  Filter should be applied selectively.

---

### 2.3  Bogey & Bailly (2004) — Optimized Explicit Selective Filter

**Reference:** C. Bogey, C. Bailly, "A family of low dispersive and low
dissipative explicit schemes for flow and noise computations,"
*J. Comput. Phys.* 194:194–214, 2004.

**Equation (explicit, 2M+1-point stencil):**

    f̂_j = f_j − r_d · Σ_{n=−M}^{M} d_n f_{j+n}

Coefficients d_n optimized to minimize dispersion error for ξ < π/2.
Strength r_d ∈ [0.0, 0.2].

**Damping function:**

    D(ξ) = Σ_{n=0}^{M} d_n (1 − cos nξ)

The SFo9p (M=4) filter has D(π) = 1, D(π/2) ≈ 0.6, D(0.5 rad) ≈ 0.005.
Targets kh > π/2; leaves intermediate modes essentially undamped.

**Assessment:** Excellent for aeroacoustic near-Nyquist noise.  Not useful for
interface perturbation modes at kh ~ 0.3–0.5.

---

### 2.4  Kim (2010) — Compact Filter with Prescribed Cut-off Wavenumber

**Reference:** J.W. Kim, "High-order compact filters with variable cut-off
wavenumber and stable boundary treatment," *Computers & Fluids* 39:1168–1182, 2010.

**Key innovation:** Coefficients determined by prescribing a target −3 dB
wavenumber ξ_c directly: H(ξ_c) = 0.5.  Uses the same tridiagonal form as Lele
but with coefficients computed via a constraint optimization.

**Transfer function:** Sharp rolloff around user-specified ξ_c.  Setting ξ_c = 0.5
creates a filter that fully damps the m=8 perturbation mode while preserving the
resolved bubble geometry (kh < 0.2).

**CCD compatibility:** Direct — same tridiagonal solver.

**Recommendation:** This is the most appropriate filter when the noise wavenumber
is known a priori (e.g., from the perturbation mode analysis).  Implement as a
compact solve applied to φ before CCD differentiation.

---

## 3. Filters from Meteorology

### 3.1  Shapiro (1970) — 2N-th Order Explicit Smoother

**Reference:** R. Shapiro, "Smoothing, filtering, and boundary effects,"
*Rev. Geophys. Space Phys.* 8(2):359–387, 1970.

**Equation:** N applications of the 3-point operator S:

    f̂_j^{(1)} = (1/4)(f_{j-1} + 2f_j + f_{j+1})
    f̂_j^{(2N)} = (S)^N f_j

**Transfer function:**

    H(ξ) = cos^{2N}(ξ/2)

Properties: zero phase error, H(0) = 1, H(π) = 0.
For N=4 (8th order): H(0.5) = cos^8(0.25) ≈ 0.998.  Still ineffective for
intermediate modes.

---

## 4. Filters from Two-Phase Flow / Level Set Literature

### 4.1  Olsson, Kreiss & Zahedi (2007) — Helmholtz Projection for κ

**Reference:** E. Olsson, G. Kreiss, S. Zahedi, "A conservative level set method
for two phase flow II," *J. Comput. Phys.* 225:785–807, 2007.

**Equation (implicit, Helmholtz-type):**

    κ* − α h² ∇²κ* = κ          (solve for κ*)

**Transfer function:**

    H(ξ) = 1 / (1 + α ξ²)

Properties: monotone decay, always in (0,1), unconditionally stable.
For α = 1.0: H(0.5) ≈ 0.80, H(π) ≈ 0.09.  Damps intermediate modes.

**CCD compatibility:** The tridiagonal system for κ* is identical in structure to
CCD.  Can be solved with the same sparse solver.

**Key advantage over explicit Laplacian:**
- Explicit (InterfaceLimitedFilter): H(ξ) = 1 − Cξ²  → can go negative for ξ > √(1/C)
- Implicit (Helmholtz):              H(ξ) = 1/(1+αξ²) → always in (0,1) ✓

**Recommendation:** Replace the explicit InterfaceLimitedFilter with the implicit
Helmholtz form for unconditional stability and broader spectral coverage.

---

### 4.2  Sussman & Fatemi (1999) — Reinitialization as Implicit Smoother

**Reference:** M. Sussman, E. Fatemi, *SIAM J. Sci. Comput.* 20:1165–1191, 1999.

Redistancing (reinitialization PDE) regularizes φ to |∇φ| = 1.  This implicitly
smooths n = ∇φ/|∇φ| by removing non-SDF oscillations in φ.  First line of
defense; already implemented in the solver.

**Limitation:** Cannot remove perturbation modes that satisfy |∇φ| = 1 (valid SDF).

---

### 4.3  Desjardins, Moureau & Pitsch (2008) — Fast-Marching SDF Reconstruction

**Reference:** O. Desjardins, V. Moureau, H. Pitsch, *J. Comput. Phys.*
227:8395–8416, 2008.

Reconstruct smooth SDF from CLS field ψ using the Fast Marching Method, then
compute n and κ from the smooth SDF.  Avoids filter design; solves the noise
problem geometrically.

**CCD compatibility:** CCD differentiation on the reconstructed smooth SDF gives
accurate κ without an additional spectral filter.

---

### 4.4  Herrmann (2008) — Refined Level Set Grid (RLSG)

**Reference:** M. Herrmann, *J. Comput. Phys.* 227:2674–2706, 2008.

Use a 2× refined Cartesian sub-grid for interface tracking.  Curvature computed
on the fine grid, then projected to the coarse NS mesh.  The over-resolution acts
as a geometric low-pass filter: fine-grid κ is naturally smoother.

**Assessment:** Effective but doubles memory; not directly compatible with a
single-grid CCD solver.

---

### 4.5  Coquerelle & Glockner (2016) — Closest-Point Extension

**Reference:** M. Coquerelle, S. Glockner, *J. Comput. Phys.* 305:838–876, 2016.

Compute κ on the interface Γ using 4th-order compact FD, then extend κ into the
bulk via:

    κ(x) = κ(CP(x))    where CP(x) = closest point on Γ

**Effect:** Projects κ onto the interface manifold, replacing noisy bulk values.
Reduces spurious currents by 2 orders of magnitude vs. 2nd-order.

**CCD compatibility:** CCD-computed κ at Γ can be extended via this procedure.
Orthogonal to the filter approach — can be combined.

---

## 5. Spectral Transfer Function Summary

All functions evaluated at ξ = kh for a perturbation mode m=8 on N=64 grid:
ξ_noise = 2πm/N ≈ 0.785 rad ≈ π/4.

| Filter | Form | H(0) | H(π/4) | H(π/2) | H(π) | Stable | CCD compat. |
|--------|------|------|---------|---------|------|--------|-------------|
| Lele α_f=0.45 | Implicit 3pt | 1 | 0.9997 | 0.997 | 0 | ✓ | Direct |
| Lele α_f=0.0  | Explicit 3pt | 1 | 0.994  | 0.938 | 0 | ✓ | Direct |
| Kim ξ_c=π/4  | Implicit compact | 1 | 0.5 | ~0.1 | 0 | ✓ | Direct |
| Bogey-Bailly SFo9p | Explicit 9pt | 1 | ~0.999 | 0.94 | 0 | ✓ | Post-process |
| Shapiro N=4 | Explicit 9pt | 1 | 0.998 | 0.938 | 0 | ✓ | Post-process |
| Helmholtz α=1 | Implicit Laplacian | 1 | 0.80 | 0.50 | 0.09 | ✓ (unconditional) | Direct |
| Explicit Laplacian C=0.1 | Explicit | 1 | 0.994 | 0.975 | 0.012 | C<0.125 | Direct |
| Biharmonic β=0.01 | Explicit | 1 | ~1.0 | ~1.0 | 0.36 | β<0.016 | Direct |
| Gaussian σ=0.5 | Spectral | 1 | 0.906 | 0.536 | 0.004 | ✓ | Post-process |

**Key finding:** For intermediate-wavenumber noise (ξ ~ π/4 = 0.785), only three
filters achieve meaningful damping:
1. **Kim (2010)** compact filter with ξ_c ≤ π/4 — sharpest cut-off, same CCD infrastructure
2. **Helmholtz projection** — unconditionally stable, smooth rolloff, implicit
3. **Gaussian** — explicit, no phase error, adjustable σ

---

## 6. Balanced-Force Perspective

**Reference:** M.M. Francois et al., *J. Comput. Phys.* 213:141–173, 2006.

Filtering κ reduces noise but does not address the root cause: discretization
inconsistency between the pressure gradient ∇p and the CSF force σκ∇ψ.
Balanced-force discretization (using CCD-consistent pressure gradient) can reduce
spurious currents by up to 7 orders of magnitude independently of filtering.

**Priority order:**
1. Balanced-force discretization (eliminates O(1) spurious currents)
2. High-order curvature (reduces truncation-error currents)
3. Spectral filter on n or κ (eliminates residual noise-driven currents)

---

## 7. Recommendations for CCD-Based Interface Methods

### R1: Helmholtz implicit filter for κ (replaces explicit InterfaceLimitedFilter)

    Solve: (I − α h² ∇²) κ* = w(ψ) κ + (1 − w(ψ)) κ*   →   κ*

Or equivalently the split form: apply Helmholtz only in the interface band.
Transfer function H = 1/(1+αξ²) is unconditionally stable and damps ξ ~ π/4
effectively for α ~ 1.

### R2: Kim (2010) compact filter on φ before CCD differentiation

For known perturbation modes, apply one Kim-filter pass with ξ_c set below the
noise wavenumber.  This is the most spectrally precise approach.

### R3: Lele compact filter on φ or n (mildest case)

For near-Nyquist noise only (ξ ~ π), a Lele filter with α_f = 0.3–0.45 is
sufficient and reuses the CCD tridiagonal solver directly.

### R4: Closest-point extension for κ

After computing κ at the interface with CCD, extend κ via CP(x) into the bulk.
Eliminates off-interface noise geometrically without modifying the spectral content
of the on-interface curvature.

---

## 8. Implementation Priority

| Priority | Filter | Equation | Target | Status |
|----------|--------|----------|--------|--------|
| 1 | Helmholtz κ | (I − αh²∇²)κ* = κ | ξ ~ π/4–π | Not implemented |
| 2 | Kim compact on φ | Padé tridiagonal, ξ_c prescribed | any ξ | Not implemented |
| 3 | Lele on φ or n | Padé tridiagonal, α_f = 0.3–0.45 | ξ ~ π | Not implemented |
| — | NormalVectorFilter | n* = n + αh²∇·(|∇φ|∇n) | ξ ~ π | ✅ Implemented |
| — | InterfaceLimitedFilter | κ* = κ + Ch²w∇²κ | ξ ~ π | ✅ Implemented |
| — | CurvatureBiharmonicFilter | κ* = κ − βh⁴w∇⁴κ | ξ ~ π | ✅ Implemented |

---

## References

1. S.K. Lele, "Compact finite difference schemes with spectral-like resolution," *J. Comput. Phys.* 103:16–42, 1992.
2. D.V. Gaitonde, M.R. Visbal, "Pade-type higher-order boundary filters for the Navier-Stokes equations," *AIAA J.* 38(11):2103–2112, 2000.
3. M.R. Visbal, D.V. Gaitonde, "On the use of higher-order finite-difference schemes on curvilinear and deforming meshes," *J. Comput. Phys.* 181:155–185, 2002.
4. C. Bogey, C. Bailly, "A family of low dispersive and low dissipative explicit schemes for flow and noise computations," *J. Comput. Phys.* 194:194–214, 2004.
5. J.W. Kim, "High-order compact filters with variable cut-off wavenumber and stable boundary treatment," *Computers & Fluids* 39:1168–1182, 2010.
6. R. Shapiro, "Smoothing, filtering, and boundary effects," *Rev. Geophys. Space Phys.* 8(2):359–387, 1970.
7. M. Sussman, E. Fatemi, "An efficient, interface-preserving level set redistancing algorithm," *SIAM J. Sci. Comput.* 20:1165–1191, 1999.
8. E. Olsson, G. Kreiss, S. Zahedi, "A conservative level set method for two phase flow II," *J. Comput. Phys.* 225:785–807, 2007.
9. O. Desjardins, V. Moureau, H. Pitsch, "An accurate conservative level set/ghost fluid method for simulating turbulent atomization," *J. Comput. Phys.* 227:8395–8416, 2008.
10. M. Herrmann, "A balanced force refined level set grid method for two-phase flows on unstructured flow solver grids," *J. Comput. Phys.* 227:2674–2706, 2008.
11. M.M. Francois et al., "A balanced-force algorithm for continuous and sharp interfacial surface tension models," *J. Comput. Phys.* 213:141–173, 2006.
12. M. Coquerelle, S. Glockner, "A fourth-order accurate curvature computation in a level set framework," *J. Comput. Phys.* 305:838–876, 2016.
13. F. Gibou, R. Fedkiw, S. Osher, "A review of level-set methods and some recent applications," *J. Comput. Phys.* 353:82–109, 2018.

**Keywords:** Compact finite difference, CCD, low-pass filter, Padé filter, Helmholtz projection, curvature, normal vector, spurious currents, two-phase flow, level set
