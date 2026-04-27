---
ref_id: WIKI-T-008
title: "Curvature Computation: Invariance Theorem and Direct psi-Based Evaluation"
domain: T
status: ACTIVE
superseded_by: null
sources:
  - path: paper/sections/02c_nondim_curvature.tex
    git_hash: 7328bf1
    description: "Curvature definition, 2D formula, invariance theorem"
  - path: paper/sections/03b_levelset_mapping.tex
    git_hash: 7328bf1
    description: "Direct psi-curvature, denominator clamping, implementation checklist"
consumers:
  - domain: L
    usage: "curvature.py computes kappa from psi derivatives via CCD"
  - domain: T
    usage: "Curvature feeds into CSF surface tension and Young-Laplace validation"
  - domain: E
    usage: "Circle test (kappa = -1/R) is primary curvature verification"
depends_on:
  - "[[WIKI-T-001]]"
  - "[[WIKI-T-007]]"
  - "[[WIKI-T-010]]"
  - "[[WIKI-T-018]]"
compiled_by: KnowledgeArchitect
compiled_at: 2026-04-07
---

## Curvature Definition

kappa = -div(grad(phi) / |grad(phi)|)

Sign convention: kappa = -1/R for a circle/sphere (interface curves toward center → negative). Matches Young-Laplace: p_gas - p_liq = sigma * kappa (negative → p_liq > p_gas).

## 2D Cartesian Formula

kappa = -(psi_y^2 * psi_xx - 2*psi_x*psi_y*psi_xy + psi_x^2 * psi_yy) / (psi_x^2 + psi_y^2)^(3/2)

Requires: first derivatives (psi_x, psi_y), second derivatives (psi_xx, psi_yy), mixed derivative (psi_xy). All available from CCD at O(h^6) — see [[WIKI-T-001]], [[WIKI-X-002]].

## Curvature Invariance Theorem (Critical)

**For any monotonic transformation psi = g(phi) with g' > 0:**

-div(grad(psi)/|grad(psi)|) = -div(grad(phi)/|grad(phi)|) = kappa

**Proof sketch**: g' factors cancel in the quotient grad(psi)/|grad(psi)| = g'*grad(phi) / |g'*grad(phi)| = grad(phi)/|grad(phi)|.

**Consequence**: The CLS smoothed Heaviside psi = H_eps(phi) computes identical curvature whether using phi or psi. No logit inversion needed for curvature.

**2026-04-26 discrete caveat**: this is a continuum theorem, not a discrete
energy-stability theorem. On non-uniform grids, compact finite-difference
operators do not satisfy the nonlinear chain rule exactly, so direct
`psi`-curvature may fail to be the variational derivative of a discrete
surface-area functional. See [[WIKI-T-077]] for the production capillary
geometry contract.

## Implementation: psi-Direct Path

1. Compute psi_x, psi_xx via x-direction CCD (O(h^6))
2. Compute psi_y, psi_yy via y-direction CCD (O(h^6))
3. Compute psi_xy via sequential 1D CCD (see [[WIKI-X-002]])
4. Apply domain filter: kappa = 0 outside psi_min < psi < (1-psi_min), psi_min = 0.01
5. Evaluate kappa formula with denominator clamping
6. (Optional) Gaussian 3x3 filter for high-density-ratio noise

### Denominator Clamping

kappa = -numerator / max(psi_x^2 + psi_y^2, eps_norm^2)^(3/2)

eps_norm = 1e-3. Prevents division by zero in pure-phase regions where |grad(psi)| → 0.

Error analysis: if |grad(phi)|^2 = 1 + delta^2, curvature error is O(delta^2) — reinitialization quality is the primary accuracy guarantee.

## Advantages Over phi-Based Curvature

1. **No logit singularity**: phi = eps*ln(psi/(1-psi)) has log singularities at psi=0,1; psi-direct avoids this
2. **Smoother derivatives**: psi derivatives remain bounded; no intermediate discretization error
3. **Eikonal independence**: accuracy not tied to |grad(phi)| ≈ 1 maintenance

## Effective Interface Thickness Monitor

eps_eff_i = psi_i*(1-psi_i) / |grad(psi)|_i

If eps_eff ≈ eps (design value), profile is normal. If eps_eff >> eps, numerical diffusion is widening the interface → trigger reinitialization.
