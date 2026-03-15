# HANDOVER

Last update: 2026-03-15
Status: Implementation complete

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

# Important

Previous `base/` directory has been removed.

Do not reference it.

---

# TODO

- GPU optimization (CuPy kernels)
- Non-uniform grid tests
- 3D verification
- Periodic boundary support
- Output writers (VTK / HDF5)

---

# Possible Next Tasks

1. Rising bubble benchmark
2. Zalesak disk test
3. GPU backend verification
4. 3D test case