# CHK-RA-CH14-VAR-050 - Experiment Readiness Theory/Implementation Review

Date: 2026-05-17

Scope: answer whether the implementation needed to start experiments is
complete, and cross-check the current theory against the implemented G0--G5
PhaseRegion face-force gates.

## Verdict

The implementation is ready for zero-step and controlled admission/projection
experiments.  It is not yet ready for a physical Ch14 T/8 run or a runtime
micro-step.

The remaining required implementation before a physical run is a controlled
single-step gate that consumes the G5 projected face arrays, reconstructs or
updates the runtime velocity in the solver-owned space, and verifies
divergence, work, energy, and no unintended state drift.  The nodal
`force_components` route remains closed.

## Theory Review

The active theory is internally consistent:

```text
owned state:        PhaseRegion Omega_h
derived interface:  Gamma_h = boundary Omega_h
derived measure:    q = Q_h(Omega_h)
chart/gauge:        phi or graph/curve/local atlas representation
energy:             E[Omega_h] = sigma * Perimeter(Omega_h)
force object:       face cochain s_f in the same M_f work metric as velocity
pressure reaction:  pressure/range component paired in the same face metric
```

This resolves the earlier split where `q` was conserved, `phi` was rebuilt,
curvature was taken from `phi`, and pressure/velocity lived in another space.
The key invariant is not "make a smooth phi from noisy q"; it is "admit only a
surface-force cochain whose work is the first variation of the same owned
PhaseRegion state."

The main unresolved theory boundary is topology/runtime ownership, not the
zero-step algebra.  Multi-component atlases, open boundary-attached layers, and
topology changes are represented in the design, but this dry-run exercises only
the closed-interface runtime chart.  That is acceptable for admission tests but
not sufficient for a production rising-bubble/top-layer experiment.

## Equation -> Discretization -> Code

| Equation / invariant | Discretization | Code / test evidence |
|---|---|---|
| `dE[Omega_h](v) = <s_f, v_f>_M` | PhaseRegion Riesz face cochain and face mass metric | `build_phase_region_force_admission(...)`; `self_riesz_residual=0` |
| pressure and capillary work share one metric | `pressure_face_components`, `surface_acceleration`, and `face_weight_components` on identical face shapes | G0--G2 reports; `same_weight_surface_work_residual=5.55e-17` |
| explicit zero-step projection | `u_f^+ = u_f - dt p_f + dt s_f` | G3/G5; `face_projection_identity_linf=2.08e-17` |
| admitted payload identity | consumed `s_f` equals `admission.cochain.surface_acceleration` componentwise | G5; `face_force_component_linf=0` |
| exact norm check | `||u_f^+||_M = sqrt(sum M_f (u_f^+)^2)` | unit test recomputes the closed-form expression |
| boundary/nonuniform grid compatibility | direct face boundary space and metric weights from grid coordinates, no uniform-h shortcut | G0 tests and dry-run `boundary_residual_linf=0`, `grid_alpha=2` |

## Review Finding

The previous CHK-049 hardening checked that the consumed G5 face force had the
same weighted norm as the G4-admitted payload.  That was necessary but not
sufficient: a same-norm direction change could still satisfy the norm check.

This checkpoint strengthens G5 with a componentwise identity check against
`admission.cochain.surface_acceleration`:

```text
max_axis ||s_f(G4 payload) - s_f(admitted cochain)||_inf <= tol
```

The failure mode is `face_force_component_linf`.  A test now flips the sign of
the G4 payload; the weighted norm is unchanged, but G5 rejects it.

## Validation

Remote tests:

```text
make test PYTEST_ARGS='twophase/tests/test_phase_region_force_admission.py -q'
```

Result:

```text
866 passed, 35 skipped
```

Runtime dry-run:

```text
make cycle EXP=experiment/ch14/diagnose_phase_region_runtime_force_dry_run.py
```

Key metrics:

```text
g0_valid                         = 1.000000000000e+00
g1_valid                         = 1.000000000000e+00
g2_valid                         = 1.000000000000e+00
g3_valid                         = 1.000000000000e+00
g4_valid                         = 1.000000000000e+00
g5_valid                         = 1.000000000000e+00
face_force_exposed               = 1.000000000000e+00
face_force_consumed              = 1.000000000000e+00
face_force_component_linf        = 0.000000000000e+00
face_force_consistency_residual  = 0.000000000000e+00
face_projection_identity_linf    = 2.081668171172e-17
face_projected_weighted_l2       = 1.279680161323e-02
boundary_residual_linf           = 0.000000000000e+00
force_admissible                 = 1.000000000000e+00
```

## Remaining Work Before Physical T/8

1. Build the controlled single-step consumer for G5 projected face arrays.
2. Verify velocity reconstruction/update in the runtime-owned space without
   using nodal `force_components`.
3. Check divergence, pressure work, capillary work, and kinetic/surface energy
   after one step.
4. Only after that, run a short bounded micro-step experiment.
5. T/8 remains blocked until the micro-step gate passes.

[SOLID-X] No C1 violation found.  This checkpoint changes only the G5
diagnostic guard/tests/dry-run metric and review evidence; it does not add a
production runtime force route, nodal force route, velocity reconstruction,
state mutation, YAML route, solver algorithm, nonlinear optimizer, CFL change,
damping, smoothing, tolerance weakening, rebuild skipping, FD/WENO/PPE
fallback, hidden CPU fallback, micro-step, T/8 runtime run, main merge, branch
deletion, worktree removal, or origin push.
