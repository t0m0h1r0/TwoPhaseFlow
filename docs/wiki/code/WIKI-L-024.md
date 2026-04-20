---
ref_id: WIKI-L-024
title: "FCCD Library Module: FCCDSolver, FCCDConvectionTerm, FCCDLevelSetAdvection"
domain: code
status: IMPLEMENTED  # CHK-158; V1-V10 pass
superseded_by: null
sources:
  - path: src/twophase/ccd/fccd.py
    description: FCCDSolver primitives (face_gradient, face_value, node_gradient, face_divergence, advection_rhs)
  - path: src/twophase/ns_terms/fccd_convection.py
    description: FCCDConvectionTerm
  - path: src/twophase/levelset/fccd_advection.py
    description: FCCDLevelSetAdvection
  - path: src/twophase/config.py
    description: advection_scheme / convection_scheme dispatch
  - path: src/twophase/simulation/builder.py
    description: SimulationBuilder wires the above via single shared FCCDSolver
depends_on:
  - "[[WIKI-T-053]]: FCCD calculation via CCD d2 closure"
  - "[[WIKI-T-054]]: FCCD matrix formulation + wall/periodic BC"
  - "[[WIKI-T-055]]: FCCD advection operator"
  - "[[WIKI-T-056]]: FCCD wall Option IV"
  - "[[WIKI-L-015]]: CuPy / GPU backend unification"
consumers:
  - domain: paper
    description: SP-D short paper
  - domain: cross-domain
    description: WIKI-X-018 advection-axis row
tags: [fccd, ccd, advection, convection, level_set, gpu_cpu_unified, library, research_proposal]
compiled_by: Claude Opus 4.7
compiled_at: "2026-04-21"
---

# FCCD Library Module

## 1. Scope

This entry documents the additive library delivered in CHK-158:
- `src/twophase/ccd/fccd.py` — `FCCDSolver` primitives;
- `src/twophase/ns_terms/fccd_convection.py` — `FCCDConvectionTerm`;
- `src/twophase/levelset/fccd_advection.py` — `FCCDLevelSetAdvection`;
- config flag wiring in `src/twophase/config.py` and `src/twophase/simulation/builder.py`.

No existing public API is modified. Defaults are unchanged: `convection_scheme = "ccd"` and `advection_scheme = "dissipative_ccd"`. To opt into FCCD, set either flag to `"fccd_nodal"` or `"fccd_flux"`.

## 2. `FCCDSolver` API

```python
class FCCDSolver:
    def __init__(self, grid, backend, bc_type="wall", ccd_solver=None):
        """Inject or build a CCDSolver; share LU factorisation."""

    # — primitives —
    def face_gradient(self, u, axis, q=None):
        """FCCD 4th-order face gradient (WIKI-T-054 §4). Returns length-N face array."""
    def face_value(self, u, axis, q=None):
        """4th-order compact face reconstruction (WIKI-T-055 §3). Returns length-N face array."""
    def node_gradient(self, u, axis, q=None):
        """Option C Hermite reconstructor (WIKI-T-055 §5). Returns length-(N+1) node array."""
    def face_divergence(self, F_faces, axis):
        """Face-to-node central divergence; returns length-(N+1) node array."""

    # — composed —
    def advection_rhs(self, velocity, mode='flux', scalar=None):
        """
        Compute -(u·∇)φ at nodes.

        velocity : list of (N+1,...) nodal velocity components.
        mode     : 'flux' (WIKI-T-055 §4, Option B) or 'node' (§5, Option C).
        scalar   : optional transported scalar (for level-set); if None, computes
                   the vector advection of each velocity component.

        Returns : list of nodal arrays, same shape as `velocity` (or [(N+1,...)]
                  when `scalar` supplied).
        """

    # — BC helpers —
    def enforce_wall_option_iii(self, face, axis):
        """Zero the two boundary-face slots (Neumann ψ, p). WIKI-T-054 §6."""
    def enforce_wall_option_iv(self, face, axis):
        """Zero the two boundary-face slots for Dirichlet u (WIKI-T-056)."""

    # — utility —
    def periodic_symbol(self, omega_H):
        """Analytic symbol Ĥ^FCCD(ω) at normalised wavenumber ω·H (unit tests)."""
```

### 2.1 LU sharing and cost

`FCCDSolver` accepts an existing `CCDSolver` via `ccd_solver=...`. `SimulationBuilder` always passes the already-built CCD solver, so the CCD block-tridiagonal (wall) / block-circulant (periodic) LU factorisation is **computed once** and reused for every FCCD call. Per call per axis:

