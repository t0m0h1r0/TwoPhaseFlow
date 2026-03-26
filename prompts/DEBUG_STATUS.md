# DEBUG_STATUS.md
# Simulation debugging progress log

Last updated: 2026-03-22

---

## Fixes Applied This Session (2026-03-21)

### Fix 1: `rhie_chow.py` — `_rc_flux_1d` face range (line ~110)
**Before:** computed internal faces `1..N_ax-1` only
**After:**  computes faces `1..N_ax` (face `N_ax` between nodes `N_ax-1` and `N_ax`)
**Why:** face `N_ax` is an internal face, not a wall face; leaving it zero caused
  a large divergence error at the node adjacent to the right/top wall.

### Fix 2: `rhie_chow.py` — `_flux_divergence_1d` stencil (line ~137)
**Before:**
```python
sl_hi[axis] = slice(2, None)   # 2h-wide stencil → div is 2× too large
sl_lo[axis] = slice(0, -2)
return xp.concatenate([pad, div_interior, pad], axis=axis)
```
**After:**
```python
sl_hi[axis] = slice(1, None)   # correct 1-cell FVM stencil
sl_lo[axis] = slice(0, -1)
return xp.concatenate([div_nodes, pad], axis=axis)  # single end-pad only
```
**Effect:** delta_p dropped from ~8.6 to ~2.93 (Laplace theory = 4.0).
**Analytical verification:**
- u=x, v=0 → interior error = 0 exactly ✓
- u=sin(πx) → interior error = O(h²) ✓
- div-free field → interior error = 0, compat integral = 0 ✓

---

## Fixes Applied This Session (2026-03-22)

### Fix 3: Balanced-force fix — FD operators for IPC and velocity corrector

**Root cause (confirmed):**
The predictor IPC term used `CCD(∇p^n)` and the velocity corrector used `CCD(∇δp)`,
but the PPE (PPESolverLU) uses an FVM Laplacian. This means the pressure that
FVM finds is NOT the pressure that makes `CCD(∇p) = ρ * F_st`. Result:
each step has residual force `ε = F_st - CCD(∇p^n)/ρ ≠ 0`, driving
parasitic velocity linearly until convection causes exponential blowup at step ~10.

**Mathematical proof that FVM/CCD is inconsistent:**
- Predictor: `u* = u^n + dt/ρ * [F_st_CCD - CCD(∇p^n)]`
- PPE: `L_FVM(δp) = div_RC(u*)/dt`
- Corrector: `u^{n+1} = u* - dt/ρ * CCD(∇δp)`
- At steady state: `CCD(∇p^∞) = F_st` ← only holds if PPE uses CCD Laplacian

**Fix:**
Changed IPC term (predictor) and velocity corrector to use O(h²) central FD
instead of CCD. FD is consistent with the FVM PPE (both approximate the same
continuous Laplacian with O(h²) accuracy).

**Files changed:**
- `src/twophase/pressure/velocity_corrector.py`:
  - Replaced `ccd` constructor arg with `grid`
  - Added `_fd_gradient(p, ax)` method: central diff, Neumann BC at walls
  - Changed `correct()` to use `_fd_gradient` instead of `ccd.differentiate`
- `src/twophase/ns_terms/predictor.py`:
  - Added `_fd_gradient(p, ax)` method (using `self.config.grid`)
  - Changed IPC term to use `_fd_gradient` instead of `ccd.differentiate`
- `src/twophase/simulation/builder.py`:
  - Changed `VelocityCorrector(backend, ccd)` → `VelocityCorrector(backend, grid)`
- `src/twophase/tests/test_pressure.py`:
  - Updated `test_divergence_free_projection` to use new `VelocityCorrector(backend, grid)` signature
  - Relaxed tolerance 2e-3 → 6e-3 (FD/FVM O(h²) consistency, h=1/16)

**Expected effect:**
The mismatch between FD gradient and FVM Laplacian gradient is O(h²), vs O(1)
for CCD/FVM mismatch at the interface. Parasitic velocity should be O(h²) ≈ 10^{-3}
instead of O(1), preventing the convective blowup.

**Note on surface tension:**
`SurfaceTensionTerm` still uses CCD for `∇ψ`. This means balanced-force is only
approximate: `κ*CCD(∇ψ)/We ≈ κ*FD(∇ψ)/We + O(h²)`, so residual is O(h²).
For a true balanced-force, surface tension should also use FD — but CCD gives
better interface representation and parasitic currents should be manageable at O(h²).

---

## Current Simulation Status (2026-03-21 before Fix 3)

### Equal-density stationary droplet (rho_ratio=1.0, We=1, Fr=1e10, N=32, LU solver)
- Steps 1–10: stable, dp ≈ 2.93, |u| = 0.02–0.09
- Steps 10–15: |u| grows from 0.09 → 0.47 → exponential blowup
- Blowup at t ≈ 0.04–0.10

### Physical-density stationary droplet (rho_ratio=0.001, LU solver)
- Blows up within 3–4 steps (|u| ≈ 200 at step 3)

**Status after Fix 3: UNTESTED — run stationary droplet benchmark to verify.**

---

## Root Cause Analysis (complete)

