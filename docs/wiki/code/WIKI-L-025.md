---
ref_id: WIKI-L-025
title: "Ridge-Eikonal Non-Uniform Reinitializer Library Module"
domain: code
status: IMPLEMENTED  # CHK-159; V1-V6 pass (GPU gated)
superseded_by: null
sources:
  - path: src/twophase/levelset/ridge_eikonal.py
    description: "NonUniformFMM, RidgeExtractor, RidgeEikonalReinitializer"
  - path: src/twophase/levelset/reinitialize.py
    description: "Reinitializer facade registers 'ridge_eikonal' Strategy branch"
  - path: src/twophase/config.py
    description: "NumericsConfig.reinit_method, NumericsConfig.ridge_sigma_0"
  - path: src/twophase/simulation/builder.py
    description: "SimulationBuilder forwards method + sigma_0 to Reinitializer"
  - path: src/twophase/tests/test_ridge_eikonal.py
    description: "V1-V6 unit tests"
  - path: experiment/ch13/config/ch13_04_capwave_ridge_alpha2.yaml
    description: "V4 end-to-end capillary-wave probe at α=2"
depends_on:
  - "[[WIKI-T-047]]: Gaussian-ξ Ridge Interface Representation (SP-B)"
  - "[[WIKI-T-048]]: Eikonal Reconstruction — Uniqueness"
  - "[[WIKI-T-049]]: Notation disambiguation (ξ_idx vs ξ_ridge vs ω(φ))"
  - "[[WIKI-T-057]]: σ_eff / ε_local spatial scaling (D1, D4)"
  - "[[WIKI-T-058]]: Physical-space Hessian (D2)"
  - "[[WIKI-T-059]]: Non-uniform FMM (D3)"
  - "[[WIKI-L-015]]: CuPy / GPU backend unification"
consumers:
  - domain: experiment
    description: "ch13_04 capillary-wave probe on α=2 stretched grid"
  - domain: paper
    description: "SP-E short paper"
tags: [ridge_eikonal, non_uniform_grid, reinitialization, fmm, gaussian, gpu_cpu_unified, library, chk_159]
compiled_by: Claude Opus 4.7
compiled_at: "2026-04-21"
chk: CHK-159
---

# Ridge-Eikonal Non-Uniform Reinitializer Library Module

## 1. Scope

CHK-159 ships `src/twophase/levelset/ridge_eikonal.py` with three additive classes implementing SP-E on interface-fitted grids. No existing module is modified except `reinitialize.py` (Strategy branch registration), `config.py` (two new fields + validator), `simulation/builder.py` (method/sigma_0 forwarding), and `levelset/__init__.py` (exports). Default `reinit_method='split'` preserves all prior runs bit-exactly.

## 2. API

### 2.1 `NonUniformFMM(grid)`

Physical-space Fast Marching. CPU-serial (heap-based Dijkstra) by construction — D3 is inherently serial, so the caller handles D2H/H2D across the GPU/CPU boundary.

| method | description |
|---|---|
| `solve(phi_np, extra_seeds=None) -> phi_sdf_np` | Returns SDF solving $\|\nabla_x\phi\|=1$ with physical-space quadratic (§6.2) and caustic fallback. `extra_seeds` accepts iterable of `(i, j, d)` physical-distance anchors (e.g., ridge cells). |

### 2.2 `RidgeExtractor(backend, grid, sigma_0=3.0, h_ref=None)`

Computes $\xi_\text{ridge}$ and the ridge admissibility mask on the GPU/CPU device via `backend.xp`.

| property / method | description |
|---|---|
| `sigma_eff` | Pre-computed spatial field $\sigma_\text{eff}(x)=\sigma_0\cdot h(x)/h_\text{ref}$ (D1). |
| `compute_xi_ridge(phi) -> xi_field` | Vectorised Gaussian sum over sub-cell interface crossings. |
| `extract_ridge_mask(xi) -> bool_field` | Local-max test + physical-space FD Hessian sign test + gradient-small tolerance. |

### 2.3 `RidgeEikonalReinitializer(backend, grid, ccd, eps, sigma_0=3.0, eps_scale=1.4, mass_correction=True, h_ref=None)`

