# HANDOVER

Last update: 2026-03-15
Status: Extended with visualization / IO / YAML config / benchmarks

---

# Current State

Two-phase flow solver implemented from scratch.

All tests pass.

```
pytest src/twophase/tests
→ 28 passed
```

Python ≥ 3.9

---

# Recent Changes (2026-03-15)

## Pressure solver improvements

### `src/twophase/pressure/rhie_chow.py`
- Vectorized `_rc_flux_1d`: replaced Python `for` loop with `slice`-based numpy ops.

### `src/twophase/pressure/ppe_solver.py`
- Added `p_init` (warm-start) parameter to `solve()`.
- `simulation.py` now passes previous-step pressure `p^n` as `x0` to BiCGSTAB.

### `src/twophase/pressure/ppe_solver_pseudotime.py` (new)
- `PPESolverPseudoTime`: alternative solver using **MINRES** + warm-start.
- Assembles the same FVM matrix as `PPEBuilder` but uses **symmetric pinning**
  (row AND column 0 zeroed), preserving matrix symmetry for MINRES.
- Warm-starts from `p^n` for fast convergence on slowly-varying solutions.
- Enabled via `SimulationConfig(ppe_solver_type="pseudotime")`.

### `src/twophase/config.py`
- New fields: `ppe_solver_type` (`"bicgstab"` | `"pseudotime"`),
  `pseudo_tol`, `pseudo_maxiter`.

### `src/twophase/simulation.py`
- Solver selection based on `config.ppe_solver_type`.
- BiCGSTAB path passes `p_init=self.pressure.data` (warm-start).
- MINRES path calls `PPESolverPseudoTime.solve(p_init, rhs, rho, ccd)`.

---

# Recent Changes (2026-03-15) — Visualization / IO / Config / Benchmarks

## New modules

### `src/twophase/visualization/`
- `plot_scalar.py` — 2D scalar field plots (pressure, ψ, density). `plot_multi_field` for side-by-side layout.
- `plot_vector.py` — velocity magnitude+quiver, vorticity (via CCD), streamlines.
- `realtime_viewer.py` — `RealtimeViewer`: matplotlib interactive callback for `sim.run(callback=viewer)`.

### `src/twophase/io/checkpoint.py`
- `CheckpointManager`: HDF5 (h5py) or npz fallback.
- `save(sim)` / `restore(sim, path)` / `make_callback(interval)`.
- Saves: step, time, ψ, pressure, velocity (all axes), SimulationConfig JSON.
- After `restore()` calls `_update_properties()` + `_update_curvature()` automatically.

### `src/twophase/configs/config_loader.py`
- `load_config(path)` → `(SimulationConfig, output_cfg_dict)`.
- `config_to_yaml(config, path)` for config export.
- Unknown YAML keys emit `UserWarning` (not error).

### `src/twophase/benchmarks/`
- `rising_bubble.py` — Hysing et al. (2009) TC1; records centroid_y, rise velocity, volume error.
- `zalesak_disk.py` — 1-revolution slotted-disk advection test; L1 shape error + volume error.
- `rayleigh_taylor.py` — RT instability; spike/bubble tip tracking.
- `run_all_benchmarks.py` — CLI runner: `python -m twophase.benchmarks.run_all_benchmarks --N 32`.

### `src/main.py`
- CLI entry point: `python src/main.py configs/bubble_2d.yaml [--restart PATH] [--visualize] [--benchmark]`.

### `src/configs/`
- `bubble_2d.yaml` — example config (Re=35, N=64×128).
- `rayleigh_taylor.yaml` — example config (Re=3000, N=64×256).

## Updated
- `src/pyproject.toml` — added optional extras: `vis`, `io`, `all`.

---

# Important

Previous `base/` directory has been removed.

Do not reference it.

---

# TODO

- GPU optimization (CuPy kernels)
- Non-uniform grid tests
- 3D verification
- Periodic boundary support
- VTK output writer

---

# Possible Next Tasks

1. Run benchmarks at higher resolution (N=128) and compare to reference values
2. GPU backend verification (CuPy)
3. 3D test case
4. VTK output writer
5. Convergence plots for benchmark problems