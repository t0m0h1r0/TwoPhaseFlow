# HANDOVER

Last update: 2026-03-17 (12_REVIEW complete)
Status: Paper revised (102 pages, clean compile); 28 tests passing

---

## Current State

### Code (`src/twophase/`)

| Aspect | State |
|--------|-------|
| Tests | 28 passed (`pytest src/twophase/tests`) |
| Config | `SimulationConfig` = pure sub-config composition (`GridConfig` / `FluidConfig` / `NumericsConfig` / `SolverConfig`) |
| Construction | `SimulationBuilder` is sole path — `TwoPhaseSimulation.__init__` deleted |
| CCD injection | Constructor injection throughout (`Reinitializer`, `CurvatureCalculator`, `RhieChowInterpolator`, `VelocityCorrector`, `Predictor`) |
| PPE solvers | `PPESolver` (BiCGSTAB) + `PPESolverPseudoTime` (MINRES), unified `IPPESolver` ABC |
| Time integration | TVD-RK3 for CLS reinitialization; projection method (predictor-PPE-corrector) for NS |
| CFL | Convection + capillary wave (`Δt_σ`) constraints; viscous excluded when `cn_viscous=True` |
| Benchmarks | rising_bubble, zalesak_disk, rayleigh_taylor, stationary_droplet |
| Visualization | `plot_scalar`, `plot_vector`, `RealtimeViewer` |
| I/O | `CheckpointManager` (HDF5 / npz), `config_loader` (YAML) |

### Paper (`paper/`)

**Chapter structure (11 chapters, 4 parts):**

```
Part I   Ch.1 Introduction, Ch.2 Governing equations
Part II  Ch.3 CLS method,   Ch.4 Time integration (WENO5, TVD-RK3, stability)
Part III Ch.5 CCD method,   Ch.6 Grid (interface-fitted), Ch.7 Collocate (Rhie-Chow, BF),
                             Ch.8 Variable-density PPE (FVM + CCD-Poisson, unit tests C-1/C-2/C-3)
Part IV  Ch.9 Full algorithm, Ch.10 Verification (benchmarks), Ch.11 Conclusion
```

Key placements:
- CCD-Poisson unit tests (C-1/C-2/C-3) — moved to §8 (`07_pressure.tex`); Ch.10 has pointer mybox only
- `tab:accuracy_summary` + accuracy-mismatch warnbox — in §8, removed from Ch.11
- `fig:ns_solvers` — in Ch.9 intro
- `fig:algo_flow` — concept-level only in Ch.1

---

## Outstanding Issues (from 12_REVIEW — highest priority first)

### D: Critical — Definitions & Correctness

| ID | Issue | File | Action |
|----|-------|------|--------|
| D-1 | PPE dual-definition: §8.2-8.3 derives FVM harmonic mean but §8.4 + Ch.9 implement CCD differential form `(1/ρ)D²p − (∂ρ/ρ²)Dp`; `tab:accuracy_summary` incorrectly labels it "FVM+CCD" | `07_pressure.tex`, `09_full_algorithm.tex` | Delete FVM derivation or explicitly label it as motivation; relabel table row |
| D-2 | §8.3 boundary-condition derivation for CCD-Poisson: ghost-cell condition for variable-density case is stated without proof | `07_pressure.tex` | Add derivation or cite |

### B: Significant — Missing Content

| ID | Issue | File | Action |
|----|-------|------|--------|
| B-3 | WENO5 needs 6-point stencil (i−2 to i+3) — boundary treatment (padding / one-sided) completely absent | `08_time_integration.tex` | Add boundary stencil subsection |
| B-4 | CN viscous term: `µ(∂u*/∂y + ∂v*/∂x)` cross-derivative couples u* and v* — manuscript implies independent block-tridiagonal solves, which is incorrect | `08_time_integration.tex` | Clarify: decouple by freezing cross terms or use ADI |

### C: Minor — Clarity & Consistency

| ID | Issue | File |
|----|-------|------|
| C-1 | `tab:chapter_overview` row for Ch.5 CCD omits mention of pseudo-time interpretation | `01_introduction.tex` |
| C-2 | §3.4 Newton inversion convergence: quadratic convergence claim lacks proof or reference | `03_levelset.tex` |
| C-3 | §6.2 Rhie-Chow: harmonic density coefficient derivation refers to §8 (forward reference) | `06_collocate.tex` |
| C-4 | §9 Step 4 (curvature update): CCD stencil across density jump not discussed | `09_full_algorithm.tex` |

### M: Minor — Notation & Typos

| ID | Issue | File |
|----|-------|------|
| M-1 | §2.5 CSF: `δ_ε(ψ)` definition inconsistent with §3.1 | `02_governing.tex` |
| M-2 | §4.2 WENO5 coefficients table: `d₀,d₁,d₂` should be `3/10, 3/5, 1/10` | `08_time_integration.tex` |
| M-3 | §5.3 CCD matrix: missing factor 2 in off-diagonal block for Neumann BC | `04_ccd.tex` |
| M-4 | §8.4 capillary wave stability: coefficient sign `+` vs `−` in dispersion relation | `07_pressure.tex` |
| M-5 | §10.2 Zalesak disk: area error formula uses L2 but text says L1 | `10_verification_metrics.tex` |

---

## Possible Next Tasks

### Paper (priority order)
1. Fix D-1 — resolve PPE dual-definition (most important for correctness)
2. Fix B-3 — add WENO5 boundary stencil treatment
3. Fix B-4 — clarify CN viscous cross-derivative coupling
4. Fix M-2/M-3/M-4 — notation typos (quick wins)

### Code
1. Run benchmarks at higher resolution (N=128) and compare to reference values
2. GPU backend verification (CuPy)
3. 3D test case
4. VTK output writer

---

## Important Notes

- `base/` directory has been removed — do not reference it
- File numbering ≠ chapter numbering: `08_time_integration.tex` = Ch.4, `04_ccd.tex` = Ch.5, `05_grid.tex` = Ch.6, `06_collocate.tex` = Ch.7, `07_pressure.tex` = Ch.8
- Backend: always use `xp = backend.xp` (no global mutable state)
