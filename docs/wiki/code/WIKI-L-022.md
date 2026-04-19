---
ref_id: WIKI-L-022
title: "G^adj FVM-Consistent Pressure Gradient: Implementation in ns_pipeline.py"
domain: code
status: ACTIVE
superseded_by: null
sources:
  - path: src/twophase/simulation/ns_pipeline.py
    description: _precompute_fvm_grad_spacing(), _fvm_pressure_grad(), velocity corrector guard
depends_on:
  - "[[WIKI-T-044]]: FVM-CCD Metric Inconsistency Theory"
  - "[[WIKI-L-001]]: Algorithm Flow: 7-Step Time Integration Loop"
  - "[[WIKI-L-015]]: CuPy / GPU Backend Unification"
tags: [ns_pipeline, pressure_gradient, non_uniform_grid, FVM, GPU, velocity_corrector]
compiled_by: Claude Sonnet 4.6
compiled_at: "2026-04-19"
---

# G^adj FVM-Consistent Pressure Gradient: Implementation in ns_pipeline.py

## Context in the Pipeline

The 7-step projection loop (WIKI-L-001) includes:

```
Step 5 — Corrector: u = u* - (dt/rho) * grad(p)
```

On non-uniform grids, replacing `grad(p)` from CCD with the FVM face-average gradient
G^adj eliminates the metric inconsistency that causes kinetic energy blowup at ~50 steps
(see WIKI-T-044).

---

## Precomputation: `_precompute_fvm_grad_spacing`

Called once from `_rebuild_grid` when `not self._grid.uniform`.

```python
def _precompute_fvm_grad_spacing(self) -> None:
    import numpy as _np
    xp = self._backend.xp
    self._d_face_grad: list = []
    for ax in range(self._grid.ndim):
        d = _np.diff(_np.asarray(self._grid.coords[ax]))  # shape (N,)
        shape = [1] * self._grid.ndim
        shape[ax] = -1
        self._d_face_grad.append(xp.asarray(d.reshape(shape)))
```

- `self._grid.coords[ax]` has length N+1 (node coordinates including both walls)
- `d_face[i] = coords[i+1] - coords[i]` for i in 0..N-1
- Reshaped for broadcasting: axis=0 → (N, 1), axis=1 → (1, N)
- **Backend**: `self._backend.xp` (not `self.xp`) — `TwoPhaseNSSolver` has no `.xp` shortcut

---

## Gradient Method: `_fvm_pressure_grad`

```python
def _fvm_pressure_grad(self, p: "array", ax: int) -> "array":
    """Face-average gradient: J_face = 1/d_face, consistent with L_FVM and GFM."""
    xp = self._backend.xp
    d = self._d_face_grad[ax]       # shape (N,) broadcast-ready
    N = self._grid.N[ax]

    def sl(start, stop):
        s = [slice(None)] * self._grid.ndim
        s[ax] = slice(start, stop)
        return tuple(s)

    g_face = (p[sl(1, N + 1)] - p[sl(0, N)]) / d        # face gradients, shape (N,)
    g = xp.zeros_like(p)
    g[sl(1, N)] = 0.5 * (g_face[sl(0, N - 1)] + g_face[sl(1, N)])  # interior avg
    # Boundaries remain 0: wall Neumann dp/dn=0
    return g
```

### Index Map (1D, N interior nodes + 2 ghost/wall nodes)

```
p:      [p_0, p_1, ..., p_N, p_{N+1}]   length N+2
g_face: [f_0, f_1, ..., f_{N-1}]        length N   (f_i = (p[i+1]-p[i])/d[i])
g:      [0,   g_1, ..., g_N,   0  ]     length N+2
         ^-- wall           wall --^
g[i] = 0.5*(f[i-1] + f[i])  for i=1..N
```

---

## Velocity Corrector Guard

Location: `_project_velocity` (or equivalent corrector block), replacing the CCD differentiation:

```python
# ── 5. Corrector ─────────────────────────────────────────────────
if not self._grid.uniform and self.bc_type == "wall":
    dp_dx = self._fvm_pressure_grad(p, 0)
    dp_dy = self._fvm_pressure_grad(p, 1)
else:
    dp_dx, _ = ccd.differentiate(p, 0)
    dp_dy, _ = ccd.differentiate(p, 1)
    if self.bc_type == "wall":
        ccd.enforce_wall_neumann(dp_dx, 0)
        ccd.enforce_wall_neumann(dp_dy, 1)

u = u_star - dt / rho * dp_dx + dt * f_x / rho
v = v_star - dt / rho * dp_dy + dt * f_y / rho
```

Guard conditions:
- `not self._grid.uniform`: avoids unnecessary path change for uniform grids (CCD = G^adj there)
- `self.bc_type == "wall"`: periodic BC does not need this fix (capwave tests unaffected)

---

## Backend Note

`TwoPhaseNSSolver` does not expose a `.xp` property. Always use `self._backend.xp` in these methods.
Using `self.xp` raises `AttributeError` immediately at simulation start.

---

## Commits

| Hash | Description |
|------|-------------|
| f61e0cd | `fix(ns_pipeline): FVM-consistent pressure gradient for non-uniform grids` |
| 4706f37 | `fix(ns_pipeline): use self._backend.xp in FVM gradient methods` |

Branch: `gfm-nonuniform` (worktree: `TwoPhaseFlow-gfm-nonuniform`)
