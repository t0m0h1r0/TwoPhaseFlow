---
ref_id: WIKI-T-058
title: "Physical-Space Hessian for Ridge Detection; Direct Non-Uniform CCD (Approach A) vs FD Fallback"
domain: theory
status: PROPOSED
superseded_by: null
sources:
  - path: docs/memo/short_paper/SP-E_ridge_eikonal_nonuniform_grid.md
    description: "SP-E §4 (D2) — derivation of physical-space Hessian and ξ-space prohibition"
  - path: src/twophase/levelset/ridge_eikonal.py
    description: "RidgeExtractor.extract_ridge_mask — FD Hessian with Approach A upgrade marker"
depends_on:
  - "[[WIKI-T-047]]: Gaussian-ξ Ridge Interface Representation"
  - "[[WIKI-T-039]]: Impossibility Theorem — ξ-space CCD cannot resolve J-containing derivatives"
  - "[[WIKI-T-057]]: σ_eff / ε_local spatial scaling"
consumers:
  - domain: code
    description: "WIKI-L-025 (RidgeEikonalReinitializer library card)"
  - domain: theory
    description: "Deferred CHK-160 — Approach A implementation"
tags: [hessian, ridge_detection, chain_rule, direct_ccd, approach_a, fd_fallback, chk_159, chk_160]
compiled_by: Claude Opus 4.7
chk: CHK-159
---

# Physical-Space Hessian for Ridge Detection

## Context

SP-B §4 defines the admissibility Hessian $n^{T}\nabla_{x}^{2}\xi_\text{ridge}\,n<0$ in physical space. On non-uniform grids the naive implementation computes $\nabla_{\xi_\text{idx}}^{2}$ in computational-index space and applies the chain rule
$$\nabla_{x}^{2}\;=\;J^{T}\nabla_{\xi}^{2}J+(\nabla_{\xi}J^{T})\nabla_{\xi}.$$

## Theorem 2 (ξ-space Hessian prohibition)

**Claim.** Under [WIKI-T-039](WIKI-T-039.md) any Hessian evaluation whose leading term lives in $\xi_\text{idx}$ space carries an $\mathcal{O}(10^{-1})$ floor error whenever the transition width is $\le 4$ cells.

**Consequence.** The $\xi_\text{ridge}$ field is by construction concentrated within $\sigma_\text{eff}\sim 3h$ of the interface (SP-B §3), so Theorem 2 forbids the chain-rule path. Any conformant implementation must evaluate the Hessian in physical space directly.

## Approach A (paper-exact, CHK-160 target)

Direct Non-Uniform CCD ([WIKI-T-039 §5a](WIKI-T-039.md)) builds a compact finite-difference system whose stencils use physical spacings $h_\text{x}(i),h_\text{y}(j)$ explicitly. The second-derivative operator is $\mathcal{O}(h^{6})$ and by construction does *not* route through $\xi_\text{idx}$.

## Approach B (FD fallback, CHK-159)

Second-order physical-space finite differences:
$$[\partial_{xx}\xi]_{ij}=\frac{\xi_{i+1,j}-2\xi_{ij}+\xi_{i-1,j}}{h^{-}\cdot h^{+}},\quad h^{\pm}=h_\text{x}(i\pm{\tfrac{1}{2}}),$$
$$[\partial_{yy}\xi]_{ij}=\frac{\xi_{i,j+1}-2\xi_{ij}+\xi_{i,j-1}}{h_\text{y}^{-}h_\text{y}^{+}},\qquad [\partial_{xy}\xi]_{ij}=\frac{\xi_{i+1,j+1}-\xi_{i+1,j-1}-\xi_{i-1,j+1}+\xi_{i-1,j-1}}{4\,h_\text{x}(i)\,h_\text{y}(j)}.$$

## Sign-stability of Approach B

The $\mathcal{O}(h^{2})$ FD Hessian is sign-correct for any point outside an $\mathcal{O}(h)$ neighbourhood of a Morse-degenerate ridge point. Standard benchmarks (disc reinit, capillary wave, Zalesak) contain no Morse-degenerate ridges, so Approach B is adequate for CHK-159 verification.

## Ridge mask assembly

$$\text{ridge}_{ij}=\text{local\_max}(\xi_{ij})\;\land\;\left(n^{T}H^{\text{FD}}n<0\right)\;\land\;\|\nabla_{x}\xi\|_{ij}<\tau\,\max_{ij}\|\nabla_{x}\xi\|_{ij}.$$

The gradient-small tolerance $\tau=0.5$ is scale-free; the $n^{T}Hn$ test uses axis-aligned surrogates plus trace sign (sufficient since a true ridge passes along at least one axis).

## Equation → Discretization → Code

  - Equation: $n^{T}\nabla_{x}^{2}\xi_\text{ridge}\,n<0$ (physical space)
  - Discretization: Approach B FD stencils above
  - Code: `RidgeExtractor.extract_ridge_mask` in [`src/twophase/levelset/ridge_eikonal.py`](../../../src/twophase/levelset/ridge_eikonal.py)
  - CHK-160 upgrade site: marked `# CHK-160: upgrade Hessian to Approach A DirectNonUniformCCDSolver`
  - Verification: `test_ridge_eikonal.py::test_ridge_topology_two_disks`, `..._single_merged_disk`

## References

  - SP-E, `docs/memo/short_paper/SP-E_ridge_eikonal_nonuniform_grid.md` §4
  - WIKI-T-039 (Impossibility Theorem), WIKI-T-047 (ξ_ridge), WIKI-T-057 (σ_eff)
