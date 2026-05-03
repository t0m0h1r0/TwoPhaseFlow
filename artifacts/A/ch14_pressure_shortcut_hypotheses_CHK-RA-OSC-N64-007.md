# CHK-RA-OSC-N64-007 — Pressure-oscillation shortcut hypotheses

Date: 2026-05-03
Branch: `ra-oscillating-droplet-n64-20260503`

## Goal

Find the shortest theory-respecting route to solve the pressure oscillation.
No damping, timestep tightening, smoothing, or parameter tuning is accepted as a
fix unless it follows from the governing equations.

## Governing constraint

For pressure-jump surface tension the physical pressure operator is not the
plain gradient of a discontinuous pressure.  It is the jump-aware operator

`G_Gamma(p; j) = G(p) - B_Gamma(j)`,

where `j = p_gas - p_liquid = -sigma kappa`.  A static droplet at rest requires

- `u = 0`,
- phasewise constant pressure,
- `[p] = sigma/R`,
- all momentum stages that use pressure gradients must use the same
  jump-aware pressure representation.

## Code-path audit

The current code is not obviously using one pressure-gradient representation
everywhere:

- Predictor pressure history uses a plain nodal gradient:
  `src/twophase/simulation/ns_step_services.py:303`.
- Projection face fluxes can use the affine jump correction:
  `src/twophase/simulation/ns_step_services.py:710`.
- The affine correction subtracts `signed_pressure_jump_gradient` in
  `src/twophase/simulation/divergence_ops.py:327`.
- The signed jump gradient is defined in
  `src/twophase/coupling/interface_stress_closure.py:125`.

This mismatch is a mathematically plausible shortcut target: even if the PPE
solve is jump-aware, the IPC predictor may re-inject an unphysical acceleration
from the plain gradient of the previous discontinuous pressure.

## Minimal new probe

Added `experiment/ch14/probe_pressure_history_gradient_n64.py`.

It runs the alpha-2 static droplet only to `T=0.40` and compares:

1. `baseline`: current route,
2. `no_prev_pressure_gradient`: diagnostic removal of previous-pressure
   predictor gradient,
3. `constant_curvature`: diagnostic replacement of computed curvature by exact
   circular `kappa=1/R=4`.

These are not proposed fixes.  They are falsification probes.

Command:

```bash
make cycle EXP=experiment/ch14/probe_pressure_history_gradient_n64.py
make cycle EXP=experiment/ch14/probe_pressure_history_gradient_n64.py ARGS="--case constant_curvature"
```

## Results

| case | final t | max KE | max volume drift | jump | jump error | liquid residual RMS | gas residual RMS | max deformation |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| baseline | 0.40 | 4.091e-04 | 1.844e-05 | 2.635e-01 | 2.445e-02 | 2.224e-01 | 1.437e-02 | 2.345e-03 |
| no previous pressure gradient | 0.40 | 1.503e-05 | 1.111e-06 | 1.754e+02 | 1.751e+02 | 2.767e-01 | 1.318e-02 | 0 |
| constant curvature | 0.40 | 6.485e-05 | 2.282e-06 | 3.008e-01 | 1.282e-02 | 1.724e-01 | 4.762e-03 | 0 |

Additional direct first-snapshot check:

- alpha-2 static initial Young--Laplace jump is correct: `0.288438` vs
  theoretical `0.288`.
- On cut faces, the plain pressure gradient RMS is about `20.566`, while
  subtracting a jump-gradient estimate reduces it to about `2.727`.
- Thus a plain gradient of the jump field is not a small perturbation; it is an
  `O([p]/h)` interface acceleration.

## Hypotheses and verdicts

### H1 — previous-pressure predictor gradient is the sole cause

Verdict: falsified as sole cause, supported as a kinetic-energy injection path.

Removing it reduces max KE by about `27x` at `T=0.40`, but the pressure jump
becomes nonsensical (`~175`) and liquid residual RMS does not improve.  Therefore
"just remove pressure history" is not a valid solution.  However, the strong KE
drop supports that the pressure-history gradient participates in the instability.

### H2 — curvature noise is the sole cause

Verdict: falsified as sole cause, supported as a major source.

Replacing curvature by exact `kappa=4` reduces max KE by about `6.3x`, volume
drift by about `8x`, and gas residual by about `3x`; liquid pressure residual
improves more modestly (`0.222 -> 0.172`).  Thus curvature contamination is real
and important, but exact curvature alone does not restore phasewise constant
pressure.

### H3 — the short path is alpha/dt tuning

Verdict: rejected.

Alpha=2 delays the problem and can complete `T=1.5`, but pressure residuals
still grow.  Lowering dt may hide the injection rate but does not repair the
operator identity `G_Gamma(p;j)`.

### H4 — projection is jump-aware but predictor is not

Verdict: strongest current shortcut hypothesis.

The current code has an evident representation mismatch: projection calls the
affine face pressure flux path, while the predictor subtracts a plain previous
pressure gradient.  Static Young--Laplace pressure is discontinuous; taking a
plain gradient of it produces an `O([p]/h)` nonphysical interface acceleration.
The no-history probe proves this path strongly affects KE, and the exact-
curvature probe proves the capillary jump source also matters.  The combined
theory points to a single root: pressure-jump representation is not enforced
consistently across predictor, PPE, projection, and stored pressure history.

### H5 — pressure increment/base pressure bookkeeping is the bug

Verdict: still plausible, not yet isolated.

The pressure stage stores `pressure_increment`, `pressure_base`, and
`p_corrector` separately.  For affine jump, `apply_interface_jump` is a no-op,
but the affine jump appears in RHS/face-gradient operators.  The next audit must
prove whether `p_corrector` and `previous_pressure` are both in the same
mathematical pressure space.  If not, pressure modes can be accumulated even
with exact curvature.

## Current problem localization

The nearest real solution is likely not in the droplet size, alpha, CFL, or
plotting path.  It is in the pressure-jump operator contract:

`stored pressure / pressure increment / previous-pressure predictor gradient / affine PPE RHS / projection face flux`

must all represent the same mathematical pressure variable and the same
Young--Laplace jump.

The shortest theory-respecting next implementation step is therefore:

1. define an explicit interface for jump-aware pressure gradients/fluxes,
2. use it in the predictor pressure-history term instead of plain
   `pressure_grad_op.gradient(previous_pressure, axis)`,
3. audit whether `p_corrector` should be the affine base increment or a
   physical jump-bearing increment in each correction path,
4. add a static Young--Laplace equilibrium test that requires phasewise pressure
   residuals and velocities to stay near zero over several capillary steps.

No damping/smoothing/timestep patch is justified before this operator contract
is repaired and tested.

[SOLID-X] Diagnostic script/artifact only; no solver/operator/builder boundary
was changed, and no tested implementation was deleted.
