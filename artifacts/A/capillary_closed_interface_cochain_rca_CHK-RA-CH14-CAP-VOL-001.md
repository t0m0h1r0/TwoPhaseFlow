# CHK-RA-CH14-CAP-VOL-001 - Closed-Interface Capillary Cochain RCA

Date: 2026-05-06
Branch: `codex/ra-ch14-capillary-virtual-work-20260506`

## Question

`CHK-RA-CH14-CAP-VW-001` found two facts:

1. production `capillary_range_projection: range_projected` kills oscillating
   droplet drive by replacing `c_sigma` with `Pi_range c_sigma`;
2. simply using the full `face_implicit` cochain is not yet theorem-grade
   because a static circle leaves an O(4-5%) weighted Hodge residual.

This RCA asks what creates that static-circle residual.

## Mathematical Contract

For a static circle, Young--Laplace equilibrium is

```text
u = 0,
p_liquid - p_gas = sigma / R,
a_f = A_f G_f p - c_f = 0.
```

If the discrete affine jump cochain is exact in the production face complex,
then a constant jump on a circular interface must lie in
`range(A_f G_f)` up to discretization error:

```text
P_h c_f = c_f - A_f G_f (D_f A_f G_f)^-1 D_f c_f ~= 0.
```

If this fails even for constant curvature, the problem is not curvature
estimation.  If it succeeds for planar jumps but fails for curved closed
interfaces, the problem is the compatibility between local cut-face jump
cochains and the FCCD pressure-gradient complex on closed geometry.

## Hypotheses

| ID | Hypothesis | Verdict |
|---|---|---|
| H01 | Static-circle residual is caused by nonconstant computed curvature. | Rejected. Replacing curvature by exact constant `1/R` leaves the same residual. |
| H02 | The sign convention for `kappa_lg` is wrong. | Rejected as root. `+1/R` and `-1/R` produce identical residual norms. |
| H03 | The residual is only fitted nonuniform-grid error. | Rejected. Uniform-grid residual remains comparable. |
| H04 | The residual is low resolution and should vanish from N32 to N64. | Rejected. Relative residual remains O(4-5%). |
| H05 | Missing volume constraint `-lambda V_h` is the root. | Rejected for current cochains. Adding continuum `lambda=sigma/R` to the P2 transport-adjoint covector changes almost nothing. |
| H06 | Existing P2 transport-adjoint cochain is correct once volume constrained. | Rejected strongly. It leaves nearly the whole cochain in the Hodge component and has large divergence. |
| H07 | The affine jump/FCCD machinery cannot represent any constant pressure jump. | Rejected. Wall-bounded flat interfaces pass to ~1e-9 relative Hodge residual. |
| H08 | Periodic flat-interface probe is valid. | Rejected. A single periodic step creates an incompatible topology and enormous projection values. |
| H09 | The failure appears specifically on closed curved/cut geometry. | Supported. Circle residual persists; planar wall interface is exact. |
| H10 | Closed axis-aligned interfaces are as bad as circles. | Rejected. Square residual is much smaller and decreases relatively with N. |
| H11 | Oblique/diagonal cuts are the whole cause. | Partially rejected. Diamond residual is small compared with circle; curvature/closed smooth geometry matters too. |
| H12 | FCCD high-order pressure range and local cut-face jump are not the same cochain complex on curved closed interfaces. | Supported. Constant jump is not exact for circle despite exact planar behavior. |
| H13 | A nodal phase-step pressure is the missing exact potential for a circular constant jump. | Rejected as exact representation. Best sign phase-step pressure still mismatches the local cochain by about 20%. |
| H14 | Diffuse pressure `q ~ psi` fixes the mismatch. | Rejected. Diffuse candidates mismatch the sharp local jump by O(1). |
| H15 | The static residual is harmless if divergence is small. | Rejected. It is a divergence-free face cochain, exactly the component that can accelerate an incompressible velocity. |
| H16 | Range projection is therefore a valid production fix for statics. | Rejected. It removes the same Hodge space that carries real dynamic capillary release. |
| H17 | The correct fix is damping, smaller CFL, curvature smoothing, or caps. | Rejected by energy theory; those hide a cochain-complex defect. |
| H18 | The correct target is a closed-interface capillary cochain that is exact for constant Young--Laplace jumps and nonzero only for noncritical shape modes. | Supported. |

