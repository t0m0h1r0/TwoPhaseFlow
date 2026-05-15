# CHK-RA-CH14-CAPILLARY-AO-RCA-004 — SP-AO reread RCA

Date: 2026-05-12
Branch/worktree: `codex/ra-ch14-capillary-ao-run-20260512` at `.claude/worktrees/codex-ra-ch14-capillary-ao-run-20260512`

## Scope

User request: return to the short paper AO theory and reason from physics and mathematics, generating and checking many hypotheses.  No small hacks, offsets, CFL changes, damping, smoothing, caps, or hidden fallback fixes are allowed.

## SP-AO Definitions Re-read

SP-AO defines the state by hard geometric cell volume:

```text
q_C = Q_h(phi)_C.
```

Face velocity work is not read from curvature arrays.  A face-volume cochain `w` changes cell volumes by

```text
delta q = T_q(Gamma_h) w.
```

The bundle lift is:

```text
L_B(w) = argmin ||delta_phi||_W
         subject to J_q delta_phi = T_q w.
```

The capillary face covector is virtual work:

```text
r_sigma(w) = -sigma dS_h(phi)[L_B(w)].
```

Static Young-Laplace balance is a separate test:

```text
sigma dS_h(delta_phi) + pi^T J_q delta_phi = 0
```

for all admissible bundle variations.  The runtime drive is not `e = sigma dS_h + J_q^T pi` by itself.  It is the face-space residual after projecting the capillary covector only onto an admissible physical pressure-reaction subspace:

```text
r_bal = r_sigma - Pi^{M_f}_{R_p(q_T)} r_sigma.
```

The paper-facing rule says the same thing: the object is `r_sigma` and its pressure-reaction decomposition, not `r_sigma` projected into the full cell-pressure image and then read as a residual.  The standard pressure-jump/Hodge route removes pressure and component-volume reactions in the same face metric and keeps the remaining admissible capillary drive.

## Code-Object Mismatch

The current CPU classifier and GPU packet look at different mathematical objects.

CPU classification in `src/twophase/simulation/geometric_phase_runtime.py` uses the nodal residual:

```text
if residual.residual_linf <= tolerance:
    pressure_exact_static
else:
    nonzero_capillary_drive
```

That is insufficient under SP-AO: `e != 0` does not imply a nonzero face drive when the runtime reaction space is the full cell-pressure image.

The GPU packet in `src/twophase/simulation/geometric_phase_runtime_gpu.py` then constructs:

```text
pressure_cell = diag-Schur approximate pressure
capillary_face = T_q^T pressure_cell
pressure_face  = capillary_face
residual_face  = capillary_face - pressure_face = 0
```

So the classifier says "nonzero capillary drive" from nodal `e`, while the applied face cochain has zero drive by construction.

The CPU helper `geometric_pressure_capillary_hodge_2d` explicitly describes its full-pressure residual as a geometry-layer identity gate, not a runtime pressure subtraction route.  The current AO admission path treated that identity-style full-pressure construction as if it were the runtime split.

## Hypotheses Re-generated From SP-AO

