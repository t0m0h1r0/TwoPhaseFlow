---
ref_id: WIKI-X-003
title: "Sign Conventions and Variable Definitions: phi, psi, kappa, n_hat"
domain: cross-domain
status: ACTIVE
superseded_by: null
sources:
  - path: paper/sections/02_governing.tex
    git_hash: 7328bf1
    description: "phi/psi definitions, sign convention"
  - path: paper/sections/02c_nondim_curvature.tex
    git_hash: 7328bf1
    description: "Curvature sign, gravity convention"
  - path: paper/sections/03_levelset.tex
    git_hash: 7328bf1
    description: "CLS variable range, logit inversion"
consumers:
  - domain: L
    usage: "All modules must follow these conventions consistently"
  - domain: T
    usage: "Derivations assume these signs"
  - domain: E
    usage: "Validation: kappa=-1/R for circle, p_liq > p_gas"
  - domain: A
    usage: "Consistent notation throughout paper"
depends_on: []
compiled_by: KnowledgeArchitect
compiled_at: 2026-04-07
---

## Interface Variables

| Variable | Symbol | Range | Liquid | Interface | Gas |
|----------|--------|-------|--------|-----------|-----|
| Signed distance | phi | (-inf, +inf) | phi < 0 | phi = 0 | phi > 0 |
| Conservative LS | psi | [0, 1] | psi ≈ 0 | psi = 0.5 | psi ≈ 1 |

**Relationship**: psi = H_eps(phi) (smoothed Heaviside); phi = eps * ln(psi/(1-psi)) (logit inverse).

## Normal Vector

n_hat = grad(phi) / |grad(phi)|

- Points from **liquid to gas** (outward from liquid)
- When |grad(phi)| = 1 (Eikonal): n_hat = grad(phi)

## Curvature

kappa = -div(n_hat) = -div(grad(phi) / |grad(phi)|)

| Geometry | kappa | Physical meaning |
|----------|-------|-----------------|
| Circle (radius R) | -1/R | Negative (curves inward toward center) |
| Sphere (radius R) | -2/R | Sum of two principal curvatures |
| Flat interface | 0 | No surface tension pressure jump |

## Young-Laplace Pressure Jump

[p]_Gamma = p_gas - p_liq = sigma * kappa

For circle: p_gas - p_liq = -sigma/R < 0, so **p_liq > p_gas** (liquid interior has higher pressure).

## Gravity Convention

g_hat = -g * z_hat (gravity points downward; z-axis upward positive)

Nondimensional: -rho(psi) / Fr^2 * z_hat

## Property Interpolation Convention

| Property | Formula | psi=0 (liquid) | psi=1 (gas) |
|----------|---------|----------------|-------------|
| Density | rho_l + (rho_g - rho_l)*psi | rho_l | rho_g |
| Viscosity | mu_l + (mu_g - mu_l)*psi | mu_l | mu_g |

## Code Convention Note

In the codebase, the builder uses exp(+phi/eps) with phi<0=liquid (outward SDF), while the paper uses exp(-phi/eps) with phi>0=liquid. These are equivalent: phi_builder = -phi_paper. The self-consistency was verified in CHK-036 (REVIEWER_ERROR). See 02_ACTIVE_LEDGER.md.
