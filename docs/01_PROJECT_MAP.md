# 01_PROJECT_MAP — Module Map, Interface Contracts & Numerical Reference
# Rules: docs/00_GLOBAL_RULES.md | Live state: docs/02_ACTIVE_LEDGER.md

────────────────────────────────────────────────────────
# §1 — Module Map

> **Experiment Policy:** When running experiments, reuse existing `src/` libraries as much as possible. Do NOT reimplement physics, numerics, or I/O that already exists in the module tree below. Write experiment scripts that import and compose from `src/twophase/`.

```
src/twophase/
├── ccd/                        # CCD solver kernels (block-tridiag, §04)
│   ├── ccd_solver.py           # CCDSolver — 1D block-tridiag LU (O(h⁶)/O(h⁵))
│   └── block_tridiag.py        # Block tridiagonal matrix assembly
├── core/                       # Shared data structures
│   ├── field.py                # ScalarField, VectorField wrappers
│   ├── flow_state.py           # FlowState dataclass (velocity, psi, rho, mu, kappa, pressure)
│   ├── grid.py                 # Grid — node-centered, interface-fitted, metric tensors
│   ├── metrics.py              # compute_metrics() — CCD/FD metric computation (SRP extraction)
│   ├── boundary.py             # BCType enum, BoundarySpec, pad_ghost_cells
│   └── components.py           # SimulationComponents dataclass (17 fields)
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
│   │   ├── ccd_lu.py           # PPESolverCCDLU — CCD Kronecker + sparse LU (PRODUCTION)
│   │   ├── iim.py              # PPESolverIIM — CCD + IIM interface correction
│   │   ├── iterative.py        # PPESolverIterative — research toolkit
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
│   ├── boundary_condition.py   # BoundaryConditionHandler (BCType enum)
│   ├── builder.py              # SimulationBuilder — SOLE construction path (ASM-001)
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
└── tests/                      # pytest suite — 154 tests passing (2026-04-10)
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

Implementations: PPESolverPseudoTime (PRODUCTION), PPESolverSweep, PPESolverCCDLU,
PPESolverLU, PPESolverBiCGSTAB (testing only).

### INSTerm (`interfaces/ns_terms.py`)
Marker only — SimulationBuilder.with_*() enforces type safety at construction.

### Level-set interfaces (`interfaces/levelset.py`)
```python
ILevelSetAdvection.advance(psi, velocity_components: List, dt) → psi_new
IReinitializer.reinitialize(psi) → psi_new
ICurvatureCalculator.compute(psi) → kappa
```
All inputs/outputs shaped `grid.shape`. `velocity_components = [u, v]` (2D).

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
├── PhysicsConfig    (Re, We, Fr, rho_ratio, epsilon)
├── GridConfig       (Nx, Ny, domain size)
├── SolverConfig     (solver_type: "pseudotime" | "bicgstab", max_iter, tol)
├── TimeConfig       (dt, t_end, CFL limit)
└── OutputConfig     (output_dir, save_interval)
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

### PPE Solver Consistency (ASM-003)
| solver_type | Matrix | Corrector ∇ | Status |
|---|---|---|---|
| `"pseudotime"` | CCD Laplacian | CCD ∇ | CONSISTENT — production |
| `"bicgstab"` | FVM matrix | CCD ∇ | Approximate O(h²) — testing only |

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
| ASM-003 | ACTIVE | "pseudotime" is production solver; "bicgstab" testing-only |
| ASM-004 | ACTIVE | CCD boundary PASS: d1 slope ≥ 3.5, d2 slope ≥ 2.5 |
| ASM-005 | ACTIVE | PPE global: LGMRES primary, spsolve fallback |
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
| `PPESolver` (FVM BiCGSTAB) | `pressure/legacy/ppe_solver.py` | `PPESolverCCDLU` | FVM reference (PR-1) |
| `PPESolverLU` | `pressure/legacy/ppe_solver_lu.py` | `PPESolverCCDLU` | FVM direct LU reference |
| `PPESolverPseudoTime` | `pressure/legacy/ppe_solver_pseudotime.py` | `PPESolverCCDLU` | CCD+LGMRES baseline (PR-6) |
| `PPESolverSweep` | `pressure/legacy/ppe_solver_sweep.py` | `PPESolverCCDLU` | Matrix-free sweep reference |
| `PPESolverDCOmega` | `pressure/legacy/ppe_solver_dc_omega.py` | `PPESolverCCDLU` | Under-relaxed ADI reference |
| `CurvatureCalculator` | `levelset/curvature.py` | `CurvatureCalculatorPsi` | phi-inversion cross-validation |

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
| `03_levelset.tex` + `03b_cls_transport.tex` + `03c_levelset_mapping.tex` | §3 | CLS advection, reinitialization, ψ-φ mapping |
| `04_ccd.tex` + `04b_ccd_bc.tex` + `04c_dccd_derivation.tex` + `04d_uccd6.tex` + `04e_fccd.tex` + `04f_face_jet.tex` | §4 | O(h⁶), block Thomas, boundary scheme, DCCD/UCCD6/FCCD/face-jet |
| `05_reinitialization.tex` + `05b_cls_stages.tex` | §5 | CLS Ridge-Eikonal reinitialization, A-F 6 stages |
| `06_scheme_per_variable.tex` + `06b_advection.tex` + `06c_fccd_advection.tex` + `06d_viscous_3layer.tex` | §6 | Per-variable spatial discretization, CLS/momentum FCCD advection, viscous 3-layer |
| `07_time_integration.tex` | §7 | TVD-RK3/IMEX-BDF2/CN defect-correction, velocity-PPE ordering, CFL |
| `08_collocate.tex` + `08b_pressure.tex` + `08c_bf_failure.tex` + `08d_bf_seven_principles.tex` + `08e_fccd_bf.tex` + `08f_pressure_filter.tex` | §8 | Collocated-grid pressure coupling, BF failure modes/principles, FCCD BF sub-system, pressure-filter limits |
| `09_ccd_poisson.tex` + `09b_split_ppe.tex` + `09c_hfe.tex` + `09d_defect_correction.tex` + `09e_ppe_bc.tex` + `09f_pressure_summary.tex` | §9 | Variable-density PPE, split-PPE, HFE, defect correction, BC |
| `10_grid.tex` + `10b_ccd_extensions.tex` + `10c_fccd_nonuniform.tex` + `10d_ridge_eikonal_nonuniform.tex` | §10 | Non-uniform interface-fitted grid, CCD/FCCD/Ridge-Eikonal non-uniform extensions |
| `11_full_algorithm.tex` + `11c_dccd_bootstrap.tex` + `11d_pure_fccd_dns.tex` | §11 | Full solver loop, operator mapping, DCCD bootstrap, pure FCCD DNS architecture |
| `12_component_verification.tex` (+ sub-files) | §12 | Component-level mathematical verification (CCD/DCCD/curvature/CLS/HFE/PPE/RK3) |
| `13_verification.tex` + `13b`–`13i` | §13 | NS physical consistency: force balance, conservation, accuracy, coupling, limits, error budget |
| `14_benchmarks.tex` | §14 | Multi-phase flow benchmarks (capillary wave, rising bubble, Taylor deformation) |
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
| K — Knowledge | `docs/wiki/` | Compiled wiki (96+ entries) |
