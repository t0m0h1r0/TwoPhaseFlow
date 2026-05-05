# CHK-RA-SRC-MAJOR-ROUNDS-001 — src MAJOR+ Iterative Review

Date: 2026-05-05
Branch: `ra-src-major-rounds-20260505`
Worktree: `.claude/worktrees/ra-src-major-rounds-20260505`

## Scope

Review `src/` against the paper/docs/CHK contracts, with special focus on:

- paper-exact pressure-jump and defect-correction behavior;
- GPU-first hot paths and avoidable host/device transfers;
- CuPy/NumPy semantic parity;
- recent-10-day experimental side effects;
- whether paper text needs updates.

[SOLID-X] No production boundary/SOLID violation was found in the final round.
The code changes restore existing contracts rather than adding a new abstraction
or deleting tested implementations.

## Review Rounds

### Round 1 — MAJOR found and fixed

MAJOR findings:

1. `InterfaceStressContext.is_active()` required both an explicit
   `pressure_jump_gas_minus_liquid` and `sigma != 0`.  This incorrectly
   disabled an explicit affine jump when `sigma` was zero, although the paper
   contract is in terms of the gas-minus-liquid jump `j_gl`, not the raw
   capillary coefficient.
2. `build_interface_stress_context()` synthesized a zero jump whenever
   curvature was present and `sigma == 0`, which made "explicit no jump" and
   "zero capillary coefficient" indistinguishable from a physically supplied
   jump context.
3. `_LowOrderViscousHelmholtzSolver` accepted scalar `mu`/`rho` as 0-D arrays
   and later indexed them as grid fields.  The implicit-BDF2 DC contract lets
   the low operator be scalarized, but not shape-incompatible with the full
   grid coefficient contract.
4. `_apply_periodic_row_constraints()` used host `np.isin` on device triplet
   rows.  This was an avoidable GPU hot-path transfer in sparse PPE assembly.
5. `grid_remap` monotonicity checks used `bool(xp.any(...))` after device
   conversion.  The coordinates are canonical host metadata, so the check
   should stay on host and avoid device synchronization.

Fix commit: `209e9703 fix: align src affine jumps and GPU hot paths`.

### Round 2 — zero-shortcut GPU sync audit

Audited `all_arrays_exact_zero()` users in convection, FCCD advection,
divergence, PPE defect correction, and viscous predictors.  The predicate is
syncing by nature because it returns a Python `bool`, but production call sites
guard it with `not backend.is_gpu()` before use.  No MAJOR+ finding remained.

### Round 3 — remaining host-transfer and fallback audit

Audited remaining `to_host`, `.get()`, `float(xp...)`, WENO/FD/fallback
patterns outside tests/tools/visualization.  Remaining cases are diagnostics,
legacy/reference paths, explicit CPU solvers, FMM/host algorithms, or control
scalars such as CFL/diagnostic recording.  The device-side mass correction path
already uses 0-D array arithmetic and retains the legacy float-gated path only
as C2 reference.  No MAJOR+ finding remained.

### Round 4 — paper/docs consistency and stop condition

Checked the touched contracts against:

- `paper/sections/02b_surface_tension.tex`
- `paper/sections/07_time_integration.tex`
- `paper/sections/09b_split_ppe.tex`
- `paper/sections/12_component_verification.tex`
- `paper/sections/14_benchmarks.tex`
- `docs/wiki/theory/WIKI-T-127.md`

The paper already states the scientific contracts being restored:

- the pressure-jump object is `j_gl = p_gas - p_liq`, not raw `sigma*kappa`;
- `InterfaceStressContext` stores the gas-minus-liquid pressure jump;
- implicit-BDF2 DC uses a low-order operator only as a correction path, with
  the high-order residual defining the fixed point;
- GPU/CuPy execution is an implementation reproducibility contract through
  `backend.xp`, not a separate scientific claim.

Stop condition reached: Round 4 found no MAJOR+ findings, before round 10.

## Recent-10-Day Side-Effect Audit

The modified files overlap recent 2026-04-25--2026-05-05 work:

- affine interface stress closure:
  `bc4034e2`, `0cf04fb8`, `13af59ec`, `626a68ea`;
- implicit-BDF2 viscous DC:
  `9ef67ee4`, `b56e8895`;
- mixed periodic/nonuniform PPE GPU assembly:
  `099d8c69`, `cee34e92`, `d09d28bf`;
- Ch14 object initial conditions and split-reinit tests:
  `06a47c8f`, `b4a661fe`, `d68fa52d`, `9a8451c1`.

Side-effect verdict:

- The interface-stress change restores the controlling `j_gl` contract and
  does not alter the legacy `sigma,kappa` fallback when `sigma != 0`.
- The viscous low-operator change broadens scalar coefficients to valid full
  grid fields, preserving field inputs unchanged and fixing scalar inputs.
- The PPE row-mask change is namespace-preserving (`xp.isin`) and leaves the
  algebraic periodic constraints unchanged.
- The remap monotonicity change moves metadata validation to host coordinates
  before device conversion; interpolation coefficients remain unchanged.
- Test expectation updates remove stale assumptions from recent experiment
  bookkeeping and keep thresholds below the documented pre-fix drift.

## Paper Reflection

No paper edit is required.  The changes are implementation corrections to
already documented contracts, not new scientific claims.  Adding details such
as "`is_active` checks jump presence rather than `sigma`" would make the paper
more implementation-specific without changing the mathematical narrative.

## Validation

- `PATH=/Users/tomohiro/Downloads/TwoPhaseFlow/.venv/bin:$PATH make test ...`
  attempted remote-first; remote was unavailable, so Make ran local CPU fallback.
- Full suite result: `520 passed, 31 skipped in 75.38s`.
- `git diff --check`: PASS.

