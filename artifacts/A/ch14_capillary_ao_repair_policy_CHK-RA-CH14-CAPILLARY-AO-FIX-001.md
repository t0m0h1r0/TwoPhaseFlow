# CHK-RA-CH14-CAPILLARY-AO-FIX-001 - SP-AO/AO-Fast repair policy

Date: 2026-05-12
Branch/worktree: `codex/ra-ch14-capillary-ao-run-20260512` at `.claude/worktrees/codex-ra-ch14-capillary-ao-run-20260512`

## Scope

User request: establish the repair policy from the previous RCA, based on
physics and mathematics.  The policy must preserve AO-Fast.  It must not use
small offsets, CFL changes, damping, smoothing, curvature caps, dense CPU
runtime fallback, hidden component-Hodge fallback, or a return to direct dense
AO.

## Theory Boundary

The fix is a face-space virtual-work split, not a nodal residual tweak.

SP-AO defines the capillary object as the face covector

```text
delta E_Gamma,h[w_f] = - <r_sigma, w_f>,
```

and the physically active acceleration as

```text
a_sigma,bal = M_f^{-1}(r_sigma - Pi^{M_f}_{R_p(q_T)} r_sigma).
```

Therefore the implementation must compute the three objects in this order:

```text
source_face      = r_sigma
reaction_face    = Pi^{M_f}_{R_p(q_T)} source_face
balanced_face    = source_face - reaction_face
balanced_accel   = M_f^{-1} balanced_face
```

The pressure reaction subspace is not the full cell-pressure image.  It is the
subspace admitted by the same active AO-Fast face complex, boundary contract,
PPE operator, gauge, component-volume constraints, and pressure-history
contract used by the momentum correction:

```text
R_p(q_T) = range(G_A under active PPE contract) + range(B_component).
```

Equivalently, using the paper's notation, define

```text
L_A(c) = G_A p_c,       D_f G_A p_c = D_f c,
Z_A(c) = c - L_A(c).
```

For component reactions, solve the small face-metric saddle elimination:

```text
C_ij = <Z_A(B_i), Z_A(B_j)>_{M_f}
r_i  = <Z_A(B_i), Z_A(source_face)>_{M_f}
C mu = r

corrected_source = source_face - B mu
balanced_face    = Z_A(source_face) - Z_A(B) mu
```

The corrected source passed to the pressure/correction pipeline is
`corrected_source`; the non-pressure physical drive used for admission and
diagnostics is `balanced_face`.

## What Changes

1. The capillary-drive classifier must stop using nodal
   `residual_linf = ||g + J_q^T pi||` as the runtime non-static certificate.
   That residual remains an admission diagnostic for the pressure solve.

2. The GPU packet must stop constructing

   ```text
   capillary_face = T_q^T pressure_cell
   pressure_face  = capillary_face
   residual_face  = 0.
   ```

   This is the algebraic cancellation proven in the RCA.  The capillary face
   object must instead be the AO-Fast source covector `r_sigma` obtained from
   the bundle virtual work.

3. `pressure_exact_static` and `capillary_drive_present` must be classified
   from the face-space balanced norm:

   ```text
   pressure_exact_static    := ||balanced_face||_{M_f^{-1}} <= tol
   capillary_drive_present  := ||balanced_face||_{M_f^{-1}} >  tol
   ```

   `Young-Laplace normal residual <= tol` remains a prerequisite, not the
   drive definition.

4. `pressure_history_mode='pressure_coordinate'` may be admitted only after a
   scalar AO pressure coordinate is reconstructed from the same active PPE
   projection used in `L_A(corrected_source)`.  Until that scalar coordinate is
   available, pressure-coordinate runs must continue to fail closed.

## AO-Fast Preservation

The repair must keep the AO-Fast contract:

- compact active-stratum tables plus one-face halo;
- fixed-stratum approximations used only as proposal generators;
- exact active `Q_h/S_h/J_q/dS_h` refresh for accepted states;
- matrix-free active Schur/PPE projection with warm starts and admitted
  preconditioners;
