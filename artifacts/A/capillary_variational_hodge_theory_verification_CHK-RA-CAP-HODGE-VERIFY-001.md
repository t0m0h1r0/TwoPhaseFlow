# CHK-RA-CAP-HODGE-VERIFY-001 - Verification of Generic Variational-Hodge Capillary Theory

Date: 2026-05-06
Branch: `codex/ra-ch14-osc-n32-t1-20260506`

## Question

Verify whether `CHK-RA-CAP-HODGE-THEORY-001` is mathematically correct:

1. pressure may remove only the pressure-range part of a force;
2. the remaining Hodge/Leray component is the incompressible capillary drive;
3. replacing a capillary cochain `c_f` by `Pi_R c_f` in the corrector is not a
   generic production law;
4. static rest must be a variational critical-point condition, not a
   shape-specific branch.

## Verdict

The theory is correct under its stated assumptions.

The essential assumptions are:

- `c_f` is a genuine discrete surface-energy covector, i.e. a
  transport-adjoint or discrete-gradient derivative of `E_h = sigma |Gamma_h|`;
- the PPE and velocity corrector use the same face-space complex
  `D_f A_f G_f`;
- the equilibrium gate is evaluated in the same admissible velocity space and
  boundary conditions as the production projection.

This verification does not prove that the current raw curvature-derived
`c_f` is already a faithful variational cochain.  It verifies the projection
and Hodge contract that the next implementation must satisfy.

## Check 1 - Continuum Variational Sanity

For a closed curve with surface energy `E = sigma L`, the first variation is

```text
delta L[u_n] = - integral_Gamma kappa u_n ds
```

up to the sign convention for normal orientation.  At a circle, `kappa` is
constant.  Therefore every first-order area-preserving perturbation has zero
first variation.  For a non-equilibrium perturbation, the first variation with
respect to its amplitude is nonzero.

Numerical check with `r(theta)=R+eps cos(n theta)`:

```text
mode=0 dArea=6.283185307221e+00 dLength=6.283185307021e+00
mode=1 dArea=0.000000000000e+00 dLength=0.000000000000e+00
mode=2 dArea=0.000000000000e+00 dLength=0.000000000000e+00
mode=3 dArea=0.000000000000e+00 dLength=0.000000000000e+00
mode=4 dArea=0.000000000000e+00 dLength=0.000000000000e+00
perturbed_n2 eps=0.02 dLength/deps=2.512269566601e-01
perturbed_n2 eps=0.05 dLength/deps=6.267550578087e-01
perturbed_n2 eps=0.10 dLength/deps=1.244301322467e+00
```

Interpretation:

- the circle passes the generic first-variation equilibrium condition for
  volume-preserving modes;
- finite-amplitude mode-2 shapes do not;
- no special `circle` logic is needed to state the condition.

## Check 2 - Finite-Dimensional Hodge Algebra

A random finite-dimensional complex was constructed with:

```text
D: cell x face
A: SPD face coefficient
G = D^T
L = D A G
Pi_R c = A G pinv(L) D c
h = c - Pi_R c
```

Results:

```text
random capillary cochain
  ||D h||                3.915904e-15
  ||h||                  1.327896e+00
  full_accel_norm        1.327896e+00
  replaced_accel_norm    0.000000e+00

pure pressure-range cochain
  ||D h||                1.553564e-14
  ||h||                  4.941428e-15
  full_accel_norm        4.941428e-15
  replaced_accel_norm    0.000000e+00

pure divergence-free cochain
  ||D h||                4.079220e-16
  ||h||                  2.214438e+00
  full_accel_norm        2.214438e+00
  replaced_accel_norm    0.000000e+00
```

Interpretation:

- `h` is divergence-free to roundoff;
- the full corrector preserves the Hodge acceleration;
- replacing `c` by `Pi_R c` kills the acceleration even when the whole cochain
  is divergence-free;
- the kill-switch theorem is geometry-independent algebra, not an artifact of
  the oscillating-droplet case.

## Check 3 - Repo One-Step N=32 Consistency

The canonical `ch14_oscillating_droplet.yaml` was probed at `N=32` for one
step, with no file output and no production changes.

```text
range_projected:
  capillary_jump_linf              3.477644e-02
  capillary_range_projection_linf  3.398389e-02
  capillary_hodge_residual         1.813600e-03
  capillary_face_linf              0.000000e+00
  u_linf, v_linf                   0.000000e+00, 0.000000e+00
  pressure_face_linf               0.000000e+00, 0.000000e+00

none:
  capillary_jump_linf              3.477644e-02
  capillary_range_projection_linf  3.398389e-02
  capillary_hodge_residual         1.813600e-03
  capillary_face_linf              1.813600e-03
  u_linf, v_linf                   1.235913e-05, 9.806495e-06
  pressure_face_linf               1.813600e-03, 1.314046e-03
```

Interpretation:

- the capillary jump exists in both cases;
- the Hodge component is nonzero;
- `range_projected` removes the applied face acceleration and velocity;
- preserving the full cochain produces nonzero capillary release.

This matches the finite-dimensional theorem exactly.

## Limits of Verification

This verification supports the theory, but it also narrows what remains
unproven:

1. The raw `face_implicit` curvature jump is not yet proven to be the
   transport-adjoint discrete gradient of surface energy.
2. The next implementation must construct or verify such a variational cochain,
   rather than merely setting `capillary_range_projection:none`.
3. Static equilibrium must be accepted by a generic `||P_h c_f||` variational
   gate.  If a circle fails that gate, the cochain construction is wrong; the
   remedy is not blanket Hodge deletion.

## Conclusion

The generic variational-Hodge theory is correct as a target contract:

```text
build c_f from discrete surface-energy virtual work;
solve D_f A_f G_f p = r_h + D_f c_f;
apply the full a_f = A_f G_f p - c_f;
use range/Hodge projection only as diagnostics and equilibrium verification.
```

[SOLID-X] verification/docs only; no solver/config production change; no
tested implementation deleted; no FD/WENO/PPE fallback or alternate numerical
route introduced.
