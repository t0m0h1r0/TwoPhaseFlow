---
ref_id: WIKI-T-006
title: "One-Fluid Formulation: Two-Fluid to Single-Domain NS via CSF"
domain: T
status: ACTIVE
superseded_by: null
sources:
  - path: paper/sections/02_governing.tex
    git_hash: 7328bf1
    description: "Two-Fluid → One-Fluid transformation, jump conditions, property interpolation"
  - path: paper/sections/02b_surface_tension.tex
    git_hash: 7328bf1
    description: "CSF model, Young-Laplace relation, Balanced-Force preview"
  - path: paper/sections/02c_nondim_curvature.tex
    git_hash: 7328bf1
    description: "Nondimensionalization, Re/Fr/We definitions, curvature formula"
consumers:
  - domain: L
    usage: "ns_terms/ implements one-fluid NS with CSF surface tension"
  - domain: T
    usage: "Foundation for all subsequent spatial/temporal discretization"
  - domain: A
    usage: "§2 provides the continuous equations discretized in §4–§10"
depends_on:
  - "[[WIKI-T-010]]"
compiled_by: KnowledgeArchitect
compiled_at: 2026-04-07
---

## Core Transformation

Two separate per-phase NS equations + interface jump conditions are unified into a **single NS equation** valid throughout the domain:

rho(psi) * (du/dt + u . grad(u)) = -grad(p) + div[mu(psi)(grad(u) + grad(u)^T)] + rho(psi)*g + f_sigma

The surface tension jump condition [stress]_Gamma = sigma*kappa*n_hat is absorbed as a volume force via the CSF model:

f_sigma = sigma * kappa * grad(psi)

where grad(psi) = delta_eps(phi) * grad(phi) naturally localizes the force to the interface region.

## Property Interpolation

| Property | Formula | Interpolation | Rationale |
|----------|---------|---------------|-----------|
| Density | rho(psi) = rho_l + (rho_g - rho_l)*psi | Arithmetic | Volume average |
| Viscosity | mu(psi) = mu_l + (mu_g - mu_l)*psi | Arithmetic | FVM volume average for diffuse interface (Appendix proof) |
| Inverse density (PPE) | 1/rho face | Harmonic mean | Flux continuity (series resistance analogy) |

**Critical note on viscosity**: Harmonic mean would give mu ≈ 1.98*mu_g for water/air (mu_l/mu_g=100), suppressing liquid viscous effects. Arithmetic mean (≈ 50.5*mu_g) is physically correct for the CLS diffuse interface.

## Nondimensional Form

Scaled by liquid density rho_l, characteristic velocity U, length L:

rho(psi) * (du/dt + u . grad(u)) = -grad(p) + (1/Re)*div[mu(psi)(...)] - (rho(psi)/Fr^2)*z_hat + (kappa*grad(psi))/We

| Number | Definition | Example (1mm water droplet, U=1m/s) |
|--------|-----------|--------------------------------------|
| Re | rho_l*U*L / mu_l | 1000 |
| Fr | U / sqrt(g*L) | 10.1 |
| We | rho_l*U^2*L / sigma | 13.7 |

## Design Significance

The One-Fluid formulation enables solving a single velocity field on a single grid, with interface effects encoded in spatially-varying rho(psi), mu(psi), and the CSF force term. This is the foundation for the collocated-grid CCD approach (§4–§10).
