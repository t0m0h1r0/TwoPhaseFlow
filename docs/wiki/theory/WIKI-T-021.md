---
ref_id: WIKI-T-021
title: "IIM-CCD: Immersed Interface Method for High-Order Pressure Solver"
domain: T
status: ACTIVE
superseded_by: null
sources:
  - path: docs/memo/iim_ccd_note.tex
    git_hash: e62cd50
    description: "IIM correction for CCD PPE: RHS correction using known jump [p]=σκ, validation on static droplet"
consumers:
  - domain: L
    usage: "Future split-PPE solver with explicit pressure jump handling"
  - domain: A
    usage: "Alternative to HFE for interface-crossing pressure treatment"
depends_on:
  - "[[WIKI-T-001]]"
  - "[[WIKI-T-012]]"
  - "[[WIKI-T-018]]"
compiled_by: KnowledgeArchitect
verified_by: null
compiled_at: 2026-04-08
---

## Problem

CCD achieves O(h⁶) for smooth fields but breaks down when the field is discontinuous at the interface — as for pressure in two-phase flow with [p] = σκ.

Standard hybrid strategy: fall back to 2nd-order FD within 2–3 cells of interface, retain CCD elsewhere. This sacrifices high-order accuracy at the interface where it matters most.

## IIM-CCD Approach

Apply Immersed Interface Method corrections directly to the assembled CCD operator. Preserves O(h⁶) everywhere without rederiving CCD coefficients.

### Correction Procedure

For grid points whose stencil crosses Γ, add a RHS correction based on the known jump conditions:

[p] = σκ (pressure jump)
[1/ρ · ∂p/∂n] = 0 (flux continuity)

The correction modifies only the RHS vector b of the linear system L_CCD p = b, not the operator matrix itself. The Kronecker-product assembly (see [[WIKI-T-012]]) remains unchanged.

### Key Result

Static droplet validation: Laplace pressure error reduced by 2–3× compared to hybrid FD/CCD baseline.

## Current Status

**Implemented but insufficient as standalone fix.** The RHS correction alone cannot fully compensate when the CCD stencil spans a sharp discontinuity — the operator matrix eigenvalues become problematic (positive eigenvalues from boundary stencil asymmetry).

**Recommended path:** Combine with HFE ([[WIKI-T-018]]) or use split-PPE where each phase has its own smooth pressure field.
