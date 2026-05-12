# CHK-RA-CH14-AO-FASTVOL-029 - Rung-0 AO algebraic split RCA

## Purpose

User request:

> ではその方針で実験し、問題を潰していって。問題が発生した際には、その原因を物理学・数学の理論に基づいて仮説考案し推理してください。仮説をできるだけ多数創出し、それを検証することで問題特定を行なってください。理論を絶対視し、小手先の技で修正するのは絶対に禁止です。

This note executes the first rung of the CHK-028 blow-up-assumed strategy:
algebraic capillary split diagnostics only, no Navier--Stokes time advance.

## Diagnostic Added

Added `experiment/ch14/diagnose_ao_algebraic_split.py`.

The probe builds the same geometric interface three ways:

```text
cpu_exact:
  dense fixed-stratum pressure/capillary Hodge split

cpu_component_hodge:
  existing component-volume reaction Hodge residual, used only as a
  hypothesis probe for a smaller pressure-reaction subspace

gpu_packet:
  current device-resident diagonal active-Schur packet plus fail-close gate
```

Output columns include q/phi compatibility, pressure range status,
Young--Laplace residuals, predictor/reaction norms, and pressure-balanced
face increment norms.  The probe is algebraic; it does not reduce CFL, add
damping, smooth curvature, or advance the flow.

## Experiments

Commands:

```text
make cycle EXP=experiment/ch14/diagnose_ao_algebraic_split.py ARGS="--nx 32 --ny 32 --mode capillary_wave"
make cycle EXP=experiment/ch14/diagnose_ao_algebraic_split.py ARGS="--nx 32 --ny 32 --mode flat"
make run EXP=experiment/ch14/diagnose_ao_algebraic_split.py ARGS="--nx 32 --ny 32 --mode capillary_wave --pressure-history face_acceleration"
make run EXP=experiment/ch14/diagnose_ao_algebraic_split.py ARGS="--nx 64 --ny 64 --mode capillary_wave"
make run EXP=experiment/ch14/diagnose_ao_algebraic_split.py ARGS="--nx 32 --ny 32 --mode capillary_wave --amplitude 1.0e-4"
make run EXP=experiment/ch14/diagnose_ao_algebraic_split.py ARGS="--nx 32 --ny 32 --mode capillary_wave --amplitude 4.0e-4"
```

Key outputs:

| Case | cpu_exact balanced_l2 | cpu_component_hodge balanced_l2 | gpu fail-close |
|---|---:|---:|---|
| N32 flat | 0.0 | 0.0 | none after zero-predictor classification fix |
| N32 wave, A=1e-4 | 0.0 | 1.2566480188877793 | diagonal Schur residual + zero balanced drive |
| N32 wave, A=2e-4 | 0.0 | 2.117576366046111 | diagonal Schur residual + zero balanced drive |
| N32 wave, A=4e-4 | 0.0 | 3.558211768995462 | diagonal Schur residual + zero balanced drive |
| N64 wave, A=2e-4 | 0.0 | 2.3054842783888376 | diagonal Schur residual + zero balanced drive |

The `face_acceleration` history run still failed on GPU with zero
pressure-balanced drive, so the primary defect is not the scalar pressure
history mode.  The pressure-coordinate history defect remains real, but it is
downstream of the algebraic split defect.

## Hypotheses And Outcomes

| Hypothesis | Evidence | Status |
|---|---|---|
| H1: the failed quarter-period run is a CFL/time-step problem | Rung-0 fails before any time advance | rejected |
| H2: the problem is only the GPU diagonal active-Schur approximation | CPU exact also gives zero face-balanced drive for the capillary wave | rejected as sole cause |
| H3: pressure-coordinate history is the primary cause | `pressure_history=face_acceleration` still fails with zero balanced drive | rejected as primary cause |
| H4: nonzero nodal Young--Laplace residual automatically gives nonzero face drive under the current lift | N32/N64 CPU exact have nonzero Young--Laplace residual but zero residual face covector | rejected |
| H5: the current capillary Riesz and pressure reaction solve the same Schur problem | Code uses `S lambda = J(-g)` for capillary and `S pi = -Jg` for pressure, so `lambda=pi` | supported |
| H6: the pressure reaction space is too large | Removing only component-volume reaction directions leaves nonzero wave drive and zero flat drive | supported as a candidate, not yet final |
| H7: the geometry is a flat/aliasing artifact | N32/N64 wave cases reproduce the issue; flat remains zero | rejected |
| H8: GPU flat-interface fail-close was a real physics failure | Flat has zero predictor and zero residual; fail-close was a classification bug | rejected, fixed |

## Root Cause

The fixed-stratum implementation currently builds the capillary face covector
and the cell-pressure reaction face covector from the same active Schur solve.
Let `g = sigma dS_h`.  The dense capillary Riesz path uses

```text
S lambda = J_q(-g),
r_sigma = T_q^T lambda.
```

The pressure split uses

```text
S pi = -J_q g,
pressure_face = T_q^T pi.
```

These are the same linear system, so `lambda=pi` and
`r_sigma-pressure_face=0` by construction.  A nonzero nodal residual

```text
e = g + J_q^T pi
```

can still be orthogonal to the implemented bundle-lift range; it is therefore
not, by itself, a certified face-space drive.  CHK-027's proof obligation must
be tightened: the non-static drive is certified only after the pressure
reaction subspace is specified as a proper physical reaction space and the
face residual is recomputed in the same `M_f` work metric.

## Fix Applied In This CHK

The GPU fail-close boundary now treats declared capillary drive as non-static
only when the predictor increment has nonzero `M_f` norm.  This fixes the
flat-interface false positive without admitting capillary-wave advancement:
the wave still fail-closes on diagonal Schur residual and zero balanced drive.

The existing GPU packet still reports the coarse declared status
`gpu_diagonal_active_schur_approximation` for flat `sigma>0` because the
packet avoids inner host synchronization.  The solver boundary classification
is the authoritative gate.

## Next Implementation Direction

Do not launch long 1/4-period runs yet.  The next coding target is an exact
Rung-0 pressure-reaction subspace gate:

```text
source face covector r_sigma
  -> project only onto admitted reaction space R_p
  -> drive = r_sigma - Pi_{R_p}^{M_f} r_sigma
```

Candidate `R_p` spaces must be certified before runtime use:

1. component-volume reactions are useful as a diagnostic because they keep the
   flat interface zero and the wave nonzero;
2. the final runtime pressure coordinate must be PPE-compatible and scalar,
   not an untracked face increment;
3. GPU implementation must keep active tables and reductions device-resident;
4. exact gates must include flat/static zero drive, capillary-wave nonzero
   drive, amplitude scaling, N32/N64 consistency, and no hidden fallback.

[SOLID-S] The new diagnostic probe is separate from production runtime and
the GPU fail-close boundary remains separate from packet construction.
[SOLID-D] The boundary gate depends on runtime packet diagnostics rather than
on a concrete dense AO helper.  [SOLID-X] No CFL reduction, damping, smoothing,
curvature cap, FD/WENO/PPE fallback, hidden PCG/DC fallback, main merge, or
long-run workaround was introduced.
