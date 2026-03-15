# twophase — Two-Phase Flow Solver

Clean Python implementation of a gas-liquid two-phase flow solver combining:

- **Conservative Level Set (CLS)** — volume-preserving interface tracking
- **CCD (Combined Compact Difference)** — 6th-order spatial derivatives
- **WENO5** — shock-capturing advection for the CLS field
- **Chorin Projection** — divergence-free velocity correction
- **Rhie-Chow** — checkerboard-suppressing face-velocity interpolation
- **TVD-RK3** — 3rd-order total-variation-diminishing time integration

---

## Quick Start

```bash
pip install -e src/
```

```python
from twophase import SimulationConfig, SimulationBuilder
from twophase.config import GridConfig, FluidConfig, NumericsConfig
import numpy as np

cfg = SimulationConfig(
    grid=GridConfig(ndim=2, N=(64, 64), L=(1.0, 1.0)),
    fluid=FluidConfig(Re=100., Fr=1., We=10., rho_ratio=0.1, mu_ratio=0.1),
    numerics=NumericsConfig(t_end=0.5, cfl_number=0.3),
)
sim = SimulationBuilder(cfg).build()

# Place a circular droplet at (0.5, 0.5) with radius 0.2
X, Y = sim.grid.meshgrid()
eps = 1.5 / 64
phi0 = np.sqrt((X - 0.5)**2 + (Y - 0.5)**2) - 0.2
sim.psi.data[:] = 1.0 / (1.0 + np.exp(-phi0 / eps))

sim.run(output_interval=20, verbose=True)
```

---

## Module Structure & Paper Correspondence

```
src/twophase/
├── backend.py              — numpy/cupy abstraction                     (all)
├── config.py               — GridConfig/FluidConfig/NumericsConfig/SolverConfig + SimulationConfig  (§2.4)
│
├── interfaces/             — ABCs: IPPESolver / INSTerm / ILevelSetAdvection / IReinitializer / ICurvatureCalculator
│
├── simulation/             — SimulationBuilder + TwoPhaseSimulation + BC + Diagnostics  (§9.1)
│
├── core/
│   ├── grid.py             — Grid, metrics, interface-fitted coords      (§5)
│   └── field.py            — ScalarField, VectorField containers
│
├── ccd/
│   ├── ccd_solver.py       — CCD O(h⁶) differentiation                 (§4)
│   └── block_tridiag.py    — Block-tridiagonal LU solver
│
├── levelset/
│   ├── heaviside.py        — H_ε, δ_ε, material property update        (§3.2–3.3)
│   ├── curvature.py        — κ = −∇·(∇φ/|∇φ|) via CCD                 (§2.6)
│   ├── advection.py        — TVD-RK3 + WENO5 CLS advection             (§3.3, §8)
│   └── reinitialize.py     — Godunov reinitialization PDE              (§3.4)
│
├── ns_terms/
│   ├── convection.py       — −(u·∇)u                                   (§9)
│   ├── viscous.py          — ∇·[μ̃(∇u)^sym]/(ρ̃ Re), CN or explicit     (§9)
│   ├── gravity.py          — −ẑ/Fr²                                    (§9)
│   ├── surface_tension.py  — κ ∇ψ / We (CSF model)                    (§2.3)
│   └── predictor.py        — assembles all terms → u*                  (§9.1 Step 5)
│
├── pressure/
│   ├── rhie_chow.py        — face-velocity RC interpolation            (§6.3, §7.4)
│   ├── ppe_builder.py      — variable-density FVM Laplacian (sparse)   (§7.3)
│   ├── ppe_solver.py       — BiCGSTAB with ILU(0)                      (§7.4)
│   ├── ppe_solver_pseudotime.py — MINRES + warm-start alternative
│   ├── ppe_solver_factory.py    — create_ppe_solver(config, backend, grid)
│   └── velocity_corrector.py — u^{n+1} = u* − (Δt/ρ̃)∇p              (§9.1 Step 7)
│
├── time_integration/
│   ├── tvd_rk3.py          — TVD-RK3 (Shu-Osher)                      (§8 Eq.79–81)
│   └── cfl.py              — convective + viscous CFL                  (§8 Eq.84)
│
├── visualization/
│   ├── plot_scalar.py      — 2D scalar field plots
│   ├── plot_vector.py      — velocity magnitude, vorticity, streamlines
│   └── realtime_viewer.py  — RealtimeViewer callback for sim.run()
│
├── io/
│   ├── checkpoint.py       — CheckpointManager (HDF5 / npz)
│   └── serializers.py      — HDF5Serializer / NpzSerializer
│
├── configs/
│   └── config_loader.py    — load_config / load_config_dict / config_to_yaml
│
├── benchmarks/
│   ├── rising_bubble.py    — Hysing et al. TC1
│   ├── zalesak_disk.py     — slotted-disk advection test
│   ├── rayleigh_taylor.py  — RT instability
│   └── run_all_benchmarks.py
│
└── tests/
    ├── test_ccd.py         — CCD O(h⁶) convergence
    ├── test_levelset.py    — volume conservation, Eikonal quality, κ
    ├── test_ns_terms.py    — term-by-term NS accuracy
    └── test_pressure.py    — PPE matrix, BiCGSTAB residual, ∇·u < ε
```

