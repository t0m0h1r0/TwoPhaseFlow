# HANDOVER

Last update: 2026-03-17 (13_UPDATE complete — all D/B/C issues resolved)
Status: Paper revised (clean compile); 28 tests passing

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
                             Ch.8 Variable-density PPE (FVM motivation + CCD-Poisson O(h⁶))
Part IV  Ch.9 Full algorithm, Ch.10 Verification (benchmarks), Ch.11 Conclusion
```

**File numbering ≠ chapter numbering:**
`08_time_integration.tex`=Ch.4, `04_ccd.tex`=Ch.5, `05_grid.tex`=Ch.6,
`06_collocate.tex`=Ch.7, `07_pressure.tex`=Ch.8

Key facts established in previous sessions:
- `07_pressure.tex` (`tab:accuracy_summary`): PPE uses CCD-Poisson O(h⁶) — already updated
- FVM harmonic mean section in `07_pressure.tex` is **motivation only** (not the actual solver)
- CCD-Poisson unit tests (C-1/C-2/C-3) — in §8 (`07_pressure.tex`); Ch.10 has pointer only
- `fig:ns_solvers` — in Ch.9 intro; `fig:algo_flow` — concept-level only in Ch.1

---

## Outstanding Issues (from 12_REVIEW 2nd pass — all resolved by 13_UPDATE 2026-03-17)

### D: Critical (✅ all resolved)

| ID | Resolution |
|----|-----------|
| D-1 | `10_verification_metrics.tex` `tab:error_budget` updated to CCD-PPE O(h⁶); warnbox replaced with accuracy-design summary box |
| D-1b | `11_conclusion.tex` rewritten: FVM-PPE O(h²) → CCD-PPE O(h⁶) as fact; "future work" item replaced with PPE solver scalability |
| D-2 | `02_governing.tex` §2.1 defbox fixed: "液相でψ≈0，気相でψ≈1"; ρ formula updated to ρ_l+(ρ_g-ρ_l)ψ in two places |

### B: Significant (✅ all resolved)

| ID | Resolution |
|----|-----------|
| B-1 | M_ref defined in `03_levelset.tex` as M_eq = ∫H_ε(φ₀)(1-H_ε(φ₀))dV with implementation note |
| B-2 | `04_ccd.tex` boundary accuracy: added quantitative analysis showing O(h²) boundary → O(h³) L2 global error; reference to CCD-Poisson unit tests |
| B-3 | `06_collocate.tex` warnbox extended: RC correction is independent auxiliary stabilizer; Balanced-Force condition operates on main momentum eq. only |
| B-4 | `03_levelset.tex` Newton convergence proof added: 0-step in non-saturated, O(e²) in saturated with F'' bounded derivation |

### C / M (✅ all resolved)

| ID | Resolution |
|----|-----------|
| C-1 | `01_introduction.tex` Ch.5 row updated to include pseudo-time elliptic PPE application |
| M-5 | Already correct (formula `|\psi|dA` and label "$L^1$" agree); no change needed |

## Possible Next Tasks

### Paper
- Next review cycle: `12_REVIEW.md` → find new issues
- LaTeX compile check recommended (all edits are text-level, no package changes)

### Code
1. Run benchmarks at higher resolution (N=128) and compare to reference values
2. GPU backend verification (CuPy)
3. 3D test case
4. VTK output writer

---

## Important Notes

- `base/` directory has been removed — do not reference it
- File numbering ≠ chapter numbering (see table above)
- Backend: always use `xp = backend.xp` (no global mutable state)
- PPE solver is CCD-Poisson O(h⁶) — the FVM section in `07_pressure.tex` is **motivation only**
