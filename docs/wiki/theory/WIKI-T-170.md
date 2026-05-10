---
ref_id: WIKI-T-170
title: "Residual-Minimizing Defect Correction for PPE"
domain: theory
status: ACTIVE
tags: [ppe, defect_correction, residual_minimization, rising_bubble, hodge_projection, gpu]
sources:
  - path: artifacts/A/ch14_rising_bubble_blowup_ppe_dc_rca_CHK-RA-CH14-BUBBLE-PPE-DC-001.md
    description: "Rising-bubble blow-up RCA, hypothesis matrix, one-step probes, and implemented fix"
depends_on:
  - "[[WIKI-T-005]]"
  - "[[WIKI-T-015]]"
  - "[[WIKI-T-063]]"
  - "[[WIKI-T-164]]"
  - "[[WIKI-T-166]]"
  - "[[WIKI-T-167]]"
consumers:
  - domain: code
    usage: "Defect correction may not accept a pressure update that increases the discrete PPE residual"
  - domain: experiment
    usage: "Interpret rising-bubble stability only together with PPE residual and divergence diagnostics"
  - domain: paper
    usage: "Do not claim benchmark validity from visual stability alone"
compiled_by: ResearchArchitect
compiled_at: "2026-05-10"
---

# Residual-Minimizing Defect Correction for PPE

## Contract

For a discrete pressure operator `A`, right-hand side `b`, and pressure iterate
`p`, defect correction must be judged against the residual

```text
r(p) = b - A p.
```

Given a base correction `delta`, the admissible scalar update along that
direction is governed by

```text
alpha_* = <r, A delta> / <A delta, A delta>.
```

If `alpha_* > 0`, it is the exact minimizer of

```text
||r - alpha A delta||_2^2
```

along the correction direction.  A defect-correction implementation may use
backtracking candidates, but it must not accept an update unless the discrete
PPE residual decreases.

## Reason

The Chapter 14 rising-bubble blow-up showed that a fixed relaxation can amplify
pressure in late high-density-ratio affine-jump states.  Increasing the number
of fixed-relaxation corrections made the failure worse, not better.  This means
iteration count was not the missing ingredient; residual monotonicity was the
missing contract.

The pressure correction is part of the incompressibility projection and Hodge
force balance.  A residual-growing pressure update is not a harmless solver
error: it injects an unphysical acceleration cochain and can dominate capillary,
buoyancy, and transport diagnostics.

## Hodge-Metric Companion Contract

External component saddle systems must be assembled in the projected Hodge
metric:

```text
G_ij = <H c_i, H c_j>_M,
b_i  = <H c_i, H raw>_M.
```

Using `<c_i, H c_j>_M` is algebraically equivalent only when the projection is
exactly self-adjoint.  With an inexact pressure projection it can produce a
negative one-component denominator.  The denominator sign is then a contract
failure, not a physical capillary result.

## Negative Knowledge

Do not accept as production fixes:

- increasing `max_corrections` under a residual-growing fixed relaxation;
- case-tuned fixed relaxation constants;
- curvature caps, smoothing, CFL shrinkage, or visual damping to hide pressure
  residual growth;
- fallback PPE solver branches selected only for the rising-bubble case;
- benchmark acceptance from kinetic-energy or volume improvement alone.

The minimum acceptance set includes residual decrease, divergence control,
Hodge metric positivity, volume consistency, and the force/projection ledger.

## Verification Pattern

Efficient RCA should use this order:

1. inspect time-history diagnostics for the first residual, divergence, and
   pressure-growth signal;
2. run one-step probes from the last good and pre-blowup checkpoints;
3. manufacture an overscaled base correction to prove residual-minimizing step
   selection;
4. manufacture an oblique projection to prove positive Hodge Gram assembly;
5. only then rerun the full benchmark.
