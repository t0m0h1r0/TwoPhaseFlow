# ARCHITECTURE

## §1 — Module Map

```
src/twophase/
├── solver/          # Pure numerical computation — Solver layer (A5)
│   ├── ccd/         # Compact Finite Difference (CCD) kernels
│   ├── ppe/         # Pressure Poisson Equation solvers
│   │   ├── pseudotime.py   # PPESolverPseudoTime — CCD Laplacian (PRODUCTION)
│   │   └── bicgstab.py     # FVM matrix solver (TESTING ONLY, approx O(h²))
│   ├── advection/   # Level set advection (WENO5)
│   └── projection/  # Velocity projection / corrector
├── infra/           # I/O, logging, config, visualization — Infra layer (A5)
│   ├── config/      # SimulationConfig and sub-configs
│   └── backend/     # Compute backend injection (CPU/GPU)
├── builder.py       # SimulationBuilder — SOLE construction path (see §4)
├── run.py           # Entry point: python -m twophase.run --config ... --output ...
└── tests/           # pytest test suite
    └── test_*.py    # MMS convergence tests
```

> **§1 TODO:** Run `find src/twophase -name "*.py" | head -60` to populate complete module list.

---

## §2 — Interface Contracts

> **§2 TODO:** Populate from codebase scan. Key contracts to document:
> - Solver kernel interface (input/output array shapes, units, index conventions)
> - Backend injection protocol (CPU/GPU-agnostic array operations)
> - Callback/monitor interface (used in Protocol B staged simulation)
> - SimulationState fields accessible to callbacks: `.pressure.data`, `.psi.data`, `.velocity`, `.time`

---

## §3 — Config Hierarchy

`SimulationConfig` is pure sub-config composition — no monolithic config class (ASM-007).

```
SimulationConfig
├── PhysicsConfig        (Re, We, Fr, rho_ratio, epsilon)
├── GridConfig           (Nx, Ny, domain size)
├── SolverConfig         (solver_type: "pseudotime" | "bicgstab", max_iter, tol)
├── TimeConfig           (dt, t_end, CFL limit)
└── OutputConfig         (output_dir, save_interval)
```

> **§3 TODO:** Verify field names against `src/twophase/infra/config/`.

---

## §4 — SOLID Rules and Construction

**SimulationBuilder is the sole construction path.** Direct `TwoPhaseSimulation.__init__` is deleted. Any code that bypasses SimulationBuilder is forbidden.

Key SOLID rules:
- **DIP (Dependency Inversion):** Backends injected via constructor, not instantiated internally.
- **Default-vs-switchable:** Basic/standard schemes are defaults; alternative logics toggled by config.
- **MMS test standard:** Grid sizes N = [32, 64, 128, 256]; norms L1, L2, L∞; convergence via linear regression; assert `observed_order >= expected_order − 0.2`.
- **Test determinism:** Tests must be reproducible from config alone.
- **Code comment language:** Japanese preferred for inline comments; English for docstrings and reasoning.

---

## §5 — Implementation Constraints

### Implicit Solver Policy
| System type | Primary | Fallback | Rationale |
|---|---|---|---|
| Global PPE sparse | LGMRES | `spsolve` (sparse LU) on non-convergence | Large sparse; iterative preferred |
| Banded/block-tridiagonal (CCD Thomas, Helmholtz sweeps) | Direct LU | — | O(N) fill-in; direct is efficient |

Departure from this policy requires explicit inline justification.

### Algorithm Fidelity
Fixes MUST restore paper-exact behavior. Deviation from paper = bug. Improvement not in paper = out of scope (A3).

### Backward Compatibility
When replacing an existing implementation: provide a backward-compatible adapter (A7).

### Test Failure Halt
After delivering code and tests: if tests fail, STOP immediately. Report discrepancy. Ask user for direction. Never auto-debug.

---

## §6 — Numerical Algorithm Reference

### CCD Boundary Accuracy Baselines
- Interior: O(h⁶) for 1st derivative, O(h⁵) for 2nd derivative.
- **Boundary-limited orders (PASS thresholds on L∞):**
  - d1 (1st derivative): slope ≥ 3.5 is PASS. Slope ~4.0 is expected. NOT O(h⁶).
  - d2 (2nd derivative): slope ≥ 2.5 is PASS. NOT O(h⁵).
- Failure = slope < 3.5 (d1) or < 2.5 (d2) on uniform grids.

### WENO5 Periodic BC
- Ghost-cell rule: boundary divergence MUST NOT be unconditionally zeroed.
- Check `_weno5_divergence` wrap-around flux computation if spatial order degrades to ~O(1/h) or goes negative.

### PPE Null Space
- `PPESolverPseudoTime` Kronecker-product Laplacian has an **8-dimensional null space**.
- Do NOT use `‖Lp − q‖₂` as pass/fail metric without null-space deflation (ASM-002).
- Use physical diagnostics: divergence-free projection, Laplace pressure dp, velocity magnitude ‖u‖.

### PPE Solver Consistency
| solver_type | Matrix | Corrector ∇ | Status |
|---|---|---|---|
| `"pseudotime"` | CCD Laplacian | CCD `∇` | CONSISTENT — production |
| `"bicgstab"` | FVM matrix | CCD `∇` | Approximate O(h²) — testing only |

### Known Symmetry-Breaking Root Causes (fixed 2026-03-22)
| Root Cause | Stage Broken | Signature |
|---|---|---|
| Rhie-Chow FVM div wrong at wall node N_ax | div_rc | Error O(umax) at boundary nodes only |
| PPE gauge pin at corner (0,0) instead of center (N/2,N/2) | δp | Global asymmetry O(‖rhs‖) |
| Capillary CFL safety factor missing | u_new (step 1) | Symmetry error O(umax), disappears at smaller dt |

### Node-Centered Grid (face/divergence indexing)
```
Face indexing (N+1 nodes: indices 0..N):
  face[0]  = left wall  → flux = 0 (no-penetration BC)
  face[N]  = internal   → MUST be computed, NOT left at 0
  ✓ Correct: faces 1..N   (u_L = u[0:N], u_R = u[1:N+1])
  ✗ Wrong:   faces 1..N-1 (face N left at 0 → O(1) boundary error)

FVM divergence stencil:
  ✓ Correct: div[k] = (flux[k+1] - flux[k]) / h   (1h spacing)
  ✗ Wrong:   div[k] = (flux[k+2] - flux[k]) / h   (2h spacing → factor 2 too large)
             Symptom: Δp ≈ 2× Laplace pressure (e.g., 8.6 instead of 4.0)

Array shape: flux (N+1,) → div_nodes (N,) = (flux[1:] - flux[:-1]) / h
             pad: (N+1,) — pad zero at END only
```
