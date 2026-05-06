---
ref_id: WIKI-T-159
title: "Reinit-Aware Capillary Hodge Theory"
domain: theory
status: ACTIVE
tags: [capillary, hodge_projection, ridge_eikonal, reinitialization, surface_energy, pressure_jump]
sources:
  - path: docs/memo/short_paper/SP-AF_reinit_aware_capillary_hodge_theory.md
  - path: artifacts/A/capillary_reinit_hodge_complete_theory_CHK-RA-CAP-REINIT-HODGE-THEORY-001.md
  - path: docs/memo/short_paper/SP-AD_ridge_eikonal_transport_variational_coupling.md
  - path: docs/memo/short_paper/SP-AE_pressure_hodge_static_droplet_lessons.md
  - path: docs/02_ACTIVE_LEDGER.md
depends_on:
  - "[[WIKI-T-077]]"
  - "[[WIKI-T-155]]"
  - "[[WIKI-T-156]]"
  - "[[WIKI-T-157]]"
  - "[[WIKI-T-158]]"
  - "[[WIKI-X-041]]"
---

# Reinit-Aware Capillary Hodge Theory

## Claim

Ridge-Eikonal reinitialization can be included in capillary flow only as a
labelled representation projection:

```text
q^n -- T_h(u_f) --> q_T
q_T -- Pi_h    --> q^{n+1}
```

Capillary work pairs with the physical transport increment `q^n -> q_T`.
The reinitialization increment `q_T -> q^{n+1}` must preserve the interface
trace and trace surface energy in fixed topology, or it must be reported as a
projection defect/metric dissipation.

## Contract

Use:

```text
c_sigma = T_h^* dS_h
D_f A_f G_f p = r_h + D_f c_sigma
a_f = A_f G_f p - c_sigma
```

and evaluate the weighted face-space Hodge gate:

```text
static equilibrium        <=> P_h c_sigma = 0
dynamic capillary release <=> P_h c_sigma != 0
```

where `P_h` uses the same face mass, divergence, pressure gradient, and
corrector coefficients as the production PPE.

## Reinit Rule

For fixed-topology validation:

```text
Gamma(q^{n+1}) = Gamma(q_T)
S_h(Gamma(q^{n+1})) = S_h(Gamma(q_T)).
```

If either condition fails, the run is measuring reinitialization defect, not
physical capillary motion.

## Invalid Shortcut

Do not replace the production force by:

```text
c_sigma -> Pi_R c_sigma.
```

That deletion keeps static droplets quiet but also freezes every
zero-predictor dynamic capillary release.

## Required Diagnostics

Expose:

```text
psi_before_transport
psi_after_transport_before_reinit
psi_after_reinit
Delta S_T
Delta S_Pi
capillary_hodge_residual
```

The oscillating-droplet claim must come from `Delta S_T` and kinetic response,
not from `Delta S_Pi`.
