# 01_PROJECT_MAP — Module Map, Interface Contracts & Numerical Reference
# PROJECT CONTEXT — fluid project data only. No rule content (rules in docs/00_GLOBAL_RULES.md).
# Dynamic state (phase, CHK/KL registers) in docs/02_ACTIVE_LEDGER.md.
# Last updated: 2026-03-28

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
Marker interface only — no unified `compute()` signature.
SimulationBuilder.with_*() methods enforce type safety at construction time.

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

SimulationBuilder is the sole construction path. Direct `TwoPhaseSimulation.__init__` deleted.
DIP: backends injected via constructor, not instantiated internally.
Default-vs-switchable: basic/standard schemes are defaults; alternatives toggled by config.
Full SOLID rules: see docs/00_GLOBAL_RULES.md §C1 or meta-tasks.md § Code Domain Constraints C1.

────────────────────────────────────────────────────────
# §5 — Implementation Constraints

### Implicit Solver Policy (ASM-005, ASM-006)
| System type | Primary | Fallback |
|---|---|---|
| Global PPE sparse | LGMRES | spsolve (sparse LU) on non-convergence |
| Banded/block-tridiagonal | Direct LU | — |

### Algorithm Fidelity
Fixes MUST restore paper-exact behavior. Deviation = bug. Improvement not in paper = out of scope.

### Backward Compatibility
When replacing an existing implementation: provide a backward-compatible adapter (A7).

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

### Node-Centered Grid (face/divergence indexing)
```
Face indexing (N+1 nodes: indices 0..N):
  face[0]  = left wall  → flux = 0 (no-penetration BC)
  face[N]  = internal   → MUST be computed, NOT left at 0
  ✓ Correct: faces 1..N   (u_L = u[0:N], u_R = u[1:N+1])
  ✗ Wrong:   faces 1..N-1 (face N left at 0 → O(1) boundary error)

FVM divergence:
  ✓ div[k] = (flux[k+1] - flux[k]) / h   (1h spacing)
  ✗ div[k] = (flux[k+2] - flux[k]) / h   (2h spacing → factor 2 error)
     Symptom: Δp ≈ 2× Laplace pressure (e.g., 8.6 instead of 4.0)

Array: flux (N+1,) → div_nodes (N,) = (flux[1:] - flux[:-1]) / h; pad zero at END only
```

### Pin-Node Rule (KL-11)
All PPE solver code must use dynamic center pin:
`pin_dof = ravel_multi_index(tuple(n//2 for n in grid.N), grid.shape)`
Never hardcode pin index (0,0).

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
# Rule: docs/00_GLOBAL_RULES.md §C2. Register here; never delete without explicit authorization.

| Legacy class | File | Superseded by | Reason kept |
|---|---|---|---|
| `ReinitializerWENO5` | `src/twophase/levelset/reinitialize.py` | `Reinitializer` (DCCD+CN) | Cross-validation vs paper §5c scheme |
| `PPESolver` | `src/twophase/pressure/legacy/ppe_solver.py` | `PPESolverCCDLU` | FVM BiCGSTAB reference (PR-1 violation) |
| `PPESolverLU` | `src/twophase/pressure/legacy/ppe_solver_lu.py` | `PPESolverCCDLU` | FVM direct LU reference (PR-1 violation) |
| `PPESolverPseudoTime` | `src/twophase/pressure/legacy/ppe_solver_pseudotime.py` | `PPESolverCCDLU` | CCD+LGMRES baseline (PR-6 violation) |
| `PPESolverSweep` | `src/twophase/pressure/legacy/ppe_solver_sweep.py` | `PPESolverCCDLU` | Matrix-free sweep reference |
| `PPESolverDCOmega` | `src/twophase/pressure/legacy/ppe_solver_dc_omega.py` | `PPESolverCCDLU` | Under-relaxed ADI reference |
| `CurvatureCalculator` | `src/twophase/levelset/curvature.py` | `CurvatureCalculatorPsi` | phi-inversion cross-validation |
| `cn_advance` re-export | `src/twophase/ns_terms/cn_advance.py` (stub) | `time_integration/cn_advance/` | C2 re-export |
| `PPESolverCCDLU` re-export | `src/twophase/pressure/ppe_solver_ccd_lu.py` (stub) | `pressure/solvers/ccd_lu.py` | C2 re-export |
| `PPESolverIIM` re-export | `src/twophase/pressure/ppe_solver_iim.py` (stub) | `pressure/solvers/iim.py` | C2 re-export |
| `PPESolverIterative` re-export | `src/twophase/pressure/ppe_solver_iterative.py` (stub) | `pressure/solvers/iterative.py` | C2 re-export |
| `create_ppe_solver` re-export | `src/twophase/pressure/ppe_solver_factory.py` (stub) | `pressure/solvers/factory.py` | C2 re-export |
| `_CCDPPEBase` re-export | `src/twophase/pressure/ccd_ppe_base.py` (stub) | `pressure/solvers/ccd_ppe_base.py` | C2 re-export |
| `FDPPEMatrix` re-export | `src/twophase/pressure/fd_ppe_matrix.py` (stub) | `pressure/solvers/fd_ppe_matrix.py` | C2 re-export |
| `ccd_ppe_utils` re-export | `src/twophase/pressure/ccd_ppe_utils.py` (stub) | `pressure/solvers/ccd_ppe_utils.py` | C2 re-export |
| `thomas_sweep` re-export | `src/twophase/pressure/thomas_sweep.py` (stub) | `pressure/solvers/thomas_sweep.py` | C2 re-export |

