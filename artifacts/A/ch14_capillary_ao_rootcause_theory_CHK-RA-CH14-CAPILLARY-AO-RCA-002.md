# CHK-RA-CH14-CAPILLARY-AO-RCA-002 — capillary AO root-cause theory

Date: 2026-05-12
Branch/worktree: `codex/ra-ch14-capillary-ao-run-20260512` at `.claude/worktrees/codex-ra-ch14-capillary-ao-run-20260512`

## Scope

User request: find the shortest theory-respecting path to the Chapter 14 capillary-wave AO failure; generate many physics/math hypotheses and verify them.  Explicitly forbidden: small hacks, CFL/damping/smoothing/caps/fallbacks, or accepting an unphysical run.

## Key Observations

Current `ch14_capillary` with SP-AO `geometric_cell_fraction` fails before time advance at the GPU AO capillary admission gate:

```text
diagonal active-Schur pressure solve violates Young-Laplace normal equations
pressure_history_mode='pressure_coordinate' requires a scalar AO pressure coordinate
non-static packet has zero pressure-balanced drive
```

The algebraic probe was rerun after pushing this worktree with `make cycle`:

```bash
make cycle EXP=experiment/ch14/diagnose_ao_algebraic_split.py ARGS='--nx 32 --ny 32 --mode capillary_wave --center-fraction 0.47'
make run   EXP=experiment/ch14/diagnose_ao_algebraic_split.py ARGS='--nx 32 --ny 32 --mode capillary_wave --center-fraction 0.470000005'
make run   EXP=experiment/ch14/diagnose_ao_algebraic_split.py ARGS='--nx 32 --ny 32 --mode flat --center-fraction 0.470000005'
make run   EXP=experiment/ch14/diagnose_ao_algebraic_split.py ARGS='--nx 32 --ny 32 --mode capillary_wave --center-fraction 0.47 --pressure-history face_acceleration'
```

Important hygiene note: a plain `make run` before the `cycle` used the shared remote directory after another worktree had changed it and reported `gpu_active_pcg_component_hodge`.  That was remote contamination, not this branch.  The numbers below are from this branch after `make cycle` pushed it.

## Current Probe Results

| Case | cpu_exact balanced_l2 | cpu_component_hodge balanced_l2 | gpu_packet balanced_l2 | gpu outcome |
|---|---:|---:|---:|---|
| wave, center 0.47 | 0.0 | 2.117576366046111 | 0.0 | fail-close |
| wave, center 0.470000005 | 0.0 | 2.117575529992343 | 0.0 | fail-close |
| flat, center 0.470000005 | 0.0 | 0.0 | 0.0 | flat zero-drive control |
| wave, `face_acceleration` history | 0.0 | 2.117576366046111 | 0.0 | fail-close without pressure-coordinate clause |

The y-shift test corresponds to moving the interface by `1e-10 m` because `L_y=0.02` and `5e-9 * L_y = 1e-10`.  It does not change the diagnosis.

## Git Trace Clarification

The apparent "worked before GPU optimization" history separates into two different paths:

- `5afc8199 docs(ch14): record mainline capillary rerun` completed the checked-in mainline production capillary benchmark.  Its artifact states explicitly that it was not the experimental AO-Fast `geometric_cell_fraction` packet.  It used the mature FCCD/UCCD6 pressure-jump/component-Hodge stack.
- `ff95ab99 feat(ch14): complete AO-Fast GPU runtime packet` allowed short AO-Fast smoke progress, but later RCA (`df4509d7`, `ef07cb51`) showed that progress was physically invalid: the packet had zero pressure-balanced capillary drive and an undefined non-static pressure-coordinate history.
- `5324ff93 fix: batch gpu scalar synchronizations` only batched scalar host transfers in the fail-close gate.  Its diff changes scalar reads to a scalar packet; it does not create the zero-drive algebra.

So the regression is not the scalar-sync optimization.  The real split happened when AO-Fast GPU runtime admitted an incomplete pressure/capillary packet, then later fail-close correctly stopped it.

## Hypothesis Matrix

