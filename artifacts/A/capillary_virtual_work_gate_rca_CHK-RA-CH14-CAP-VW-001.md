# CHK-RA-CH14-CAP-VW-001 - Capillary Virtual-Work Gate RCA

Date: 2026-05-06
Branch: `codex/ra-ch14-capillary-virtual-work-20260506`

## Question

The main ch14 oscillating droplet is stable and volume preserving, but it does
not oscillate.  Previous RCA already showed that production
`capillary_range_projection: range_projected` kills the face acceleration.
The unresolved question is deeper:

```text
Is the capillary cochain itself a surface-energy virtual-work covector in the
same weighted face space used by the PPE and corrector?
```

## Theory Contract

For a closed two-phase droplet, capillarity is the first variation of
`E_sigma = sigma |Gamma|`.  A circle is a constrained critical point of
`E_sigma - lambda V`; an ellipse is not.  The discrete face cochain must
therefore satisfy the same weighted Hodge gate used by the production PPE:

```text
L_h p = D_f c_sigma,    L_h = D_f A_f G_f
P_h c_sigma = c_sigma - A_f G_f L_h^{-1} D_f c_sigma
```

Required behavior:

```text
static circle:      ||P_h c_sigma||_{A_f^{-1}} ~= 0
oscillating ellipse: ||P_h c_sigma||_{A_f^{-1}} > 0
corrector:          a_f = A_f G_f p - c_sigma
diagnostics only:   Pi_range(c_sigma)
```

Replacing the production cochain by `Pi_range(c_sigma)` makes
`a_f = A_f G_f p - Pi_range(c_sigma) = 0` for a zero-predictor release.  That
is the algebraic zero-drive theorem, not a physical equilibrium criterion.

## Hypotheses

| ID | Hypothesis | Verdict |
|---|---|---|
| H01 | The ellipse is accidentally a static Young-Laplace state. | Rejected. Curvature and deformation are nonconstant; Hodge residual is nonzero. |
| H02 | Zero initial velocity invalidates the benchmark. | Rejected. Displacement release from rest must produce acceleration for a noncritical shape. |
| H03 | Viscosity removes the first capillary acceleration. | Rejected. The missing acceleration occurs before viscous damping can act. |
| H04 | PPE convergence failure hides the force. | Rejected. Prior probes and current one-step gates have small divergence after projection. |
| H05 | `range_projected` is a valid production capillary law. | Rejected. It zeros the applied face cochain in both static and dynamic releases. |
| H06 | `range_projected` is useful as a diagnostic Hodge split. | Supported. It exposes `P_h c_sigma` without changing the theory. |
| H07 | `none` is a complete production fix. | Rejected. It restores motion but also applies the static-circle residual. |
| H08 | `face_implicit` is an exact surface-energy virtual-work cochain. | Rejected. Static circle residual is not near roundoff. |
| H09 | `face_implicit` still separates ellipse from circle qualitatively. | Supported. Ellipse weighted Hodge residual is larger than static circle. |
| H10 | Static residual is only the nonuniform fitted grid. | Rejected. Uniform-grid probes keep comparable static residuals. |
| H11 | Static residual is clearly converging away from N=32 to N=64. | Rejected. Relative residual remains O(4-5%). |
| H12 | The scalar Young-Laplace jump is preferable to current P2 variational candidates. | Supported as a diagnostic baseline; it is much less pathological. |
| H13 | Existing `transport_variational` P1 cochain passes the static/dynamic gate. | Rejected. Static and ellipse relative residuals are nearly the same. |
| H14 | Existing `transport_variational_p2` cochain is production-ready. | Rejected strongly. It leaves almost the whole cochain in the Hodge component and creates large divergence. |
| H15 | A diffuse-psi transport-adjoint identity alone proves sharp-interface pressure-jump correctness. | Rejected. It does not close the volume-constrained Young-Laplace gate in PPE face space. |
| H16 | Reinitialization can be used to read capillary deformation. | Rejected. It moves the interface without physical velocity work. |
| H17 | The next fix may be damping/CFL/curvature smoothing. | Rejected by first principles; these hide energy-accounting defects. |
| H18 | The correct root target is a volume-constrained surface-energy cochain in the same `(D_f,A_f,G_f)` complex. | Supported. It is the only route consistent with both static and dynamic gates. |

## Weighted Face-Space Diagnostic Added

The diagnostic now reports the Hodge norm in the same `A_f^{-1}` face metric:

```text
||c||_{A_f^{-1}} = sqrt( sum_f |f| c_f^2 / A_f )
```

where `A_f` is the affine-jump face inverse-density coefficient used by
`FCCDDivergenceOperator.pressure_fluxes` and by the matrix-free PPE.  This is
diagnostic only; it does not change PPE, corrector, or any production YAML.

Remote validation:

```text
SSH_AUTH_SOCK=/private/tmp/codex-ssh-agent-test.sock make test \
  PYTEST_ARGS='twophase/tests/test_interface_projection_diagnostics.py -q'
```

The Makefile pushed to remote and ran the suite; because of Makefile argument
behavior it executed the full remote pytest suite:

```text
588 passed, 32 skipped
```

## Probe 1 - Production Kill Switch

Remote in-memory one-step probes used `N=32`, `max_steps=1`, no reinit, debug
diagnostics on, and no checked-in temporary YAML.

