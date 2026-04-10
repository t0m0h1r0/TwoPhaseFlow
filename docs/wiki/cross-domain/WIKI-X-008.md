---
id: WIKI-X-008
title: "Derived Physics Resolution: Non-Dimensional → Physical Parameter Mapping"
status: ACTIVE
created: 2026-04-10
updated: 2026-04-10
depends_on: [WIKI-T-006, WIKI-L-014]
---

# Derived Physics Resolution

## Problem

Two-phase flow benchmarks are conventionally specified by non-dimensional numbers
(Re, Eo, We, Ca, λ), but the solver operates on physical quantities (μ, σ, μ_l, μ_g).
Each experiment script was independently computing the same derivation formulas,
duplicating logic and risking inconsistency.

## Resolution Formulas

All formulas assume a **buoyancy velocity scale** U = √(g d) where d = `d_ref`
(characteristic length, typically bubble diameter).

### Reynolds number → viscosity

$$
\text{Re} = \frac{\rho_l \sqrt{g\,d}\,d}{\mu}
\qquad\Longrightarrow\qquad
\mu = \frac{\rho_l \sqrt{g\,d}\,d}{\text{Re}}
$$

Both μ_l and μ_g are set to this value (uniform viscosity) unless λ is also specified.

### Eötvös number → surface tension

$$
\text{Eo} = \frac{g\,(\rho_l - \rho_g)\,d^2}{\sigma}
\qquad\Longrightarrow\qquad
\sigma = \frac{g\,(\rho_l - \rho_g)\,d^2}{\text{Eo}}
$$

### Capillary number → surface tension (shear flows)

$$
\text{Ca} = \frac{\mu_g\,\dot\gamma\,R}{\sigma}
\qquad\Longrightarrow\qquad
\sigma = \frac{\mu_g\,\dot\gamma\,R}{\text{Ca}}
$$

where R = `R_ref` (droplet radius) and γ̇ = `gamma_dot` (shear rate from Couette BC).

### Viscosity ratio → liquid viscosity

$$
\lambda = \frac{\mu_l}{\mu_g}
\qquad\Longrightarrow\qquad
\mu_l = \lambda\,\mu_g
$$

When λ is specified, the solver uses **variable viscosity**: μ(x) = μ_g + (μ_l − μ_g) ψ(x).

### Weber number → surface tension (collision problems)

$$
\text{We} = \frac{\rho_l\,v_0^2\,d}{\sigma}
\qquad\Longrightarrow\qquad
\sigma = \frac{\rho_l\,v_0^2\,d}{\text{We}}
$$

Not currently in `config_io._parse_physics` (computed in YAML sweep overrides directly).

## Implementation

Resolution is performed once at config load time in `config_io._parse_physics()`.

**Priority rules** (explicit > derived):

1. If `sigma` is explicitly given in YAML, it takes precedence over Eo/Ca derivation
2. If `mu` is explicitly given, it takes precedence over Re derivation
3. `mu_l` / `mu_g` = None means uniform viscosity (variable-μ path is skipped)

**Required YAML fields for each derivation:**

| Derivation | Required fields |
|------------|----------------|
| Re → μ | `Re`, `d_ref`, `g_acc` (must be > 0) |
| Eo → σ | `Eo`, `d_ref`, `g_acc` (must be > 0) |
| Ca → σ | `Ca`, `mu_g`, `gamma_dot`, `R_ref` (or `d_ref` → R = d/2) |
| λ → μ_l | `lambda_mu`, `mu_g` |

## Verification by Experiment

| Experiment | Derivation used | Verified values |
|------------|----------------|-----------------|
| §13.3 Rising bubble | Re=35, Eo=10, d=0.5, g=1 | σ=0.2250, μ=0.1010 |
| §13.6 DKT | Re=35, Eo=10, d=0.5, g=1 | σ=24.50, μ=10.12 (ρ_l=1000) |
| §13.8 Taylor | Ca=0.2, μ_g=0.1, γ̇=2, R=0.25 | σ=0.250 |
| §13.8 Taylor λ=5 | λ=5, μ_g=0.1 | μ_l=0.5 |

## Sweep Override Interaction

For parametric sweeps where a derived quantity varies (e.g. σ sweep at different Ca),
the pre-computed physical value is placed directly in `sweep.overrides`:

```yaml
# σ = μ_g γ̇ R / Ca = 0.1 × 2.0 × 0.25 / Ca = 0.05 / Ca
sweep:
  - label: "Ca=0.1"
    overrides: {physics.sigma: 0.500}
  - label: "Ca=0.2"
    overrides: {physics.sigma: 0.250}
```

This avoids re-resolution complexity in `override()` while keeping the mapping
traceable via comments in the YAML.