---

## Algorithm (§9.1)

| Step | What happens | Equation |
|------|-------------|---------|
| 1 | CLS advection: ∂ψ/∂t + ∇·(ψu) = 0 | Eq. 16 |
| 2 | Reinitialization: ∂ψ/∂τ + ∇·[ψ(1−ψ)n̂] = ε∇²ψ | Eq. 34 |
| 3 | Properties: ρ̃ = ρ_g + (ρ_l−ρ_g)ψ, μ̃ = … | Eq. 6–7 |
| 4 | Curvature: φ ← H_ε^{-1}(ψ), κ = −∇·(∇φ/|∇φ|) | Eq. 30 |
| 5 | Predictor u*: ρ̃(u*−uⁿ)/Δt = R^{n+1} | Eq. 85 |
| 6 | PPE: ∇·[(1/ρ̃)∇p] = (1/Δt)∇·u*_RC | Eq. 57, 65 |
| 7 | Corrector: u^{n+1} = u* − (Δt/ρ̃)∇p | Eq. 93 |

---

## Key Design Decisions

### Backend injection (`xp`)

Every class receives the array namespace through its constructor.
`backend.py` is the **only** place that imports numpy or cupy:

```python
from twophase.backend import Backend
backend = Backend(use_gpu=True)   # or False
xp = backend.xp                  # np or cp, passed everywhere
```

Mark GPU-specific optimisation points with `# TODO(gpu)`.

### SOLID architecture

- `interfaces/` contains pure ABCs; concrete classes depend only on these.
- `SimulationBuilder` is the **only** place that instantiates concrete classes (SRP/DIP).
- `INSTerm` is a marker interface — NS term classes inherit it with their own `compute()` signatures.
- PPE solvers are selected via `ppe_solver_factory.create_ppe_solver()` — `TwoPhaseSimulation` never references concrete solver classes (OCP).

### Paper over reference code

When the reference implementation conflicts with the paper,
the paper takes precedence.  Known deviations corrected in this implementation:

| Issue | Fix |
|-------|-----|
| PPE matrix built with Python for-loop | Vectorised NumPy indexing in `ppe_builder.py` |
| Crank-Nicolson not implemented | One fixed-point CN iteration in `viscous.py` |
| Interface-fitted grid goes singular at high α | `dx_min_floor` guard in `grid.py` |

---

## Running Tests

```bash
cd src
pip install -e ".[dev]"
pytest -v
```

Expected results (N=32–64 grids):

| Test | Expected |
|------|---------|
| CCD d1 convergence order | ≥ 5.5 |
| CCD d2 convergence order | ≥ 4.5 |
| Volume conservation (1 revolution) | < 2% |
| Eikonal quality near interface | error < 0.2 |
| Circle curvature κ | rel. error < 5% |
| Post-projection divergence | < 1e-6 |

---

## Configuration Reference

`SimulationConfig` is composed of four sub-config dataclasses:

### GridConfig

| Field | Default | Description |
|-------|---------|-------------|
| `ndim` | 2 | Spatial dimension (2 or 3) |
| `N` | (64,64) | Grid cells per axis |
| `L` | (1,1) | Domain lengths |
| `alpha_grid` | 1.0 | 1 = uniform; > 1 = interface-fitted |

### FluidConfig

| Field | Default | Description |
|-------|---------|-------------|
| `Re` | 100 | Reynolds number |
| `Fr` | 1 | Froude number |
| `We` | 10 | Weber number |
| `rho_ratio` | 0.001 | ρ_gas / ρ_liquid |
| `mu_ratio` | 0.01 | μ_gas / μ_liquid |

### NumericsConfig

| Field | Default | Description |
|-------|---------|-------------|
| `t_end` | 1.0 | End time |
| `cfl_number` | 0.3 | CFL safety factor |
| `epsilon_factor` | 1.5 | ε = factor × Δx_min |
| `reinit_steps` | 4 | Reinitialization sub-steps per timestep |
| `cn_viscous` | True | Crank-Nicolson for viscous term |
| `bc_type` | "wall" | Boundary condition type |

### SolverConfig

| Field | Default | Description |
|-------|---------|-------------|
| `ppe_solver_type` | "bicgstab" | "bicgstab" or "pseudotime" |
| `bicgstab_tol` | 1e-6 | BiCGSTAB convergence tolerance |
| `pseudo_tol` | 1e-6 | Pseudo-time solver tolerance |
