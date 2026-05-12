# CHK-RA-CH14-AO-FASTVOL-025 - AO-Fast 1/4-period capillary-wave theory RCA

Date: 2026-05-12
Branch: `codex/ra-ch14-ao-fast-volume-20260511`

## User Correction

The 1/4-period capillary-wave failure must not be treated as a CFL tuning
problem.  This RCA rejects CFL reduction as a remedy and analyzes the failure
from the SP-AO discrete Young--Laplace / bundle-virtual-work contract.

## Observation

The current GPU AO-Fast runtime completed the 3-step smoke, but the
1/4-period N=32 capillary-wave run did not reach
`t=0.011685745966`.  With the checked-in code at `ff95ab99`, the run blew up
near `t=0.00867`; a later uncommitted CFL/heuristic experiment was discarded
and is not used as a remedy.

The decisive short probe was run on the remote GPU with the same quarter-period
configuration and only 5 steps.  In the configured `pressure_coordinate` mode:

```text
step  force_l2  reaction_l2  balanced_l2  normal_residual  ppe_rhs       div_u
1     5.345763  5.345763     0            1.1205e-06       1.42e-14      6.87e-18
2     5.345763  5.345763     0            1.1205e-06       2.23e+08      2.98e+00
3     5.346658  5.346658     0            1.1205e-06       3.24e+08      5.95e+00
```

For the same probe with only pressure history changed to `face_acceleration`
as a diagnostic comparison:

```text
step  force_l2  reaction_l2  balanced_l2  normal_residual  ppe_rhs       div_u
1     5.345763  5.345763     0            1.1205e-06       1.42e-14      6.87e-18
2     5.345763  5.345763     0            1.1205e-06       3.67e-01      5.61e-08
3     5.345763  5.345763     0            1.1205e-06       5.59e-01      1.53e-08
```

This comparison is a diagnostic, not a proposed fallback.  The stable branch is
also physically wrong because it has zero pressure-balanced capillary drive.

## Theory Contract

At a compatible state `q = Q_h(phi)`, SP-AO defines capillarity by bundle
virtual work:

```text
L_B(w) = argmin ||delta_phi - delta_phi_pred(w)||_{W_eta}^2
         subject to J_q delta_phi = T_q(Gamma_h) w,

r_sigma(w) = -sigma dS_h(phi)[L_B(w)],
a_sigma = M_f^{-1} r_sigma.
```

The static criterion is the discrete Young--Laplace range condition:

```text
sigma dS_h(delta_phi) + pi^T J_q delta_phi = 0
```

for admissible bundle variations.  If it holds, the projected drive is zero.
If it does not hold, the interface has a physical nonzero capillary drive.
A non-flat capillary wave at rest is a displacement-release problem: it must
create acceleration, not remain pressure-exact.

## Hypotheses And Verdicts

| ID | Hypothesis | Verdict | Evidence |
|---|---|---|---|
| H1 | CFL=1 is simply too large. | Rejected as root cause. | Algebraic cancellation and pressure-history RHS explosion appear in the first 2 steps, before a long-time stability explanation is relevant. |
| H2 | q-volume leakage causes blowup. | Rejected. | 1/4 run volume drift stayed at roundoff scale (`~1.38e-16`). |
| H3 | GPU capillary diagonal Schur is too inaccurate. | Supported secondary. | `young_laplace_normal_residual_linf=1.12e-06` is far above the requested `1e-11`; the runtime reports this but does not fail close. |
| H4 | Runtime equates capillary force and pressure reaction for non-static states. | Primary supported. | Probe gives `force_l2 == reaction_l2` and `balanced_l2 == 0` while `young_laplace_residual_l2=1.48e-02` and normal residual is nonzero. |
| H5 | The nonzero Young--Laplace residual is detected but not mapped to a face drive. | Primary supported. | `capillary_drive_present=True` is set from nodal residuals, but the applied face packet has zero balanced increment. |
| H6 | `pressure_coordinate` history is incompatible with the AO face reaction. | Primary supported. | Holding all else fixed, `pressure_coordinate` gives step-2 `ppe_rhs=2.23e8`; `face_acceleration` gives `3.67e-1`. |
| H7 | Face-lattice bridge is the immediate cause. | Rejected as primary. | The same bridge under `face_acceleration` keeps `div_u` near `1e-8`; it does not create the huge RHS alone. |
| H8 | q/phi compatibility projection absence is the first-step cause. | Rejected as first-step root; retained as required fix. | First 5-step compatibility residual is initially `0` and remains `O(1e-10)` in the unstable branch, but the code currently only records it and does not enforce the bundle gate. |
| H9 | Reinitialization changes the interface. | Rejected. | The AO-Fast YAML uses `algorithm: none`, `every_steps: 0`. |
| H10 | UCCD/CCD/FCCD momentum operators are the root cause. | Rejected as primary. | The defect is visible in the AO/PPE algebra before convection or viscosity can explain it. |
| H11 | Density/nodal material bridge is the dominant cause. | Weak/secondary. | It changes Hodge weights, but cannot explain `force_l2 == reaction_l2` and zero balanced drive by itself. |
| H12 | Boundary wall handling is the dominant cause. | Weak/secondary. | The diagnostic comparison keeps wall handling fixed and isolates the huge RHS to pressure-history representation. |

