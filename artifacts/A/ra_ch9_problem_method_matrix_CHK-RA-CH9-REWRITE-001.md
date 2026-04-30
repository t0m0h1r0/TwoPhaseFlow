# CHK-RA-CH9-REWRITE-001 — Chapter 9 problem/method matrix

- Worktree: `.claude/worktrees/ra-938-affine-audit-20260430`
- Branch: `ra-938-affine-audit-20260430`
- Trigger: user reported that Chapter 9 appears to contain multiple methods
  that collide with each other, and requested decomposition, selection of
  essential problems, a rewritten narrative, and code implementation.

## Core Diagnosis

Chapter 9 currently mixes three categories at nearly equal narrative weight:

1. production requirements that are essential for the two-phase pressure
   closure;
2. legacy or comparison methods that were useful historically but are not the
   accepted route; and
3. implementation mechanisms that are only valid when attached to the selected
   production route.

The confusion comes from presenting "CCD-PPE", "CSF balanced force",
"smoothed-Heaviside variable-density PPE", "split PPE", "GFM/HFE",
"jump_decomposition", "affine_jump", "FVM baseline", and "defect correction"
as if they were peer alternatives.  They are not peers.  They answer different
questions.

## Essential Problem Selection

| ID | Candidate problem | Essential? | Decision |
|---|---|---:|---|
| P1 | Enforce incompressibility through a PPE consistent with the predictor/corrector | yes | keep as the chapter root |
| P2 | Density and pressure jumps make cross-interface stencils non-smooth | yes | solve by phase-separated coefficient plus one-sided/HFE data |
| P3 | Surface tension must enter as the oriented Young--Laplace jump, not a smeared body force | yes | solve by affine interface-stress closure |
| P4 | Pressure and capillary terms must share the same discrete face operator | yes | solve by `G_Gamma(p;j)=G(p)-B(j)` and matched corrector |
| P5 | High-order phase-local pressure evaluation needs smooth ghost/extended data | yes | solve by HFE |
| P6 | High-order PPE evaluation is expensive if solved directly | yes | solve by defect correction: high-order target, cheaper invertible base |
| P7 | Phase-separated Neumann solves have null spaces and regrid context hazards | yes | solve by phase mean gauge and no jump context in reproject PPE |
| P8 | Smoothed-Heaviside monolithic variable-density PPE can be made universally high-order | no | reject as production claim; keep as low/mid-density comparison |
| P9 | CSF body force plus balanced-force operator is the final capillary method | no | keep as motivation/history; production capillary closure is pressure jump |
| P10 | `jump_decomposition` is an equivalent pressure-jump implementation | no | keep as explicit legacy comparison only |
| P11 | CCD Kronecker/LU is the integration-test production PPE | no | keep as smooth manufactured/component reference only |
| P12 | FVM/FD pressure solve is a proposed fix for CCD pressure issues | no | keep as low-order base/comparison, not the research closure |

The reduced essential set is therefore:

```text
PPE root -> phase separation -> oriented affine jump -> HFE -> defect correction
         -> gauge/reprojection guards -> validation
```

Everything else is a baseline, a legacy route, or a local implementation aid.

## Adopted Narrative

The chapter should read as a narrowing decision tree:

1. Start from the pressure problem: the projection must make velocity
   divergence-free while preserving interfacial normal stress.
2. Reject monolithic smoothed-density PPE as a production high-density route
   because it differentiates through the density jump and damages conditioning.
3. Reject explicit CSF as the final capillary route because the pressure and
   surface-tension terms do not necessarily share the same discrete locus and
   the diffuse delta model leaves an `O(epsilon^2)` model error.
4. Reject regular pressure jump decomposition as production because the solve
   can absorb the regular jump field.
5. Select the phase-separated affine pressure-jump route:
   `j_gl=p_g-p_l=-sigma*kappa_lg`, `G_Gamma=G-B(j_gl)`.
6. Add HFE because phase-separated CCD/FCCD stencils need smooth one-sided
   data.
7. Add defect correction because the high-order target operator is evaluated
   accurately while the base solve remains robust.
8. Add gauge and reproject guards because phase-separated pressure solves are
   only unique up to phase constants and regrid projection must not inherit
   capillary jumps.

## Code Consequence

The code must encode the same decision tree.  The main inconsistency found in
the runtime layer is that omitted `poisson.operator.interface_coupling` with
`coefficient: phase_separated` defaults to `jump_decomposition`, even though
the paper and ch14 validation now identify `affine_jump` as the production
route.

Required code change:

```text
phase_separated default interface_coupling: affine_jump
aliases pressure_jump/interface_stress/jump_aware: affine_jump
jump_decomposition: still accepted only when explicitly requested
```

This preserves tested legacy code while preventing new configs from silently
selecting the rejected regular-jump path.

## SOLID Audit

[SOLID-X] No class-boundary issue in the diagnosis.  The required code change
is config canonicalization only; it does not delete `jump_decomposition` or
change the numerical operator implementation.
