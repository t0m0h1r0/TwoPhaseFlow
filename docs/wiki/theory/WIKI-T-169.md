---
ref_id: WIKI-T-169
title: "Geometric Cell Fraction State-Space Reformulation"
domain: theory
status: PROPOSED
tags: [geometric_cell_fraction, clsvof, volume_conservation, common_flux, capillary_hodge, gpu]
sources:
  - path: artifacts/A/geometric_cell_fraction_theory_CHK-RA-GEOM-CELL-FRACTION-001.md
    description: "ResearchArchitect theory artifact for geometric cell fraction reformulation"
  - path: artifacts/A/ch14_reinit_volume_priority_theory_CHK-RA-REINIT-VOLUME-PRIORITY-001.md
    description: "Volume-first reinitialization theory motivating geometric fractions as long-term route"
depends_on:
  - "[[WIKI-T-156]]"
  - "[[WIKI-T-159]]"
  - "[[WIKI-T-160]]"
  - "[[WIKI-T-162]]"
  - "[[WIKI-T-164]]"
  - "[[WIKI-T-168]]"
consumers:
  - domain: theory
    usage: "Use as the target formulation when replacing diffuse/nodal phase volume by geometric cell fractions"
  - domain: code
    usage: "Do not implement geometric fractions as diagnostics only; migrate carrier, transport, capillary, and common-flux contracts together"
  - domain: paper
    usage: "Use when rewriting the CLS/VOF position of the method around a geometric conservative carrier"
compiled_by: ResearchArchitect
compiled_at: "2026-05-10"
---

# Geometric Cell Fraction State-Space Reformulation

## Claim

Geometric cell fraction is a state-space reformulation, not a plotting or
diagnostic improvement.  The physical phase volume should become

```text
V_h(F) = sum_C |C| F_C,
F_C = |C cap Omega_l| / |C|.
```

Then the sharp geometry volume and conservative finite-volume material volume
are the same discrete functional.

## Root Problem

The current CLS theory uses a diffuse/nodal indicator:

```text
psi = H_eps(-phi),
V_h^psi = sum_nodes psi_i W_i.
```

Sharp capillary geometry uses a different object:

```text
V_h^Gamma(phi) = |Omega_{l,h}(phi)|.
```

Trying to preserve both as hard constraints can make reinitialization
infeasible.  The correct cure is not wider brackets, damping, smoothing,
fallbacks, or case branches.  The cure is selecting one physical volume
functional.  Geometric cell fractions are the route where the sharp geometry
volume and the conservative mass volume become identical.

## Target State

```text
F_C        geometric liquid cell fraction, hard conservative carrier
m_C(F)     material mass
p/u_f      common-flux momentum or face velocity state
phi        reconstructed level-set gauge, not the material volume carrier
I_h        reconstructed interface complex
```

Required identities:

```text
V_h(F) = sum_C |C| F_C = |Omega_{l,h}(I_h)|,
S_h    = surface measure of I_h,
rho_C  = rho_g + (rho_l-rho_g) F_C.
```

Capillary, gravity, pressure projection, checkpoint/restart, and visualization
must read from this same state, or from declared adjoint maps of it.

## Accepted Direction

Use a geometric CLSVOF route:

1. `F_C` is the hard material volume.
2. `phi` remains a smooth gauge for normals, curvature, HFE, and plots.
3. PLIC/cut geometry with level-set normals reconstructs a per-cell interface
   matching `F_C`.
4. Geometric swept-volume fluxes update `F_C`.
5. The common-flux momentum ledger uses that same phase flux.
6. Capillary force is the variational derivative of the same reconstructed
   surface and volume pair.

## Verification Gates

Before production implementation:

```text
G1: sum_C F_C |C| equals reconstructed sharp volume.
G2: geometric swept-volume flux is conservative and bounded.
G3: static droplet Young--Laplace Hodge residual is zero in the chosen metric.
G4: nonconstant-curvature interfaces produce nonzero capillary drive.
G5: common-flux mass and momentum use the same phase flux.
G6: nonuniform, wall, and periodic geometry is counted in physical coordinates exactly once.
```

## Negative Knowledge

Do not accept:

- geometric fractions used only in plots;
- global mass correction after non-geometric transport;
- independent hard preservation of sharp volume and diffuse nodal mass;
- clipping without a conservative flux ledger;
- density from `F_C` but capillary or gravity from diffuse `psi`;
- CCD/FCCD differentiation of discontinuous `F_C` as a smooth field;
- visual long-run success before manufactured geometry and one-step flux gates.
