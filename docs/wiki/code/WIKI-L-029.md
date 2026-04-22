---
ref_id: WIKI-L-029
title: "FCCD Weight Staleness after In-Place Grid Rebuild: update_weights() Protocol"
domain: code
status: ACTIVE
superseded_by: null
sources:
  - path: src/twophase/ccd/fccd.py
    description: "FCCDSolver._precompute_weights, _weights list"
  - path: src/twophase/simulation/gradient_operator.py
    description: "FCCDDivergenceOperator.update_weights"
  - path: src/twophase/simulation/ns_pipeline.py
    description: "_rebuild_grid — calls update_weights after grid rebuild"
consumers:
  - domain: T
    usage: "WIKI-T-068 §3"
depends_on:
  - "[[WIKI-T-046]]: FCCD"
  - "[[WIKI-E-020]]: Grid Rebuild Frequency Calibration"
tags: [fccd, grid-rebuild, stale-cache, update_weights, weights]
compiled_by: ResearchArchitect
verified_by: null
compiled_at: 2026-04-23
---

# FCCD Weight Staleness after In-Place Grid Rebuild

## §1 The stale-weights bug

`FCCDSolver.__init__` precomputes geometric weights once:

```python
self._weights = [self._precompute_weights(ax) for ax in range(self.ndim)]
```

These store per-axis arrays: `H` (face spacings), `inv_H`, `H_sq_over_16`, `H_over_16_node`, etc., derived from `grid.coords` at construction time.

When `_rebuild_grid` calls `grid.update_from_levelset(psi)`, it mutates `grid.coords` **in-place** (the grid object is the same Python object; only its internal arrays change). `FCCDSolver._weights` is NOT automatically refreshed — it still holds the old geometry arrays. All subsequent `face_value()` and `face_divergence()` calls silently use stale weights.

## §2 Manifestation

With rebuild schedule `every_step`, every step uses stale weights from the previous step's geometry. For a slowly-moving interface this is a small $O(\Delta t)$ error per step but accumulates. After many steps it contributes to div_u growth and eventually to blowup.

## §3 Fix: update_weights() protocol

`FCCDDivergenceOperator` exposes:

```python
def update_weights(self) -> None:
    self._fccd._weights = [
        self._fccd._precompute_weights(ax)
        for ax in range(self._fccd.ndim)
    ]
```

In `ns_pipeline._rebuild_grid`, after `self._ppe_solver.invalidate_cache()`:

```python
if hasattr(self._div_op, "update_weights"):
    self._div_op.update_weights()
```

This refreshes all FCCD geometric weights to the new grid geometry before the next step's `face_value`/`face_divergence` calls.

## §4 Scope

The same staleness affects `FCCDGradientOperator`, `FCCDLevelSetAdvection`, and `FCCDConvectionTerm` — they all share the same `FCCDSolver` instance via `self._fccd`. The `update_weights()` call on `FCCDDivergenceOperator` refreshes `self._fccd._weights`, which is the **shared** instance, so all consumers are fixed by a single call.

Note: `FCCDSolver` does not implement `update_grid` (unlike `CCDSolver`, `PPESolver`, `Reinit`). The `update_weights()` call is the lightweight equivalent — no re-factorization needed since FCCD weights are pure geometry (no matrix inversion), so recomputation is cheap ($O(N)$ per axis).
