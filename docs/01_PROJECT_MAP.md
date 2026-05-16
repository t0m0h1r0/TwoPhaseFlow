# 01_PROJECT_MAP — Module Map, Interface Contracts & Numerical Reference
# Rules: docs/00_GLOBAL_RULES.md | Live state: docs/02_ACTIVE_LEDGER.md

────────────────────────────────────────────────────────
# §0 — Current Codex / Execution Environment

| Area | Current contract |
|---|---|
| Codex config | `.codex/config.toml`: `model = "gpt-5.5"`, `model_reasoning_effort = "high"` |
| Sandbox | `sandbox_mode = "workspace-write"` + `sandbox_workspace_write.network_access = true` |
| Shell env | `inherit = "core"`; `ENABLE_TOOL_SEARCH=true`; Claude compatibility vars retained; `remote.sh` auto-discovers a usable ssh-agent socket when `SSH_AUTH_SOCK` is unset |
| Execution | Remote-first via `make run` / `make test`; local fallback only when SSH unavailable after ssh-agent autodiscovery |
| Work isolation | Git worktrees + `docs/locks/*.lock.json`; no main merge without explicit user instruction |

────────────────────────────────────────────────────────
# §1 — Module Map

> **Experiment Policy:** Reuse `src/twophase/` and `twophase.experiment`; run through `make run` / `make cycle` unless explicitly doing local fallback. Do NOT reimplement existing physics, numerics, or I/O in experiment scripts.

