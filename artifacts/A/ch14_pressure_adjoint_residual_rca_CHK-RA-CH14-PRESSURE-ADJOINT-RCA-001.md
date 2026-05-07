# CHK-RA-CH14-PRESSURE-ADJOINT-RCA-001

## Question

After the pressure-adjoint closed-interface residual contract was exposed,
N32/T1 static and oscillating droplets reported

```text
capillary_contract_pressure_adjoint_residual ~= 4.45e-01
```

even though the component saddle constraint was satisfied to roundoff
(`~1e-18`).  The task is to identify the root cause from the physics and
mathematics of the discrete pressure constraint, not by damping, CFL changes,
smoothing, curvature caps, fallbacks, or benchmark-specific branches.

## Theorem Being Tested

The pressure force is a constraint reaction.  In a discrete kinetic-energy
metric it must be the Riesz adjoint of the divergence constraint:

```text
<G_A p, w>_M_A = - <p, D_f w>_W_p
```

for all physically admissible pressure fields `p` and face velocities `w`.
Equivalently,

```text
M_A G_A = - D_f^T W_p .
```

If this identity fails, the PPE can still make `D_f u = 0`, but the face
corrector is not guaranteed to be an energy-orthogonal pressure reaction.  A
solenoidal pressure-face component can then be injected into the velocity, which
is precisely the mathematical form of a velocity-ring residual.

## Hypotheses

| id | Hypothesis | Verdict | Evidence |
|---|---|---|---|
| H1 | The residual is only a sign error in the diagnostic Green identity. | rejected as root | Changing the identity to `<G p,w> + <p,Dw>` is required, but the N32 residual remains nonzero. |
| H2 | The pressure-node mass `W_p` was missing. | rejected as root, supported as diagnostic contaminant | Adding `grid.cell_volumes()` is required, but the N32 residual remains nonzero. |
| H3 | The reported `0.445` is a pure production-force failure. | rejected | A large part is from probing the unreduced periodic image space rather than the physical quotient space. |
| H4 | Periodic duplicate nodes/faces are being treated as independent DOFs. | supported | FVM becomes exactly adjoint only after pressure nodes and transverse face images are synchronized and image rows/columns are excluded from the inner product. |
| H5 | The issue is a FVM/FCCD common discretization defect. | rejected | Reduced FVM has zero adjoint residual and zero symmetry residual. |
| H6 | The issue is caused by nonuniform grids, density ratio, affine jumps, or capillary geometry. | rejected as necessary cause | Uniform equal-density periodic probes already exhibit the FCCD residual. |
| H7 | The current FCCD face pressure gradient is not the variational pressure adjoint. | supported | On the physical periodic quotient, `||M G_FCCD + D^T W||/max(...) ~= 2.091e-01`. |
| H8 | A scalar/diagonal face-metric rescaling can make current `G_FCCD` adjoint. | rejected | Best diagonal least-squares metric still leaves residual `~9.46e-02` at N16/N32. |
| H9 | The PPE operator itself is non-symmetric. | rejected for uniform reduced probes | `W_p D G_FCCD` is symmetric to `~1e-16`. |
| H10 | The mismatch is a divergence-changing pressure error. | rejected | Since `W_p D G_FCCD` is symmetric while `G_FCCD` is not the adjoint representative, the difference is a divergence-free face component. |
| H11 | PPE DC tolerance or solver iteration is the source. | rejected | Dense algebraic operator probes reproduce the mismatch without solving a PDE. |
| H12 | Reinitialization causes the contract residual. | rejected | The residual is present in static no-reinit algebraic pressure probes. |
| H13 | The closed-interface Riesz cochain causes this pressure contract residual. | rejected as primary | The pressure-adjoint defect is present for arbitrary pressure/face probes before any capillary cochain is applied. |
| H14 | The component saddle is failing. | rejected | `B^T M h` is `~1e-18`; the remaining issue is pressure-range orthogonality, not component-reaction algebra. |
| H15 | The correct pressure range is `range(G_FCCD)`. | rejected physically | Constraint-force theory requires `range(M^{-1}D^TW)`.  `G_FCCD` may share the same divergence operator but not the same face representative. |

## Algebraic Verification

The following matrix probes were run on the reduced all-periodic physical
quotient.  Pressure unknowns are the unique `N x N` nodes; transverse face
image entries are synchronized and excluded from the inner product.  Thus the
test removes the diagnostic artifact from periodic image DOFs.

```text
n scheme adj_res      sym_res      best_diag_res G_vs_diag_adjoint
4 fvm    0.000000e+00 0.000000e+00 0.000000e+00 0.000000e+00
4 fccd   2.317652e-01 2.158110e-17 1.177168e-01 2.317652e-01
8 fvm    0.000000e+00 0.000000e+00 0.000000e+00 0.000000e+00
8 fccd   2.106151e-01 7.212583e-17 9.688008e-02 2.106151e-01
16 fvm   0.000000e+00 0.000000e+00 0.000000e+00 0.000000e+00
16 fccd  2.091217e-01 6.585851e-17 9.463318e-02 2.091217e-01
32 fvm   0.000000e+00 0.000000e+00 0.000000e+00 0.000000e+00
32 fccd  2.091171e-01 9.240340e-17 9.462458e-02 2.091171e-01
```

Definitions:

