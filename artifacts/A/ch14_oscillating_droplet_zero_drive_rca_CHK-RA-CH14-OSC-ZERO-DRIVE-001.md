# CHK-RA-CH14-OSC-ZERO-DRIVE-001 — Oscillating Droplet Zero-Drive RCA

Date: 2026-05-06
Branch: `codex/ra-ch14-osc-n32-t1-20260506`

## First-Principles Contract

A deformed two-phase droplet at rest is not a static Young--Laplace
equilibrium unless the interface has constant curvature.  A circle can be
balanced by a constant pressure jump.  An ellipse has curvature variation, so
the capillary pressure jump must generate a nonzero pressure-gradient
acceleration and then kinetic energy.  Therefore a run with a noncircular
initial interface, nonzero surface tension, and zero velocity may start from
rest, but it may not remain exactly at rest.

The observed N=32, T=1 result violates this physical contract: velocity and
kinetic energy stayed at machine zero.

## Hypotheses

| ID | Hypothesis | Verdict |
|---|---|---|
| H1 | The initial condition is effectively circular, not elliptical. | Rejected. Initial signed deformation is nonzero (`7.617534e-02`). |
| H2 | Starting from zero velocity is physically invalid. | Rejected. Zero velocity is a valid displacement-release initial condition; capillary pressure must accelerate it. |
| H3 | The Rayleigh--Lamb period is long, so T=1 is too short to see motion. | Rejected as zero-drive cause. The reference changes only mildly, but acceleration/KE must be nonzero. |
| H4 | Viscosity overdamps the droplet instantly. | Rejected. At the first instant `u=0`, viscosity cannot remove a missing capillary acceleration; diagnostic no-range run creates KE. |
| H5 | The capillary CFL is too small or too large. | Rejected as zero-drive cause. The first-step algebra is independent of long-time timestep tuning. |
| H6 | Curvature is absent or constant on the ellipse. | Rejected. One-step probe reports `kappa_max=40.856` and `capillary_jump_linf=3.477644e-02`. |
| H7 | The affine pressure-jump cochain is not being built. | Rejected. `capillary_jump_linf` is nonzero in debug diagnostics. |
| H8 | The PPE solve fails and erases the jump. | Rejected. DC converges; first-step relative residual is `8.782239e-09`. |
| H9 | The face/nodal velocity reconstruction is broken. | Rejected. With `capillary_range_projection:none`, the same reconstruction gives nonzero velocity. |
| H10 | `range_projected` removes the physical capillary acceleration. | Supported. It makes `capillary_face_linf=0` and pressure faces exactly zero. |
| H11 | Ridge--Eikonal reinitialization changes shape without physical motion. | Supported. With velocity zero, one step changes signed deformation from `0.076175` to `0.045033`. |
| H12 | The N=32 grid is too coarse for a benchmark-quality frequency. | Plausible secondary limitation, but rejected as the zero-drive root cause because the no-range diagnostic still accelerates. |

## Key Local Probe

One-step N=32 diagnostic from the canonical oscillating-droplet YAML:

```text
mode=range_projected
capillary_jump_linf             3.477644e-02
capillary_range_projection_linf 3.398389e-02
capillary_hodge_residual        1.813600e-03
capillary_face_linf             0
u_linf, v_linf                  0, 0
pressure_faces_linf             0, 0

mode=none
capillary_jump_linf             3.477644e-02
capillary_hodge_residual        1.813600e-03
capillary_face_linf             1.813600e-03
u_linf, v_linf                  1.235913e-05, 9.806495e-06
pressure_faces_linf             1.813600e-03, 1.314046e-03
```

This isolates the zero-drive mechanism.  The capillary jump exists, but the
production `range_projected` corrector replaces the original jump cochain by
its range projection, so the full face acceleration
`A_f G_f p - Pi_range(c_f)` becomes zero.  The remaining Hodge residual is
recorded diagnostically but not applied to the velocity.

## Remote In-Memory Controls

Remote command used the existing pushed code on `python` and in-memory configs
derived from `ch14_oscillating_droplet.yaml`; no checked-in YAML was added.
All cases used `N=32`, `T=0.1`, debug diagnostics, and no output files.

| Case | Range projection | Reinit every | Final signed D | Final KE | Snapshot velocity Linf | capillary face max | Reinit count |
|---|---|---:|---:|---:|---:|---:|---:|
| range_reinit1 | range_projected | 1 | `4.450407e-02` | `0` | `0` | `0` | `10` |
| range_reinit0 | range_projected | 0 | `7.618373e-02` | `0` | `0` | `0` | `0` |
| none_reinit0 | none | 0 | `7.617690e-02` | `3.198901e-07` | `1.309306e-04` | `1.825112e-03` | `0` |
| none_reinit1 | none | 1 | `4.449870e-02` | `3.250361e-06` | `8.426856e-04` | `1.393512e-02` | `10` |

The range-projected cases prove that no physical acceleration reaches the
velocity update.  The reinit cases prove that the large deformation change seen
in the original T=1 run can happen without physical motion.

## Root-Cause Inference

The implemented range projection was validly motivated by the static circular
droplet: a constant-curvature Young--Laplace equilibrium should not receive a
spurious divergence-free face acceleration.  The implementation then applied
the same removal to all pressure-jump runs.  That overgeneralizes a static
equilibrium condition into a dynamic capillary law.

For a noncircular droplet, the divergence-free/Hodge part of the capillary face
cochain is not automatically an error.  It is precisely the part that can do
incompressible capillary work.  Removing it generically converts the deformed
droplet into a pressure-only state with no velocity response.

Secondary issue: every-step Ridge--Eikonal reinitialization is not passive for
this diagnostic.  It can change the moment-based deformation while velocity is
zero, so it must not be mistaken for physical Rayleigh--Lamb motion.

## Excluded Quick Fixes

No remedy is applied here.  The next change must be derived from the discrete
energy/Young--Laplace contract, not by damping, CFL tuning, curvature capping,
smoothing, FD/WENO substitution, or suppressing diagnostics.

[SOLID-X] RCA/docs only; no solver/config production change; no tested
implementation deleted; no FD/WENO/PPE fallback or alternate scheme introduced.