- GPU-resident reductions inside nonlinear/PCG/DC loops;
- no dense full-grid masks in production runtime;
- no host scalar synchronization inside candidate iterations;
- no hidden switch to dense exact AO, CPU oracle, or component-Hodge fallback.

The diagonal active-Schur packet may remain as a preconditioner or fail-close
diagnostic.  It is not the production pressure reaction projection and cannot
certify capillary admission by itself.

Frozen-stratum and DC logic are allowed only under the AO-Fast accuracy
contract:

```text
beta_C = ||delta phi||_{infty,C} / min(gamma_C, m_C)
first-order candidate remainder: O(beta_C^2)
second-order candidate target:   O(beta_C^3)
accepted state: exact active residual/sign/work gates
DC: residual-monotone for exact Q_h^S(phi)-q
```

## Implementation Order

1. Add an AO-Fast capillary split service with a CPU oracle entry and the same
   public fields required by the current runtime packet:

   ```text
   source_face_covectors
   pressure_reaction_face_covectors
   balanced_face_covectors
   corrected_source_face_covectors
   weighted_balanced_acceleration_l2
   max_abs_balanced_face_covector
   pressure_coordinate_source, if available
   ```

2. Implement the range projection using the existing active PPE contract:
   compute `L_A(c)` from the same `D_f G_A` operator and gauge, then compute
   `Z_A(c)`.  For closed components, assemble only the small `C mu = r` system
   from projected Hodge residuals.  This is the mathematical `R_p(q_T)`.

3. Replace runtime classification so `balanced_face`, not nodal `e`, determines
   non-static capillary admission.  Keep nodal Young-Laplace normal residual as
   a pressure-solve accuracy gate.

4. Port the split to GPU through AO-Fast compact streams.  The first accepted
   GPU implementation may fail closed when a required device-side reduction or
   matrix-free projection is missing; it must not fall back to a different
   physics path.

5. Re-enable `pressure_coordinate` only after the scalar coordinate from
   `L_A(corrected_source)` is present and checked against the face reaction.

## Acceptance Tests

Minimum algebraic tests before a production run:

```text
flat interface:
  balanced_face ~= 0
  capillary_drive_present == False

static circle:
  balanced_face ~= 0 after component reaction removal
  pressure_exact_static == True

capillary wave, k=1,2,3:
  balanced_face > 0
  restoring sign agrees with surface-energy descent
  balanced norm grows qualitatively with wave number/amplitude

tiny y shift by 1e-10 m:
  same qualitative class as unshifted wave
```

AO-Fast-specific tests:

```text
fixed-stratum candidate:
  exact Q_h/S_h residual gates pass before state commit

GPU runtime:
  no host sync inside active projection loop
  no dense CPU/runtime fallback
  missing projection capability fails closed

pressure_coordinate:
  rejects until scalar AO coordinate is built
  accepts only when scalar coordinate reproduces L_A(corrected_source)
```

Then run, in order:

```text
diagnose_ao_algebraic_split.py
targeted unit tests for the split service
make cycle EXP=experiment/run.py ARGS='--config ch14_capillary'
```

## Rejected Repair Paths

- move the interface by `1e-10` in `y`;
- reduce timestep, add damping, add smoothing, or cap curvature;
- classify drive from `e != 0`;
- set `source_face = T_q^T pressure_cell`;
- replace `source_face` by `L_A(source_face)`;
- use full cell-pressure image as `R_p(q_T)`;
- silently use component-Hodge as production fallback without proving it is the
  admitted `R_p` complement;
- run dense direct AO in production to avoid AO-Fast implementation work.

## Decision

The shortest theory-correct repair is to implement the AO-Fast face-space
pressure-reaction projection:

```text
r_sigma -> r_sigma - Pi^{M_f}_{R_p(q_T)} r_sigma
```

and make this balanced face cochain the only non-static capillary drive
certificate.  The existing fail-close behavior is correct until that object is
available.
