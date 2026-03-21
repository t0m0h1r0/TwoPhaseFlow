# **ARCHITECTURE & DEVELOPMENT RULES**

## **1. Module Map (src/twophase/)**

```
src/
├── main.py                         # Entry point
└── twophase/
    ├── backend.py                  # NumPy/CuPy abstraction — xp = backend.xp
    ├── config.py                   # SimulationConfig (composed of 4 sub-configs)
    ├── ccd/
    │   ├── ccd_solver.py           # CCDSolver — O(h⁶) compact finite differences
    │   └── block_tridiag.py        # Block Thomas algorithm (2×2 blocks)
    ├── core/
    │   ├── grid.py                 # Grid — spacing, coordinates, ndim
    │   ├── field.py                # Field utilities
    │   ├── flow_state.py           # FlowState dataclass (velocity, psi, rho, mu, kappa, pressure)
    │   └── components.py           # SimulationComponents dataclass (builder→executor bridge)
    ├── interfaces/
    │   ├── levelset.py             # ILevelSetAdvection, IReinitializer, ICurvatureCalculator
    │   ├── ns_terms.py             # INSTerm
    │   └── ppe_solver.py           # IPPESolver
    ├── levelset/
    │   ├── advection.py            # WENO5 advection (ILevelSetAdvection)
    │   ├── reinitialize.py         # Pseudo-time reinitialization (IReinitializer)
    │   ├── curvature.py            # CCD-based κ computation (ICurvatureCalculator)
    │   └── heaviside.py            # Regularized Heaviside / delta function
    ├── ns_terms/
    │   ├── predictor.py            # Predictor — assembles NS forcing and advances u*
    │   ├── convection.py           # CCD D⁽¹⁾ + Forward Euler convection (INSTerm)
    │   ├── viscous.py              # Viscous diffusion (INSTerm)
    │   ├── gravity.py              # Buoyancy / gravity (INSTerm)
    │   └── surface_tension.py      # CSF surface tension (INSTerm)
    ├── pressure/
    │   ├── ppe_builder.py          # Variable-density PPE matrix assembly
    │   ├── ppe_solver.py           # PPESolver — BiCGSTAB (IPPESolver)
    │   ├── ppe_solver_pseudotime.py# PPESolverPseudoTime — pseudo-time implicit (IPPESolver, default)
    │   ├── ppe_solver_factory.py   # Factory: "pseudotime" → PPESolverPseudoTime, "bicgstab" → PPESolver
    │   ├── rhie_chow.py            # Rhie-Chow interpolation (Balanced-Force)
    │   └── velocity_corrector.py   # Projection correction: u^{n+1} = u* − Δt/ρ ∇p
    ├── simulation/
    │   ├── _core.py                # TwoPhaseSimulation — 7-step time loop executor
    │   ├── builder.py              # SimulationBuilder — sole construction path
    │   ├── boundary_condition.py   # BoundaryConditionHandler
    │   └── diagnostics.py          # DiagnosticsReporter
    ├── time_integration/
    │   ├── cfl.py                  # CFLCalculator — adaptive Δt
    │   └── tvd_rk3.py              # TVD-RK3 for CLS advection
    ├── io/
    │   ├── checkpoint.py           # CheckpointManager
    │   └── serializers.py          # Array serialization
    ├── configs/
    │   └── config_loader.py        # YAML/JSON config loading
    ├── visualization/
    │   ├── plot_scalar.py          # Scalar field plots
    │   ├── plot_vector.py          # Vector field plots
    │   └── realtime_viewer.py      # Live visualization
    ├── benchmarks/
    │   ├── stationary_droplet.py   # Parasitic current / Balanced-Force test
    │   ├── rising_bubble.py        # Rising bubble (ρ ratio 1000)
    │   ├── rayleigh_taylor.py      # Rayleigh-Taylor instability
    │   ├── zalesak_disk.py         # Interface advection accuracy (Zalesak disk)
    │   └── run_all_benchmarks.py   # Batch runner
    └── tests/
        ├── test_ccd.py             # CCD accuracy (MMS convergence)
        ├── test_levelset.py        # CLS advection, reinitialization, curvature
        ├── test_ns_terms.py        # Convection, viscous, surface tension terms
        ├── test_pressure.py        # PPE solve, Rhie-Chow, velocity correction
        └── test_time_integration.py# WENO5 spatial order (≥4.8), TVD-RK3 temporal order (≥2.8)
```

