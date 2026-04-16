---
ref_id: WIKI-L-018
title: "Library Additions: grid_remap, reconstruction, benchmarks.scaling, diagnostics"
domain: L
status: ACTIVE
superseded_by: null
sources:
  - path: "src/twophase/core/grid_remap.py"
    description: "Backend-agnostic grid remapper factory (Identity/Linear/Cubic)"
  - path: "src/twophase/levelset/reconstruction.py"
    description: "HeavisideInterfaceReconstructor + ReconstructionConfig"
  - path: "src/twophase/tools/benchmarks/scaling.py"
    description: "Dimensional scaling: mu_from_re, sigma_from_eo"
  - path: "src/twophase/tools/diagnostics/interface_diagnostics.py"
    description: "New functions: midband_fraction, relative_mass_error"
consumers:
  - domain: E
    usage: "exp13_90/91/92 use reconstruction + diagnostics; exp13_92 uses grid_remap"
  - domain: L
    usage: "ns_pipeline.py uses grid_remap + reconstruction at runtime"
depends_on:
  - "[[WIKI-L-008]]"
  - "[[WIKI-L-015]]"
compiled_by: ResearchArchitect
verified_by: null
compiled_at: 2026-04-16
---

# Library Additions (wt/gpu-remote)

Four new library modules added to `src/twophase/`, following the module hierarchy
defined in [[WIKI-L-008]].

---

## 1. `core/grid_remap.py` — GridRemapper Factory

**Pattern:** Strategy (factory function)

**Problem:** After grid rebuild, fields must be remapped from old to new
coordinates. The previous `RegularGridInterpolator` (SciPy) was CPU-only and
forced a device round-trip on GPU runs.

**API:**

```python
build_grid_remapper(backend, source_coords, target_coords, method="cubic") -> GridRemapper
build_nonuniform_to_uniform_remapper(backend, grid, target_shape=None) -> GridRemapper
```

**Strategy hierarchy:**

| Class | Condition | Behaviour |
|---|---|---|
| `IdentityGridRemapper` | source == target (atol=1e-14) | No-op `remap(field) -> field` |
| `LinearGridRemapper` | method="linear" | Separable bilinear interpolation |
| `CubicGridRemapper` | method="cubic" (default) | Separable 4-point Lagrange cubic |

**`CubicGridRemapper`** (commit 6e752f6): precomputes per-axis 4-point stencil
indices and Lagrange basis weights at construction time. Requires >= 4 source
nodes per axis. Error order O(h^4) vs O(h^2) for linear — but see [[WIKI-T-037]]
for why this rarely helps in practice for sharp interfaces (eps/h <= 1).

**GPU capability:** All three remappers use `backend.xp` throughout —
`searchsorted`, `take`, broadcast arithmetic — runs on NumPy or CuPy without
code change.

**Key design properties:**
- Monotonicity check on source coords enforced (`ValueError` on non-monotone).
- Degenerate-spacing guard: $|h| < 10^{-30}$ returns weight 0.
- `mapping_info(include_weights)` exports host-side arrays for reproducible
  visualization.

**Convenience function:**

```python
remap_field_to_uniform(backend, field, source_coords, domain_lengths, clip_range=(0,1))
    -> (field_uni, target_coords, remapper)
```

Builds a uniform linspace target per axis, remaps, and optionally clips.
Returns the remapper for `mapping_info()` export.

**Integration:** Replaces `RegularGridInterpolator` in `ns_pipeline._rebuild_grid`.
`remap_field_to_uniform` used in exp13_92 for converting non-uniform snapshots
to a uniform plotting grid.

---

## 2. `levelset/reconstruction.py` — HeavisideInterfaceReconstructor

**Pattern:** Facade over `heaviside()` / `invert_heaviside()` primitives.

**Problem:** Scattered direct calls to `heaviside`/`invert_heaviside` across
the pipeline made it hard to ensure consistent $\varepsilon$ usage and to add
the phi-primary transport path.

**API:**

```python
ReconstructionConfig(eps, eps_scale=1.0, clip_factor=12.0)
HeavisideInterfaceReconstructor(backend, config)
    .psi_from_phi(phi) -> psi        # H_eps(phi)
    .phi_from_psi(psi) -> phi        # H_eps^{-1}(psi)
    .clip_phi(phi) -> clipped_phi    # [-c*eps_eff, +c*eps_eff]
    .interface_points_from_phi(phi, x, y) -> ndarray  # (N,2) zero-crossings
    .interface_points_from_psi(psi, x, y) -> ndarray  # convenience wrapper
```

**Key properties:**
- `eps_effective = eps_scale * eps` — supports non-uniform interface width scaling.
- `clip_factor` clamped to $\ge 2.0$; prevents SDF domain explosion.
- `interface_points_from_phi`: 2D edge-walking algorithm scanning all cell edges
  for sign changes, linearly interpolating zero-crossing coordinates.

**Integration in `ns_pipeline.py`:** Two instances are constructed at solver init:
- `_reconstruct_base` ($\varepsilon_\text{scale}=1.0$) — grid rebuild + consistent_iim
- `_reconstruct_phi_primary` (configurable scale) — phi-primary transport path

---

## 3. `tools/benchmarks/scaling.py` — Dimensional Scaling

**Purpose:** Eliminates ad-hoc dimensional conversions in experiment scripts.

Three pure functions, no state, no dependencies beyond NumPy:

```python
mu_from_re(rho_l, g_acc, d_ref, re_num) -> float
    # mu = rho_l * sqrt(g * d) * d / Re

sigma_from_eo(rho_l, rho_g, g_acc, d_ref, eo_num) -> float
    # sigma = g * (rho_l - rho_g) * d^2 / Eo

mu_sigma_from_re_eo(rho_l, rho_g, g_acc, d_ref, re_num, eo_num) -> (mu, sigma)
```

Used by exp13_90, exp13_91, and future rising-bubble experiments.

---

## 4. `tools/diagnostics/interface_diagnostics.py` — New Functions

Two functions added to the existing module:

```python
midband_fraction(psi, lo=0.1, hi=0.9) -> float
    # Fraction of cells with lo < psi < hi
    # Lower = sharper interface; used in exp13_90/91

relative_mass_error(psi, dV, mass_ref) -> float
    # |sum(psi*dV) - mass_ref| / max(|mass_ref|, 1e-30)
    # Volume-weighted, non-uniform grid compatible
```

Both are pure NumPy (no backend dependency), usable in post-processing without
a live solver instance. Extracted from inline experiment code.

---

## Cross-References

- [[WIKI-L-008]] — Module hierarchy (placement of new modules)
- [[WIKI-L-015]] — GPU backend (`xp` dispatch used by GridRemapper, Reconstructor)
- [[WIKI-T-036]] — Phi-primary transport (uses reconstruction.py)
- [[WIKI-E-024]] — exp13_90 uses midband_fraction
- [[WIKI-E-025]] — exp13_92 uses grid_remap
