---
ref_id: WIKI-L-049
title: "Ch14 q-Manifold Vectorized Geometry Parity PASS"
domain: code
status: ACTIVE
tags: [ch14, q_manifold, vectorization, closed_radial_chart, parity, runtime_gate]
sources:
  - path: artifacts/A/ch14_vectorized_projection_parity_CHK-RA-CH14-VAR-013.md
    description: "Vectorized parity implementation, review, and validation"
  - path: src/twophase/tests/test_q_manifold_projection.py
    description: "Scalar-vs-batch closed radial geometry parity test"
depends_on:
  - "[[WIKI-L-048]]"
  - "[[WIKI-E-067]]"
consumers:
  - domain: code
    usage: "Use before adding runtime adapters or batched projection paths"
  - domain: experiment
    usage: "Use before short runtime admission probes that assume vectorized geometry"
compiled_by: ResearchArchitect
compiled_at: 2026-05-17
---

# Ch14 q-Manifold Vectorized Geometry Parity PASS

## Knowledge Card

Closed radial chart geometry now has a scalar-vs-batch parity gate for:

- vertices and radius;
- polygon surface length and area;
- surface-energy covector `dE`;
- area covector `dA`.

This keeps vectorization as an execution layout, not a new theory:

```text
Gamma_h owner -> q_phys = Q_h(Gamma_h) -> r
```

## Validation

Command:

```text
make test PYTEST_ARGS='twophase/tests/test_q_manifold_projection.py -q'
```

Result: PASS.  The make target ran the remote suite:

```text
804 passed, 35 skipped
```

## Usage

Before runtime admission, use this card to check that batched chart geometry
does not change `E`, `A`, `dE`, or `dA`.  This card does not authorize T/8,
force coupling, GPU `Q_h`, or all-cell `q` exactness.