## Root Cause

There are two coupled root defects.

1. **Non-static AO drive is algebraically canceled.**
   In `geometric_phase_runtime_gpu.py`, the diagonal pressure multiplier
   `pressure_cell` is used to build both:

   ```text
   capillary_face = T_q^T pressure_cell
   pressure_face  = capillary_face
   ```

   Therefore the runtime application always has:

   ```text
   dt a_sigma - dt a_pi = 0
   ```

   even when the Young--Laplace residual is nonzero.  This contradicts the
   theory statement that nonzero residual means physical nonzero capillary
   drive.  The code detects the drive in nodal diagnostics but applies a
   pressure-exact face packet.

2. **`pressure_coordinate` was unblocked without an AO scalar coordinate.**
   The AO pressure reaction is a face cochain.  The current pressure-coordinate
   history path extrapolates scalar base pressure coordinates, but no scalar
   coordinate for the AO reaction exists.  The first step is almost canceled;
   the second step injects an enormous PPE RHS (`O(1e8)`), which then creates
   large divergence and the later kinetic-energy blowup.

## Consequences

- Lowering CFL is not a theory fix.
- Switching pressure history is not a production fix either: it hides the
  explosive history defect but leaves the capillary wave with zero physical
  AO drive.
- The GPU diagonal active-Schur approximation cannot be admitted as a solved
  pressure range when the normal residual is above tolerance.  It must either
  fail close or be replaced by an actual active solver with a certified
  residual.

## Required Repair Direction

Before another 1/4-period run is meaningful:

1. Add a fail-close gate:
   if `young_laplace_normal_residual_linf > tolerance`, the GPU packet must not
   proceed as a solved pressure reaction.
2. Add a consistency gate:
   if `capillary_drive_present=True` and
   `pressure_balanced_increment_weighted_l2 == 0`, reject as an inconsistent
   non-static packet.
3. Rebuild the non-static capillary packet so the applied face drive represents
   the non-pressure-exact Young--Laplace residual in the same `M_f` work metric.
   Do not set `pressure_reaction = capillary_force` except for certified static
   pressure-exact states.
4. Keep `pressure_coordinate` fail-closed for AO non-static reaction until a
   scalar pressure-coordinate representation of the AO face reaction is derived
   and verified.  A diagnostic `face_acceleration` comparison may be used for
   RCA, but not as an implicit fallback.
5. Wire the active q/phi compatibility projection or fail close when
   `q != Q_h(phi)` exceeds tolerance; do not let capillarity use an
   incompatible `Gamma_h`.
6. Replace the diagonal Schur approximation with certified active PCG/Newton
   or residual-monotone DC only if its device-side residual gates are exact and
   fail-closed.

## SOLID-X

This checkpoint is RCA/probe only.  No production solver fix, no CFL remedy,
no fallback, no damping, no smoothing, no curvature cap, no FD/WENO/PPE
substitution, no hidden DCCD/UCCD damper, and no main merge is introduced.
