---
ref_id: WIKI-L-046
title: "Theory-Established Implementation Review Gate"
domain: code
status: ACTIVE
tags: [implementation_review, a3_traceability, fail_close, gpu, defect_correction, hfe, ch14]
sources:
  - path: docs/02_ACTIVE_LEDGER.md
    description: "CHK-RA-CH14-AO-FASTVOL-071 and follow-up review-failure RCA"
  - path: docs/wiki/cross-domain/WIKI-X-051.md
    description: "Theory-first RCA and countermeasure protocol"
  - path: docs/wiki/cross-domain/WIKI-X-050.md
    description: "Nonuniform-grid and interface-tracking rebuild review gates"
  - path: docs/wiki/code/WIKI-L-043.md
    description: "GPU transfer-boundary hygiene"
  - path: docs/wiki/code/WIKI-L-045.md
    description: "AO-Fast GPU efficiency and face-cochain unit lessons"
depends_on:
  - "[[WIKI-X-051]]"
  - "[[WIKI-X-050]]"
  - "[[WIKI-L-033]]"
  - "[[WIKI-L-037]]"
  - "[[WIKI-L-043]]"
  - "[[WIKI-L-045]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-15
---

# Theory-Established Implementation Review Gate

## Knowledge Card

When the physics and mathematics are already established, an implementation
mistake is usually not caused by lack of theory.  It is caused by failing to
turn that theory into an executable code contract before editing and reviewing.

For established theory, review must not ask only whether the local patch looks
reasonable.  It must prove that every symbol in the equation has the same
producer, consumer, metric, boundary condition, time level, backend residency,
and invalidation epoch throughout the production route, diagnostics, YAML, and
tests.

## Root Cause

The recent near-careless defects came from a repeated review blind spot:

- A3 traceability stopped at the headline equation, not at the per-face,
  per-cell, per-time-level discrete object.
- The high-order operator, low-order defect-correction base, RHS transform,
  corrector, builder/factory, YAML, diagnostic, and runner were reviewed in
  pieces instead of as one operator identity.
- Missing context silently selected an older default law in some paths.  A
  configured physical route must fail closed when required context is absent.
- Diagnostics were allowed to carry defaults that differed from production
  YAML, so a probe could pass while the real route failed.
- GPU optimization was reviewed for transfer count and launch granularity
  before ownership, aliasing, and metric/rebuild epochs were formalized.
- Reviews did not include negative tests that intentionally remove context,
  use nonuniform/periodic faces, or cross an interface-tracking rebuild.

This is a process/design failure, not a theory failure and not a reason to
apply tolerances, offsets, damping, solver-family substitutions, or visual
patches.

## Mandatory Coding Gate

Before coding against established theory, write the contract table first:

| Contract Field | Required Answer |
|---|---|
| Theory object | Equation symbol or invariant being implemented |
| Discrete object | Cell, face, node, graph, pressure range, or cochain space |
| Producer | Function/module that creates it |
| Consumer | Every function/module that uses it |
| Metric | Nonuniform width, face length, Hodge weight, density, or resistance |
| Boundary path | Interior, wall, periodic seam, cut face, and interface crossing |
| Time level | Predictor, pressure-history, corrector, rebuild, or snapshot epoch |
| Backend | CPU/GPU object type and allowed host/device transfers |
| Invalidation | Grid, density, phase, gauge, pressure-history, or solver-analysis epoch |
| Fail-close | Exact condition that must raise instead of defaulting |
| Regression | Smallest test that would catch a wrong implementation |

Do not implement until the table identifies all producers and consumers.  If
one consumer is unknown, the change is not ready.

## Review Questions

Every review of an established-theory change must answer:

- Where does the same theory object appear outside the modified file?
- Does the low-order/base/preconditioner operator approximate the same
  physical operator as the high-order route?
- Are RHS transforms, pressure-history terms, and corrector subtraction using
  the same coefficient, sign, gauge, and time level?
- Does every nonuniform-grid, periodic, wall, cut-face, and rebuild path use
  the same metric contract?
- What happens when the configured route lacks required context: fail closed
  or silently fall back?
- Do diagnostics default to production YAML behavior, or do they create a
  different mathematical problem?
- Is every GPU copy/synchronization an ownership or reporting boundary, not an
  accidental control dependency?

If any answer is missing, the review has not checked the implementation.

## Required Tests

For solver/operator changes, add tests in the same patch that cover:

- operator identity between high-order and low-order/base paths on the same
  physical coefficients;
- nonuniform metric and periodic seam cases, not only uniform interior cases;
- interface-crossing or cut-face cases when HFE or phase separation is active;
- absent required context raising fail-closed instead of defaulting;
- runner and diagnostic parity for pressure history, initial grid rebuild,
  grid-rebuild reset, and YAML-selected scheme;
- backend parity or exact fused-vs-unfused algebra for GPU-optimized kernels;
- stale epoch rejection after grid, phase, density, or pressure-history rebuild.

Tests must catch the contract violation, not merely the final observed symptom.

## Negative Knowledge

Do not call a review complete because:

- a short experiment passes;
- the modified function looks locally correct;
- a diagnostic passes under a default not used by YAML;
- the GPU route has fewer transfers;
- a solver reaches a smaller residual after increasing iterations;
- visual output looks smoother.

These are evidence only after the equation-to-code contract has been checked.

## Coding Recall

When implementing established theory, first say: "What is the discrete object,
who owns it, who consumes it, and what fails closed if it is missing?"

Only then edit code.