```text
adj_res       = ||M G + D^T W|| / max(||M G||, ||D^T W||)
sym_res       = ||W D G - (W D G)^T|| / ||W D G||
best_diag_res = best possible residual over all diagonal face metrics
```

The decisive pattern is:

1. Reduced FVM is exact.  Therefore the theorem and the periodic quotient test
   are correct.
2. Reduced FCCD keeps `W D G` symmetric to roundoff.  Therefore the PPE scalar
   operator can remain acceptable as a pressure solve.
3. Reduced FCCD still has `G_FCCD != -M^{-1}D^T W` by about `20.9%`.
4. Since `D G_FCCD` and `D(-M^{-1}D^T W)` agree in the energy operator but
   the face maps differ, their difference is a pressure-dependent
   divergence-free face cochain.

This is exactly the kind of cochain that a divergence-only PPE cannot see but a
kinetic-energy/capillary-work theorem must see.

## Root Cause

The root cause is a representation mismatch between the scalar pressure
operator and the face pressure corrector:

```text
G_FCCD = G_var + Z,
G_var = -M_A^{-1} D_f^T W_p,
D_f Z = 0,  Z != 0.
```

`G_FCCD` is divergence-equivalent to the variational pressure adjoint for the
PPE, but it is not the same face-space Riesz representative.  The divergence
equation only fixes `D_f G p`; it does not fix the divergence-free part of the
face pressure acceleration.  The current FCCD pressure face gradient carries
such a solenoidal component.

Physically, this violates the principle that pressure is a constraint force
doing no work on admissible divergence-free velocities.  Mathematically, it
means that the pressure range used in the capillary Hodge/saddle theorem is not
`range(G_FCCD)` but `range(G_var)` unless a nonlocal metric is proven that makes
`G_FCCD` the Riesz adjoint without changing the kinetic-energy meaning.

The originally observed `~0.445` diagnostic value has two layers:

1. A diagnostic-space artifact: the probe used unrestricted periodic image DOFs.
   On the physical periodic quotient FVM becomes exact.
2. A real FCCD face-representative defect: even after quotient reduction,
   `G_FCCD` differs from the variational pressure adjoint by `~0.209` in
   operator norm, and no diagonal face metric removes it.

## Consequences for the Droplet Problem

The component saddle currently enforces

```text
D_f h = 0,
B^T M_A h = 0,
```

but the pressure split used to define `h = c - L_A(c) - B mu` relies on PPE
solves with `G_FCCD`.  Because `G_FCCD` is not the energy adjoint, the Hodge
split is not a true `M_A`-orthogonal split against pressure reactions.  This
explains why component constraints can pass at `~1e-18` while a pressure-adjoint
contract residual remains nonzero and static velocity rings can persist.

## Rejected Fixes

The following would hide symptoms but violate the theorem:

- damping, CFL reduction, viscosity inflation, curvature caps, smoothing;
- FD/WENO/PPE fallback as production capillarity;
- treating `range(G_FCCD)` as the pressure range without proving a matching
  kinetic-energy metric;
- replacing all capillary cochains by `Pi_range(c)`;
- benchmark-name branches or static-droplet special cases.

## Theorem-Grade Remediation Direction

The pressure/corrector complex must use one of the following, in order of
mathematical cleanliness:

1. **Variational face corrector.**  Keep the scalar PPE solve if `D G_FCCD`
   is already the desired operator, but construct the face pressure acceleration
   for projection/Hodge/capillary work as

   ```text
   G_var p = -M_A^{-1}D_f^T W_p p
   ```

   on the physical periodic quotient, with nonuniform/affine coefficients
   included in the same `M_A,W_p,D_f` complex.  This removes the divergence-free
   pressure gauge component without changing the PPE source equation.

2. **FCCD variational redesign.**  Redesign `pressure_fluxes` itself so the
   returned face flux is the Riesz adjoint of `divergence_from_faces`.  The
   compact high-order pressure operator can still be used, but its face
   representative must be derived from an energy variational form, not chosen
   independently.

3. **Nonlocal metric proof.**  Prove and implement a non-diagonal face metric
   `M_*` for which `M_* G_FCCD = -D^T W`.  This is mathematically possible only
   if the resulting `M_*` is SPD, grid-local enough for GPU use, compatible with
   density/affine jumps, and still represents kinetic energy.  It is not a
   quick diagonal rescaling; the best diagonal metric already fails.

The next validation gate should not be a droplet run first.  It should be an
operator gate:

```text
G0. physical periodic quotient construction is explicit;
G1. FVM adjoint residual is roundoff;
G2. chosen FCCD variational face representative has adjoint residual roundoff;
G3. D_f G_var equals the PPE operator used in the solve;
G4. component saddle uses G_var and has D_f h≈0, B^T M h≈0, and
    pressure-range orthogonality≈0;
G5. only then rerun N32/T1 static and oscillating droplets.
```

## Verdict

The remaining pressure-adjoint residual is not a capillary-shape classifier
problem and not a time-step/stability problem.  It is a discrete mechanics
problem: the current FCCD pressure face corrector is divergence-equivalent to
the PPE pressure operator but not the kinetic-energy adjoint pressure reaction.
The physically correct fix is to make the pressure face representative
variationally adjoint on the same `D_f,M_A,W_p` complex used by capillary
Hodge projection and velocity correction.
