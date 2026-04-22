---
ref_id: WIKI-L-030
title: "FCCD face_value Amplification of Non-Smooth Fields: H²q Hazard"
domain: code
status: ACTIVE
superseded_by: null
sources:
  - path: src/twophase/ccd/fccd.py
    description: "FCCDSolver.face_value — _face_value_kernel"
  - path: src/twophase/simulation/gradient_operator.py
    description: "FCCDDivergenceOperator (project-only; NOT used for force divergence)"
consumers:
  - domain: T
    usage: "WIKI-T-068 §2"
depends_on:
  - "[[WIKI-T-046]]: FCCD"
  - "[[WIKI-T-068]]: FCCDDivergenceOperator"
tags: [fccd, face-value, non-smooth, surface-tension, amplification, hazard]
compiled_by: ResearchArchitect
verified_by: null
compiled_at: 2026-04-23
---

# FCCD face_value Amplification of Non-Smooth Fields: H²q Hazard

## §1 The formula

`FCCDSolver.face_value` computes:

$$u_f = \frac{u_i + u_{i+1}}{2} - \frac{H^2}{16}(q_i + q_{i+1})$$

where $q = \partial^2 u / \partial x^2$ is the CCD second derivative. For smooth fields
this gives 4th-order accuracy: the correction $H^2 q / 16 = O(H^4 \cdot u''''') / O(H^2)$
is small relative to the leading average.

## §2 Failure on non-smooth fields

For the surface tension force $f_x/\rho = \sigma\kappa (\partial\psi/\partial x)/\rho$:

- The level-set gradient $\partial\psi/\partial x$ has a spike of amplitude $\sim 1/\varepsilon$ near the interface
- The second derivative $q = \partial^2(f_x/\rho)/\partial x^2 \sim \sigma\kappa / (\rho \varepsilon^3)$

For a N=128 water-air run with $\varepsilon \approx 6\times10^{-3}$, $h_\text{min} \approx 5\times10^{-3}$:

$$\frac{H^2}{16} \cdot |q| \approx \frac{(5\times10^{-3})^2}{16} \cdot \frac{0.072 \cdot 4}{1.2 \cdot (6\times10^{-3})^3} \approx 1500 \gg |f_x/\rho|$$

The correction term is **three orders of magnitude larger** than the field value.
This corrupts face values → corrupts PPE RHS → wrong pressure → large velocity
correction → blowup (observed: step 1252 → step 237, a 5× regression).

## §3 Detection

A corrupted `face_value` call manifests as:
- Earlier blowup when FCCD divergence is used for the force term in the PPE RHS
- Very large `ppe_rhs_max` in step diagnostics, appearing before KE blowup
- The symptom is EARLIER blowup (not later), distinguishing it from other bugs

## §4 Safe usage rules

FCCD `face_value` is safe only for fields that are **smooth** (bounded $q$ relative to $H^2$):
- Velocity components $u$, $v$: smooth in the bulk, O(h^2) bounds on $q$ → safe
- Pressure $p$: smooth in bulk (GFM handles jumps separately) → safe
- Level-set function $\psi$: smooth by construction → safe

FCCD `face_value` is **unsafe** for:
- Surface tension force $f_x/\rho = \sigma\kappa \nabla\psi/\rho$: sharp spike → HAZARD
- Any field with O(1/h) gradients or O(1/h²) second derivatives

**Rule:** When in doubt, use FVM arithmetic averaging $(u_i + u_{i+1})/2$ for non-smooth fields.

## §5 Impact on FCCDDivergenceOperator

`FCCDDivergenceOperator.divergence([f_x/rho, f_y/rho])` must NOT be called for
surface tension forces. The operator is restricted to `project()` use only, where
FCCD face values are applied to the smooth velocity field $u^*$ and the pressure
gradient uses FVM-consistent finite differences.

See `WIKI-T-068` for the corrected design.