```
src/twophase/
├── ccd/                        # CCD solver kernels (block-tridiag, §04)
│   ├── ccd_solver.py           # CCDSolver — 1D block-tridiag LU (O(h⁶)/O(h⁵))
│   └── block_tridiag.py        # Block tridiagonal matrix assembly
├── core/                       # Shared data structures
│   ├── field.py                # ScalarField, VectorField wrappers
│   ├── flow_state.py           # FlowState dataclass (velocity, psi, rho, mu, kappa, pressure)
│   ├── grid.py                 # Grid — node-centered, boundary-fitted metric tensors
│   ├── metrics.py              # compute_metrics() — CCD/FD metric computation (SRP extraction)
│   ├── boundary.py             # BCType enum, BoundarySpec, pad_ghost_cells
│   └── components.py           # SimulationComponents dataclass (17 fields)
├── geometry/                   # AO-Fast geometric cell-fraction C1 contracts
│   ├── dense_reference.py      # Dense P1 Q_h/S_h oracle; test/debug only, no runtime fallback
│   └── import_manifest.py      # Closed direct-AO import enum + migration-status manifest
├── hfe/                        # Hermite Field Extension (§08d)
│   ├── hermite_interp.py       # hermite5_coeffs / hermite5_eval — O(h⁶) Hermite polynomial
│   └── field_extension.py      # HermiteFieldExtension — 2-D tensor-product extension via CCD
├── interfaces/                 # Abstract interfaces (DIP)
│   ├── field_extension.py      # IFieldExtension — extend(field_data, phi, n_hat)
│   ├── levelset.py             # ILevelSetAdvection, IReinitializer, ICurvatureCalculator
│   ├── ns_terms.py             # INSTerm — marker interface for NS RHS terms
│   └── ppe_solver.py           # IPPESolver — solve(rhs, rho, dt, p_init) → p
├── levelset/                   # Level-set / CLS physics (§03, §05)
│   ├── advection.py            # LevelSetAdvection (WENO5), DissipativeCCDAdvection (§05)
│   ├── curvature.py            # CurvatureCalculator (legacy, C2)
│   ├── curvature_psi.py        # CurvatureCalculatorPsi — direct ψ-based (active)
│   ├── curvature_filter.py     # InterfaceLimitedFilter for curvature smoothing
│   ├── normal_filter.py        # NormalVectorFilter + kappa_from_normals
│   ├── compact_filters.py      # Compact difference filters
│   ├── heaviside.py            # Heaviside H̃, delta δ̃, property update, mass correction
│   ├── reinitialize.py         # Reinitializer (facade) + ReinitializerWENO5 (legacy C2)
│   ├── reinit_ops.py           # Shared reinitialization operations (pure functions)
│   ├── reinit_split.py         # SplitReinitializer — compression + CN-ADI (§05c)
│   ├── reinit_unified.py       # UnifiedDCCDReinitializer — combined RHS (WIKI-T-028)
│   ├── reinit_dgr.py           # DGRReinitializer + HybridReinitializer (WIKI-T-030)
│   ├── field_extender.py       # FieldExtender (upwind FD) + NullFieldExtender
│   └── closest_point_extender.py # ClosestPointExtender (Hermite interpolation)
├── ns_terms/                   # Navier-Stokes RHS terms (§02)
│   ├── convection.py           # ConvectionTerm — u·∇u
│   ├── gravity.py              # GravityTerm — (1/Fr²) ρ̃ ĝ
│   ├── surface_tension.py      # SurfaceTensionTerm — (1/We) κ ∇H̃ (CSF, §02b)
│   ├── viscous.py              # ViscousTerm — (1/Re) ∇·(μ̃(∇u + ∇uᵀ))
│   ├── predictor.py            # C2 re-export → time_integration/ab2_predictor.Predictor
│   └── cn_advance.py           # C2 re-export → time_integration/cn_advance/
├── pressure/                   # Pressure / projection (§07, §08)
│   ├── solvers/                # PPE solver implementations
│   │   ├── ccd_ppe_base.py     # _CCDPPEBase — Template Method for CCD solvers
│   │   ├── ccd_ppe_utils.py    # CCD Laplacian evaluation helpers
│   │   ├── ccd_lu.py           # PPESolverCCDLU — legacy/reference CCD Kronecker + sparse LU
│   │   ├── iim.py              # PPESolverIIM — legacy/reference CCD + IIM interface correction
│   │   ├── iterative.py        # PPESolverIterative — legacy/reference research toolkit
│   │   ├── factory.py          # Registry-based factory (OCP)
│   │   ├── fd_ppe_matrix.py    # FDPPEMatrix — FD Laplacian matrix
│   │   └── thomas_sweep.py     # Thomas sweep for ADI solvers
│   ├── ppe_builder.py          # PPE FVM matrix assembly (legacy solvers only)
│   ├── dccd_ppe_filter.py      # DCCDPPEFilter — dissipative CCD filter for GFM
│   ├── ppe_rhs_gfm.py          # PPERHSBuilderGFM — GFM-corrected PPE RHS
│   ├── gfm.py                  # GFMCorrector — Ghost Fluid Method jump correction
│   ├── rhie_chow.py            # RhieChowInterpolator — face velocity + balanced-force (§07)
│   ├── velocity_corrector.py   # VelocityCorrector — u^{n+1} = u* − dt ∇p (§09)
│   ├── ppe_diagnostics.py      # ccd_ppe_residual() — diagnostic (SRP extraction)
│   ├── iim/                    # Immersed Interface Method sub-package
│   │   ├── jump_conditions.py  # IIM jump condition computation
│   │   └── stencil_corrector.py # IIM stencil correction
│   └── legacy/                 # C2-retained legacy solvers (§8 register)
│       ├── ppe_solver.py       # PPESolver — FVM BiCGSTAB (PR-1)
│       ├── ppe_solver_lu.py    # PPESolverLU — FVM direct LU (PR-1)
│       ├── ppe_solver_pseudotime.py # PPESolverPseudoTime — LGMRES (PR-6)
│       ├── ppe_solver_sweep.py # PPESolverSweep — ADI sweep
│       └── ppe_solver_dc_omega.py # PPESolverDCOmega — under-relaxed ADI
├── time_integration/           # Time stepping (§05b)
│   ├── ab2_predictor.py        # Predictor — AB2 + IPC + CN viscous (§09)
│   ├── tvd_rk3.py              # TVD-RK3 integrator (+ post_stage callback)
│   ├── cfl.py                  # CFL condition + dt selection
│   └── cn_advance/             # CN viscous advance strategies (Strategy pattern)
│       ├── base.py             # ICNAdvance protocol
│       ├── picard_cn.py        # PicardCNAdvance — Heun predictor-corrector
│       └── richardson_cn.py    # RichardsonCNAdvance — Richardson extrapolation
├── simulation/                 # Simulation orchestration
│   ├── _core.py                # TwoPhaseSimulation — step_forward() 7-step loop
│   ├── ao_fast_runtime_contract.py # AO-Fast disabled runtime/checkpoint contract gate
│   ├── boundary_condition.py   # BoundaryConditionHandler (BCType enum)
│   ├── builder.py              # SimulationBuilder — SOLE construction path (ASM-001)
│   ├── simulation/viscous_helmholtz_dc.py # ViscousHelmholtzDCSolver — implicit-BDF2 DC (§07)
│   └── diagnostics.py          # Runtime diagnostics / convergence monitoring
├── diagnostics/                # Reusable analysis functions (extracted from experiments)
│   ├── field_diagnostics.py    # kinetic_energy, divergence (Linf/L2)
│   └── interface_diagnostics.py # measure_eps_eff, interface_area, parasitic_current, tracking
├── configs/
│   └── config_loader.py        # YAML → SimulationConfig (auto-derived _known keys)
├── initial_conditions/
│   ├── builder.py              # ICBuilder — shapes + velocity_fields composition
│   ├── shapes.py               # Circle, Rectangle, HalfSpace, Sinusoidal, ZalesakDisk
│   └── velocity_fields.py      # RigidRotation, UniformFlow, SingleVortex, DoubleShearLayer
├── io/
│   ├── checkpoint.py           # Checkpoint save/load (HDF5/NPZ)
│   ├── serializers.py          # Field serialization helpers
│   └── vtk_writer.py           # VTK / VTR + PVD writer
├── visualization/
│   ├── plot_scalar.py          # Scalar field colormaps, contours
│   ├── plot_vector.py          # Velocity/vorticity, streamlines
│   ├── plot_fields.py          # Multi-panel overlay, symmetric ranges
│   └── realtime_viewer.py      # Live display during simulation
├── benchmarks/                 # Benchmark runners + reference solutions
│   ├── run_all_benchmarks.py   # Orchestration
│   ├── rising_bubble.py        # Buoyancy-driven flow (Hysing 2009)
│   ├── rayleigh_taylor.py      # Interfacial instability
│   ├── stationary_droplet.py   # Laplace pressure accuracy
│   ├── zalesak_disk.py         # Advection scheme quality
│   ├── presets.py              # Config factory functions (DRY)
│   └── analytical_solutions.py # TGV, Kovasznay, hydrostatic, MMS
├── experiment/                 # Experiment script toolkit
│   ├── style.py                # Matplotlib theme (colors, fonts)
│   ├── io.py                   # Result save/load + argparse
│   ├── figure.py               # Multi-panel layout helpers
│   ├── plots.py                # Convergence tables, time histories, LaTeX
│   └── convergence.py          # Convergence rate computation, error norms
├── backend.py                  # Compute backend injection (CPU/GPU, xp namespace)
├── config.py                   # SimulationConfig — sub-config composition root (ASM-007)
└── tests/                      # pytest suite; use `make test` for current status
    ├── test_ccd.py
    ├── test_config.py
    ├── test_grid.py
    ├── test_initial_conditions.py
    ├── test_io.py
    ├── test_levelset.py
    ├── test_ns_terms.py
    ├── test_pressure.py
    ├── test_simulation.py
    └── test_time_integration.py
```

