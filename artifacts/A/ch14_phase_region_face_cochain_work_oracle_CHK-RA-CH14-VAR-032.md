# CHK-RA-CH14-VAR-032 - PhaseRegion face-cochain work oracle

Date: 2026-05-17

Scope: add and validate an endpoint face-cochain work-pairing oracle for the
PhaseRegion variational route.  This checkpoint does not connect Ch14 runtime
force, pressure projection, velocity update, nonlinear optimization,
micro-step, or T/8.

## Motivation

`CHK-RA-CH14-VAR-031` proved that the closed-chart interface force is the
area-reaction-free negative variation of the same surface energy.  The next
question is whether that interface covector can be carried to the face
pressure/velocity endpoint without changing its virtual work.

The oracle checks the endpoint identity:

```text
T_h(u_f) = -D_f(psi_f u_f)
s_f = -M_f^{-1} T_h^T dE_h
dE_h[T_h(u_f)] + <s_f, u_f>_{M_f} = 0
```

## Implementation

Added:

```text
experiment/ch14/diagnose_phase_region_face_cochain_work_oracle.py
```

The script:

1. builds a uniform periodic ellipse fixed-stratum `psi`;
2. constructs the existing closed-interface Riesz cochain;
3. checks virtual work for the cochain's own face acceleration;
4. checks a mixed probe velocity (`surface_acceleration + 0.125*smooth`);
5. splits the face cochain into weighted pressure range and Hodge parts;
6. verifies a manufactured pressure-range cochain has zero Hodge leak;
7. checks the negative face-divergence adjoint on a nonuniform
   `periodic_wall` grid;
8. saves a visualization of `psi`, face cochain vectors, and diagnostic bars.

## Preserved Failed Attempt

The first implementation tried a standalone smooth face velocity as a second
work probe.  That failed the relative Riesz residual gate because the smooth
field is near-orthogonal to the symmetric ellipse and produces nearly zero
work.  The accepted oracle keeps the same equations and tolerances, but uses a
mixed probe velocity so the work denominator is meaningful.

This is not tolerance weakening and not damping; it is a discriminating probe
choice.

## Equation -> Discretization -> Code

| Equation | Discretization | Code |
|---|---|---|
| `T_h(u_f)=-D_f(psi_f u_f)` | FCCD/FVM face transport on fixed stratum | `transport_increment_from_face_velocity` via `fixed_stratum_virtual_work_check` |
| `s_f=-M_f^{-1}T_h^T dE_h` | closed-interface Riesz cochain | `closed_interface_riesz_cochain` |
| `<s_f,u_f>_{M_f}` | face-weighted dot product | `fixed_stratum_virtual_work_check` |
| pressure range/Hodge split | exact dense diagnostic `D_f` matrix | `weighted_hodge_decomposition` |
| nonuniform boundary adjoint | nonuniform `periodic_wall` face shapes | `_nonuniform_adjoint_error` |

## Validation Result

Initial remote command:

```text
make cycle EXP=experiment/ch14/diagnose_phase_region_face_cochain_work_oracle.py
```

Result: FAIL, due to standalone smooth probe near-zero work.

Final remote command:

```text
make cycle EXP=experiment/ch14/diagnose_phase_region_face_cochain_work_oracle.py
```

Result: PASS.

```text
self_fd_power_residual         = 1.678373246703e-08
self_riesz_residual           = 0.000000000000e+00
self_finite_difference        = -2.661536463708e+01
self_capillary_power          = 2.661536553049e+01
probe_fd_power_residual        = 1.678894666868e-08
probe_riesz_residual          = 6.674177881816e-17
probe_finite_difference       = -2.661536463680e+01
probe_capillary_power         = 2.661536553049e+01
component_weighted_l2         = 5.159008192520e+00
range_weighted_l2             = 5.156228180604e+00
hodge_weighted_l2             = 1.693413122495e-01
hodge_divergence_linf         = 1.989519660128e-13
manufactured_range_hodge_l2   = 3.163533455825e-12
manufactured_range_recovery_linf = 1.057287590811e-11
nonuniform_adjoint_error      = 7.105427357601e-15
force_admissible              = 0.0
```

Local outputs pulled from remote:

```text
experiment/ch14/results/diagnose_phase_region_face_cochain_work_oracle/data.npz
experiment/ch14/results/diagnose_phase_region_face_cochain_work_oracle/phase_region_face_cochain_work_oracle.pdf
```

The PDF is nonempty (`49K`) and visualizes the fixed stratum, face cochain, and
diagnostic residuals.

## Code Review

[SOLID-X] no violation.  The new code is an experiment diagnostic that reuses
the existing `closed_interface_riesz` and FCCD divergence objects.  It does not
add or modify a production force path, pressure/velocity adapter, runtime YAML
route, solver algorithm, nonlinear optimizer, smoothing, damping, CFL
retuning, tolerance weakening, rebuild skipping, FD/WENO/PPE fallback, hidden
CPU fallback, or micro-step.

## Theory Consistency

This oracle validates the endpoint adjoint identity:

```text
interface energy covector
-> fixed-stratum transport adjoint T_h^*
-> face cochain
-> same virtual work in M_f
```

It also confirms the diagnostic pressure range/Hodge decomposition is behaving
as expected, and that the face-divergence adjoint identity survives a small
nonuniform periodic-wall boundary probe.

It still does not authorize runtime T/8 because this is a fixed-stratum
`psi`/FCCD endpoint oracle, not the new PhaseRegion runtime force adapter.  The
next gate should be a zero-step runtime force dry-run that reports the mapped
face cochain, pressure range/Hodge split, and work metric with
`force_admissible = false`.

## Final Validation

```text
git diff --check = PASS
remote make cycle = PASS
docs/wiki WIKI count = 425
docs/wiki/experiment WIKI-E count = 74
targeted CHK/wiki/script scan = PASS
```