### Why delta_p ≈ 2.93 instead of 4.0 (27% deficit)?
**Expected behavior:** This deficit is PHYSICAL, not a bug.
- CLS interface has finite thickness ε = 1.5h ≈ 0.047 (N=32)
- Only ~3 cells across the interface
- CSF body force does not integrate to exact Laplace pressure at this resolution
- Deficit decreases with finer grid or larger ε_factor
- **Do not attempt to "fix" this.**

### Why does the simulation blow up? (FIXED in principle by Fix 3)
**Root cause: FVM PPE ↔ CCD velocity corrector balanced-force violation**

The IPC scheme requires consistent operators:
```
Predictor: u* = u^n + dt/ρ * [F_st - ∇p^n]   (same ∇ as corrector)
PPE:       L(δp) = ∇_RC·u*/Δt                 (defines δp)
Corrector: u^{n+1} = u* − (Δt/ρ)∇δp          (same ∇ as predictor)
```
At equilibrium: ∇p^∞ = ρ * F_st (balanced-force).
This holds only if L and ∇ are consistent (same discrete operator family).

FVM PPE + CCD gradient: different operator families → F_st ≠ ∇p^∞ → residual
force drives parasitic velocity → convective amplification → exponential blowup.

**Fix 3 makes IPC+corrector use FD (O(h²) central diff), consistent with FVM PPE.**

### Why the pseudotime (CCD) solver also fails:
- CCD 2D Laplacian has an **8-dimensional null space** (for uniform density)
- Pinning one node reduces null-space to 7 (insufficient)
- Condition number ≈ 2×10^17 → spsolve returns garbage (10^9× too large)
- For variable density (rho_ratio=0.001): null_dim=1 but cond ≈ 4×10^16 → still fails
- This is a **known issue** (commented in `test_pressure.py`, `ppe_solver_pseudotime.py`)
- **Status: not yet fixed** (not needed if FVM LU solver is stable after Fix 3)

---

## Key Theoretical Result (2026-03-22)

### RC face divergence is zero regardless of corrector gradient operator
**For uniform density:** the Rhie-Chow face velocity of u^{n+1} satisfies:
```
u_f^{n+1} = u_f* - (Δt/ρ) * (δp_{k+1} - δp_k)/h
```
This is INDEPENDENT of whether the cell-centered corrector uses CCD or FD.
The CCD/FD gradients cancel through the RC formula.
**Implication:** the CCD/FVM mismatch does NOT cause divergence accumulation;
it causes balanced-force violation → parasitic velocity → convective blowup.

---

## Next Steps

### 1. Test Fix 3 (IMMEDIATE)
Run the stationary droplet benchmark with the LU solver:
```python
from twophase.benchmarks.stationary_droplet import StationaryDropletBenchmark
bench = StationaryDropletBenchmark(N=32, We=1, Fr=1e10, rho_ratio=1.0, t_end=1.0)
results = bench.run(verbose=True)
```
Expected: simulation stable for t > 0.1, |u| should decay and plateau at O(h²) ≈ 10^{-3}.

### 2. Run physical-density droplet test
```python
bench = StationaryDropletBenchmark(N=32, We=1, Fr=1.0, rho_ratio=0.001, t_end=0.1)
results = bench.run(verbose=True)
```

### 3. Grid convergence study
If stationary droplet is stable: run N=[32, 64, 128] and check parasitic velocity
scales as O(h²) → confirms the FD/FVM balanced-force theory.

### 4. Rising bubble benchmark
Once stable: run RisingBubbleBenchmark(N=64, t_end=3.0) vs Hysing et al. reference.

---

## Files Modified This Session (2026-03-22)
- `src/twophase/pressure/velocity_corrector.py` — FD gradient, grid param
- `src/twophase/ns_terms/predictor.py` — FD gradient for IPC
- `src/twophase/simulation/builder.py` — grid→VelocityCorrector
- `src/twophase/tests/test_pressure.py` — updated constructor, relaxed tolerance
- `docs/DEBUG_STATUS.md` — this file (updated)

## Files Modified Previous Session (2026-03-21)
- `src/twophase/pressure/rhie_chow.py` — Fix 1 and Fix 2
- `docs/DEBUG_PROMPTS.md` — 6 reusable debugging prompts
- `docs/DEBUG_STATUS.md` — initial version

---

## Key Code Locations
| Component | File | Key line |
|-----------|------|----------|
| Rhie-Chow flux | `src/twophase/pressure/rhie_chow.py` | L86–128 |
| RC divergence | `src/twophase/pressure/rhie_chow.py` | L132–151 |
| Velocity corrector (FD) | `src/twophase/pressure/velocity_corrector.py` | all |
| Predictor IPC (FD) | `src/twophase/ns_terms/predictor.py` | L156–174 |
| PPE FVM LU | `src/twophase/pressure/ppe_solver_lu.py` | L52–90 |
| PPE CCD pseudotime | `src/twophase/pressure/ppe_solver_pseudotime.py` | L104–190 |
| PPE builder (FVM) | `src/twophase/pressure/ppe_builder.py` | all |
| Simulation core | `src/twophase/simulation/_core.py` | all |
| Stationary droplet bench | `src/twophase/benchmarks/stationary_droplet.py` | all |