────────────────────────────────────────────────────────
# §2 — Interface Contracts

### IPPESolver (`interfaces/ppe_solver.py`)
```python
IPPESolver.solve(rhs, rho, dt, p_init=None) → p
```
| Parameter | Shape | Description |
|---|---|---|
| `rhs` | `grid.shape` | RHS: (1/dt) ∇ᴿᶜ·u* |
| `rho` | `grid.shape` | Density ρ̃^{n+1} |
| `dt` | float | Time step |
| `p_init` | `grid.shape` or None | Warm-start pⁿ |
| **return** `p` | `grid.shape` | Solved pressure p^{n+1} |

Implementations route through `SolverConfig.ppe_solver_type`: `fvm_iterative` default;
`fd_direct`, `fd_iterative`, and `fvm_direct` are explicit active routes.
Retired reference solvers (`ccd_lu`, `iim`, legacy `iterative`) are direct-import only and
are not selectable through the public PPE factory/config path.

### INSTerm (`interfaces/ns_terms.py`)
Marker only — SimulationBuilder.with_*() enforces type safety at construction.

### Level-set interfaces (`interfaces/levelset.py`)
```python
ILevelSetAdvection.advance(psi, velocity_components: List, dt) → psi_new
IReinitializer.reinitialize(psi) → psi_new
ICurvatureCalculator.compute(psi) → kappa
```
All inputs/outputs shaped `grid.shape`. `velocity_components = [u, v]` (2D).

