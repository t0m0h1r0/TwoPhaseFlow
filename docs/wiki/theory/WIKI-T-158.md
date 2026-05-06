---
ref_id: WIKI-T-158
title: "Pressure-Hodge Visualization Is Fail-Closed, Not Interface-Band Masking"
domain: theory
status: ACTIVE
tags: [pressure, hodge_representative, affine_jump, visualization, fail_closed]
sources:
  - path: docs/memo/short_paper/SP-AE_pressure_hodge_static_droplet_lessons.md
  - path: src/twophase/tools/plot_snapshot_figures.py
  - path: experiment/ch14/config/README.md
  - path: docs/02_ACTIVE_LEDGER.md
depends_on:
  - "[[WIKI-T-153]]"
  - "[[WIKI-T-154]]"
  - "[[WIKI-X-041]]"
---

# Pressure-Hodge Visualization Is Fail-Closed

## Claim

An affine pressure-jump run must visualize pressure through a Hodge
representative reconstructed from the saved face pressure cochain.  Masking the
fitted interface band as "undefined" is not a conservative visualization; it
hides the representative that should be audited.

## Contract

Use:

```text
pressure_accel_faces -> phase-wise Hodge pressure representative
```

Do not use:

```text
raw pressure -> NaN mask over 0.05 < psi < 0.95
```

If `pressure_accel_faces` are absent, plotting fails.  The data must be
regenerated with the current affine pressure-jump runner.

## Why

The momentum update uses face-space pressure work,

```text
a_f = A_f(G_f p - B_f(j)).
```

A raw nodal value in the fitted interface band is not the physical scalar
pressure.  But the remedy is not to delete the band.  The remedy is to recover
a scalar representative whose same-phase gradients match the stored cochain.

## Implication

Production ch14 pressure figures use `field: pressure_hodge` with
`file_prefix: pressure_t`.  `pressure_bulk` is retired as an error path, and
figure generation must not silently skip failed pressure plots.