| Step | Cost |
|---|---|
| `q = ccd.differentiate(u, axis)[1]` (block Thomas) | $\mathcal{O}(N)$ |
| Face stencils `D1 u - D2 q` | $\mathcal{O}(N)$ |
| Face value stencils `P1 u - P2 q` | $\mathcal{O}(N)$ |
| Face-to-node divergence or averaging | $\mathcal{O}(N)$ |

Total FCCD overhead is ≈1.1× CCD (the CCD solve dominates). **No extra block solves are introduced.**

### 2.2 GPU/CPU unification (`backend.xp` pattern)

Array operations route through `backend.xp` (`numpy` on CPU, `cupy` on GPU). Three fused element-wise kernels are defined with a `@_fuse` decorator that dispatches to `cupy.fuse` on GPU and is a no-op on CPU — the same pattern as [`ccd_solver.py:229`](../../../src/twophase/ccd/ccd_solver.py#L229) and [`levelset/advection.py:208`](../../../src/twophase/levelset/advection.py#L208):

```python
@staticmethod
@_fuse
def _face_gradient_kernel(u_L, u_R, q_L, q_R, inv_H, H_over_24):
    return (u_R - u_L) * inv_H - H_over_24 * (q_R - q_L)
```

Analogous fused kernels exist for face value (`H²/16` coefficient) and for the Hermite reconstructor. CPU/GPU parity is verified bit-close (rtol 1e-12) by `test_fccd_gpu_smoke.py` (V7).

### 2.3 Face index convention

Throughout the module, `face[j]` stores the value at $f_{j+1/2}$ — the face between nodes $j$ and $j+1$. The face array is length $N$ (shape-matching `u.shape[axis] - 1`) on wall-BC axes and length $N$ on periodic axes (with wrap handled via `np.roll`). Callers must not mix this with the `face[j] = f_{j-1/2}` convention used elsewhere in the code base.

### 2.4 Wall / periodic dispatch

`bc_type="wall"` and `bc_type="periodic"` are passed through unchanged from the caller. The periodic face-slice uses
```python
u_lo = u_unique; u_hi = xp.roll(u_unique, -1, axis=axis)
```
(with `u_unique` the $N$-length array, last node collapsed onto first). The wall face-slice uses
```python
u_lo = u[..., :-1]; u_hi = u[..., 1:]
```
along the selected axis. These indexing conventions match [WIKI-T-054](../theory/WIKI-T-054.md) §7.1.

## 3. `FCCDConvectionTerm` API

```python
class FCCDConvectionTerm(INSTerm):
    def __init__(self, backend, fccd: FCCDSolver, mode: str = "flux"):
        """mode ∈ {'flux', 'node'} selects Option B or Option C."""

    def compute(self, velocity_components, ccd=None):
        """Same signature as ConvectionTerm.compute — returns a list of nodal arrays.
        ccd parameter is ignored (kept for ISP compatibility with the default term)."""
```

Exact API parity with [`ns_terms/convection.py:35`](../../../src/twophase/ns_terms/convection.py#L35) `ConvectionTerm.compute`. The AB2 history buffer at [`ab2_predictor.py:92`](../../../src/twophase/time_integration/ab2_predictor.py#L92) requires no shape change — verified by `test_fccd_convection.py::test_ab2_compat` (V9).

## 4. `FCCDLevelSetAdvection` API

```python
class FCCDLevelSetAdvection(LevelSetAdvection):
    def __init__(self, backend, grid, fccd, mode="flux", mass_correction=True):
        ...
    def advance(self, psi, velocity_components, dt, clip_bounds=None):
        """TVD-RK3 over -(u·∇)ψ. Same signature as DissipativeCCDAdvection.advance."""
```

The class subclasses the existing `LevelSetAdvection` base, so downstream pipelines that call `.advance(...)` see no interface change. `mode='flux'` preserves $\int\psi\,\mathrm{d}V$ up to boundary flux; `mode='node'` is consistency-only.

## 5. Config and factory wire-up

### 5.1 New config fields ([config.py](../../../src/twophase/config.py))

```python
class NumericsConfig:
    advection_scheme: str = "dissipative_ccd"
        # 'dissipative_ccd' | 'weno5' | 'fccd_nodal' | 'fccd_flux'
    convection_scheme: str = "ccd"
        # 'ccd' | 'fccd_nodal' | 'fccd_flux'
```

Defaults are unchanged from pre-CHK-158. `NumericsConfig.__post_init__` validates the enum values.

### 5.2 Builder dispatch ([builder.py](../../../src/twophase/simulation/builder.py))

`SimulationBuilder.build()` constructs a **single** `FCCDSolver` that shares the already-built `CCDSolver` when either flag selects an FCCD mode:

```python
fccd = None
if (config.numerics.advection_scheme.startswith("fccd_")
        or config.numerics.convection_scheme.startswith("fccd_")):
    from ..ccd.fccd import FCCDSolver
    fccd = FCCDSolver(grid, backend, bc_type=config.numerics.bc_type,
                      ccd_solver=ccd)

# ψ advection dispatch
adv_mode = {"fccd_nodal": "node", "fccd_flux": "flux"}
if config.numerics.advection_scheme in adv_mode:
    from ..levelset.fccd_advection import FCCDLevelSetAdvection
    ls_advect = FCCDLevelSetAdvection(backend, grid, fccd,
                                      mode=adv_mode[config.numerics.advection_scheme],
                                      mass_correction=True)

# Momentum convection dispatch (only if user did not inject a custom term)
if self._convection is None and config.numerics.convection_scheme in adv_mode:
    from ..ns_terms.fccd_convection import FCCDConvectionTerm
    self._convection = FCCDConvectionTerm(backend, fccd,
                                          mode=adv_mode[config.numerics.convection_scheme])
```

The two flags are independent — users can run FCCD convection with dissipative-CCD ψ-advection, or vice versa, or both FCCD. **Single FCCD instance is shared between momentum + level-set**; no duplicate LU or stencil setup cost.

## 6. Backward compatibility

- No existing public symbol renamed or removed.
- Default behaviour is bit-exact pre-CHK-158 (`advection_scheme="dissipative_ccd"`, `convection_scheme="ccd"`).
- 242 existing tests pass + 14 GPU skipped + 2 xfailed — full suite green.
- `INSTerm` / `LevelSetAdvection` interface compliance verified structurally; the new classes can be dropped in by users with `SimulationBuilder.with_convection(...)`.

## 7. Verification matrix

| # | Claim | Test | Status |
|---|---|---|---|
| V1 | $\mathcal{O}(H^4)$ face gradient (periodic) | `test_fccd.py::test_face_gradient_order` | PASS |
| V2 | Periodic symbol $-7/5760$ (±1%) | `test_fccd.py::test_periodic_symbol` | PASS |
| V3 | $\mathcal{O}(H^4)$ face value | `test_fccd.py::test_face_value_order` | PASS |
| V4 | $\mathcal{O}(H^4)$ Hermite node gradient | `test_fccd.py::test_node_gradient_hermite_order` | PASS |
| V5 | Wall Option III zero faces (Neumann) | `test_fccd.py::test_wall_option_iii` | PASS |
| V6 | Wall Option IV Dirichlet u | `test_fccd.py::test_wall_option_iv` | PASS |
| V7 | CPU/GPU parity (rtol 1e-12) | `test_fccd_gpu_smoke.py` | PASS (GPU host) |
| V8 | TGV agreement vs CCD baseline | `test_fccd_convection.py::test_tgv_agreement` | PASS |
| V9 | AB2 buffer shape compat | `test_fccd_convection.py::test_ab2_compat` | PASS |
| V10 | Flux-mode mass conservation | `test_fccd_advection_levelset.py::test_flux_mode_mass_conservation_uniform_divfree` | PASS |
| V11 | BF residual on WIKI-E-030 | (experiment, deferred) | PENDING |

## 8. Migration notes for callers

To enable FCCD in an existing config:

```python
from twophase.config import SimulationConfig, NumericsConfig
cfg = SimulationConfig(
    numerics=NumericsConfig(
        convection_scheme="fccd_flux",      # Option B momentum advection
        advection_scheme="fccd_flux",       # Option B ψ advection
        # bc_type and extension_method unchanged
    ),
)
sim = SimulationBuilder(cfg).build()
```

No other changes required. AB2, PPE RHS, CSF, Rhie-Chow, GFM, and diagnostics all operate unchanged on the nodal-shape output of `FCCDConvectionTerm` / `FCCDLevelSetAdvection`.

## 9. Cross-references

- Theory: [WIKI-T-053](../theory/WIKI-T-053.md), [WIKI-T-054](../theory/WIKI-T-054.md), [WIKI-T-055](../theory/WIKI-T-055.md), [WIKI-T-056](../theory/WIKI-T-056.md)
- Code precedent: [WIKI-L-015](WIKI-L-015.md) (CuPy/GPU pattern), [WIKI-L-022](WIKI-L-022.md) (`_fvm_pressure_grad`), [WIKI-L-023](WIKI-L-023.md) (R-1.5 roadmap — velocity companion)
- Cross-domain: [WIKI-X-018](../cross-domain/WIKI-X-018.md) (H-01 remediation map)
- Short paper: SP-D (`docs/memo/short_paper/SP-D_fccd_advection.md`)
