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
    │   └── block_tridiag.py        # Block Thomas algorithm (3×3 blocks)
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
    │   ├── ppe_solver_pseudotime.py# PPESolverPseudoTime — pseudo-time implicit (IPPESolver)
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
        ├── test_ccd.py             # CCD accuracy (MMS O(h⁶) convergence)
        ├── test_levelset.py        # CLS advection, reinitialization, curvature
        ├── test_ns_terms.py        # Convection, viscous, surface tension terms
        └── test_pressure.py        # PPE solve, Rhie-Chow, velocity correction
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
- **Docstrings:** Google-style, English. MUST cite the specific paper equation number(s) implemented (e.g., `Implements eq:rc-face from §6`).
- **MMS Test Standard:** Every new numerical component requires a pytest with Method of Manufactured Solutions. Use N = [32, 64, 128, 256]. Assert `observed_order ≥ expected_order − 0.2` via linear regression on L1/L2/L∞ norms.
- **Test Determinism:** Fix RNG seeds and set `OMP_NUM_THREADS=1` in all tests for reproducibility.
- **Code Comments:** Japanese preferred; English acceptable. Be explicit about physical intent.

## **6. LaTeX Authoring Constraints (paper/)**

### Cross-references
- **NO hardcoded references.** Never write "Section 3", "Eq. (5)", "下図", "次章". Always use `\ref{sec:...}`, `\eqref{eq:...}`, `\ref{fig:...}`, `\ref{tab:...}`.

### Page Layout
- **New Page Rule (MANDATORY):** Every `\part{...}` and `\section{...}` MUST begin on a new page. Use `\clearpage` or (for double-sided) `\cleardoublepage`.
- **No Double Breaks:** If a Part and its first Section start consecutively, use ONE page break only (before the Part). Do not insert another `\clearpage` before the Section.

```latex
% Correct
\cleardoublepage
\part{Methodology}
\section{Governing equations}   % no extra \clearpage here

% Standalone section
\clearpage
\section{Numerical method}
```

### tcolorbox Environments

| Environment | Purpose |
|------------|---------|
| `defbox` | Formal definitions (numbered) |
| `warnbox` | Implementation warnings / pitfalls |
| `algbox` | Step-by-step algorithms |
| `mybox` | Supplementary notes / derivation asides |
| `resultbox` | Key numerical results / summary tables |
| `derivbox` | Mathematical derivations (collapsible or inline) |

**Usage rule:** Consistent and sparse — only for governing equations, algorithm boxes, or explicit "column"-style notes. Avoid mixing box types or over-using colors.

### Label Consistency
- Every section, equation, figure, and table must have a descriptive `\label{}`.

### Content Rules
- Move tangential detail to `appendix_proofs.tex`. Do not detour readers in the main text.
- Every equation must be followed by its physical meaning and implementation implications (Pedagogy First).

## **7. Paper Structure**

| File | Chapter | Content |
|------|---------|---------|
| `00_abstract.tex` | Abstract | CCD-PPE O(h⁶), CLS, WENO5, Balanced-Force summary |
| `01_introduction.tex` | §1 Introduction | Background, 4 challenges (§1.2), novelty table (tab:method_comparison) |
| `02_governing.tex` | §2 Governing Equations | One-Fluid NS, CSF, Heaviside, ψ-convention (液相≈0, 気相≈1) |
| `03_levelset.tex` | §3 Level Set Method | CLS advection, reinitialization (Δτ=0.25Δs), logit inverse |
| `04_ccd.tex` | §4 CCD | O(h⁶) scheme, block Thomas solver, boundary scheme (O(h⁵)/O(h²)) |
| `05_grid.tex` | §5 Grid & Discretization | Staggered grid, CCD-based Jacobian (step 5) |
| `06_collocate.tex` | §6 Rhie-Chow & Collocated | Rhie-Chow interpolation with ρⁿ, Balanced-Force condition |
| `07_pressure.tex` | §7 Pressure Solver | Variable-density PPE, pseudo-time implicit, BiCGSTAB (tab:ppe_methods) |
| `08_time_integration.tex` | §8 Time Integration | WENO5 + TVD-RK3, CFL, Godunov LF flux |
| `09_full_algorithm.tex` | §9 Full Algorithm | 7-step loop diagram (fig:ns_solvers), density interpolation |
| `10_verification_metrics.tex` | §10 Verification | Error norms, tab:error_budget (CSF bottleneck O(ε²)≈O(h²)) |
| `11_conclusion.tex` | §11 Conclusion | Summary, Thomas solver (逐次Thomas法), future work |
| `appendix_proofs.tex` | Appendix | 1D One-Fluid proof, logit inverse derivation, Newton convergence |

## **8. Numerical Algorithm Reference**

### CCD Coefficients
`α₁=7/16, a₁=15/16, b₁=1/16, β₂=−1/8, a₂=3, b₂=−9/8`

Block structure (3×3 per node): `A_L` (left coupling), `B` (diagonal), `A_R` (right coupling).
Last interior row (i=N-2) uses `C_{N-1}` instead of `A_R` — modified by right boundary scheme.

### Time Integration
- **NS convection:** CCD D⁽¹⁾ + Forward Euler O(Δt)
- **CLS advection:** WENO5 + TVD-RK3 (conservative form `∇·(ψu)`)
- **CLS reinitialization:** Pseudo-time, `Δτ=0.25Δs`, N_reinit≈28 steps
- **NS viscous/pressure:** Crank-Nicolson O(Δt²) via Helmholtz decomposition

### PPE Factory
```python
create_ppe_solver(solver_type, backend, config, grid) -> IPPESolver
# "pseudotime" → PPESolverPseudoTime (default, paper-primary)
# "bicgstab"   → PPESolver
```

### Rhie-Chow / Balanced-Force
Face density uses `(1/ρⁿ)^harm_f` (previous time step); `ρⁿ⁺¹` is unavailable before PPE solve.
Balanced-Force: CCD curvature evaluation suppresses parasitic currents to O(h⁶).
