# CHK-RA-CH14-BUBBLE-RCA-BOUNDARY-HODGE-001

## Scope

Reorganize the rising-bubble investigation and identify the shortest path to
the remaining blow-up cause using physical and mathematical hypotheses rather
than damping, CFL tuning, curvature caps, smoothing, or fallback solvers.

The target problem is the SI water-air rising bubble on the canonical
conservative common-flux, pressure-adjoint, closed-interface Riesz,
variational-gravity route.

## Theory Baseline

For a bounded tank with no-slip walls, the continuous velocity space is not
only the divergence-free space.  It is the constrained space

```text
V_0 = { u in H^1(Ω)^d : div u = 0, u|∂Ω = 0 }.
```

The pressure part removes the gradient/range component in a kinetic-energy
metric, but it cannot by itself impose tangential no-slip.  A discrete
fractional step must therefore keep the face Hodge space, nodal reconstruction,
transport flux, conservative momentum, and wall boundary operator in one
commuting diagram:

```text
face flux f  --R--> nodal velocity u
     |                  |
     | D_f f = 0        | B u = u
     v                  v
div-free faces      no-slip nodes
```

If the code computes a divergence-free face state `f`, reconstructs `R f`,
then applies nodal no-slip `B R f` while preserving the original `f`, the next
step transports mass using `f` but stores momentum from `B R f`.  That breaks
the common-flux ledger and creates a boundary work defect localized on the wall
nodes:

```text
F_transport = f,            m_saved = rho * B R f,
but generally R f != B R f.
```

This is not a cosmetic visualization mismatch.  It means the state is not a
single point in the discrete phase space.

## Hypotheses

### H1: old hot checkpoint is not a valid new-route state

Status: accepted for cross-map restarts.

The production manifest gate rejects the old checkpoint on config fingerprint
mismatch.  Diagnostic bypass shows the old hot velocity/momentum becomes
unstable even with `sigma=g=0`, while the same hot geometry with zero velocity,
zero momentum, and zero projected faces survives to `t=0.024`.

This explains why old checkpoints are useful only as diagnostic probes.

### H2: basic common-flux transport is intrinsically unstable

Status: rejected.

Zero-start `sigma=0, g=0` reached `t=0.002` in one step with exactly zero
velocity, zero kinetic energy, zero volume drift, zero face/nodal mismatch,
zero divergence, and zero momentum inconsistency.

```text
speed_linf = 0
KE = 0
volume_drift = 0
projected_face_div = 0
momentum_consistency_linf = 0
```

### H3: static circular capillary pressure jump is the primary blow-up cause

Status: rejected as primary.

Zero-start `sigma=0.072, g=0` ran to `t=0.002` under the capillary time step
with tiny kinetic energy and conserved volume:

```text
steps = 283
speed_linf = 2.2877443385790515e-03
KE = 5.127129596395177e-09
volume_drift = 4.087663367513539e-13
projected_face_div = 4.6391157582093e-10
```

The static capillary residual is not perfect, but it is not the observed fast
blow-up mechanism.

### H4: variational gravity covector alone is wrong

Status: not supported as primary.

The covector has a direct virtual-work unit test:

```text
sum_f r_g,f w_f + sum_c (g y)_c delta rho_c = 0,
delta rho = -D_f(rho_f w_f).
```

Zero-start `sigma=0, g=9.81` produces a finite buoyant response.  The important
observation is not a bulk work-sign failure but that a single large step already
creates a face/nodal boundary mismatch:

```text
speed_linf = 8.45881214613182e-02
face_node_mismatch = 4.1048574883619085e-02
projected_face_div = 3.4335198209944906e-05
momentum_consistency_linf = 0
```

### H5: pressure projection fails in the bulk

Status: rejected as primary for the canonical face-state route.

For zero-start normal `sigma=0.072, g=9.81`, the canonical face-state route
reached `t=0.002` with projected-face divergence near roundoff:

```text
projected_face_div = 4.5054715513970223e-10
div_u_max = 4.5054715513970223e-10
```

The face Hodge solve is doing its bulk divergence-removal job.

### H6: face/nodal wall-space mismatch is the active root

Status: accepted as the leading cause.

For normal `sigma=0.072, g=9.81`, the canonical route at `t=0.002` has:

```text
speed_linf = 7.87863191930569e-02
KE = 6.060369321347314e-06
volume_drift = 5.6208536767079e-11
face_node_mismatch = 2.783239863665568e-02
projected_face_div = 4.5054715513970223e-10
momentum_consistency_linf = 0
```

