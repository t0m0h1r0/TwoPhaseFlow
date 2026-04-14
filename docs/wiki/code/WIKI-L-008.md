---
id: WIKI-L-008
title: "Library Architecture: Module Hierarchy, Design Patterns, and Dependency Flow"
status: ACTIVE
created: 2026-04-10
updated: 2026-04-15
depends_on: [WIKI-L-001, WIKI-X-005]
---

# Library Architecture Overview

## Module Hierarchy (chapter-aligned, restructured 2026-04-15)

```
src/twophase/
├── ccd/                   # §5 CCD solver kernels
│   ├── ccd_solver.py      # CCDSolver: differentiate, _wall/_periodic
│   └── block_tridiag.py   # Block-tridiagonal LU factorization
├── core/                  # §3–§4 Shared data structures
│   ├── field.py           # ScalarField, VectorField
│   ├── flow_state.py      # FlowState dataclass
│   ├── grid.py            # Grid (uniform + interface-fitted)
│   ├── components.py      # SimulationComponents (17 fields)
│   ├── boundary.py        # BCType enum, BoundarySpec, pad_ghost_cells
│   └── metrics.py         # Grid metrics (Jacobian, dV)
├── coupling/              # §8 Interface coupling (NEW — split from ns_terms/)
│   ├── gfm.py             # Ghost Fluid Method
│   ├── ppe_rhs_gfm.py     # GFM-augmented PPE RHS
│   └── velocity_corrector.py  # Velocity correction step
├── hfe/                   # §8 Hermite Field Extension
│   ├── field_extension.py # HFE core
│   ├── hermite_interp.py  # Hermite interpolation
│   └── interfaces.py      # IFieldExtension
├── levelset/              # §6–§7 CLS physics
│   ├── advection.py       # DissipativeCCDAdvection, LevelSetAdvection
│   ├── reinitialize.py    # Reinitializer facade
│   ├── reinit_split.py    # Operator-split strategy
│   ├── reinit_unified.py  # Unified DCCD strategy
│   ├── reinit_dgr.py      # DGR strategy
│   ├── curvature.py       # CurvatureCalculator
│   ├── curvature_psi.py   # ψ-based curvature (invariance)
│   ├── compact_filters.py # Compact/Lele filters
│   └── interfaces.py      # ILevelSetAdvection, IReinitializer, ICurvatureCalculator
├── ns_terms/              # §9 NS RHS terms
│   ├── convection.py      # ConvectionTerm
│   ├── gravity.py         # GravityTerm
│   ├── surface_tension.py # SurfaceTensionTerm
│   ├── viscous.py         # ViscousTerm (delegates to cn_advance/)
│   └── interfaces.py      # INSTerm (marker)
├── ppe/                   # §8 PPE solvers (RENAMED from pressure/)
│   ├── factory.py         # PPE solver factory registry
│   ├── ccd_ppe_base.py    # _CCDPPEBase template method
│   ├── ccd_lu.py          # PPESolverCCDLU (ch11-only, see WIKI-X-009)
│   ├── iterative.py       # GMRES+DC iterative solver
│   ├── fd_ppe_matrix.py   # FD PPE matrix assembly
│   ├── thomas_sweep.py    # Thomas algorithm for tridiag
│   ├── iim/               # Immersed Interface Method
│   ├── interfaces.py      # IPPESolver
│   └── ppe_builder.py     # PPE assembly helper
├── spatial/               # §5 Spatial operators (NEW)
│   ├── rhie_chow.py       # Rhie-Chow interpolation
│   └── dccd_ppe_filter.py # DCCD-based PPE filter
├── time_integration/      # §6,§9 Time integration (EXPANDED)
│   ├── ab2_predictor.py   # AB2 predictor (moved from ns_terms/)
│   ├── cn_advance/        # CN viscous advance strategies (NEW, see WIKI-L-016)
│   │   ├── base.py        # ICNAdvance protocol
│   │   ├── picard_cn.py   # PicardCNAdvance (Heun, O(Δt²))
│   │   └── richardson_cn.py  # RichardsonCNAdvance (O(Δt³/⁴))
│   ├── cfl.py             # CFL calculator
│   └── tvd_rk3.py         # TVD-RK3 for reinit
├── simulation/            # §10 Orchestration
│   ├── builder.py         # SimulationBuilder (sole construction path)
│   ├── _core.py           # TwoPhaseSimulation run loop
│   ├── ns_pipeline.py     # Per-timestep NS pipeline
│   └── boundary_condition.py  # BC handler
├── tools/                 # Infrastructure (NEW — split from experiment/)
│   └── plot_factory.py    # Plot style factory
├── config.py              # SimulationConfig (sub-config composition)
├── config_io.py           # Config file loading helpers
├── backend.py             # numpy/cupy xp dispatch
├── linalg_backend.py      # thomas_batched, solve helpers
└── tests/                 # Unit + integration tests
```

