---
ref_id: WIKI-T-078
title: "Interface Role Separation: psi Transport, phi Metric, and Oriented Stress Jump"
domain: theory
status: ACTIVE
superseded_by: null
tags: [cls, level_set, curvature, young_laplace, pressure_jump, interface_roles]
sources:
  - path: paper/sections/02_governing.tex
    description: "Defines phi, psi, n_lg, kappa_lg, and j_gl sign convention"
  - path: paper/sections/03_levelset.tex
    description: "Separates Eikonal degradation from mass loss"
  - path: paper/sections/03c_levelset_mapping.tex
    description: "Explains psi--phi mapping, curvature invariance, and profile diagnostics"
  - path: paper/sections/03d_ridge_eikonal.tex
    description: "Separates topology freedom from metric consistency"
depends_on:
  - "[[WIKI-X-003]]"
  - "[[WIKI-T-007]]"
  - "[[WIKI-T-020]]"
  - "[[WIKI-T-048]]"
  - "[[WIKI-T-065]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-04
---

# Interface Role Separation

## Knowledge Card

The paper uses "interface" in three distinct mathematical roles.  These roles
must not be collapsed into a single variable:

| Role | Object | Contract |
|---|---|---|
| Conservative transport | `psi = H_epsilon(-phi)` | Advect in conservative form; measure volume/mass drift. |
| Metric geometry | `phi` or Ridge--Eikonal reconstructed distance | Maintain signed-distance quality and nearest-interface geometry. |
| Interface stress | `n_lg`, `kappa_lg`, `j_gl` | Apply oriented Young--Laplace pressure jump. |

The oriented stress convention is:

```text
psi = 1 liquid, psi = 0 gas
n_lg = liquid-to-gas normal
kappa_lg = div n_lg
j_gl = p_gas - p_liquid = -sigma kappa_lg
```

## Why It Matters

Several common mistakes are role-confusion errors:

- Improving Eikonal quality does not automatically prove mass conservation.
- Conservative `psi` transport does not by itself prove accurate curvature.
- Pointwise `psi` curvature invariance does not imply a discrete capillary
  energy law.
- A pressure jump is not a smooth nodal pressure field; it is an oriented
  interface-stress datum.

This card should be checked before modifying CLS reinitialization, curvature,
pressure-jump signs, or claims about volume conservation.

## Paper-Derived Rule

Repair one interface role at a time, and state which role the evidence covers.
Do not let a mass result, an Eikonal result, or a curvature result silently
stand in for the other two.