A more detailed decomposition shows the mismatch is entirely on the wall:

```text
total mismatch    = 2.7832398636655688e-02
wall mismatch     = 2.7832398636655688e-02
interior mismatch = 0
face div Linf     = 4.505475992289121e-10
```

One-step normal diagnostics show the same pattern immediately:

```text
u_interior_linf = 0
v_interior_linf = 0
u_wall_linf     = 5.159944560699693e-05
v_wall_linf     = 1.4519890391527474e-04
nodal wall speed = 0
reconstructed wall speed = 1.4519890391527474e-04
```

Thus the state saved after a step is simultaneously:

```text
divergence-free in face space,
no-slip only after nodal BC overwrite,
transported next step by the preserved face flux,
published as conservative momentum from the overwritten nodal velocity.
```

That is a discrete phase-space inconsistency.

### H7: simply discarding the face state is a valid fix

Status: rejected.

Diagnostic `canonical_face_state=false, preserve_projected_faces=false` removes
the face/nodal mismatch by not carrying faces, but it loses the face-native
Hodge constraint and blows up earlier:

```text
t = 8.90983124435474e-04
steps = 133
speed_linf = 2.5080621064154008e+02
KE = 7.293892213767518e+02
ppe_rhs_max = 1.0710995280956676e+13
div_u_max = 1.5784475205854836e+06
```

Therefore the fix cannot be "turn off face state".  The face state is necessary,
but it must live in the same constrained wall space as the nodal/momentum
state.

### H8: nonuniform-grid volume accounting is the primary cause

Status: rejected for the early route.

All zero-start short diagnostics keep volume drift tiny:

```text
sigma-only: volume_drift = 4.087663367513539e-13
normal:     volume_drift = 5.6208536767079e-11
```

The observed defect appears before any volume error large enough to explain
the blow-up.

### H9: reinitialization is the active cause

Status: rejected for this route.

The canonical rising-bubble YAML uses `reinitialization.schedule.every_steps: 0`.
The early defect appears in a no-reinit common-flux step.

### H10: the cure is DCCD/FCCD/UCCD damping or a CFL tweak

Status: rejected by theory.

The failure is an algebraic incompatibility of discrete state spaces:

```text
R f != B R f,
F_transport = f,
m_saved = rho * B R f.
```

Damping, CFL reduction, smoothing, or curvature caps may delay symptoms, but
they do not restore the missing commuting diagram.

## Identified Cause

The leading cause is a boundary-constrained Hodge incompatibility:

1. The pressure/corrector produces a divergence-free projected face state.
2. Nodal velocity is reconstructed from that face state.
3. Nodal no-slip is applied after reconstruction.
4. The projected face state is preserved without the same nodal wall constraint.
5. Conservative momentum is published from the wall-clamped nodal velocity.
6. The next common-flux transport uses the preserved face state.

This splits one physical velocity into two discrete velocities.  The defect is
zero in the interior and localized at the wall, exactly as the diagnostics show.
Gravity makes the mismatch large because it creates a sustained face-space
impulse that pressure projection can make divergence-free but cannot make
tangentially no-slip unless the face Hodge space itself encodes that constraint.

## Shortest Valid Path

The promising route is not to abandon face-native projection.  It is to make
the face-native Hodge state and nodal no-slip state mathematically identical.
Candidate implementations to evaluate next:

1. Constrained reconstruction:
   build `R_0 : F_0 -> N_0` so reconstructed nodes satisfy wall no-slip without
   a post-hoc nodal overwrite.
2. Constrained face projection:
   solve the pressure/face correction in a face subspace whose reconstruction
   already satisfies `B R f = R f`.
3. Coupled saddle projection:
   after pressure correction, solve the minimum kinetic-energy correction
   subject to both `D_f f=0` and `B R f=0`.
4. Momentum publication from the canonical velocity:
   once a constrained face/nodal pair exists, publish conservative momentum
   from the same canonical velocity used for transport.

The rejected shortcut is to set `canonical_face_state=false`; it destroys the
face Hodge constraint and fails earlier.

## Verification Commands Run

Remote diagnostics were run on host `python` with
`SSH_AUTH_SOCK=/private/tmp/codex-ssh-agent-test.sock`, using the canonical
`ch14_rising_bubble.yaml` at N=32x64 and the runner-equivalent initial
nonuniform grid rebuild.

Validation artifacts are diagnostic-only; no solver source or YAML was changed.
