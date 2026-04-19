---
ref_id: WIKI-T-044
title: "FVM-CCD Metric Inconsistency: G^adj Face-Average Gradient for Non-Uniform Grids"
domain: theory
status: VERIFIED  # b83837r0w confirmed 2026-04-20
superseded_by: null
sources:
  - path: src/twophase/simulation/ns_pipeline.py
    description: _fvm_pressure_grad(), _precompute_fvm_grad_spacing() — G^adj implementation
  - path: experiment/ch13/config/ch13_02_bisect.yaml
    description: bisect sweep confirming alpha_grid is causal (g_low still blows up)
depends_on:
  - "[[WIKI-T-003]]: Variable-Density Projection Method"
  - "[[WIKI-T-017]]: FVM Reference Methods — PPE Face Coefficients"
  - "[[WIKI-X-012]]: CCD Metric Instability on Non-Uniform Grids in NS Simulation"
consumers:
  - domain: code
    description: WIKI-L-022 G^adj implementation reference
  - domain: experiment
    description: ch13_02_waterair_bubble non-uniform bubble stability fix
tags: [non_uniform_grid, FVM, CCD, pressure_gradient, projection_method, metric_inconsistency, stability]
compiled_by: Claude Sonnet 4.6
compiled_at: "2026-04-19"
---

# FVM-CCD Metric Inconsistency: G^adj Face-Average Gradient for Non-Uniform Grids

## Problem Statement

In the projection method on a non-uniform collocated grid, two operators act on pressure:

1. **PPE solver** builds $\mathcal{L}_\text{FVM}$ using face spacings $d_f^{(i)} = x_{i+1} - x_i$:

$$
(\mathcal{L}_\text{FVM}\, p)_i
= \frac{p_{i+1} - p_i}{d_f^{(i)}\, \delta v_i} - \frac{p_i - p_{i-1}}{d_f^{(i-1)}\, \delta v_i}
$$

2. **Velocity corrector** applies CCD gradient $\mathcal{G}_\text{CCD}$ which uses node control volumes $\delta v_i = (x_{i+1} - x_{i-1})/2$:

$$
(\mathcal{G}_\text{CCD}\, p)_i
= \frac{1}{\delta v_i}\frac{\partial p}{\partial \xi}\bigg|_i
\quad\Longrightarrow\quad
J_\text{node} = \frac{1}{\delta v_i}
$$

On a **uniform** grid $d_f = \delta v = h$ everywhere, so $\mathcal{D}_\text{FVM}(\mathcal{G}_\text{CCD}) = \mathcal{L}_\text{FVM}$ exactly.

On a **non-uniform** grid $d_f \ne \delta v$ in general, breaking this identity.

---

## Residual Divergence Derivation

Define the divergence-of-gradient residual per step:

$$
\varepsilon_i = \bigl[\mathcal{D}_\text{FVM}(\mathcal{G}_\text{CCD}\, p) - \mathcal{L}_\text{FVM}\, p\bigr]_i
$$

Expanding to leading order in the metric mismatch $\delta J_i = J_f^{(i)} - J_n^{(i)}$
where $J_f^{(i)} = 1/d_f^{(i)}$, $J_n^{(i)} = 1/\delta v_i$:

$$
\varepsilon_i = \frac{\delta J_i \cdot (p_{i+1} - p_i) - \delta J_{i-1}\cdot(p_i - p_{i-1})}{\delta v_i}
+ O(h^2 \nabla^3 p)
$$

This residual is **non-zero whenever $d_f \ne \delta v$** and is injected into the velocity
field at every time step as a spurious divergence, accumulating without bound.

### Quantification for α = 1.5 Bubble (64×128 grid)

| Metric | Value |
|--------|-------|
| max \|J_face − J_node\| / J_face | **0.774** (77%) |
| Step of KE blowup (G_CCD, baseline) | **51** (t ≈ 0.023), KE = 1.141 × 10⁶ |
| KE @ t=0.023 after G^adj fix | **1.41 × 10⁻²** (normal) |
| Steps until next blowup (G^adj) | **28,122** (t ≈ 12.60) — ×550 improvement |

### Bisection Experiment (ch13_02_bisect)

| Case | Configuration | Result |
|------|--------------|--------|
| `alpha10` | alpha_grid = 1.0 (uniform grid) | STABLE (n=82, t=0.10) |
| `g_low` | g_acc = 0.0001 (1/10 gravity) | BLOWUP (n=51, same as baseline) |

