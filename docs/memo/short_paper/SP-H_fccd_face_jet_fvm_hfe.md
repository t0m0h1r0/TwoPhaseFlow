# SP-H: FCCD Face-Jet Extension for FVM Projection and HFE Advection

**Status**: PROPOSED + additive library primitive
**Date**: 2026-04-23
**Related**: [SP-A](SP-A_face_centered_upwind_ccd.md), [SP-D](SP-D_fccd_advection.md), [SP-F](SP-F_gpu_native_fvm_projection.md), [WIKI-T-046](../../wiki/theory/WIKI-T-046.md), [WIKI-T-055](../../wiki/theory/WIKI-T-055.md), [WIKI-T-063](../../wiki/theory/WIKI-T-063.md), [WIKI-T-068](../../wiki/theory/WIKI-T-068.md)

## Abstract

This note records the ResearchArchitect extension requested on 2026-04-23:
instead of using FCCD only as a face gradient operator, expose a **face jet**

$$
\mathcal{J}_{i-1/2}(u) = (u_{i-1/2}, u'_{i-1/2}, u''_{i-1/2})
$$

as a first-class primitive. The face jet is the executable bridge between
FVM conservation, variable-density pressure projection, and HFE-style upwind
flux evaluation. The present implementation is additive: it reuses the
existing CCD solve for nodal $(u'_i,u''_i)$ and builds the face jet by compact
Hermite formulas. A later block-system FCCD may promote $(u_f,u'_f,u''_f)$ to
independent unknowns, but the caller-facing contract should remain the same.

## 1. Motivation

The previous FCCD stack solved the H-01 locus mismatch by evaluating gradients
at faces. The new memo adds a stronger requirement: the face should also carry
the reconstructed variable and local curvature. That is the natural object for:

1. FVM pressure projection, where the conservative quantity is the face flux
   $(1/\rho)_f p'_f$.
2. Two-phase jump handling, where pressure continuity and flux continuity are
   both face conditions.
3. HFE advection, where the upwind state should be reconstructed at the same
   face used by the Riemann flux.

## 2. A3 Chain

**Equation.** For a scalar field $u$ on nodes $x_i$, define the face jet

$$
u_f = P_f u,\qquad u'_f = G_f u,\qquad u''_f = Q_f u,
$$

where $P_f$ is the compact face-value interpolation from SP-D, $G_f$ is the
FCCD face-gradient operator from SP-C/SP-D, and $Q_f$ is the compact face
average of the CCD second derivative:

$$
Q_{i-1/2}u = \frac{1}{2}(q_{i-1}+q_i),\qquad q = S_{\rm CCD}u.
$$

**Discretization.** The executable first stage is

$$
P_{i-1/2}u =
\frac{u_{i-1}+u_i}{2}
-\frac{H_i^2}{16}(q_{i-1}+q_i),
$$

$$
G_{i-1/2}u =
\frac{u_i-u_{i-1}}{H_i}
-\frac{H_i}{24}(q_i-q_{i-1}).
$$

The second derivative component is intentionally lower order at this stage:
it is a face-carried auxiliary quantity used for HFE reconstruction and
diagnostics, not yet a fourth-order independent FCCD unknown.

**Code.** `FCCDSolver.face_jet()` returns the triple, and
`FCCDSolver.upwind_face_value()` uses nodal $(u,u',u'')$ to form a directional
Taylor-HFE state:

$$
u^+_{i-1/2}
= u_{i-1}+\frac{H_i}{2}u'_{i-1}+\frac{H_i^2}{8}u''_{i-1},
$$

$$
u^-_{i-1/2}
= u_i-\frac{H_i}{2}u'_i+\frac{H_i^2}{8}u''_i.
$$

The sign of the face advective velocity selects the upwind branch.

## 3. Variable-Density PPE Interpretation

For the one-dimensional pressure equation

$$
\partial_x\left(\alpha\,\partial_x p\right)=S,\qquad \alpha=1/\rho,
$$

the FVM cell equation is

$$
(\alpha p')_{i+1/2}-(\alpha p')_{i-1/2}
= \int_{x_{i-1/2}}^{x_{i+1/2}} S\,dx.
$$

The face jet makes the pressure gradient term explicit:

$$
F^p_f = \alpha_f\,\mathcal{J}_f(p)_1.
$$

Across a material interface, the jump conditions are imposed on face-jet
components, not on post-averaged nodal gradients:

$$
[p]_f = \sigma\kappa,\qquad [\alpha p']_f = 0
$$

for the no phase-change incompressible case. This is the clean separation:
FVM owns conservation, FCCD owns face accuracy, and GFM/IIM owns the jump rows.

## 4. HFE Advection Interpretation

The new upwind face-value primitive is the HFE side of the same design. It
uses only the immediate upwind node and its compact derivatives, so its stencil
is compatible with the requested biased triple $(i,i-1/2,i-1)$:

1. Build nodal derivatives with CCD.
2. Reconstruct the directional face state by Taylor-HFE.
3. Send left/right states to a Riemann or Lax-Friedrichs flux.

The primitive deliberately stops before a limiter or Riemann solver. That
keeps the FCCD operator reusable by pressure, level-set, and momentum code
without coupling it to a specific nonlinear flux policy.

## 5. Design Consequences

- **Face jet is the public contract.** A later direct block solve for
  $(u_f,u'_f,u''_f)$ can replace the current closure without changing callers.
- **Do not replace FVM conservation.** The pressure equation should still be
  assembled as a face-flux divergence.
- **Do not use the face-value primitive on discontinuous raw fields without
  jump handling.** WIKI-L-030's $H^2q$ hazard still applies.
- **HFE upwinding is a reconstruction layer.** It prepares directional states;
  dissipation and entropy selection remain the Riemann solver's job.

## 6. Verification Targets

1. `face_jet.value` matches `face_value`; `face_jet.gradient` matches
   `face_gradient`.
2. `face_second_derivative` converges at least second order on smooth periodic
   fields.
3. `upwind_face_value` converges at third order for smooth fields, matching
   the Taylor truncation in the memo.