| ID | Hypothesis | Verification | Status |
|---|---|---|---|
| H26 | The SP-AO state variable `q` is wrong for capillary waves. | `q/phi` compatibility residual is zero in Rung-0 probes; YAML correctly declares `q`. | Rejected |
| H27 | The bundle lift `L_B` is absent, so any capillary result is meaningless. | The code has `T_q/J_q` Schur-based bundle diagnostics, but the runtime misuses the resulting full-pressure identity. | Partial, not root |
| H28 | `e = g + J_q^T pi` is the physical face drive. | CPU exact has nonzero `e` but face balanced drive `0`. | Rejected |
| H29 | `e != 0` is only an admission signal unless lifted into face space. | SP-AO states face work through `L_B(w)` and `M_f`; probes show nodal/face disagreement. | Supported |
| H30 | Full cell-pressure image is the correct `R_p`. | It deletes all non-flat wave drive for A sweep, k sweep, and N64. | Rejected |
| H31 | Full cell-pressure image is useful as a static identity gate. | It can test Young-Laplace representability but cannot be used as runtime subtraction. | Supported |
| H32 | The component-volume residual is the final SP-AO solution. | It passes qualitative gates but lacks scalar pressure-coordinate proof. | Rejected as final, retained as diagnostic |
| H33 | The physical pressure-adjoint `R_p` must live in the same face metric as PPE/corrector. | Paper §9 and SP-AO both require pressure work Green identity and `M_f/M_A` consistency. | Supported |
| H34 | The current `capillary_drive_present` flag is mathematically well-defined. | It is set from nodal residual but contradicted by face residual zero. | Rejected |
| H35 | The immediate code defect is only diagonal Schur accuracy. | CPU exact full-pressure split also gives zero face drive. | Rejected |
| H36 | A certified PCG solve of the current full Schur system fixes motion. | It would certify the same over-large full pressure image and preserve zero drive. | Rejected |
| H37 | `pressure_coordinate` is primary. | Face-acceleration diagnostic still has zero drive; scalar coordinate remains a secondary gate. | Rejected as primary |
| H38 | Boundary wall constraints are the root cause. | Valid wall-complex probes isolate the algebra; invalid y-periodic probe fails closure. | Rejected as primary |
| H39 | Tiny geometry offsets are valid. | `1e-10 m` y-shift leaves the failure class unchanged and would violate translational invariance as a remedy. | Rejected |
| H40 | Mainline production success proves AO-Fast is fine. | Mainline uses a different pressure-jump/component-Hodge route. | Rejected |
| H41 | The SP-AO capillary force should be built by reusing the scalar pressure multiplier as the force. | That makes `r_sigma` and pressure reaction identical in face space. | Rejected |
| H42 | `r_sigma` must be assembled as the source face covector first, then decomposed. | This is exactly SP-AO/paper wording and avoids identity-gate misuse. | Supported |
| H43 | A production run is meaningful before Rung-0 face gates pass. | It would run an unadmitted packet. | Rejected |
| H44 | The shortest repair can be hidden component-Hodge fallback. | YAML forbids hidden fallback and component-Hodge lacks final coordinate proof. | Rejected |
| H45 | The shortest theory-respecting repair is a diagnostic `R_p` gate with scalar-coordinate proof obligation. | It directly tests the missing SP-AO object: `r_sigma - Pi_{R_p}^{M_f} r_sigma`. | Supported |

## Problem Identification

The root cause is a **category error between three SP-AO objects**:

1. `e = g + J_q^T pi`: a nodal Young-Laplace residual/admission signal.
2. `r_sigma`: the face covector obtained by bundle virtual work.
3. `R_p`: the physical pressure-reaction subspace in the face mass metric.

The current path uses object 1 to declare non-static drive, then uses a full-pressure version of object 2/3 that makes the actual face residual zero.  The contradiction is not numerical; it is mathematical.

In SP-AO terms, the current code solves or approximates:

```text
S lambda = J_q(-g)
S pi     = -J_q g
```

and then uses both through the same `T_q^T` face map.  Thus `lambda=pi`, so full-pressure subtraction cancels the force.  This is why improving the diagonal Schur solve alone cannot restore motion.

## Theory-Exact Next Step

The next slice should not advance the capillary wave.  It should implement a diagnostic gate around the exact SP-AO object:

```text
source:       r_sigma(w) = -sigma dS_h[L_B(w)]
reaction:     Pi^{M_f}_{R_p(q_T)} r_sigma
runtime gate: r_bal = r_sigma - Pi^{M_f}_{R_p(q_T)} r_sigma
```

Required pass/fail set:

- flat interface: `r_bal = 0`;
- capillary wave k=1/2/3: `r_bal != 0` with monotone trend;
- amplitude sweep: monotone scaling;
- y shift of `1e-10 m`: same qualitative result;
- N32/N64: same qualitative result;
- non-static `pressure_coordinate`: fail-closed until scalar AO coordinate is reconstructed from the admitted `R_p` split.

Only after this gate exists should GPU optimization or production admission be attempted.

[SOLID-X] Theory/probe/artifact only; no production solver source, YAML physical parameter, CFL reduction, damping, smoothing, curvature cap, FD/WENO/PPE fallback, hidden dense/CPU fallback, hidden component-Hodge fallback, offset workaround, long unadmitted run, main merge, or branch deletion introduced.