## Probe 1 - Exact Constant Curvature on the Static Circle

Remote command pattern:

```text
SSH_AUTH_SOCK=/private/tmp/codex-ssh-agent-test.sock ssh python ...
```

The same `psi`, `rho`, `D_f`, `A_f`, `G_f`, and PPE were used.  Only the
curvature source was changed.

| Grid | N | Curvature | `||c||_w` | `||P_h c||_w` | Relative | Hodge Linf |
|---|---:|---|---:|---:|---:|---:|
| fitted | 32 | computed | `1.151e-01` | `4.889e-03` | `4.247e-02` | `1.137e-03` |
| fitted | 32 | constant `+1/R` | `1.149e-01` | `4.918e-03` | `4.281e-02` | `1.149e-03` |
| uniform | 32 | computed | `1.059e-01` | `5.672e-03` | `5.358e-02` | `1.179e-03` |
| uniform | 32 | constant `+1/R` | `1.058e-01` | `5.683e-03` | `5.374e-02` | `1.181e-03` |
| fitted | 64 | computed | `1.655e-01` | `7.453e-03` | `4.503e-02` | `2.282e-03` |
| fitted | 64 | constant `+1/R` | `1.654e-01` | `7.382e-03` | `4.462e-02` | `2.316e-03` |
| uniform | 64 | constant `+1/R` | `1.469e-01` | `6.779e-03` | `4.617e-02` | `2.348e-03` |

Conclusion: curvature noise is not the root cause.  Even an exact constant
Young--Laplace jump is not exact in the current closed-circle face complex.

## Probe 2 - P2 Surface Covector Plus Volume Constraint

The tested covector was

```text
g = d(sigma S_h) +/- lambda dV_h,
lambda in {0, sigma/R, -sigma/R, sigma/(2R), 2 sigma/R}.
```

For static circle:

```text
uniform N=32: relative Hodge ~= 1.007 for every lambda/sign
uniform N=64: relative Hodge ~= 1.007 for every lambda/sign
fitted  N=32: relative Hodge ~= 1.005 for every lambda/sign
fitted  N=64: relative Hodge ~= 1.008 for every lambda/sign
```

Conclusion: the existing P2 transport-adjoint route is not merely missing the
continuum volume multiplier.  It is not a validated pressure-jump cochain in
the production affine-FCCD face space.

## Probe 3 - Flat Interface Sanity

A wall-bounded flat interface with constant artificial jump was tested in the
same affine-FCCD machinery.

| Shape | Boundary | N | `||c||_w` | `||P_h c||_w` | Relative | Hodge Linf |
|---|---|---:|---:|---:|---:|---:|
| vertical plane | wall | 32 | `8.972e-02` | `1.270e-10` | `1.416e-09` | `4.237e-11` |
| horizontal plane | wall | 32 | `8.972e-02` | `1.270e-10` | `1.416e-09` | `4.237e-11` |
| vertical plane | wall | 64 | `1.259e-01` | `1.783e-10` | `1.416e-09` | `8.474e-11` |
| horizontal plane | wall | 64 | `1.259e-01` | `1.783e-10` | `1.416e-09` | `8.474e-11` |

Conclusion: the affine jump/FCCD range is not generically broken.  It exactly
represents a flat constant pressure jump in compatible topology.

The periodic flat-interface probe was discarded: a single step in a periodic
domain is topologically incompatible and generated enormous projection values.

## Probe 4 - Closed Geometry Dependence

Constant jump, uniform periodic grid, no reinit:

