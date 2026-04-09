---
id: WIKI-L-008
title: "Library Architecture: Module Hierarchy, Design Patterns, and Dependency Flow"
status: ACTIVE
created: 2026-04-10
depends_on: [WIKI-L-001, WIKI-X-005]
---

# Library Architecture Overview

## Module Hierarchy (~14,900 LOC production code)

```
src/twophase/
├── ccd/                   # CCD solver kernels (670 LOC)
├── core/                  # Shared data structures (332 LOC)
│   ├── field.py           # ScalarField, VectorField
│   ├── flow_state.py      # FlowState dataclass
│   ├── grid.py            # Grid (uniform + interface-fitted)
│   ├── components.py      # SimulationComponents (17 fields)
│   └── boundary.py        # BCType enum, BoundarySpec, pad_ghost_cells
├── interfaces/            # Abstract contracts (239 LOC)
│   ├── ppe_solver.py      # IPPESolver
│   ├── levelset.py        # ILevelSetAdvection, IReinitializer, ICurvatureCalculator
│   ├── ns_terms.py        # INSTerm (marker)
│   └── field_extension.py # IFieldExtension
├── levelset/              # CLS physics (~2,300 LOC)
├── ns_terms/              # NS RHS terms (~250 LOC)
├── pressure/              # PPE solvers + projection (~2,600 LOC)
│   └── legacy/            # C2-retained deprecated solvers
├── hfe/                   # Hermite Field Extension (~350 LOC)
├── time_integration/      # TVD-RK3, CFL (~165 LOC)
├── simulation/            # Orchestration + Builder (~640 LOC)
├── initial_conditions/    # Shape primitives + IC builder
├── io/                    # Checkpoint, VTK writer
├── visualization/         # matplotlib plotting
├── benchmarks/            # Rising bubble, RT, etc.
├── experiment/            # Experiment toolkit (style, IO, plots)
├── config.py              # SimulationConfig (sub-config composition)
└── backend.py             # numpy/cupy abstraction
```

## Design Patterns in Use

| Pattern | Location | Purpose |
|---------|----------|---------|
| **Builder** | `SimulationBuilder` | Sole construction path for TwoPhaseSimulation (ASM-001) |
| **Strategy** | `reinit_split/unified/dgr` | Swappable reinitialization algorithms |
| **Facade** | `Reinitializer` | Delegates to strategy based on `method` parameter |
| **Template Method** | `_CCDPPEBase` | Shared matrix assembly; subclasses override `_solve_linear_system()` |
| **Factory Registry** | `ppe_solver_factory` | OCP-compliant `_SOLVER_REGISTRY` dict for PPE solver creation |
| **Null Object** | `NullFieldExtender` | Eliminates null checks in orchestration loop |
| **Marker Interface** | `INSTerm` | Type tag for NS terms without enforcing unified signature |
| **DIP** | All interfaces | High-level modules depend on abstractions, not concretes |

## Dependency Flow (strict layering)

```
interfaces/  ←──  core/  ←──  ccd/
     ↑                ↑          ↑
     │                │          │
 levelset/       ns_terms/   pressure/
     ↑                ↑          ↑
     └────────────────┴──────────┘
                      │
              simulation/builder.py  (assembly point)
                      │
              simulation/_core.py    (orchestration)
```

**A9 enforcement**: `core/` has zero dependency on `simulation/`. Infrastructure (`io/`, `visualization/`) may import core but never vice versa.

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
