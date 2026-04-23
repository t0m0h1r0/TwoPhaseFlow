---
id: WIKI-T-069
title: "FCCD Face Jet: Face-Carried Value, Gradient, and Curvature for FVM/HFE"
status: PROPOSED
date: 2026-04-23
links:
  - "[[WIKI-T-046]]: FCCD face-gradient foundation"
  - "[[WIKI-T-055]]: FCCD advection Option B/C"
  - "[[WIKI-T-063]]: FCCD face-flux PPE"
  - "[[WIKI-T-068]]: FCCD face-flux projector"
  - "[[WIKI-L-031]]: FCCDSolver face-jet implementation"
compiled_by: ResearchArchitect
---

# FCCD Face Jet: Face-Carried Value, Gradient, and Curvature for FVM/HFE

## Core idea

The useful FCCD object for two-phase FVM is not only a face gradient. It is
the face jet

$$
\mathcal{J}_f(u)=(u_f,u'_f,u''_f).
$$

This aligns three roles at the same geometric locus:

- FVM conservation uses face fluxes.
- Variable-density PPE uses $(1/\rho)_f p'_f$.
- HFE advection reconstructs directional states at the same face.

## Executable first-stage equations

Let $q=S_{\rm CCD}u$ be the nodal CCD second derivative and
$H_i=x_i-x_{i-1}$. The current executable jet is

$$
u_{i-1/2} =
\frac{u_{i-1}+u_i}{2}
-\frac{H_i^2}{16}(q_{i-1}+q_i),
$$

$$
u'_{i-1/2} =
\frac{u_i-u_{i-1}}{H_i}
-\frac{H_i}{24}(q_i-q_{i-1}),
$$

$$
u''_{i-1/2} = \frac{q_{i-1}+q_i}{2}.
$$

The third equation is intentionally a bridge closure. It exposes the face
curvature needed by HFE while preserving the option to replace it with a direct
face-unknown block solve later.

## Pressure-Poisson role

For

$$
\partial_x(\alpha p_x)=S,\qquad \alpha=1/\rho,
$$

the FVM discrete cell equation remains

$$
(\alpha p_x)_{i+1/2}-(\alpha p_x)_{i-1/2}=S_i\Delta x.
$$

FCCD contributes the face derivative:

$$
(\alpha p_x)_f = \alpha_f\,\mathcal{J}_f(p)_1.
$$

At an interface face, jump handling belongs at the face:

$$
[p]_f=\sigma\kappa,\qquad [\alpha p_x]_f=0.
$$

This prevents a nodal gradient reconstruction from smearing the mobility jump
before conservation is enforced.

## HFE upwind role

For a positive face advective velocity, the left/upwind face state is

$$
u_{i-1/2}^{\rm up}
=u_{i-1}+\frac{H_i}{2}u'_{i-1}
+\frac{H_i^2}{8}u''_{i-1}.
$$

For a negative face advective velocity, use the right node:

$$
u_{i-1/2}^{\rm up}
=u_i-\frac{H_i}{2}u'_i
+\frac{H_i^2}{8}u''_i.
$$

The resulting state is third-order as a directional Taylor reconstruction.
Flux dissipation is intentionally separate and should be supplied by the
chosen Riemann/Lax-Friedrichs layer.

## Implementation rule

Expose this as an additive primitive on `FCCDSolver`, not as a replacement for
`face_gradient` or `face_value`. Existing ch13 FCCD behavior remains unchanged
unless a caller explicitly requests the face jet or HFE upwind state.