## **2. Interfaces (ABCs)**

| ABC | Module | Key Method |
|-----|--------|-----------|
| `ILevelSetAdvection` | `interfaces/levelset.py` | `advance(psi, velocity, dt) → psi_new` |
| `IReinitializer` | `interfaces/levelset.py` | `reinitialize(psi) → psi_reinit` |
| `ICurvatureCalculator` | `interfaces/levelset.py` | `compute(psi) → kappa` |
| `INSTerm` | `interfaces/ns_terms.py` | (forcing term interface, no single canonical method) |
| `IPPESolver` | `interfaces/ppe_solver.py` | `solve(vel_star, rho, dt) → p_new` |

## **3. Config Hierarchy**

```python
SimulationConfig
├── GridConfig        # N (grid size), L (domain size), ndim
├── FluidConfig       # rho_l, rho_g, mu_l, mu_g, sigma, g
├── NumericsConfig    # eps (interface width), ccd_order, weno_order
└── SolverConfig      # solver_type ("pseudotime"|"bicgstab"), dt, t_end, ...
```

**Bridge dataclasses** (not sub-configs; live in `core/`):

- `SimulationComponents` — all assembled components passed from `SimulationBuilder` → `TwoPhaseSimulation._from_components()`. Adding a new component requires only a new field here (OCP).
- `FlowState` — single-timestep field aggregate: `velocity`, `psi`, `rho`, `mu`, `kappa`, `pressure`. Passed between `step_forward()`, `Predictor.compute()`, etc.

## **4. SOLID Design & Construction Rules**

- **No Direct Instantiation:** `TwoPhaseSimulation.__init__` is deleted. Build exclusively via `SimulationBuilder(cfg).build()`.
- **_from_components() Pattern:** `TwoPhaseSimulation._from_components(components: SimulationComponents)` is the private factory method called by `SimulationBuilder.build()`. It accepts one argument instead of 15.
- **Dependency Injection:** All components (e.g., `IReinitializer`, `ICurvatureCalculator`, `RhieChowInterpolator`) are injected via constructors. `SimulationBuilder` orchestrates this.
- **OCP for PPE solvers:** To add a new PPE solver: (1) implement `IPPESolver`, (2) register in `ppe_solver_factory.py`. Never modify `TwoPhaseSimulation`.
- **SRP:** `BoundaryConditionHandler`, `DiagnosticsReporter`, `CheckpointManager` are decoupled from numerical solvers.
- **No Global Mutable State:** `rho`, `u`, `p`, `psi` are passed explicitly. Use `FlowState` for bundling.

## **5. Implementation Constraints**

