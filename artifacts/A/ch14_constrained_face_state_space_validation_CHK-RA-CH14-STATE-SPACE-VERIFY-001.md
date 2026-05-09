# CHK-RA-CH14-STATE-SPACE-VERIFY-001: Constrained Face-State Space Validation

## Question

After implementing the SP-AN constrained face-state building blocks, what is
the fastest theory-driven way to decide whether they are mathematically
consistent enough to proceed toward a production restricted pressure solve?

## Efficient Validation Ladder

Long rising-bubble reruns are intentionally deferred until the algebraic
operator gates pass.  The validation order is:

```text
S1  P_w^2=P_w and P_w is M_f-self-adjoint.
S2  C_w P_w=0 and C_w P_w G_A p=0.
S3  restricted Green identity:
    <P_w G_A p, eta>_{M_f} + <p,D_h eta>_Q = 0,
    eta in F_w.
S4  rank gate:
    rank(D_h P_w G_A) = rank(D_h | F_w).
S5  manufactured restricted projection:
    f_dag = h + P_w G_A p0, h in K_w,
    solve D_h P_w G_A p = D_h f_dag and recover h.
S6  only after S1--S5: one-step rising-bubble publication gate.
S7  short N=32x64 run.
S8  droplet/capillary regressions.
```

This ordering is cheap because S1--S5 use small manufactured operators and
unit tests; it also avoids confusing a long unstable wall-bounded run with a
basic adjoint/rank failure.

## Metric Hypothesis And Result

The first probe tested whether the implemented metric could be density-only:

```text
M_f ?= rho_f.
```

It failed the restricted Green identity:

```text
CASE wall:
  S4 rank(D_h P_w)=19, rank(D_h P_w G_A)=19
  S3 density-only restricted Green relative residual = 9.169329e-01
```

The theory explains the failure: pressure work and divergence live on
cell/control volumes, so the face-state metric must use the same quadrature:

```text
M_f = Q_f rho_f.
```

After changing `project_wall_trace` and `face_mass_inner_product` to use
`Q_f rho_f`, the full-wall gates passed:

```text
CASE wall:
  S4 rank(D_h P_w)=19, rank(D_h P_w G_A)=19
  cond(D_h P_w G_A)=2.085924e+01
  S3 restricted Green residual=2.220446e-16
  S3 restricted Green relative residual=8.826843e-17
  S5 manufactured K_w relative recovery error=1.537101e-14
  S5 manufactured divergence L2=4.713074e-13
  S5 manufactured wall-trace Linf=5.532534e-31
```

This is a structural correction, not a parameter adjustment.

## Periodic-Wall Fail-Close Gate

The same probe still fails on mixed periodic-wall topology:

```text
CASE periodic_wall:
  S4 rank(D_h P_w)=30, rank(D_h P_w G_A)=27
  cond(D_h P_w G_A)=2.714085e+01
  S3 restricted Green residual=-2.074887e-01
  S3 restricted Green relative residual=1.037769e-01
```

Decision: do not enable `periodic_wall` production restricted pressure.  This
is consistent with the SP-AN quotient warning: periodic identifications,
pressure gauge variables, wall trace rows, and pressure basis must be
assembled in one quotient space before the rank gate can be trusted.  Adding a
fallback, damping, or a post-wall repair would hide this violation.

## Regression Tests Added

`src/twophase/tests/test_boundary_hodge.py` now includes:

```text
test_restricted_pressure_green_identity_on_full_wall_space
test_restricted_pressure_manufactured_projection_recovers_kw_state
```

These complement the existing `P_w`, YAML, and rank gates.

## Validation Commands

```text
git diff --check
SSH_AUTH_SOCK=/private/tmp/codex-ssh-agent-test.sock make test \
  PYTEST_ARGS='twophase/tests/test_boundary_hodge.py -q'
```

The Makefile wrapper expanded the targeted request to the remote CPU suite:

```text
648 passed, 33 skipped in 42.44s
```

The targeted `boundary_hodge` file itself reported:

```text
twophase/tests/test_boundary_hodge.py ........
```

## Production Decision

The full-wall constrained face-state operator has passed S1--S5 and is ready
for the next implementation slice: a matrix-free restricted solve of

```text
D_h P_w G_A p = D_h P_w f_dag.
```

Do not proceed to long rising-bubble reruns or mixed periodic-wall production
before:

```text
1. the restricted solve is implemented,
2. one-step publication gates pass for D_h f, C_w f, u=R_h f, and m=rho u,
3. periodic-wall quotient rank/Green gates pass or remain explicitly disabled.
```

## Negative Knowledge

Rejected again by this validation:

```text
density-only face metric,
post-pressure wall projection as production,
generic D_h^T pressure replacement,
dense CPU KKT production path,
periodic-wall fallback,
damping/CFL/smoothing/DCCD/UCCD suppression.
```
