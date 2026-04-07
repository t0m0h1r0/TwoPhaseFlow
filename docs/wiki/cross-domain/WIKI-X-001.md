---
ref_id: WIKI-X-001
title: "DCCD Usage Map: Three Modes Across the Algorithm"
domain: cross-domain
status: ACTIVE
superseded_by: null
sources:
  - path: paper/sections/04d_dissipative_ccd.tex
    git_hash: 7328bf1
    description: "DCCD filter definition, switch function"
  - path: paper/sections/07_advection.tex
    git_hash: 7328bf1
    description: "CLS advection: uniform eps_d=0.05, no S(psi)"
  - path: paper/sections/08_collocate.tex
    git_hash: 7328bf1
    description: "Checkerboard suppression: eps_d=1/4"
  - path: paper/sections/10b_implementation_details.tex
    git_hash: 7328bf1
    description: "Adaptive control: eps_d = eps_max * S(psi), spectral design"
consumers:
  - domain: L
    usage: "All DCCD call sites must use correct mode and parameters"
  - domain: A
    usage: "Cross-reference map for paper narrative (recommended for S10)"
  - domain: E
    usage: "Filter parameters affect convergence rates"
depends_on:
  - "[[WIKI-T-002]]"
compiled_by: KnowledgeArchitect
compiled_at: 2026-04-07
---

## Overview

DCCD (Dissipative CCD) filter appears in 4 chapters with 3 distinct parameter regimes. This entry provides the consolidated cross-algorithm usage map.

## Three Parameter Modes

### Mode 1: Adaptive (Velocity/Pressure Fields)

| Parameter | Value |
|-----------|-------|
| eps_d | eps_{d,max} * S(psi_i) = 0.05 * (2*psi_i - 1)^2 |
| S(psi) control | YES |
| At interface (psi=0.5) | eps_d = 0 (no dissipation) |
| In bulk (psi=0 or 1) | eps_d = 0.05 (full) |
| Applied to | u, v velocity components; pressure gradient evaluation |
| Purpose | Suppress aliasing in smooth bulk regions; preserve sharp interface |
| Defined in | S4 (sec:dccd_switch), S10 (sec:dccd_adaptive) |

### Mode 2: Uniform (CLS Advection/Reinitialization)

| Parameter | Value |
|-----------|-------|
| eps_d | 0.05 (constant, all grid points) |
| S(psi) control | NO |
| Applied to | CLS advection flux (psi' in d(psi)/dt + u*psi' = 0) |
|  | CLS reinitialization compression flux |
|  | Curvature evaluation |
| Purpose | Stabilize interface-crossing advection; S(psi)=0 at interface would disable filter exactly where needed |
| Defined in | S7 (sec:advection_dccd_design, eq:eps_adv), S7b (sec:cls_compression) |

**Design contradiction**: Mode 1 disables filter at interface for accuracy; Mode 2 enables it at interface for stability. Resolution: the CLS profile psi itself IS the interface variable — it requires dissipation to remain stable during advection.

### Mode 3: Checkerboard Kill (PPE RHS)

| Parameter | Value |
|-----------|-------|
| eps_d | 1/4 (maximum stable value) |
| S(psi) control | NO |
| Applied to | Predicted velocity divergence before PPE RHS computation |
|  | Corrector divergence |
| Purpose | Eliminate collocated-grid pressure-velocity decoupling |
| Defined in | S8 (sec:dccd_decoupling, eq:dccd_eps_checkerboard) |

## Algorithm Step Mapping

| Algorithm Step (S10) | DCCD Mode | eps_d |
|---------------------|-----------|-------|
| Step 1: CLS advection | Mode 2 (uniform) | 0.05 |
| Step 2: CLS reinitialization | Mode 2 (uniform) | 0.05 |
| Step 3: Property update | None | — |
| Step 4: Curvature | Mode 2 (uniform) | 0.05 |
| Step 5: Predictor | Mode 1 (adaptive) | 0.05*S(psi) |
| Step 6: PPE (RHS divergence) | Mode 3 (checkerboard) | 1/4 |
| Step 7: Corrector (divergence check) | Mode 3 (checkerboard) | 1/4 |

## Pressure Filter Prohibition

DCCD must NEVER be applied directly to the pressure field p. Filtering p destroys the divergence-free projection property. Approved alternatives:
1. Filter the pressure gradient (grad(p)), not p itself
2. Regularize PPE RHS before solving

See sec:dccd_pressure_nofilt (08c_pressure_filter.tex).

## Paper Narrative Note

This cross-cutting information is scattered across S4, S7, S8, and S10. The scheme_roles table in S7 partially consolidates but precedes S8-S9 content. Recommendation: add a consolidated table in S10 near sec:dccd_params. See [[WIKI-P-001]] ISSUE-6.