### Restructure Summary (2026-04-15, commit bbbd4f1 + aced15c)

- `pressure/` → `ppe/`: aligns with paper §8 terminology
- `ns_terms/predictor.py` → `time_integration/ab2_predictor.py`: SRP separation
- `ns_terms/cn_advance.py` → `time_integration/cn_advance/` subpackage: Strategy pattern
- New `coupling/`: GFM + velocity corrector extracted from ns_terms
- New `spatial/`: Rhie-Chow + DCCD filter extracted from ns_terms
- New `tools/`: plot infrastructure extracted from experiment toolkit

## Design Patterns in Use

| Pattern | Location | Purpose |
|---------|----------|---------|
| **Builder** | `SimulationBuilder` | Sole construction path for TwoPhaseSimulation (ASM-001) |
| **Strategy** | `reinit_split/unified/dgr` | Swappable reinitialization algorithms |
| **Strategy** | `cn_advance/picard_cn/richardson_cn` | Swappable viscous time-advance (see [[WIKI-L-016]]) |
| **Decorator** | `RichardsonCNAdvance(base)` | Richardson extrapolation wrapping any ICNAdvance |
| **Facade** | `Reinitializer` | Delegates to strategy based on `method` parameter |
| **Template Method** | `_CCDPPEBase` | Shared matrix assembly; subclasses override `_solve_linear_system()` |
| **Factory Registry** | `ppe/factory.py` | OCP-compliant `_SOLVER_REGISTRY` dict for PPE solver creation |
| **Null Object** | `NullFieldExtender` | Eliminates null checks in orchestration loop |
| **Marker Interface** | `INSTerm` | Type tag for NS terms without enforcing unified signature |
| **DIP** | All interfaces | High-level modules depend on abstractions, not concretes |

## Dependency Flow (strict layering)

```
core/  ←──  ccd/
  ↑          ↑
  │          │
levelset/  ns_terms/  ppe/  spatial/  coupling/
  ↑          ↑         ↑       ↑         ↑
  └──────────┴─────────┴───────┴─────────┘
                       │
            time_integration/  (ab2_predictor, cn_advance/)
                       │
              simulation/builder.py  (assembly point)
                       │
              simulation/_core.py    (orchestration)
```

**A9 enforcement**: `core/` has zero dependency on `simulation/`. Infrastructure (`tools/`) may import core but never vice versa.

## Top-Level API

```python
from twophase import Backend, SimulationConfig, SimulationBuilder, TwoPhaseSimulation

sim = SimulationBuilder(config).build()
sim.run(t_end=1.0, callback=my_callback)
```

Only 4 symbols exported at package level. All construction goes through `SimulationBuilder.build()`.

## SimulationComponents Dataclass (17 fields)

Replaces 15+ parameter constructor signatures. Adding a new component requires only:
1. Add field to `SimulationComponents`
2. Wire it in `SimulationBuilder.build()`
3. Use it in `TwoPhaseSimulation._from_components()`

Core fields: config, backend, grid, eps, ccd, ls_advect, ls_reinit, curvature_calc, predictor, ppe_solver, rhie_chow, vel_corrector, cfl_calc, bc_handler, diagnostics.
Optional: ppe_rhs_gfm (GFM mode), field_extender (NullFieldExtender when disabled).