| Case | Projection | KE after one step | `||jump||_w` | `||P_h jump||_w` | applied `||face||_w` | Hodge Linf |
|---|---|---:|---:|---:|---:|---:|
| static circle | `range_projected` | `2.208e-38` | `1.151e-01` | `4.889e-03` | `3.995e-17` | `1.137e-03` |
| static circle | `none` | `5.561e-10` | `1.151e-01` | `4.889e-03` | `4.889e-03` | `1.137e-03` |
| ellipse | `range_projected` | `1.581e-38` | `1.172e-01` | `8.898e-03` | `3.502e-17` | `1.814e-03` |
| ellipse | `none` | `2.853e-09` | `1.172e-01` | `8.898e-03` | `8.898e-03` | `1.814e-03` |

Interpretation:

- `range_projected` makes the applied face acceleration zero even when the
  dynamic Hodge residual is larger than the static one.
- `none` applies the full Hodge component and produces motion, but it also
  applies the nonzero static-circle residual.
- Therefore `none` is a diagnostic proof of missing drive, not yet a proof of
  correct capillary physics.

## Probe 2 - Resolution and Grid

`face_implicit`, `range_projected`, no reinit:

| Grid | N | Shape | `||P_h jump||_w` | relative to `||jump||_w` | Hodge Linf |
|---|---:|---|---:|---:|---:|
| fitted | 32 | static circle | `4.889e-03` | `4.247e-02` | `1.137e-03` |
| fitted | 32 | ellipse | `8.898e-03` | `7.593e-02` | `1.814e-03` |
| fitted | 64 | static circle | `7.453e-03` | `4.503e-02` | `2.282e-03` |
| fitted | 64 | ellipse | `1.033e-02` | `6.166e-02` | `3.539e-03` |
| uniform | 32 | static circle | `5.672e-03` | `5.358e-02` | `1.179e-03` |
| uniform | 32 | ellipse | `8.741e-03` | `8.427e-02` | `1.238e-03` |
| uniform | 64 | static circle | `6.773e-03` | `4.610e-02` | `2.347e-03` |
| uniform | 64 | ellipse | `9.692e-03` | `6.562e-02` | `2.847e-03` |

Interpretation:

- The static residual is not only a fitted-grid artifact.
- It does not visibly converge to zero from N=32 to N=64 in this gate.
- The ellipse residual is consistently larger, so `face_implicit` retains a
  dynamic signal, but the static gate still fails at the level needed for a
  theorem.

## Probe 3 - Existing Variational Candidates

`N=32`, fitted grid, `range_projected`, no reinit:

| Curvature/cochain route | Shape | `||P_h c||_w` | relative | Hodge Linf | Diagnostic outcome |
|---|---|---:|---:|---:|---|
| `face_implicit` | static circle | `4.889e-03` | `4.247e-02` | `1.137e-03` | imperfect but bounded |
| `face_implicit` | ellipse | `8.898e-03` | `7.593e-02` | `1.814e-03` | dynamic signal |
| `transport_variational` | static circle | `2.283e-02` | `5.402e-02` | `6.477e-03` | no useful static/dynamic separation |
| `transport_variational` | ellipse | `2.456e-02` | `5.410e-02` | `8.123e-03` | no useful static/dynamic separation |
| `transport_variational_p2` | static circle | `4.082e-01` | `1.005e+00` | `8.345e-02` | fail |
| `transport_variational_p2` | ellipse | `3.189e+00` | `1.009e+00` | `1.642e+00` | fail |

The P2 result is decisive negative knowledge for this production face space:
the diffuse-psi surface-energy gradient may satisfy its own transport-adjoint
unit tests, but it is not a validated pressure-jump cochain for the
FCCD/Affine-Jump PPE.  It fails the static Young-Laplace gate before long-time
physics is considered.

## Root Cause

The problem has two layers.

1. The direct zero-drive cause is production replacement
   `c_sigma -> Pi_range(c_sigma)`.  This makes a zero-predictor capillary
   release algebraically stationary, including the oscillating ellipse.
2. The deeper unresolved cause is that none of the currently available
   capillary cochains has been proven, and the tested candidates do not pass,
   the volume-constrained surface-energy Hodge gate in the production
   `(D_f,A_f,G_f)` complex.

`face_implicit` is the least bad current diagnostic candidate: it has a larger
ellipse Hodge component than static circle, and it avoids the catastrophic P2
failure.  But it is not yet a theorem-grade surface-energy virtual-work
cochain because the static circle leaves an O(4-5%) weighted Hodge residual.

## Required Fix Direction

The next implementation must construct or verify

```text
c_sigma = T_h^* d(sigma S_h - lambda V_h)
```

in the same face metric and boundary conditions used by
`FCCDDivergenceOperator.pressure_fluxes` and the matrix-free PPE.  Acceptance
gates:

```text
static circle:        ||P_h c_sigma||_{A_f^{-1}} / ||c_sigma||_{A_f^{-1}} -> 0
oscillating ellipse:  ||P_h c_sigma||_{A_f^{-1}} > static gate by a clear margin
production corrector: uses full c_sigma, not Pi_range(c_sigma)
range projection:     diagnostic/static-equilibrium gate only
reinit:               recorded separately from capillary work
```

Do not fix by damping, smaller CFL, curvature caps, smoothing, FD/WENO/PPE
fallbacks, blanket `c -> Pi_R c`, or treating a QP/range projection as the
capillary law.

[SOLID-X] Diagnostic/RCA work only; no production solver behavior or checked-in
ch14 production YAML was changed.  The added weighted norms are read-only
diagnostics in the existing step-diagnostics path; no tested implementation was
deleted; no FD/WENO/PPE fallback or alternate numerical route was introduced.