### AO-Fast Geometry C1-C9 (`geometry/`, `simulation/config_*`)

`geometry/dense_reference.py` owns only the dense P1 oracle:

```python
cut_geometry_2d(grid, phi) -> P1CutGeometry(q, theta, surface_length, ...)
MetricCellComplex.from_grid(grid).cell_measures
```

Status: oracle/test-only.  It is allowed for active-vs-dense tests and debug
comparison, but must not be called from simulation runtime, experiment YAML
activation, or fallback paths.  `geometry/import_manifest.py` is the closed
direct-branch import registry; every imported AO symbol must be classified as
`oracle_only`, `gpu_production`, or `reject`, with migration status recorded
separately.

`geometry/active_kernels.py` and `geometry/active_table.py` own compact
active-row P1 geometry:

```python
refresh_active_geometry_2d(grid, phi, cell_ids) -> P1ActiveGeometry
build_active_table_for_cell_ids(grid, phi, cell_ids, q_target=...) -> ActiveGeometryTable
```

The compact path consumes explicit `cell_ids_A` streams and does not discover
support by a full-grid dense oracle scan.  Dense support scans are confined to
`build_debug_active_table_from_dense(..., allowed_context=...)` and are ledgered
as initialization/oracle/debug work.  The temporary host compactor enforces
`max_support_stream_ratio` before halo expansion, enforces the final active
support capacity after halo expansion, and rejects CUDA/device streams until the
fused GPU support-compaction path is admitted.  Compact active-table
construction consumes `cell_measure_A` from the active geometry refresh, avoiding
duplicate coordinate-axis device conversions, and does not call the dense
metric-complex cache.  `metric_key_A` aliases `cell_measure_A` until a real cache
key is admitted, so compact construction does not allocate an unused float64
device vector.  GPU ledgers report
`device_resident=True`, `host_transfer_count=0`, and defer count fields that
would require synchronization instead of calling `.get()`.
`geometry/active_projection.py` owns matrix-free active `J`, `J^T`, Schur
matvecs, CPU-control PCG with `tau_cg_floor` fail-close, and exact active-row
residual acceptance.  Schur matvecs operate on compact unique active nodes, so
PCG iterations do not allocate or zero a full nodal grid.  Full nodal scatter is
kept only for explicit gauge updates and uses direct assignment on unique active
nodes.  Compact GPU `J^T` accumulation uses backend `bincount`; a missing GPU
`bincount` fails closed rather than falling back to atomic scatter.  GPU active
tables stay device-resident;
nonempty GPU diagnostics/PCG/projection fail closed until fused device-side
solver, reduction, and line-search kernels are admitted.  Empty active support returns
an explicit no-op ledger rather than reducing an empty residual.  After C8,
`geometric_cell_fraction` YAML may build an `ExperimentConfig` when it declares
the closed AO-Fast contract (`q` transport, `geometric_swept_volume`,
`bundle_virtual_work`, `cell_volume`, and either no projection for static
diagnostics or `algorithm: compatibility_projection` for transported
production runs).  Solver construction validates the runtime adapter,
checkpoint, and chapter-14 smoke gates; no chapter-14 runtime path is silently
activated.  Conversely, the legacy/default diffuse front door rejects
geometric capillary declarations (`bundle_virtual_work`,
`endpoint=geometric_cell_fraction`, or `constraints=[cell_volume]`) unless
`interface.state_space.kind=geometric_cell_fraction` is explicit.