- **Backend:** `xp = backend.xp` everywhere. NEVER hardcode `numpy`.
- **Dimension Agnostic:** Support `ndim = 2` or `3` where possible.
- **Vectorization:** Prefer vectorized array operations. Avoid Python loops over grid points.
- **Testing:** Every new feature requires a pytest test (preferably MMS) checking L1, L2, L∞ norms.
- **Algorithm Sync:** Codebase must track paper's theoretical developments. New paper logic → implementation.
- **Default vs. Alternative:** Paper's primary scheme = default behavior. Alternatives (discussed in columns/appendices) must be switchable via config, not hardcoded.
- **Algorithm Fidelity:** NEVER alter an algorithm or discretization scheme from the paper. A deviation is always a bug.
- **Implicit Solver Policy:**
  - **PPE (global sparse system):** Use **iterative solver (LGMRES) as primary**, with **sparse LU (`spsolve`) as automatic fallback** on non-convergence. Rationale: the global PPE matrix is O(n²) in memory for LU fill-in; iterative is O(n·k). The LU fallback prevents iterative convergence failures from blocking downstream development. See `PPESolverPseudoTime`.
  - **All other implicit systems** (CCD block tridiagonal, Helmholtz 1D sweeps): use **direct LU** (block Thomas algorithm / `spsolve`). These are banded/block-tridiagonal with O(N) fill-in — direct LU is both fast and memory-efficient for them.
  - When introducing a new implicit system, decide by matrix size and structure: banded → direct; large unstructured sparse → iterative-primary with LU fallback.
  - Always document the solver choice and justification inline.
- **Docstrings:** Google-style, English. MUST cite the specific paper equation number(s) implemented (e.g., `Implements eq:rc-face from §7`).
- **MMS Test Standard:** Every new numerical component requires a pytest with Method of Manufactured Solutions. Use N = [32, 64, 128, 256]. Assert `observed_order ≥ expected_order − 0.2` via linear regression on L1/L2/L∞ norms.
- **Test Determinism:** Fix RNG seeds and set `OMP_NUM_THREADS=1` in all tests for reproducibility.
- **Code Comments:** Japanese preferred; English acceptable. Be explicit about physical intent.

## **6. Numerical Algorithm Reference**

### CCD Coefficients

Interior coefficients (uniform grid):
`α₁=7/16, a₁=15/16, b₁=1/16, β₂=−1/8, a₂=3, b₂=−9/8`

Truncation errors:
`TE_I = −(1/7!)h⁶f^(7) = −1/5040·h⁶f^(7)`,  `TE_II = −(2/8!)h⁶f^(8) = −1/20160·h⁶f^(8)`

Block matrices (2×2 per node):
```
A_L = [[ α₁,   +b₁h ],     A_R = [[ α₁,   −b₁h ],
        [+b₂/h,  β₂ ]]              [−b₂/h,  β₂ ]]
```
Numeric: `A_L(2,1) = b₂/h = −9/(8h) < 0`,  `A_R(2,1) = −b₂/h = +9/(8h) > 0`

Left boundary Eq-I (O(h⁵)):
`f'₀ + (3/2)f'₁ − (3h/2)f''₁ = (1/h)(−23/6·f₀ + 21/4·f₁ − 3/2·f₂ + 1/12·f₃)`
Recovery matrix: `M_left = [[−3/2, 3h/2], [5/(2h), −17/2]]`

Left boundary Eq-II (paper, O(h²)):
`f''₀ = (2f₀ − 5f₁ + 4f₂ − f₃) / h²`

Block structure roles: `A_L` (left coupling), `B` (diagonal), `A_R` (right coupling).
Last interior row (i=N-2) uses `C_{N-1}` instead of `A_R` — modified by right boundary scheme.

**CCD Boundary Accuracy (Eq-II-bc limitation):**
The boundary formula for f'' uses a one-sided O(h²) stencil (`f''₀ = (2f₀−5f₁+4f₂−f₃)/h²`).
This couples into the global tridiagonal solve and limits global L∞ accuracy:
- d1 (1st derivative): global L∞ ~ O(h⁴), not O(h⁶). Paper's O(h⁶) claim holds in the interior far from domain boundaries.
- d2 (2nd derivative): global L∞ ~ O(h³), not O(h⁵). Same caveat.
- **Consequence for tests:** MMS convergence order thresholds must account for boundary contamination: d1 ≥ 3.5 (not 5.5), d2 ≥ 2.5 (not 4.5). The 2D axis-independence polynomial must be degree ≤ 3 so Eq-II-bc is exact.