────────────────────────────────────────────────────────
# §9 — Paper Structure Reference (P2)
# WARNING: filename ≠ chapter number. Consult main.tex comments (%% 第N章) for chapter order.

| File(s) | Chapter | Content |
|---|---|---|
| `00_abstract.tex` | Abstract | CCD-PPE O(h⁶), CLS, Balanced-Force summary |
| `01_introduction.tex` | §1 Introduction | Background, 4 challenges, novelty table |
| `02_governing.tex` + `02b_surface_tension.tex` + `02c_nondim_curvature.tex` | §2 | One-Fluid NS, CSF, Heaviside, ψ-convention |
| `03_levelset.tex` + `03b_levelset_mapping.tex` | §3 | CLS advection, reinitialization |
| `04_ccd.tex` + `04b_ccd_bc.tex` + `04c_ccd_extensions.tex` + `04d_dissipative_ccd.tex` | §4 | O(h⁶), block Thomas, boundary scheme, dissipative filter |
| `05_advection.tex` + `05b_time_integration.tex` + `05c_reinitialization.tex` | §5 | CLS advection, TVD-RK3/AB2+IPC, CFL |
| `06_grid.tex` | §6 | Non-uniform interface-fitted grid |
| `07_collocate.tex` | §7 | Rhie-Chow, Balanced-Force |
| `08_pressure.tex` + `08b_ccd_poisson.tex` + `08c_defect_correction.tex` + `08d_gfm.tex` + `08e_ppe_bc.tex` + `08f_pressure_summary.tex` | §8 | Variable-density PPE, defect correction, GFM, BC |
| `09_full_algorithm.tex` | §9 | 7-step loop diagram, operator mapping, timestep control |
| `10_implementation.tex` + `10b_spatial.tex` + `10c_interface.tex` + `10d_solver_time.tex` + `10e_verification_summary.tex` | §10 | CCD/DCCD/curvature/CLS/GFM/PPE/RK3 mathematical verification |
| `11_verification.tex` + `11a`–`11f` | §11 | NS physical consistency: force balance, conservation, time/space accuracy, coupling, error budget |
| `12_benchmarks.tex` | §12 | Multi-phase flow benchmarks (static drop, capillary wave, rising bubble, RT) |
| `13_conclusion.tex` | §13 | Summary, future work |
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
| `ε_tol` | `08_pressure.tex` (eq:etol_physical) | `08_pressure.tex` (box:dtau_impl), `09_full_algorithm.tex` |
| `Δτ_opt` | `08_pressure.tex` (eq:dtau_opt) | `appendix_proofs.tex` (sec:dtau_derive) |
| `Δτ_par` (CLS) | `03_levelset.tex` | `03_levelset.tex` warnbox |
| Time accuracy order | `04b_time_schemes.tex` | `00_abstract.tex`, `01_introduction.tex`, `11_conclusion.tex` |

────────────────────────────────────────────────────────
# §11 — Matrix Domain Map
# T/L/E/A directory inventory + current interface contract status

| Domain | Code | Directory | Description | Interface Contract |
|--------|------|-----------|-------------|-------------------|
| T — Theory & Analysis | Mathematical Truth | `paper/` (theory sections) | Formal equation derivations, mathematical proofs | `docs/legacy/AlgorithmSpecs.md` (T→L) |
| L — Core Library | Functional Truth | `src/twophase/` | Solver kernels, numerical modules, tests | `docs/legacy/SolverAPI_v1.py` (L→E) |
| E — Experiment | Empirical Truth | `experiment/` | Simulation scripts, benchmark results | `docs/legacy/TechnicalReport.md` (T/E→A) |
| A — Academic Writing | Logical Truth | `paper/` | LaTeX manuscript, sections, bibliography | Signed by ConsistencyAuditor AU2 gate |
| M — Meta-Logic | Constitutional | `prompts/meta/` | System rules, axioms, agent design (A10: read-only) | — |
| P — Prompt & Environment | Agent Intelligence | `prompts/` | Generated agent prompts, README | — |
| Q — QA & Audit | Audit Trails | `docs/02_ACTIVE_LEDGER.md` | Verification logs, AU2 verdicts in CHK register | — |

**Interface Contract Status:**

| Contract | Path | Status | Upstream Domain | Downstream Domain |
|----------|------|--------|----------------|------------------|
| AlgorithmSpecs | `docs/legacy/AlgorithmSpecs.md` | pending | T-Domain | L-Domain (CodeArchitect) |
| SolverAPI v1 | `docs/legacy/SolverAPI_v1.py` | pending | L-Domain | E-Domain (ExperimentRunner) |
| TechnicalReport | `docs/legacy/TechnicalReport.md` | pending | T-Domain + E-Domain | A-Domain (PaperWriter) |

**Note:** `{pending}` status means the corresponding domain pipeline has not yet been executed.
Downstream domains must BLOCK new dev/ work until upstream contract is signed (meta-workflow.md §CI/CP).
