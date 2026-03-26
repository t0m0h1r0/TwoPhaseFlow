# ARCHITECTURE

## §1 — Module Map

```
src/twophase/
├── ccd/                        # CCD solver kernels (block-tridiag, §04)
│   ├── ccd_solver.py           # CCDSolver — 1D block-tridiag LU (O(h⁶)/O(h⁵))
│   └── block_tridiag.py        # Block tridiagonal matrix assembly
├── core/                       # Shared data structures
│   ├── field.py                # Field wrapper
│   ├── flow_state.py           # FlowState dataclass (velocity, psi, rho, mu, kappa, pressure)
│   ├── grid.py                 # Grid — node-centered, metric tensors, density fn
│   └── components.py           # Component registry helpers
├── interfaces/                 # Abstract interfaces (DIP)
│   ├── levelset.py             # ILevelSetAdvection, IReinitializer, ICurvatureCalculator
│   ├── ns_terms.py             # INSTerm — marker interface for NS RHS terms
│   └── ppe_solver.py           # IPPESolver — solve(rhs, rho, dt, p_init) → p
├── levelset/                   # Level-set / CLS physics (§03)
│   ├── advection.py            # LevelSetAdvection (WENO5 + TVD-RK3)
│   ├── curvature.py            # CurvatureCalculator (CCD 6th-order, §02c)
│   ├── heaviside.py            # Heaviside H̃ and delta δ̃ functions
│   └── reinitialize.py         # Reinitializer (pseudo-time PDE, §05c)
├── ns_terms/                   # Navier-Stokes RHS terms (§02)
│   ├── convection.py           # ConvectionTerm — u·∇u
│   ├── gravity.py              # GravityTerm — (1/Fr²) ρ̃ ĝ
│   ├── surface_tension.py      # SurfaceTensionTerm — (1/We) κ ∇H̃ (CSF, §02b)
│   ├── viscous.py              # ViscousTerm — (1/Re) ∇·(μ̃(∇u + ∇uᵀ))
│   └── predictor.py            # Predictor — u* = uⁿ + dt Σ Fᵢ (§09)
├── pressure/                   # Pressure / projection (§07, §08)
│   ├── ppe_builder.py          # PPE RHS assembly: (1/dt) ∇ᴿᶜ·u*
│   ├── ppe_solver.py           # PPESolverBiCGSTAB — FVM (TESTING ONLY, ~O(h²))
│   ├── ppe_solver_ccd_lu.py    # PPESolverCCDLU — CCD Laplacian + sparse LU
│   ├── ppe_solver_lu.py        # PPESolverLU — FVM matrix + sparse LU
│   ├── ppe_solver_pseudotime.py# PPESolverPseudoTime — CCD + pseudo-time (PRODUCTION, §08d)
│   ├── ppe_solver_sweep.py     # PPESolverSweep — alternating-direction sweep
│   ├── ppe_solver_factory.py   # Factory: "pseudotime" | "bicgstab" | "sweep" | ...
│   ├── rhie_chow.py            # RhieChowInterpolation — face velocity (§07)
│   └── velocity_corrector.py   # VelocityCorrector — u^{n+1} = u* − dt ∇p (§09)
├── time_integration/           # Time stepping (§05b)
│   ├── tvd_rk3.py              # TVD-RK3 integrator
│   └── cfl.py                  # CFL condition + dt selection
├── simulation/                 # Simulation orchestration
│   ├── _core.py                # TwoPhaseSimulation — step_forward() loop
│   ├── boundary_condition.py   # BoundaryCondition (no-slip, periodic, etc.)
│   ├── builder.py              # SimulationBuilder — SOLE construction path (ASM-001)
│   └── diagnostics.py          # Diagnostics / convergence monitoring
├── configs/                    # Config loading
│   └── config_loader.py        # YAML → SimulationConfig
├── initial_conditions/         # Initial condition builders
│   ├── builder.py              # ICBuilder — shapes + velocity_fields
│   ├── shapes.py               # Circle, Rectangle, HalfSpace, Sinusoidal interface
│   └── velocity_fields.py      # RigidRotation, UniformFlow
├── io/                         # I/O
│   ├── checkpoint.py           # Checkpoint save/load
│   ├── serializers.py          # Field serialization helpers
│   └── vtk_writer.py           # VTK / VTR + PVD writer
├── visualization/              # Visualization
│   ├── plot_scalar.py
│   ├── plot_vector.py
│   └── realtime_viewer.py
├── benchmarks/                 # Benchmark runners (§10b)
│   ├── run_all_benchmarks.py
│   ├── rising_bubble.py
│   ├── rayleigh_taylor.py
│   ├── stationary_droplet.py
│   └── zalesak_disk.py
├── backend.py                  # Compute backend injection (CPU/GPU)
├── config.py                   # SimulationConfig — sub-config composition root
└── tests/                      # pytest suite — 95 tests, all passing (2026-03-27)
    ├── test_ccd.py
    ├── test_config.py
    ├── test_grid.py
    ├── test_initial_conditions.py
    ├── test_io.py
    ├── test_levelset.py
    ├── test_ns_terms.py
    ├── test_pressure.py
    └── test_time_integration.py
```

