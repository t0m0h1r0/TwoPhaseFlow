# TwoPhaseFlow

High-order CFD solver for gas-liquid two-phase flow, combining a 6th-order CCD spatial scheme, Conservative Level Set interface tracking, and a variable-density Navier-Stokes projection method.

## Repository Layout

```
paper/          Mathematical specification (XeLaTeX, 106 pages)
src/twophase/   Python implementation
docs/           Workflow prompts and project state
```

## Quick Start

```bash
pip install -e src/
```

```python
from twophase import SimulationConfig, SimulationBuilder
from twophase.config import GridConfig, FluidConfig, NumericsConfig

cfg = SimulationConfig(
    grid=GridConfig(ndim=2, N=(64, 64), L=(1.0, 1.0)),
    fluid=FluidConfig(Re=100., Fr=1., We=10., rho_ratio=0.1, mu_ratio=0.1),
    numerics=NumericsConfig(t_end=0.5, cfl_number=0.3),
)
sim = SimulationBuilder(cfg).build()
sim.run(output_interval=20, verbose=True)
```

See [src/README.md](src/README.md) for full module structure, algorithm table, and configuration reference.

## Tests

```bash
cd src && pytest -v   # 28 tests passing
```

## Paper

The `paper/` directory is a self-contained XeLaTeX document. Build with:

```bash
cd paper && latexmk
```

See [docs/ACTIVE_STATE.md](docs/ACTIVE_STATE.md) for current project status.
