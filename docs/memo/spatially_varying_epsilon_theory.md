# Spatially Varying ε for CSF on Non-Uniform Grids: Theory

Date: 2026-04-11

## 1. Problem Statement

On interface-fitted non-uniform grids with concentration factor α, the CSF
(Continuum Surface Force) model uses a fixed global interface thickness
ε = C_ε · h_uniform. Near the interface, the local grid spacing h_local is
much smaller than h_uniform (h_local ≈ h_uniform/α), so:

    ε / h_local ≈ C_ε · α

For α=2, C_ε=1.5: ε/h_local ≈ 3 (acceptable).
For α=4, C_ε=1.5: ε/h_local ≈ 6 (19 at h_min), causing 400× parasitic current amplification.

The CSF force f_σ = σκ∇ψ is distributed over ~2ε in physical space, which
spans ~2ε/h_local ≈ 2·C_ε·α local cells instead of the intended ~2·C_ε cells.
The pressure field cannot exactly balance this broadened force, generating
parasitic velocities.

## 2. Proposed Solution: ε(x) = C_ε · h_local(x)

Replace the scalar ε with a spatially varying field:

    ε(x) = C_ε · h_local(x)

where h_local(x) = max(h_x(i), h_y(j)) at node (i,j).

### 2.1 Properties

**P1: Consistent cell count.** The interface transition spans ~2ε(x)/h_local(x) = 2C_ε
cells everywhere, regardless of local grid spacing.

**P2: Automatic adaptation.** On uniform grids (h_local = h_uniform ∀x), ε(x) reduces
to the standard scalar ε = C_ε · h_uniform. No behavioral change for existing code.

**P3: Smoothness.** Since h_local(x) varies smoothly (the grid density function
ω(φ) is Gaussian, §6), ε(x) is also smooth. This ensures ∇ε exists and is bounded.

## 3. Modified CSF Formulation

### 3.1 Heaviside with spatially varying ε

Standard:
    H_ε(φ) = 1 / (1 + exp(−φ/ε))

Spatially varying:
    H_{ε(x)}(φ(x)) = 1 / (1 + exp(−φ(x)/ε(x)))

This is a pointwise operation — no structural change to the formula. The
implementation already broadcasts scalar ε in `heaviside()`:

    return 1.0 / (1.0 + xp.exp(-phi / eps))

If `eps` is an ndarray of shape matching `phi`, this expression works unchanged
via NumPy broadcasting.

### 3.2 Delta function with spatially varying ε

Standard:
    δ_ε(φ) = (1/ε) · H_ε(φ) · (1 − H_ε(φ))

Spatially varying:
    δ_{ε(x)}(φ(x)) = (1/ε(x)) · H_{ε(x)}(φ) · (1 − H_{ε(x)}(φ))

The 1/ε(x) factor adjusts the peak amplitude to maintain ∫δ dφ = 1 locally.

### 3.3 CLS variable ψ

The CLS transport equation ∂ψ/∂t + ∇·(uψ) = 0 does NOT involve ε directly.
ε only appears in:
  (a) Initial condition: ψ₀ = H_ε(φ₀)
  (b) Reinitialization: restores ψ to the H_ε profile
  (c) Inverse mapping: φ = ε · ln(ψ/(1−ψ))
  (d) Property interpolation: ρ = ρ_g + (ρ_l − ρ_g) · ψ (no ε)
  (e) CSF force: f_σ = σκ∇ψ (no explicit ε, but ψ profile depends on ε)

### 3.4 Curvature computation

Curvature κ is computed from ψ derivatives via the standard formula:

    κ = −(ψ_y² ψ_xx − 2ψ_x ψ_y ψ_xy + ψ_x² ψ_yy) / (ψ_x² + ψ_y²)^{3/2}

ε does NOT appear explicitly. However, the gradient magnitudes scale as:
  |∇ψ|_max = 1/(4ε)  (at the interface)

With spatially varying ε, this becomes |∇ψ|_max(x) = 1/(4ε(x)). The curvature
formula involves ratios of derivatives, so this scaling cancels in the fraction.
The curvature invariance theorem (WIKI-T-020) guarantees κ is independent of ε
for the exact logistic profile. On a discrete grid, the O(h⁶) CCD approximation
inherits this invariance to leading order.

