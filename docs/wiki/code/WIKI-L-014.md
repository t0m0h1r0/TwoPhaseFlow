---
id: WIKI-L-014
title: "Config-Driven Experiment Framework: ExperimentConfig, NS Pipeline, Unified Runner"
status: REFERENCE
created: 2026-04-10
updated: 2026-04-10
superseded_by: WIKI-X-041
depends_on: [WIKI-L-009, WIKI-X-041]
---

# Config-Driven Experiment Framework

> Curation note (CHK-RA-WIKI-REVIEW-RECUR-001, 2026-05-05):
> Retain this as provenance for the YAML-runner migration.  The listed
> `TwoPhaseNSSolver`, five-stage loop, and file locations are not a current
> implementation map.  Use the active project map and `WIKI-X-041` before
> editing experiment runners or configs.

## Motivation

§13 benchmarks (8 experiments) share a common 5-stage NS predictor-corrector loop.
Without library support, each script duplicated ~200 lines of solver setup, CCD/PPE
initialization, and the time-stepping loop.  Refactoring yielded a 3-layer architecture
where **YAML is the single source of truth** for all experiment parameters.

## Architecture

```
YAML config ──→ ExperimentConfig ──→ TwoPhaseNSSolver ──→ run_simulation()
                       │                                        │
                       ├── GridCfg                              ├── DiagnosticCollector
                       ├── PhysicsCfg (derived physics)        ├── PlotFactory
                       ├── RunCfg                               └── results dict
                       ├── OutputCfg (figures: spec)
                       ├── initial_condition (dict)
                       ├── initial_velocity (dict|null)
                       ├── boundary_condition (dict|null)
                       └── sweep (list|null)
```

### Key files

| File | Role |
|------|------|
| `src/twophase/config_io.py` | `ExperimentConfig` dataclass + YAML loader + derived physics |
| `src/twophase/ns_pipeline.py` | `TwoPhaseNSSolver` (solver setup) + `run_simulation(cfg)` |
| `src/twophase/diagnostics.py` | `DiagnosticCollector` — 7 per-step metrics |
| `src/twophase/plot_factory.py` | `generate_figures(cfg, results, outdir)` from YAML spec |
| `experiment/ch13/run.py` | Unified runner: single/sweep dispatch, `--plot-only`, `--all` |

## ExperimentConfig Design

### Derived physics resolution (`_parse_physics`)

Non-dimensional parameters in YAML are resolved to physical quantities at load time:

| Input | Formula | Output |
|-------|---------|--------|
| `Re`, `d_ref`, `g_acc` | μ = ρ_l √(g d) d / Re | `mu` |
| `Eo`, `d_ref`, `g_acc` | σ = g(ρ_l−ρ_g) d² / Eo | `sigma` |
| `Ca`, `mu_g`, `gamma_dot`, `R_ref` | σ = μ_g γ̇ R / Ca | `sigma` |
| `lambda_mu`, `mu_g` | μ_l = λ μ_g | `mu_l` |

Priority: explicit values override derived values (e.g. if both `sigma` and `Eo` given,
`sigma` wins).

### override() method

Supports dot-notation for nested fields:

```python
cfg2 = cfg.override(**{"physics.sigma": 0.02, "grid.NX": 128})
```

Special case: `physics.lambda_mu` triggers `mu_l = λ × mu_g` re-computation.

### IC normalization (`_normalise_ic_dict`)

Three YAML formats accepted, all normalized to `InitialConditionBuilder.from_dict`:

1. **Builder format**: `{background_phase: ..., shapes: [...]}`
2. **Single-shape shorthand**: `{type: circle, center: [...], ...}` → auto-wraps
3. **Union shorthand**: `{type: union, shapes: [...]}` → multi-body

Background phase is inferred from shapes' `interior_phase` (gas shape → liquid background).

## TwoPhaseNSSolver: 5-Stage Loop

```
step(psi, u, v, dt, ...) → (psi, u, v, p)
```

| Stage | Operation | Skip condition |
|-------|-----------|----------------|
| 1 | Advect ψ (DCCD) + reinitialize (every 2 steps) | — |
| 2 | Curvature κ + HFE filter + CSF force f = σκ∇ψ | σ = 0 |
| 3 | NS predictor: convection + viscous + buoyancy | — |
| 4 | PPE (balanced-force: div(f/ρ) added to RHS) | — |
| 5 | Velocity corrector + BC hook | — |

### Variable viscosity

When `mu_l` and `mu_g` are both given, viscosity is recomputed after advection:
μ(x) = μ_g + (μ_l − μ_g) ψ(x).  This tracks the interface as ψ evolves.

### BC hook pattern

`make_bc_hook(cfg)` returns a callable `hook(u, v) → None`:
- `wall` → zero all boundaries
- `couette` → u = ±U at y boundaries, Neumann lateral
- `None` (periodic) → no-op

## Sweep: Declarative Parameter Study

YAML `sweep:` section defines parametric studies without Python code:

```yaml
sweep:
  - label: "sigma=0.02"
    overrides: {physics.sigma: 0.02}
  - label: "sigma=0.05"
    overrides: {physics.sigma: 0.05}
```

The unified runner (`run.py`) iterates over cases, calling
`run_simulation(cfg.override(**overrides))` for each.  Results are saved
as `{label}/{key}` in a single npz file.

## DiagnosticCollector: 7 Metrics

| Key | Formula | Usage |
|-----|---------|-------|
| `volume_conservation` | \|ΔV\| / V₀ | all experiments |
| `kinetic_energy` | ½ Σ ρ\|u\|² h² | blowup guard (always on) |
| `mean_rise_velocity` | ∫ v dA_gas / V_gas | bubble rise (§13.3, 13.6, 13.7) |
| `bubble_centroid` | (x_c, y_c, v_c) from gas mask | rising bubble tracking |
| `deformation` | D = (L−B)/(L+B) from 2nd moments | capillary wave, Taylor |
| `interface_amplitude` | max \|y_int − y_mid\| on ψ=0.5 | RT instability |
| `laplace_pressure` | \|Δp_sim − σ/R\| / (σ/R) | static droplet |

## PlotFactory: YAML-Driven Figures

Supported figure types in `output.figures:`:

| Type | Description |
|------|-------------|
| `snapshot` | ψ colour map + ψ=0.5 contour at specified time index |
| `time_series` | Diagnostic(s) vs time; optional analytical overlay |
| `convergence` | Log-log error vs h with O(h^p) reference slopes |
| `deformation_comparison` | D vs Ca with Taylor (1932) theoretical lines |

Analytical overlays: `prosperetti` (damped oscillation), `taylor` (D = f(Ca,λ)),
`rt_exponential` (linear RT growth).

## Lesson Learned

- **YAML-first design** eliminates script proliferation: 8 scripts → 1 runner + 8 YAML files
- **Derived physics in config loader** prevents formula duplication across scripts
- **IC normalization** (3 formats → 1) avoids forcing users to know the builder API
- **override() with dot-notation** enables sweep without sub-config reconstruction