`simulation/ao_fast_runtime_contract.py` owns the disabled C9 runtime contract
adapter.  It validates the parsed q/theta/phi handoff, the
`bundle_virtual_work` capillary contract, required continuation checkpoint
arrays, and pressure/projected face-history shapes, then raises
`AOFastRuntimeDisabledError` before `build_solver_init_options` can enter the
legacy diffuse runtime.  Checkpoint continuation distinguishes cell cochains
(`state/q`, `state/theta`, `state/stratum/case_code`) from P1 node gauges
(`state/phi`); for cell shape `(nx, ny)`, the node shape is `(nx+1, ny+1)` and
the face histories are `(nx, ny+1)` / `(nx+1, ny)`.  This is a
test-only/disabled gate until bounded swept-volume transport, bundle capillary
runtime, and chapter-14 smoke gates are implemented.

### FlowState (`core/flow_state.py`)
Pure data class — no logic.
| Field | Shape | Description |
|---|---|---|
| `velocity` | `[u, v]` each `(Nx, Ny)` | Velocity at time n |
| `psi` | `(Nx, Ny)` | CLS field ψ ∈ [0,1] (liquid≈0, gas≈1) |
| `rho` | `(Nx, Ny)` | Regularised density ρ̃ |
| `mu` | `(Nx, Ny)` | Regularised viscosity μ̃ |
| `kappa` | `(Nx, Ny)` | Interface curvature κ |
| `pressure` | `(Nx, Ny)` | Pressure pⁿ (warm-start for PPE) |

────────────────────────────────────────────────────────
# §3 — Config Hierarchy

`SimulationConfig` is pure sub-config composition (ASM-007):
```
SimulationConfig
├── GridConfig       (ndim, N, L, fitting/wall refinement)
├── FluidConfig      (Re, We, Fr, rho_ratio, mu_ratio)
├── NumericsConfig   (CFL, t_end, reinit, advection/convection, surface tension, HFE)
├── SolverConfig     (ppe_solver_type: "fvm_iterative" default; FD/FVM/IIM/legacy refs)
└── use_gpu          (backend selection; array ops through backend.xp)
```

────────────────────────────────────────────────────────
# §4 — Construction & SOLID

SimulationBuilder = sole construction path; `TwoPhaseSimulation.__init__` deleted.
DIP: backends injected via constructor. Full rules: docs/00_GLOBAL_RULES.md §C.

────────────────────────────────────────────────────────
# §6 — Numerical Algorithm Reference

### CCD Accuracy Baselines (ASM-004)
- Interior: O(h⁶) for 1st derivative, O(h⁵) for 2nd derivative.
- Boundary-limited PASS thresholds (L∞):
  - d1 (1st derivative): slope ≥ 3.5 (expected ~4.0)
  - d2 (2nd derivative): slope ≥ 2.5

### WENO5 Periodic BC
Ghost-cell rule: boundary divergence MUST NOT be unconditionally zeroed.
Check `_weno5_divergence` wrap-around flux if spatial order degrades to ~O(1/h).

### PPE Null Space (ASM-002)
8-dimensional null space. Do NOT use ‖Lp−q‖₂ as pass/fail metric.
Use physical diagnostics: divergence-free projection, Laplace pressure dp, ‖u‖.

### PPE Solver Consistency (ASM-003/005)
| ppe_solver_type | Operator | Status |
|---|---|---|
| `"fvm_iterative"` | FVM matrix-free | Default production route |
| `"fvm_direct"` / `"fd_direct"` | Sparse direct | Deterministic direct routes |
| `"iim"` | Jump-corrected CCD/IIM | Retired reference; direct-import tests only |
| `"ccd_lu"` | CCD Kronecker LU | Retired reference/component tests only |

### Known Symmetry-Breaking Root Causes (fixed 2026-03-22, ASM-008)
| Root Cause | Stage | Signature |
|---|---|---|
| Rhie-Chow FVM div wrong at wall node N_ax | div_rc | Error O(umax) at boundary nodes |
| PPE gauge pin at corner (0,0) instead of center (N/2,N/2) | δp | Global asymmetry O(‖rhs‖) |
| Capillary CFL safety factor missing | u_new (step 1) | Symmetry error O(umax), disappears at smaller dt |

### FVM/CCD Mismatch Fix (ASM-009)
CCD replaced with FD in velocity_corrector.py and predictor.py IPC term (2026-03-22).

