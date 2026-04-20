---
ref_id: WIKI-T-057
title: "σ_eff and ε_local Spatial Scaling for Ridge-Eikonal on Non-Uniform Grids"
domain: theory
status: PROPOSED
superseded_by: null
sources:
  - path: docs/memo/short_paper/SP-E_ridge_eikonal_nonuniform_grid.md
    description: "SP-E §3 (D1), §5 (D4) — σ_eff and ε_local derivation"
  - path: src/twophase/levelset/ridge_eikonal.py
    description: "RidgeExtractor.sigma_eff + RidgeEikonalReinitializer._eps_local"
depends_on:
  - "[[WIKI-T-047]]: Gaussian-ξ Ridge Interface Representation (SP-B source)"
  - "[[WIKI-T-038]]: eps_g Bandwidth Constraint"
  - "[[WIKI-T-040]]: ε_ξ on Stretched Grids"
  - "[[WIKI-T-042]]: ε-widening caveat (CHK-138/139)"
consumers:
  - domain: theory
    description: "WIKI-T-058 (physical-space Hessian), WIKI-T-059 (non-uniform FMM)"
  - domain: code
    description: "WIKI-L-025 (RidgeEikonalReinitializer library card)"
tags: [non_uniform_grid, sigma_scaling, eps_local, ridge_eikonal, spatial_field, chk_159]
compiled_by: Claude Opus 4.7
chk: CHK-159
---

# σ_eff and ε_local Spatial Scaling on Non-Uniform Grids

## Context

SP-B specifies the Gaussian-weighted auxiliary field $\xi_\text{ridge}$ with a single scalar width $\sigma$; the SP-B uniqueness argument presupposes a uniform Cartesian grid. On interface-fitted grids ($\alpha_\text{grid}>1$) the *cell count* covered by a constant $\sigma$ varies across the domain, breaking the SP-B guidance $\sigma\sim 2{-}4$. The same issue afflicts the reconstruction width $\varepsilon$ used by the final sigmoid $\psi=1/(1+e^{-\phi/\varepsilon})$.

## Result (D1 — σ_eff)

$$\sigma_\text{eff}(x)\;=\;\sigma_{0}\cdot\frac{h(x)}{h_\text{ref}},\qquad h_\text{ref}=\left(\prod_{ax}L_{ax}/N_{ax}\right)^{1/d},\quad h(x)=\sqrt{h_\text{x}(i)h_\text{y}(j)}.$$

$\sigma_{0}$ is a dimensionless constant expressed in $h_\text{ref}$-cells. The Gaussian half-width in *physical cells* is $\sigma_\text{eff}(x)/h(x)=\sigma_{0}/h_\text{ref}$, a constant, so the SP-B guidance $\sigma_{0}\in[2,4]$ is inherited verbatim.

## Result (D4 — ε_local)

$$\varepsilon_\text{local}(x)\;=\;\varepsilon_\text{scale}\cdot\varepsilon_{\xi}\cdot h(x),\qquad \varepsilon_{\xi}=\varepsilon/h_\text{min}.$$

CHK-138/139 calibrated $\varepsilon_\text{scale}=1.4$ on uniform grids. CHK-159 retains that baseline and lets $h(x)/h_\text{ref}$ carry the spatial correction.

## Resolution-consistency lemma

Any statement of the form "the Gaussian at $c_{k}$ covers $M$ physical cells at resolution $h$" is invariant under the $\sigma\to\sigma_\text{eff}$ substitution when $M$ is expressed in $h(x)$-cells. The SP-B §3 evolution PDE is written in physical coordinates; substituting a spatially-varying $\sigma$ changes only the pointwise coefficient of the diffusion operator, not the variational structure.

## Bandwidth-constraint compatibility

The [WIKI-T-038](WIKI-T-038.md) constraint `eps_g_factor ≥ (|u_max|·C_CFL·reinit_freq)/(c·eps_ratio)` applies to the grid-rebuild width $\varepsilon_{g}$, not to $\varepsilon_\text{local}$. For `reinit_every=2`, $|u_\text{max}|\sim\mathcal{O}(1)$, $C_\text{CFL}=0.1$, $c=2$, $\varepsilon_\text{ratio}\sim 1$, the bound is $\approx 0.225$ — easily satisfied by default configurations. The D4 $\varepsilon$ is independent of the rebuild path.

## Open caveat

If the CHK-159 V4 capillary-wave probe at $\alpha=2$ shows $|\Delta V/V|>5\%$, an adaptive field $\varepsilon_\text{scale}(x)=1.4\cdot h_\text{ref}/h_\text{min}$ is scheduled as a CHK-160 follow-up. The baseline ships with fixed $\varepsilon_\text{scale}=1.4$ to keep CHK-159 self-contained.

## Equation → Discretization → Code

  - Equation: $\sigma_\text{eff}(x)=\sigma_{0}\cdot h(x)/h_\text{ref}$
  - Discretization: `h_field = sqrt(hx·hy)` with `hx, hy` broadcast from `grid.h[ax]`
  - Code: `_sigma_eff_kernel(h_field, sigma_0, h_ref)` in [`src/twophase/levelset/ridge_eikonal.py`](../../../src/twophase/levelset/ridge_eikonal.py) (GPU/CPU via `@_fuse`)
  - Code (D4): `_eps_local_kernel(h_field, eps_scale, eps_xi)` (same module)
  - Verification: `test_ridge_eikonal.py::test_sigma_eff_convergence_alpha2`, `test_sigma_eff_cpu_fuse_identity`

## References

  - SP-E, `docs/memo/short_paper/SP-E_ridge_eikonal_nonuniform_grid.md` §3, §5
  - WIKI-T-038, WIKI-T-040, WIKI-T-042, WIKI-T-047