| ID | Hypothesis | Verification | Verdict |
|---|---|---|---|
| H1 | The capillary wave is actually a static Young-Laplace equilibrium. | A non-flat two-layer capillary wave at rest must release surface energy; flat control is zero but wave has nonzero component-Hodge residual. | Rejected |
| H2 | CFL/time-step instability is the root cause. | Rung-0 algebraic probe fails before Navier-Stokes time advance. | Rejected |
| H3 | Viscosity or inertia suppresses motion. | Algebraic drive is zero before viscosity/convection can act. | Rejected |
| H4 | q/phi incompatibility is the first blocker. | Probe reports `compat_linf=0.0`. | Rejected for this failure |
| H5 | Reinitialization changed the interface. | YAML has `algorithm: none`, `every_steps: 0`. | Rejected |
| H6 | Wall or periodic boundary handling is the primary cause. | Holding boundary fixed, flat is zero and wave is nonzero in component-Hodge; y-shift does not change zero-drive in full pressure split. | Rejected as primary |
| H7 | A 1e-10 y-shift fixes an active-stratum degeneracy. | Shifted wave still has `cpu_exact balanced_l2=0.0` and GPU fail-close; component-Hodge remains nonzero. | Rejected |
| H8 | `pressure_coordinate` history is the primary cause. | `face_acceleration` removes only the pressure-coordinate clause; zero balanced drive and diagonal-Schur fail-close remain. | Secondary only |
| H9 | GPU diagonal active-Schur inaccuracy is the only cause. | GPU normal residual is invalid, but CPU exact full-pressure split also gives zero balanced drive. | Secondary only |
| H10 | Nonzero nodal Young-Laplace residual guarantees nonzero face drive. | CPU exact has nonzero Young-Laplace residual but zero face residual. | Rejected |
| H11 | Full cell-pressure reaction image is too large. | The full pressure split removes all face capillary work for the wave; component-volume reaction leaves nonzero wave and zero flat. | Supported |
| H12 | GPU packet builds force and pressure reaction from the same object. | Current code sets `capillary_face = T_q^T pressure_cell` and then `pressure_face = capillary_face`, so subtraction is zero by construction. | Supported primary |
| H13 | The mainline production success clears AO-Fast. | `5afc8199` was a different production route and explicitly did not clear CHK-029. | Rejected |
| H14 | Scalar-sync GPU optimization caused the math defect. | `5324ff93` batches scalar transfers only; zero-drive RCA predates it. | Rejected |
| H15 | The fix can be a hidden fallback to component-Hodge or dense CPU. | SP-AO/YAML forbids dense runtime fallback and hidden solver family switches. | Rejected as invalid remedy |

## Root Cause

The immediate GPU-code defect is:

```text
pressure_cell = approximate solution of S pi = J_q(-sigma dS)
capillary_face = T_q^T pressure_cell
pressure_face  = capillary_face
balanced_face  = capillary_face - pressure_face = 0
```

The deeper mathematical defect is that the current "full cell-pressure" reaction space is not the physically admitted pressure-reaction subspace for a non-static capillary wave.  It projects the capillary covector into the same Schur image used to build the force, so it deletes the drive.  A nonzero nodal residual `g + J_q^T pi` is not enough: the residual must be lifted and measured in the same admissible face work space.

Therefore a tiny y-shift is not a remedy.  If it changed the outcome, that would reveal a discretization instability; in the actual probe it does not even change the failure class.

## Theory-Respecting Shortest Path

The next implementation slice should be Rung-0 only, before any long capillary-wave run:

1. Define the admitted pressure-reaction subspace `R_p(q_T)` explicitly.  It must be smaller than the full cell-pressure Schur image and must be justified by the SP-AO pressure-adjoint work metric.
2. Build the source face covector `r_sigma` from bundle virtual work, not by reusing the full pressure multiplier as both force and pressure reaction.
3. Compute `r_bal = r_sigma - Pi^{M_f}_{R_p(q_T)} r_sigma`.
4. Keep these gates exact and fail-closed:
   - flat interface gives zero drive;
   - capillary wave gives nonzero drive;
   - `1e-10 m` y-shift leaves the qualitative result unchanged;
   - amplitude scaling is monotone;
   - N32/N64 are consistent;
   - GPU reductions stay device-resident except scalar gate packets.
5. Keep non-static `pressure_coordinate` closed until a scalar AO pressure coordinate is derived.  `face_acceleration` may remain a diagnostic comparison, not a production fallback.

[SOLID-X] Theory/probe/artifact only; no production solver source, YAML physical parameter, CFL reduction, damping, smoothing, curvature cap, FD/WENO/PPE fallback, hidden dense/CPU fallback, hidden component-Hodge fallback, benchmark-specific offset, main merge, or branch deletion introduced.