### Node-Centered Grid
Face indexing uses N+1 nodes (0..N); compute faces 1..N (face[0]=wall, flux=0).
FVM divergence: `div[k] = (flux[k+1] - flux[k]) / h` (1h spacing — 2h spacing → factor-2 error).
Array: `flux (N+1,) → (flux[1:] - flux[:-1]) / h`, pad zero at END only.

### Pin-Node Rule (KL-11)
PPE code must use dynamic center pin — never hardcode (0,0):
`pin_dof = ravel_multi_index(tuple(n//2 for n in grid.N), grid.shape)`

────────────────────────────────────────────────────────
# §7 — Active Assumption Register (summary)
# Full entries with scope and risk: docs/02_ACTIVE_LEDGER.md § ASSUMPTIONS

| ASM-ID | Status | One-line summary |
|---|---|---|
| ASM-001 | ACTIVE | SimulationBuilder is sole construction path |
| ASM-002 | ACTIVE | PPE Kronecker Laplacian has 8-dim null space — ‖Lp−q‖₂ not valid |
| ASM-003 | DEPRECATED | CCD Kronecker PPE indefinite; CCD-LU restricted to reference/component tests |
| ASM-004 | ACTIVE | CCD boundary PASS: d1 slope ≥ 3.5, d2 slope ≥ 2.5 |
| ASM-005 | DEPRECATED | LGMRES prohibited for PPE production (PR-6) |
| ASM-006 | ACTIVE | Banded systems: direct LU |
| ASM-007 | ACTIVE | SimulationConfig is pure sub-config composition |
| ASM-008 | FIXED | Three symmetry-breaking root causes found and fixed (2026-03-22) |
| ASM-009 | FIXED | FVM/CCD mismatch in IPC+corrector fixed (2026-03-22) |
| ASM-010 | ACTIVE | docs/00_GLOBAL_RULES.md §P1 is authoritative LaTeX standard |

────────────────────────────────────────────────────────
# §8 — C2 Legacy Class Register
# Rule: docs/00_GLOBAL_RULES.md §C2. Never delete without explicit authorization.

### Legacy implementations (active reference for cross-validation)

| Legacy class | File | Superseded by | Reason kept |
|---|---|---|---|
| `ReinitializerWENO5` | `levelset/reinitialize.py` | `Reinitializer` (DCCD+CN) | Paper §5c cross-validation |
| `PPESolver` (FVM BiCGSTAB) | `pressure/legacy/ppe_solver.py` | `ppe_solver_type="fvm_iterative"` | FVM reference (PR-1) |
| `PPESolverLU` | `pressure/legacy/ppe_solver_lu.py` | `ppe_solver_type="fvm_direct"` | FVM direct LU reference |
| `PPESolverPseudoTime` | `pressure/legacy/ppe_solver_pseudotime.py` | current FD/FVM/DC routes | CCD+LGMRES baseline (PR-6) |
| `PPESolverSweep` | `pressure/legacy/ppe_solver_sweep.py` | DC/PPE sweep routes | Matrix-free sweep reference |
| `PPESolverDCOmega` | `pressure/legacy/ppe_solver_dc_omega.py` | `PPESolverCCDLU` | Under-relaxed ADI reference |
| `CurvatureCalculator` | `levelset/curvature.py` | `CurvatureCalculatorPsi` | phi-inversion cross-validation |
| `PPESolverCCDLU` | `ppe/ccd_lu.py` | `fvm_direct` / `fd_direct` / DC routes | ch11 smooth-RHS component reference; excluded from public factory |
| `PPESolverIIM` | `ppe/iim_solver.py` | affine-jump/FCCD projection routes | IIM research reference; excluded from public factory |
| `PPESolverIterative` | `ppe/iterative.py` | `fvm_iterative` / `fd_iterative` | retired host-only research toolkit; excluded from public factory |
| `ConsistentIIMReprojector` | `simulation/velocity_reprojector_iim.py` | `variable_density_only` / active GFM pressure-jump routes | IIM reprojection reference; excluded from run config registration |
| `simulation.interface_stress_closure` imports | `simulation/interface_stress_closure.py` | `coupling/interface_stress_closure.py` | Compatibility path after affine face-jump helpers moved to neutral coupling layer |
| `masked_bulk_pressure` / `pressure_bulk_snapshot` | `tools/plot_snapshot_figures.py` | `pressure_hodge_snapshot` | Former interface-band masking retained only as fail-closed compatibility hooks; excluded from figure registries |
| `exp_V6_density_ratio_convergence_legacy.py` | `experiment/ch13/legacy/exp_V6_density_ratio_convergence_legacy.py` | `experiment/ch13/exp_V6_density_ratio_convergence.py` | Reduced smoothed-density CSF/PPE density sweep reference |
| `exp_V7_imex_bdf2_twophase_time_legacy.py` | `experiment/ch13/legacy/exp_V7_imex_bdf2_twophase_time_legacy.py` | `experiment/ch13/exp_V7_imex_bdf2_twophase_time.py` | Reduced hand-rolled BDF2/PPE time-order proxy |
| `exp_V2_manufactured_periodic_residual_legacy.py` | `experiment/ch13/legacy/exp_V2_manufactured_periodic_residual_legacy.py` | `experiment/ch13/exp_V2_kovasznay_residual.py` | Manufactured periodic NS residual cross-check |
| `exp_V1_spectral_tgv_energy_legacy.py` | `experiment/ch13/legacy/exp_V1_spectral_tgv_energy_legacy.py` | `experiment/ch13/exp_V1_tgv_energy_decay.py` | Spectral TGV projection/time-order reference |