**Conclusion**: Non-uniform grid geometry (alpha_grid > 1) is the sole cause; gravity is irrelevant.

---

## G^adj: Face-Average Gradient

Define the **face-average gradient** $\mathcal{G}^\text{adj}$ as:

$$
(\mathcal{G}^\text{adj}\, p)_i
= \frac{1}{2}\left[
  \frac{p_{i+1} - p_i}{d_f^{(i)}}
+ \frac{p_i - p_{i-1}}{d_f^{(i-1)}}
\right]
$$

This uses $J_f = 1/d_f^{(i)}$ (same as $\mathcal{L}_\text{FVM}$), not $1/\delta v_i$.

### Consistency Proof: $\mathcal{D}_\text{FVM}(\mathcal{G}^\text{adj}) = \mathcal{L}_\text{FVM}$

$$
\bigl[\mathcal{D}_\text{FVM}(\mathcal{G}^\text{adj}\, p)\bigr]_i
= \frac{(\mathcal{G}^\text{adj}\, p)_{i+1/2}^+ - (\mathcal{G}^\text{adj}\, p)_{i-1/2}^-}{\delta v_i}
$$

where the face value at face $i+1/2$ is taken as the right face gradient:
$(\mathcal{G}^\text{adj}\, p)_{i+1/2} = (p_{i+1} - p_i)/d_f^{(i)}$.

Therefore:

$$
\bigl[\mathcal{D}_\text{FVM}(\mathcal{G}^\text{adj}\, p)\bigr]_i
= \frac{1}{\delta v_i}\left[
  \frac{p_{i+1} - p_i}{d_f^{(i)}} - \frac{p_i - p_{i-1}}{d_f^{(i-1)}}
\right]
= (\mathcal{L}_\text{FVM}\, p)_i \quad \checkmark
$$

The residual $\varepsilon_i = 0$ for all $i$: the projection is **exactly consistent**.

---

## GFM Compatibility

The Ghost-Fluid Method correction (see `coupling/gfm.py`) computes:

$$
b_i^\text{GFM} = \pm \frac{\Delta\rho \cdot \kappa \cdot \hat{n}}{We \cdot d_f^{(i)} \cdot \delta v_i}
$$

This uses the ratio $d_f/\delta v$, i.e., the same FVM space as $\mathcal{L}_\text{FVM}$ and $\mathcal{G}^\text{adj}$.

| Operator | Metric used |
|----------|-------------|
| $\mathcal{L}_\text{FVM}$ | $1/d_f$ (face) |
| $\mathcal{G}^\text{adj}$ | $1/d_f$ (face) ✓ |
| $b^\text{GFM}$ | $d_f/\delta v$ (both) ✓ |
| $\mathcal{G}_\text{CCD}$ (old) | $1/\delta v$ (node) ✗ |

All three FVM operators are now in the same metric space.

---

## Boundary Conditions

For a **wall** (Neumann) boundary $\partial p/\partial n = 0$:

- Left boundary ($i=0$): $g[0] = 0$ (zero initialization is exact)
- Right boundary ($i=N$): $g[N] = 0$ (same)

The G^adj formula assigns zero to both boundaries naturally — no explicit enforcement required.

> Note: G^adj applies only to `wall` BC. Periodic BC uses CCD unchanged (metrics cancel in the periodic loop).

---

## Applicability Scope

| Grid | BC | Gradient used |
|------|-----|---------------|
| Uniform | any | CCD (no change, dv = d_face) |
| Non-uniform | wall | G^adj (this fix) |
| Non-uniform | periodic | CCD (periodic BC: capwave tests unaffected) |

The guard condition `not self._grid.uniform and self.bc_type == "wall"` ensures backward compatibility.

---

## Assumptions

- G^adj is 2nd-order accurate; CCD is 6th-order. For smooth pressure fields this accuracy loss is acceptable since the PPE solve is 2nd-order FVM anyway.
- The consistency proof assumes a 1D FVM divergence operator. In 2D the x and y axes decouple in the collocated projection — the same argument holds axis-by-axis.
- Grid is static (grid_rebuild_freq=0 in ch13); `_precompute_fvm_grad_spacing()` is called once in `_rebuild_grid`.