Implements `IReinitializer`. End-to-end orchestrator: ψ → φ → ridge → FMM → sigmoid → mass-corrected ψ.

| method | description |
|---|---|
| `reinitialize(psi) -> psi_new` | Full SP-E pipeline; preserves input shape; output ∈ [0, 1]. |

## 3. Configuration switch

```yaml
# NumericsConfig
reinit_method: ridge_eikonal       # default 'split' — bit-exact compat
ridge_sigma_0:  3.0                # D1 σ₀ in h_ref cells
```

Activated `Reinitializer(method='ridge_eikonal', sigma_0=...)` via `SimulationBuilder`. All other reinit methods (`split`, `unified`, `dgr`, `hybrid`, `eikonal`, `eikonal_xi`, `eikonal_fmm`) are untouched.

## 4. GPU/CPU unification pattern

- `@_fuse` decorators on pure-arithmetic elementwise kernels:
  - `_sigma_eff_kernel(h_field, sigma_0, h_ref)` — D1 per-node σ_eff field
  - `_eps_local_kernel(h_field, eps_scale, eps_xi)` — D4 per-node ε_local field
- Helper `_sigmoid_xp(xp, phi, eps_local)` is plain arithmetic parameterised on `xp`; no `@_fuse` (would require unconditional `cupy` import).
- `NonUniformFMM.solve` runs on CPU with numpy; caller handles D2H/H2D. Mirrors the stock `_fmm_phi` pattern in `reinit_eikonal.py`.

## 5. Traceability matrix

| Derivation | SP-E § | Wiki | Code |
|---|---|---|---|
| D1 σ_eff spatial scaling | §3 | [WIKI-T-057](../theory/WIKI-T-057.md) | `_sigma_eff_kernel`, `RidgeExtractor.__init__` |
| D2 physical-space Hessian (FD) | §4 | [WIKI-T-058](../theory/WIKI-T-058.md) | `RidgeExtractor.extract_ridge_mask` (FD; CHK-160 Approach A marker) |
| D3 non-uniform FMM | §6 | [WIKI-T-059](../theory/WIKI-T-059.md) | `NonUniformFMM.solve` |
| D4 ε_local spatial scaling | §5 | [WIKI-T-057](../theory/WIKI-T-057.md) | `_eps_local_kernel`, `RidgeEikonalReinitializer.__init__` |

## 6. Verification matrix

| ID | Test | Scope | Status |
|---|---|---|---|
| V1 | ridge topology (two disks, single disk) | uniform 64² | PASS |
| V2 | σ_eff convergence on α=2 | stretched 64² | PASS |
| V3 | FMM residual (p99, mean) | α∈{1,2,3}, 64² | PASS |
| V4 | volume conservation 1 step | α∈{1,2}, 64² | PASS |
| V5 | CPU/GPU parity fused kernels | α=2, 32² | `--gpu` gated |
| V6 | default method='split' bit-exact | any | PASS |

Pytest: `pytest src/twophase/tests/test_ridge_eikonal.py -v` (14 pass, 1 GPU-skip; 225 in full suite, no regressions).

End-to-end probe: `make cycle EXP=experiment/ch13/run.py ARGS='ch13_04_capwave_ridge_alpha2'`.

## 7. Scope limits

- Hessian precision: FD $O(h^2)$ — CHK-160 upgrades to Approach A (Direct Non-Uniform CCD, [WIKI-T-039 §5a](../theory/WIKI-T-039.md)). Code carries a `# CHK-160:` marker at the swap site.
- Adaptive $\varepsilon_\text{scale}(x)$: CHK-160 follow-up if V4 capillary-wave probe exceeds 5% drift.
- 3D: implementation is `grid.ndim`-parametric; verification is 2D only.
- GFM coupling: deferred.

## 8. Related commits

- `feat(CHK-159): Ridge-Eikonal hybrid on non-uniform grids (SP-E library)` — library + tests + config wire-up
- `docs(CHK-159): SP-E — Ridge-Eikonal hybrid on non-uniform grids` — short paper
- (this commit) `docs(CHK-159): wiki entries T-057, T-058, T-059, L-025`