### Re-export stubs (backward compat after `pressure/solvers/` restructure)

All under `src/twophase/pressure/*.py` forward to `pressure/solvers/*.py`:
`ppe_solver_ccd_lu`, `ppe_solver_iim`, `ppe_solver_iterative`, `ppe_solver_factory`, `ccd_ppe_base`, `fd_ppe_matrix`, `ccd_ppe_utils`, `thomas_sweep`. Also `ns_terms/cn_advance.py` → `time_integration/cn_advance/`.

────────────────────────────────────────────────────────
# §9 — Paper Structure Reference (P2)
# Filenames: `{NN}_topic.tex` (chapter head), `{NN}{letter}_topic.tex` (continuations).

| File(s) | Chapter | Content |
|---|---|---|
| `00_abstract.tex` | Abstract | CCD-PPE O(h⁶), CLS, Balanced-Force summary |
| `01_introduction.tex` | §1 Introduction | Background, 4 challenges, novelty table |
| `02_governing.tex` + `02b_surface_tension.tex` + `02c_nondim_curvature.tex` | §2 | One-Fluid NS, CSF, Heaviside, ψ-convention |
| `03_levelset.tex` + `03b_cls_transport.tex` + `03c_levelset_mapping.tex` + `03d_ridge_eikonal.tex` | §3 | CLS advection, reinitialization, ψ-φ mapping, Ridge-Eikonal interface reconstruction |
| `04_ccd.tex` + `04b_ccd_bc.tex` + `04c_dccd_derivation.tex` + `04d_uccd6.tex` + `04e_fccd.tex` + `04f_face_jet.tex` | §4 | O(h⁶), block Thomas, boundary scheme, DCCD/UCCD6/FCCD/face-jet |
| `05_reinitialization.tex` + `05a_ridge_eikonal_details.tex` + `05b_cls_stages.tex` | §5 | CLS Ridge-Eikonal reinitialization, comparison paths, A-F 6 stages |
| `06_scheme_per_variable.tex` + `06b_advection.tex` + `06c_fccd_advection.tex` + `06d_viscous_3layer.tex` | §6 | Per-variable spatial discretization, CLS/momentum FCCD advection, viscous 3-layer |
| `07_time_integration.tex` + `07b_defect_viscous.tex` + `07c_capillary_projection_buoyancy.tex` + `07d_order_timestep.tex` | §7 | TVD-RK3/IMEX-BDF2/CN defect-correction, capillary/projection/buoyancy ordering, CFL |
| `08_collocate.tex` + `08b_pressure.tex` + `08c_bf_failure.tex` + `08d_bf_seven_principles.tex` + `08e_fccd_bf.tex` | §8 | Collocated-grid pressure coupling, BF failure modes/principles, pressure-jump face cochain, FCCD BF subsystem |
| `09_ccd_poisson.tex` + `09b1_split_ppe.tex` + `09b2_fccd_projection.tex` + `09b3_pressure_jump_form.tex` + `09b4_capillary_work_state.tex` + `09c_hfe.tex` + `09d_defect_correction.tex` + `09e_ppe_bc.tex` + `09f_pressure_summary.tex` | §9 | Variable-density PPE, split-PPE, HFE, defect correction, BC |
| `10_grid.tex` + `10a1_2d_tracking_grid.tex` + `10a2_epsilon_width_constraints.tex` + `10b_ccd_extensions.tex` + `10c_fccd_nonuniform.tex` + `10d_ridge_eikonal_nonuniform.tex` | §10 | Non-uniform and boundary-fitted grid, CCD/FCCD/Ridge-Eikonal non-uniform extensions |
| `11_full_algorithm.tex` + `11b1_full_timestep.tex` + `11b2_state_contracts.tex` + `11c_dccd_bootstrap.tex` + `11d_pure_fccd_dns.tex` + `11e_ao_fast_state_space.tex` | §11 | Full solver loop, operator mapping, DCCD bootstrap, pure FCCD DNS architecture, active-geometry capillary state space |
| `12_component_verification.tex` (+ sub-files) | §12 | Component-level mathematical verification (CCD/DCCD/curvature/CLS/HFE/PPE/RK3) |
| `13_verification.tex` + `13a`–`13d` + `13e1`–`13e2` + `13f` | §13 | NS physical consistency: force balance, conservation, accuracy, coupling, limits, error budget |
| `14_benchmarks.tex` + `14a_capillary_wave.tex` + `14b_oscillating_droplet.tex` + `14c_rising_bubble.tex` + `14d_rayleigh_taylor.tex` + `14e_benchmark_summary.tex` | §14 | Two-phase physical benchmarks: capillary wave, oscillating droplet, rising bubble, Rayleigh-Taylor, summary |
| `15_conclusion.tex` | §15 | Summary, future work |
| `appendix_*_s*.tex` (21 files, A–E) | Appendix | Interface math, CCD coefficients, implementation, schemes, solver analysis |