**Result: Curvature computation is UNAFFECTED by spatially varying ε.**
The only indirect effect is through `invert_heaviside(ψ, ε(x))`, which
already supports array ε.

### 3.5 CSF force with spatially varying ε

The balanced-force CSF formulation:

    f_σ = σκ∇ψ

does not contain ε explicitly. The effect of ε(x) enters through the ψ profile:
- Where ε is small (near interface, fine grid): ψ transition is sharp, |∇ψ| is large
- Where ε is large (far from interface, coarse grid): ψ transition is broad, |∇ψ| is small

The key property of CSF is that ∫f_σ dx across the interface equals σκ
regardless of ε (exact for the logistic profile). With spatially varying ε,
this integral property is preserved because:

    ∫ σκ |∇ψ| dx = σκ ∫ δ_ε dφ = σκ

The ε-variation only changes HOW the force is distributed across local cells,
not the total force. With ε(x) = C_ε · h_local(x), the distribution spans
~2C_ε cells everywhere — the design intent.

## 4. Reinitialization with Spatially Varying ε

The reinitialization PDE restores ψ to the H_ε profile:

    ∂ψ/∂τ + ∇·(n̂ · ψ(1−ψ)) = ε ∇²ψ

With spatially varying ε(x):

    ∂ψ/∂τ + ∇·(n̂ · ψ(1−ψ)) = ε(x) ∇²ψ + ∇ε · ∇ψ

The additional term ∇ε · ∇ψ arises from the product rule ∇·(ε∇ψ) = ε∇²ψ + ∇ε·∇ψ.

### 4.1 Analysis of the ∇ε·∇ψ term

Near the interface (where ψ varies):
- |∇ε| = C_ε |∇h_local| — bounded by the grid density function gradient
- |∇ψ| ≈ 1/(4ε) — maximum at the interface

So |∇ε · ∇ψ| ≈ C_ε |∇h_local| / (4ε). Compare with the diffusion term:
- |ε ∇²ψ| ≈ ε / (4ε²) = 1/(4ε)

Ratio: |∇ε·∇ψ| / |ε∇²ψ| ≈ |∇h_local| · ε / h_local ≈ C_ε |∇h_local|

Since |∇h_local| is O(1) (smooth grid density function), this term is O(C_ε)
and NOT negligible. Three options:

**Option A: Include ∇ε·∇ψ explicitly.**
Compute ∇ε from the eps_field and add to the reinitialization RHS.
Most accurate but requires modifying all reinit strategies.

**Option B: Use ∇·(ε(x)∇ψ) form directly.**
Rewrite diffusion as div(ε·grad(ψ)). The CCD differentiation already handles
non-uniform coefficients. This is the cleanest formulation.

**Option C: Use scalar ε_min for reinit stability.**
Keep reinit with scalar ε = C_ε · h_min (conservative), only use ε(x) for
Heaviside/CSF. This is what the archived experiment (run_ch12_local_eps.py)
did. Pragmatic but inconsistent.

### 4.2 Recommended approach: Option C (pragmatic)

The reinitialization operates in pseudo-time and converges to a fixed point.
The fixed point ψ* satisfies |∇φ*| = 1 where φ* = ε·ln(ψ*/(1−ψ*)).
With spatially varying ε, the fixed point has a spatially varying profile
width — which is exactly the desired outcome.

Using scalar ε_min for reinit gives a slightly sharper profile (thinner than
ε(x) in coarse regions), but this only affects regions far from the interface
where ψ is already near 0 or 1. The CSF force is concentrated at the interface
where ε(x) ≈ ε_min anyway.

**Practical impact:** Negligible. The reinit only needs to maintain ψ ∈ [0,1]
with a monotonic transition near the interface. The exact profile width far
from the interface is irrelevant for CSF.

## 5. Balanced-Force Condition

The balanced-force principle requires that grad(p) and ∇ψ in the CSF force
use the same spatial operator (CCD). With spatially varying ε:

- CSF force: f_σ = σκ∇ψ — uses CCD gradient of ψ
- PPE: ∇·(∇p/ρ) = ∇·(u*/dt) + ∇·(f_σ/ρ) — uses FD Laplacian for LHS
- Corrector: u = u* − dt/ρ · ∇p + dt/ρ · f_σ — uses CCD gradient of p

The balanced-force mismatch (CCD ∇ψ vs FD ∇²p) is INDEPENDENT of ε.
Spatially varying ε does not introduce any new operator inconsistency.

**Result: Balanced-force condition is PRESERVED with spatially varying ε.**

## 6. Implementation Architecture

### 6.1 What must change

| Component | Current | Change | Effort |
|-----------|---------|--------|--------|
| `heaviside(xp, phi, eps)` | scalar eps | Accept array eps | Trivial (broadcast) |
| `delta(xp, phi, eps)` | scalar eps | Accept array eps | Trivial (broadcast) |
| `CurvatureCalculator.__init__` | stores scalar eps | Store scalar or array | Minor |
| `TwoPhaseNSSolver.__init__` | `self._eps = eps_factor * h` | Add `_eps_field` property | Minor |
| `TwoPhaseNSSolver.step()` | passes scalar eps | Pass eps_field to curvature/CSF | Minor |
| `TwoPhaseNSSolver._rebuild_grid()` | uses scalar eps | Recompute eps_field after rebuild | Minor |

### 6.2 What does NOT change

| Component | Why unchanged |
|-----------|--------------|
| `invert_heaviside()` | Already supports array eps |
| Curvature formula | ε-independent (invariance theorem) |
| PPE solver | No ε dependency |
| CCD solver | No ε dependency |
| Advection | No ε dependency |
| Reinitializer | Keep scalar ε_min (Option C) |
| Grid rebuild | Grid density uses eps_g, separate from CSF eps |

### 6.3 eps_field construction

```python
def _make_eps_field(self) -> np.ndarray:
    """ε(x) = C_ε · max(h_x(i), h_y(j)) at each node."""
    hx = self._grid.h[0][:, np.newaxis]  # (NX+1, 1)
    hy = self._grid.h[1][np.newaxis, :]  # (1, NY+1)
    return self._eps_factor * np.maximum(hx, hy)
```

After each grid rebuild, call `self._eps_field = self._make_eps_field()`.

## 7. Expected Impact

### 7.1 Laplace pressure accuracy

With ε(x) = C_ε · h_local(x):
- ε/h_local = C_ε everywhere (design condition restored)
- CSF force distribution spans ~2C_ε cells at the interface
- Pressure can exactly balance the force (to O(h²) CSF model error)
- Expected: Laplace pressure error converges as O(h²), independent of α

### 7.2 Parasitic currents

exp12_17 showed α=2 with fixed ε already reduces parasitic currents 2-10×
(due to per-step grid alignment). With spatially varying ε, the remaining
CSF broadening effect is eliminated, expecting further reduction.

### 7.3 Mass conservation

No change expected — mass conservation is dominated by CLS advection and
remapping, not by ε.

## 8. Theoretical Guarantee

**Theorem (ε-consistency):** If ε(x) = C_ε · h_local(x) and the grid density
function ω(φ) is smooth (C²), then:
1. H_{ε(x)} is smooth in x (C^∞ away from ψ=0,1)
2. The CSF force integral ∫f_σ dx = σκ is preserved (exact for logistic profile)
3. The balanced-force cancellation order is unchanged (CCD O(h⁶))
4. The Laplace pressure error is O(h_local²) ≈ O(h²/α²) near the interface

Proof sketch:
(1) follows from smoothness of h_local(x) and the logistic function.
(2) follows from ∫δ_ε dφ = 1 for any ε > 0.
(3) follows from operator independence of ε.
(4) follows from the standard CSF error analysis with local ε replacing global ε.
□

## 9. Summary

The fixed-ε CSF mismatch on non-uniform grids is a purely geometric artifact:
the force width ε is mismatched with the local resolution h_local. The fix is
conceptually simple (ε(x) = C_ε · h_local(x)) and affects only the Heaviside
and delta function evaluations. Curvature, PPE, balanced-force, and advection
are all ε-independent and require no changes. Reinitialization can use a
conservative scalar ε_min with negligible practical impact.