| Shape | N | `||c||_w` | `||P_h c||_w` | Relative | Hodge Linf |
|---|---:|---:|---:|---:|---:|
| square | 32 | `1.288e-01` | `2.264e-03` | `1.758e-02` | `5.928e-04` |
| diamond | 32 | `1.375e-01` | `2.702e-03` | `1.966e-02` | `1.283e-03` |
| circle | 32 | `1.058e-01` | `5.683e-03` | `5.374e-02` | `1.181e-03` |
| square | 64 | `1.794e-01` | `2.264e-03` | `1.262e-02` | `1.186e-03` |
| diamond | 64 | `1.786e-01` | `2.561e-03` | `1.434e-02` | `2.329e-03` |
| circle | 64 | `1.469e-01` | `6.779e-03` | `4.617e-02` | `2.348e-03` |
| square | 128 | `2.518e-01` | `2.264e-03` | `8.991e-03` | `2.371e-03` |
| diamond | 128 | `2.223e-01` | `2.350e-03` | `1.057e-02` | `3.889e-03` |
| circle | 128 | `2.087e-01` | `9.591e-03` | `4.596e-02` | `4.692e-03` |

The ad-hoc ellipse signed-function probe was discarded because the supplied
dimensionless implicit function was not a signed-distance/profile-compatible
field and produced pathological projection values.  The canonical oscillating
ellipse result from `CHK-RA-CH14-CAP-VW-001` remains the valid ellipse gate.

Conclusion: the residual is tied to closed-interface geometry, not to the
existence of an affine jump alone.  Axis-aligned/diamond closed interfaces are
closer to exact; the smooth circle retains O(4-5%) relative residual.

## Probe 5 - Nodal Phase-Step Pressure Candidate

If the local cut-face constant jump were simply `A_f G_f q` for a nodal
piecewise-constant pressure, then `q = +/- j 1_g` or `q = +/- j 1_l` should
match it.

Best relative mismatch for the static circle:

```text
uniform N=32: phase-step q mismatch ~= 2.17e-01
uniform N=64: phase-step q mismatch ~= 2.14e-01
fitted  N=32: phase-step q mismatch ~= 2.04e-01
fitted  N=64: phase-step q mismatch ~= 2.03e-01
diffuse q ~ psi or 1-psi: O(1) mismatch
```

Conclusion: the current local cut-face cochain is not the FCCD gradient of the
obvious phase pressure.  The PPE range projection finds a better least-squares
representative than this naive `q`, but a nonzero Hodge component remains.

## Root Cause

The original no-oscillation symptom has a direct and a deeper cause.

Direct cause:

```text
production uses c_sigma_production = Pi_range(c_sigma)
```

so the corrector applies

```text
a_f = A_f G_f p - Pi_range(c_sigma) = 0
```

for a zero-predictor capillary release.  This kills the physical ellipse drive.

Deeper cause:

The current local sharp affine jump cochain is not a closed-interface exact
cochain in the production FCCD face complex.  It is exact for compatible flat
interfaces, but for a circular closed interface even a constant Young--Laplace
jump leaves a divergence-free residual:

```text
D_f P_h c ~= 0,  P_h c != 0.
```

That residual is not curvature noise, not sign error, not grid fitting alone,
not missing continuum `lambda`, and not a generic PPE failure.  It is a
cochain-complex mismatch:

```text
local cut-face B_Gamma(j)  notin  range(A_f G_f)
```

on curved closed geometry.

## Consequences

1. `range_projected` cannot be the production law.  It deletes both the
   spurious static residual and the genuine dynamic capillary release.
2. `none` is not theorem-grade either.  It restores motion but also applies
   the static-circle closed-interface residual as parasitic capillary work.
3. Existing P2 transport-adjoint routes are not validated remedies in this
   face space.
4. The next constructive target must be a closed-interface exact cochain:

```text
constant Young-Laplace jump on circle -> P_h c ~= 0
nonconstant constrained shape mode    -> P_h c != 0
```

in the same `(D_f, A_f, G_f)` complex used by PPE and corrector.

## Prohibited Non-Fixes

Do not solve this by damping, CFL reduction, curvature caps, smoothing,
FD/WENO/PPE fallback, blanket range projection, or treating a QP projection as
physical capillarity.  These alter symptoms without repairing the variational
cochain contract.

[SOLID-X] RCA/docs only; no production solver/config/YAML behavior changed;
no tested implementation deleted; no FD/WENO/PPE fallback introduced.