### Time Integration
- **NS convection:** CCD D⁽¹⁾ + Forward Euler O(Δt)
- **CLS advection:** WENO5 + TVD-RK3 (conservative form `∇·(ψu)`)
- **CLS reinitialization:** Pseudo-time, `Δτ=0.25Δs`, N_reinit≈28 steps
- **NS viscous/pressure:** Crank-Nicolson O(Δt²) via Helmholtz decomposition

**WENO5 Periodic BC — Ghost Cell Rule (node-centered grid):**
On a node-centered periodic grid, node index Nx equals node index 0 (same physical point — duplicate endpoint).
Ghost cells must **skip the duplicate endpoint**:
```python
left  = arr[Nx-1-n_ghost : Nx-1]   # arr[Nx-3:Nx] — does NOT include arr[Nx]
right = arr[1 : 1+n_ghost]          # arr[1:4]   — does NOT start from arr[0]
```
Wrap-around divergence at the periodic boundary nodes:
```python
div[0] = div[Nx] = (flux_face[0] - flux_face[-1]) / h
```
Setting `div[0]=div[Nx]=0` unconditionally causes O(dt²/h) error in TVD-RK3 stages 2 and 3, degrading spatial order to ~O(1/h) and temporal order to ~O(h/dt). Always compute the wrap-around flux difference.

### PPE Factory
```python
create_ppe_solver(solver_type, backend, config, grid) -> IPPESolver
# "pseudotime" → PPESolverPseudoTime (default, paper-primary)
# "bicgstab"   → PPESolver
```

**PPESolverPseudoTime — Kronecker Product Assembly + LGMRES / LU fallback:**
The solver assembles the 2D CCD-Poisson operator via Kronecker products (C-order flat index k=i·Ny+j):
```python
L = diag(1/ρ) @ (kron(D2x, I_Ny) + kron(I_Nx, D2y))
    - diag(∂ρ_x/ρ²) @ kron(D1x, I_Ny)
    - diag(∂ρ_y/ρ²) @ kron(I_Nx, D1y)
```
Solve strategy: LGMRES primary (O(n·k) memory, warm start from p_init),
spsolve (SuperLU) fallback on non-convergence (info != 0).
Paper ref: `appendix_ccd_impl.tex` §app:ccd_kronecker, §app:ccd_lu_direct.

**CAUTION — C-order vs. Fortran-order (KL-08):**
kron(D_axis0, I_Ny) is correct for x-derivatives (slow index) ONLY in C-order.
Never swap kron argument order without updating the data layout accordingly.

**PPESolverPseudoTime — CCD Laplacian Null-Space (Known Limitation):**
The 2D CCD Laplacian has an **8-dimensional null space** (e.g., rank 17/25 for N=4) with condition
number ~1e17 after pinning one node. `spsolve` returns a numerically garbage solution; the algebraic
residual `‖Lp − q‖₂` is O(‖q‖₂) even when the physical solution is correct.
- **Algebraic residual tests are suppressed** for this solver — do not reinstate them without first
  implementing null-space deflation (project q and p onto the range of L before and after solve).
- Root cause: compact one-sided boundary stencils (Eq-II-bc) break the translation-invariance that
  would make the null space 1-dimensional. Upgrading Eq-II-bc to an O(h⁴) or higher formula is the
  clean fix; see §8b and ARCHITECTURE §6 CCD Boundary Accuracy.

### Rhie-Chow / Balanced-Force
Face density uses `(1/ρⁿ⁺¹)^harm_f` (current time step). `ρⁿ⁺¹` is available because CLS advection (Step 3 of the 7-step algorithm) updates density before the Predictor (Step 5) and PPE solve (Step 6). Using `ρⁿ` here would be stale and inconsistent with the algorithm order.
Balanced-Force: with CCD-based curvature, numerical discretization error cancels and parasitic currents are dominated by CSF model error O(h²) — NOT h⁴ as the unbalanced `h^{p-2}` formula would suggest.