---

## §2 — Interface Contracts

### IPPESolver (`interfaces/ppe_solver.py`)
```python
IPPESolver.solve(rhs, rho, dt, p_init=None) → p
```
| Parameter | Shape | Description |
|---|---|---|
| `rhs` | `grid.shape` | Right-hand side: (1/dt) ∇ᴿᶜ·u* |
| `rho` | `grid.shape` | Density field ρ̃^{n+1} |
| `dt` | float | Time step (for interface consistency) |
| `p_init` | `grid.shape` or None | Warm-start initial guess pⁿ |
| **return** `p` | `grid.shape` | Solved pressure field p^{n+1} |

Implementations: `PPESolverPseudoTime` (PRODUCTION), `PPESolverSweep`, `PPESolverCCDLU`, `PPESolverLU`, `PPESolverBiCGSTAB` (testing only).

### INSTerm (`interfaces/ns_terms.py`)
Marker interface only — no unified `compute()` signature. Each NS term uses its own arguments. `SimulationBuilder.with_*()` methods enforce type safety at construction time.

### Level-set interfaces (`interfaces/levelset.py`)
```python
ILevelSetAdvection.advance(psi, velocity_components: List, dt) → psi_new
IReinitializer.reinitialize(psi) → psi_new
ICurvatureCalculator.compute(psi) → kappa
```
All inputs/outputs are arrays shaped `grid.shape`. `velocity_components = [u, v]` (2D).

### FlowState (`core/flow_state.py`)
Pure data class — no logic. Fields accessible to callbacks and sub-components:
| Field | Type / Shape | Description |
|---|---|---|
| `velocity` | `List[array]` — `[u, v]` each `(Nx, Ny)` | Velocity components at time n |
| `psi` | `(Nx, Ny)` | CLS field ψ ∈ [0, 1] (liquid≈0, gas≈1) |
| `rho` | `(Nx, Ny)` | Regularised density ρ̃ = ρ_g + (ρ_l − ρ_g)ψ |
| `mu` | `(Nx, Ny)` | Regularised viscosity μ̃ |
| `kappa` | `(Nx, Ny)` | Interface curvature κ |
| `pressure` | `(Nx, Ny)` | Pressure pⁿ (also warm-start for PPE) |

### Backend injection (`backend.py`)
CPU/GPU-agnostic array operations injected via constructor into solvers. Not yet standardised to a formal protocol — see `backend.py` directly.

---

## §3 — Config Hierarchy

`SimulationConfig` is pure sub-config composition — no monolithic config class (ASM-007).

```
SimulationConfig
├── PhysicsConfig        (Re, We, Fr, rho_ratio, epsilon)
├── GridConfig           (Nx, Ny, domain size)
├── SolverConfig         (solver_type: "pseudotime" | "bicgstab", max_iter, tol)
├── TimeConfig           (dt, t_end, CFL limit)
└── OutputConfig         (output_dir, save_interval)
```

> **§3 TODO:** Verify field names against `src/twophase/infra/config/`.

---

## §4 — SOLID Rules and Construction

**SimulationBuilder is the sole construction path.** Direct `TwoPhaseSimulation.__init__` is deleted. Any code that bypasses SimulationBuilder is forbidden.

