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

## Execution Environment

When working from a sibling git worktree, the reusable local Python environment
lives in the top checkout:

```bash
../TwoPhaseFlow/.venv/bin/python
```

Run expensive experiments on the external Python server through `remote.sh`:

```bash
./remote.sh check
./remote.sh push
./remote.sh run experiment/ch12/exp12_XX_name.py
./remote.sh pull
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

## Research-Agent Prompt System

The shared metaprompt kernel is managed as a Git submodule at
`prompts/meta/`. This project keeps its project-specific profile in
`prompts/meta/kernel-project.md`; the user edits that file to define project
identity, PR-1..PR-6 rules, path conventions, validation commands,
remote/local execution policy, forbidden shortcuts, and portability notes.

Use `make sync-research-agent` or `python scripts/sync_research_agent.py` to
sync the submodule. The helper preserves `prompts/meta/kernel-project.md`
across the submodule update before redeploying generated prompts, skills, and
reports. See [prompts/README.md](prompts/README.md) and
[prompts/meta/README.md](prompts/meta/README.md) for the full deployment
contract.

## Paper

The `paper/` directory is a self-contained XeLaTeX document. Build with:

```bash
cd paper && latexmk
```

See [docs/ACTIVE_STATE.md](docs/ACTIVE_STATE.md) for current project status.
