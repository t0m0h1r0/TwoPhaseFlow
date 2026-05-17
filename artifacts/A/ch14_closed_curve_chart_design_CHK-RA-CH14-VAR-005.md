# CHK-RA-CH14-VAR-005 — Closed-curve chart design after graph oracle PASS

## Claim

The closed-droplet route should be a second chart of the same
interface-configuration primary variational principle validated by the graph
oracle, not a special closed-surface branch.

The owned state is a material closed curve `Gamma_h`, represented by periodic
vertices or a smooth periodic parameterization `X(theta)`.  The cell-volume
field remains a derived measurement:

```text
Gamma_h -> q = Q_h(Gamma_h)
```

## Continuous Chart

For a closed curve `X(theta,t)` with liquid inside,

```text
E[X] = sigma integral |X_theta| dtheta
A[X] = 1/2 integral X cross X_theta dtheta
```

The admissible virtual work is

```text
dE[X](delta X) + lambda dA[X](delta X)
```

with `lambda` the pressure/volume reaction.  In the continuous normal
direction this gives the usual capillary pressure jump, but the chart should
not be implemented as "curvature first."  It should be implemented as
variation of `E[X]` plus the area constraint in the same face/pressure metric
that transports the material interface.

## Discrete Closed-Curve State

Use a periodic polygonal chart first:

```text
X_i = (x_i, y_i),      i = 0,...,M-1,      X_M = X_0
e_i = X_{i+1} - X_i
l_i = |e_i|
E_h[X] = sigma sum_i l_i
A_h[X] = 1/2 sum_i X_i cross X_{i+1}
```

The exact nodal covectors are:

```text
dE/dX_i = sigma ( e_{i-1}/l_{i-1} - e_i/l_i )
dA/dX_i = 1/2 R90( X_{i+1} - X_{i-1} )
```

where `R90(a,b)=(-b,a)` for the oriented polygon convention.  These are the
closed-curve analogues of the graph oracle's segment-energy gradient.  The
graph chart is recovered when `X_i=(x_i, eta_i)` with fixed ordered `x_i`; the
closed chart keeps both coordinates free but uses the same edge-length energy.

## Derived Measurements

`phi` may be generated as a gauge for measurement or visualization, for example
by a signed-distance, winding-number, or radial-star chart when valid.  That
gauge is not the owner.  `q` is produced only after the curve state is known:

```text
q_C = Q_h(Gamma_h)_C
```

For the first closed-curve oracle, use direct polygon area/cell clipping or a
regular gauge generated from `Gamma_h`.  The acceptance record must compare:

- polygon area `A_h[X]`;
- derived cell volume `sum_C q_C`;
- interface length `E_h[X]/sigma`;
- finite-difference checks of both `dE/dX` and `dA/dX`.

If a generated gauge places `phi=0` exactly on mesh nodes, that is a chart
singularity and must be moved by the oracle setup; it is not a smoothing or
tolerance issue.

## Face-Cochain Runtime Design

The runtime connection should convert curve virtual work into the same face
cochain space that moves the material interface:

```text
T_h(u_f; Gamma_h)          = curve/material transport map
dE/dt                     = dE[X](T_h u_f)
surface force covector    = -T_h^T dE
volume reaction covector  =  T_h^T dA
acceleration cochain      = M_f^{-1} force covector
```

This is the same structure as the existing fixed-stratum diagnostic language
in `src/twophase/coupling/closed_interface_riesz.py`, but the ownership order
must be inverted for the origin-reset route:

```text
old diagnostic: psi stratum -> trace length gradient -> face Riesz
new chart:      Gamma_h owner -> derived q/phi -> face Riesz
```

The existing closed-interface Riesz code can be reused only if its inputs are
proven to be a derived regular chart of `Gamma_h`, not if it makes `psi` or a
screened projection the owner.

## Closed-Droplet Oracle Before T/8

The first closed-droplet oracle should use a mode-2 perturbation:

```text
X(theta) = c + R(1 + eps cos(2 theta)) (cos theta, sin theta)
```

Acceptance gates:

| Gate | PASS criterion |
|---|---|
| area conservation | `A_h[X]` and `sum q` agree; area reaction direction is nonzero and independent of surface variation |
| energy trend | `E_h[X] - E_h[circle]` grows like `eps^2` |
| variation finite difference | `dE/dX` and `dA/dX` match finite-difference perturbations |
| force sign | mode-2 restoring covector opposes the deformation mode after removing pure area reaction |
| rigid modes | translation and rotation modes produce zero/near-zero surface-energy variation |
| chart consistency | graph and closed-chart signs follow the same virtual-work convention |
| visualization | PDF shows curve, derived q/area, surface covector, area reaction, and mode projection |

Only after these gates pass should Ch14 runtime receive the closed chart, and
the first runtime probe should still be short.  A T/8 oscillating-droplet run
is not admissible as the first closed-chart test.

## Runtime Non-Negotiables

- Do not make "closed surface Riesz active" a theory condition.
- Do not make "screened projection converged" a theory condition.
- Do not conserve transported q while computing surface energy from an
  unrelated rebuilt phi/curve.
- Do not accept visual circularity without `A_h`, `Q_h`, energy, variation, and
  face-cochain diagnostics.
- Do not introduce tolerance weakening, smoothing, damping, curvature caps,
  CFL retuning, rebuild skipping, FD/WENO/PPE fallback, or hidden CPU fallback.