### §9b — LaTeX Notation Conventions (MANDATORY, enforced 2026-04-01)

| Rule | Correct | Wrong | Exception |
|------|---------|-------|-----------|
| Bold nabla | `\bnabla` | `\nabla` | Inside tcolorbox `defbox` proof derivations; `\texorpdfstring` args |
| Order macro | `$\Ord{h^6}$` | `$O(h^6)$`, `$\mathcal{O}(h^6)$` | Computational complexity `$O(N)$`; qualitative `$O(1)$`; `\texorpdfstring` args |
| Tilde before ref | `式~\eqref{eq:foo}`, `第~\ref{sec:bar}章` | `式 \eqref{...}`, `式\eqref{...}` | `§\ref{...}` (no tilde needed) |

────────────────────────────────────────────────────────
# §10 — P3-D Multi-Site Parameter Register
# Rule: docs/00_GLOBAL_RULES.md §P §P3-D

| Parameter | Defined in | Referenced in |
|---|---|---|
| `ε_tol` | `appendix_ppe_pseudotime.tex` (eq:etol_physical) | `appendix_ppe_pseudotime.tex` (box:dtau_impl), `11_full_algorithm.tex` |
| `Δτ_opt` | `appendix_ppe_pseudotime.tex` (eq:dtau_opt) | `appendix_ccd_impl_s3.tex` (sec:dtau_derive), `appendix_ppe_pseudotime.tex` (sec:dtau_derive) |
| `Δτ_par` (CLS) | `03_levelset.tex` | `03_levelset.tex` warnbox |
| Time accuracy order | `07_time_integration.tex` | `00_abstract.tex`, `01_introduction.tex`, `15_conclusion.tex` |

────────────────────────────────────────────────────────
# §11 — Domain Map

| Domain | Directory | Description |
|--------|-----------|-------------|
| T — Theory | `paper/` (theory sections) | Equation derivations, proofs |
| L — Library | `src/twophase/` | Solver kernels, tests |
| E — Experiment | `experiment/` | Simulation scripts, benchmarks |
| A — Paper | `paper/` | LaTeX manuscript |
| K — Knowledge | `docs/wiki/` | Compiled wiki; live counts in `docs/wiki/INDEX.md` |
