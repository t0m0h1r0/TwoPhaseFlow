---
ref_id: WIKI-T-068
title: "FCCDDivergenceOperator: FCCD Face-Flux Projector with FVM-Consistent Pressure Gradient"
domain: theory
status: ACTIVE
superseded_by: null
sources:
  - path: src/twophase/simulation/gradient_operator.py
    description: "FCCDDivergenceOperator.project, FCCDDivergenceOperator.divergence"
  - path: src/twophase/ccd/fccd.py
    description: "FCCDSolver.face_value, face_divergence"
  - path: src/twophase/simulation/ns_pipeline.py
    description: "_fccd_div_op, _face_flux_projection auto-enable"
consumers:
  - domain: X
    usage: "ch13 non-uniform+wall face-flux projection (Fix 2)"
depends_on:
  - "[[WIKI-T-004]]: Balanced-Force Condition"
  - "[[WIKI-T-046]]: FCCD: Face-Centered Upwind Combined Compact Difference"
  - "[[WIKI-T-055]]: FCCD Advection Operator"
  - "[[WIKI-T-063]]: FCCD Face-Flux PPE"
  - "[[WIKI-X-029]]: Balanced-Force Operator Consistency for CCD/FCCD"
tags: [fccd, divergence-operator, face-flux-projection, bf-pairing, non-uniform-grid]
compiled_by: ResearchArchitect
verified_by: null
compiled_at: 2026-04-23
---

# FCCDDivergenceOperator: FCCD Face-Flux Projector

## §1 Problem: div_u ≈ 0.2 with FVM div + FCCD gradient

With `FVMDivergenceOperator` (O(h²) arithmetic face averaging) as the primary PPE
divergence and `FCCDGradientOperator` (O(h⁴) Hermite) as the velocity corrector,
the post-correction divergence is:

$$\text{FVM\_div}(\mathbf{u}_\text{corr}) = \text{FVM\_div}(\mathbf{u}^*) - \Delta t \cdot \text{FVM\_div}\left[\frac{1}{\rho}\text{FCCD\_grad}(p)\right]$$

Since $\text{FVM\_div} \neq -(\text{FCCD\_grad})^*$ (they are not adjoint), the residual is
$O(h^2) \approx 0.2$ for a 128² grid. Over 1200 steps this grows until redistance
triggers blowup.

## §2 Why FCCD face_value must not be used for the PPE RHS surface tension term

A naïve fix — replace `FVMDivergenceOperator` with `FCCDDivergenceOperator` as the
primary `_div_op` for the PPE RHS — causes **earlier** blowup (step 237 vs 1252).

The root cause: `FCCDSolver.face_value` applies the correction
$u_f = (u_i + u_{i+1})/2 - (H^2/16)(q_i + q_{i+1})$ where $q = \partial^2 u / \partial x^2$.

For the surface tension force $f_x/\rho = \sigma\kappa (\partial\psi/\partial x)/\rho$, which has a
spike of order $1/\varepsilon$ near the interface:

$$|q| = \left|\frac{\partial^2(f_x/\rho)}{\partial x^2}\right| \sim \frac{\sigma\kappa}{\rho\,\varepsilon^3}$$

With $\varepsilon \approx 6\times10^{-3}$ (N=128) and $\sigma\kappa/\rho \sim 10$, $|q| \sim 5\times10^7$.  
The correction $H^2/16 \cdot |q| \sim (6\times10^{-3})^2/16 \cdot 5\times10^7 \approx 1125$ — orders of
magnitude larger than the actual face value. This corrupts the PPE RHS for the force
term, producing a wrong pressure that causes large divergence after correction.

## §3 Correct design: FCCD face-flux projector

`FCCDDivergenceOperator` is used exclusively through its `project()` method.  
The PPE RHS continues to use `FVMDivergenceOperator` (arithmetic averaging, safe for
non-smooth force fields).  The velocity correction is done in face-flux space:

1. **FCCD face values** for $u^*$ and $f/\rho$ (smooth fields): O(h⁴)
2. **FVM-consistent face pressure gradient** $(2/(\rho_l + \rho_r)) \cdot (p_r - p_l) / H$:
   matches the FVM PPE solver exactly
3. **FVM-style reconstruction** $u_i \approx (F_{i-1/2} + F_{i+1/2}) / 2$

## §4 Cancellation proof (exact FVM divergence)

Let $F_i^* = \text{FCCD\_face}(u^*)_i$, $G_i = (p_{i+1}-p_i)/H_i$, $\text{FVM\_Lap} = \text{FVM\_face\_div}(G_i)$.

PPE solution: $\text{FVM\_Lap}(p) = \text{FVM\_div}(u^*)/\Delta t + \text{FVM\_div}(f/\rho)$

Post-projection face flux: $F_i^\text{corr} = F_i^* - \Delta t G_i/\rho_f + \Delta t \cdot \text{FCCD\_face}(f/\rho)_i$

$$\text{FVM\_face\_div}(F^\text{corr}) = \text{FVM\_face\_div}(F^*) - \Delta t \cdot \text{FVM\_Lap}(p) + \Delta t \cdot \text{FVM\_face\_div}(\text{FCCD\_face}(f/\rho))$$

Since $\text{FVM\_face\_div}(F^*) = \text{FVM\_div}(u^*)$ (arithmetic average is the FVM face flux)
and $\text{FVM\_face\_div}(\text{FCCD\_face}(f/\rho)) = \text{FVM\_div}(f/\rho) + O(h^2)$:

$$\text{FVM\_face\_div}(F^\text{corr}) = \text{FVM\_div}(u^*) - \text{FVM\_div}(u^*) - \Delta t\,\text{FVM\_div}(f/\rho) + \Delta t\,\text{FVM\_div}(f/\rho) + O(\Delta t h^2) \approx 0$$

The FVM divergence of the reconstructed nodal velocity is $O(\Delta t h^2)$ after projection.
Compare to $O(h^2) \approx 0.2$ without face-flux projection.

## §5 Activation in ns_pipeline

- `_div_op = FVMDivergenceOperator` (non-uniform+wall): PPE RHS, safe for all fields
- `_fccd_div_op = FCCDDivergenceOperator`: velocity projection only
- `_face_flux_projection = True` auto-set when `_fccd_div_op is not None`
- `_rebuild_grid` calls `_fccd_div_op.update_weights()` to refresh FCCD geometry

## §6 Relationship to FVM appendix

The face-flux structure — face values in, divergence out — mirrors the FVM appendix
construction. The upgrade is O(h⁴) Hermite face interpolation for the smooth velocity
field $u^*$, replacing O(h²) arithmetic averaging. Non-smooth fields (surface tension
force) retain FVM averaging, avoiding the $H^2 q$ amplification identified in §2.