Key SOLID rules:
- **DIP (Dependency Inversion):** Backends injected via constructor, not instantiated internally.
- **Default-vs-switchable:** Basic/standard schemes are defaults; alternative logics toggled by config.
- **MMS test standard:** Grid sizes N = [32, 64, 128, 256]; norms L1, L2, L∞; convergence via linear regression; assert `observed_order >= expected_order − 0.2`.
- **Test determinism:** Tests must be reproducible from config alone.
- **Code comment language:** Japanese preferred for inline comments; English for docstrings and reasoning.

---

## §5 — Implementation Constraints

### Implicit Solver Policy
| System type | Primary | Fallback | Rationale |
|---|---|---|---|
| Global PPE sparse | LGMRES | `spsolve` (sparse LU) on non-convergence | Large sparse; iterative preferred |
| Banded/block-tridiagonal (CCD Thomas, Helmholtz sweeps) | Direct LU | — | O(N) fill-in; direct is efficient |

Departure from this policy requires explicit inline justification.

### Algorithm Fidelity
Fixes MUST restore paper-exact behavior. Deviation from paper = bug. Improvement not in paper = out of scope (A3).

### Backward Compatibility
When replacing an existing implementation: provide a backward-compatible adapter (A7).

### Test Failure Halt
After delivering code and tests: if tests fail, STOP immediately. Report discrepancy. Ask user for direction. Never auto-debug.

---

## §6 — Numerical Algorithm Reference

### CCD Boundary Accuracy Baselines
- Interior: O(h⁶) for 1st derivative, O(h⁵) for 2nd derivative.
- **Boundary-limited orders (PASS thresholds on L∞):**
  - d1 (1st derivative): slope ≥ 3.5 is PASS. Slope ~4.0 is expected. NOT O(h⁶).
  - d2 (2nd derivative): slope ≥ 2.5 is PASS. NOT O(h⁵).
- Failure = slope < 3.5 (d1) or < 2.5 (d2) on uniform grids.

### WENO5 Periodic BC
- Ghost-cell rule: boundary divergence MUST NOT be unconditionally zeroed.
- Check `_weno5_divergence` wrap-around flux computation if spatial order degrades to ~O(1/h) or goes negative.

### PPE Null Space
- `PPESolverPseudoTime` Kronecker-product Laplacian has an **8-dimensional null space**.
- Do NOT use `‖Lp − q‖₂` as pass/fail metric without null-space deflation (ASM-002).
- Use physical diagnostics: divergence-free projection, Laplace pressure dp, velocity magnitude ‖u‖.

### PPE Solver Consistency
| solver_type | Matrix | Corrector ∇ | Status |
|---|---|---|---|
| `"pseudotime"` | CCD Laplacian | CCD `∇` | CONSISTENT — production |
| `"bicgstab"` | FVM matrix | CCD `∇` | Approximate O(h²) — testing only |

### Known Symmetry-Breaking Root Causes (fixed 2026-03-22)
| Root Cause | Stage Broken | Signature |
|---|---|---|
| Rhie-Chow FVM div wrong at wall node N_ax | div_rc | Error O(umax) at boundary nodes only |
| PPE gauge pin at corner (0,0) instead of center (N/2,N/2) | δp | Global asymmetry O(‖rhs‖) |
| Capillary CFL safety factor missing | u_new (step 1) | Symmetry error O(umax), disappears at smaller dt |

### Node-Centered Grid (face/divergence indexing)
```
Face indexing (N+1 nodes: indices 0..N):
  face[0]  = left wall  → flux = 0 (no-penetration BC)
  face[N]  = internal   → MUST be computed, NOT left at 0
  ✓ Correct: faces 1..N   (u_L = u[0:N], u_R = u[1:N+1])
  ✗ Wrong:   faces 1..N-1 (face N left at 0 → O(1) boundary error)

FVM divergence stencil:
  ✓ Correct: div[k] = (flux[k+1] - flux[k]) / h   (1h spacing)
  ✗ Wrong:   div[k] = (flux[k+2] - flux[k]) / h   (2h spacing → factor 2 too large)
             Symptom: Δp ≈ 2× Laplace pressure (e.g., 8.6 instead of 4.0)

Array shape: flux (N+1,) → div_nodes (N,) = (flux[1:] - flux[:-1]) / h
             pad: (N+1,) — pad zero at END only
```
