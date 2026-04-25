# SP-U — Mathematical and Physical Foundation for a Well-Balanced Buoyancy Predictor

Date: 2026-04-25  
Status: ACTIVE  
Author: ResearchArchitect

## 1. Abstract

This note re-derives the ch13 rising-bubble failure and its admissible cure from
the viewpoint of structure-preserving CFD. The goal is not a local patch, but a
physically and mathematically justified redesign principle.

The main claim is:

> the correct cure is not “stabilise buoyancy by itself”, nor “move gravity to
> pressure”, nor “add a late witness”. The correct cure is a
> **well-balanced, pressure-robust, mass-momentum-consistent predictor
> assembly** in which the buoyancy-carrying predictor substate is constructed on
> the same discrete support as the later pressure/divergence closure, and where
> the gradient-compatible part of buoyancy is prevented from polluting the
> velocity update.

The note combines:

- variable-density projection theory,
- pressure-robustness / gradient-robustness theory,
- well-balanced source-term discretization,
- multiphase mass-momentum consistency,
- balanced-force interface coupling,
- and the in-repo PoC ladder.

The resulting redesign principle is a **stage-split, interface-band,
multidimensional buoyancy predictor**.

## 2. Governing Equations and One-Fluid Form

We consider the one-fluid incompressible two-phase system

\[
\rho(\psi)\left(\partial_t \mathbf{u} + \nabla\cdot(\mathbf{u}\otimes\mathbf{u})\right)
= -\nabla p
+ \nabla\cdot(2\mu(\psi)\mathbf{D}(\mathbf{u}))
+ \rho(\psi)\mathbf{g}
+ \mathbf{f}_\sigma,
\qquad
\nabla\cdot\mathbf{u}=0,
\]

with level-set / CLS indicator `ψ`, density `ρ(ψ)`, viscosity `μ(ψ)`, gravity
`g e_y`, and surface tension `f_σ`.

In this code base, the predictor uses a buoyancy form based on a reference
density `ρ_ref`, i.e. the explicit branch contains the body-force contribution

\[
\mathbf{b}(\psi)
= - \frac{\rho(\psi)-\rho_{\rm ref}}{\rho(\psi)}\, g\,\mathbf{e}_y.
\]

This is the numerically relevant object: it vanishes only in the reference
phase, is strongest across the interface band, and is the branch that the PoC
ladder has consistently identified as the dominant trigger.

## 2.1 Coordinate-Free Gravity Decomposition

The mathematically correct invariant is not the Cartesian label `x` or `y`,
but the conservative body-force field itself. For uniform gravity one may write

\[
\mathbf{g} = -\nabla \Phi_g,
\qquad
\Phi_g(\mathbf{x}) = -\mathbf{g}\cdot\mathbf{x}.
\]

Then

\[
\rho(\psi)\mathbf{g}
=
-\nabla\!\bigl(\rho(\psi)\Phi_g\bigr)
+ \Phi_g\,\nabla\rho(\psi).
\]

Therefore gravity contains two qualitatively different pieces:

1. a **gradient-compatible part** `-\nabla(\rho\Phi_g)`, which belongs with the
   pressure family, and
2. an **interface-local residual** `\Phi_g \nabla\rho`, which survives because
   variable density destroys pure hydrostatic reducibility.

Since `\rho=\rho(\psi)`, one also has

\[
\nabla\rho(\psi)=\rho'(\psi)\nabla\psi,
\]

so the residual is localized in the diffuse interface band and follows the
density-gradient / interface-normal geometry, not the gravity vector alone.

This yields the strict theoretical ranking:

- **Cartesian `x/y` splitting** is not fundamental;
- **gravity-aligned / transverse splitting** is a good reduced description for
  uniform gravity on orthogonal grids;
- the deepest invariant is the **gradient-compatible vs interface-local
  residual** decomposition.

For mapped or nonuniform coordinates, this split must be defined in **physical
space** and then transferred with the metric-aware discrete gradient/divergence
operators. That is the proper way to treat interface-tracking coordinates.

At the discrete level this means the ultimate invariant is not axis direction
but the decomposition modulo the discrete pressure-gradient range:

\[
\mathbf{f}_h = \mathbf{f}_h^{\nabla} + \mathbf{f}_h^{\mathrm{res}},
\qquad
\mathbf{f}_h^{\nabla}\in \mathrm{Range}(G_h).
\]

Any physically admissible redesign should therefore make the hydrostatic /
pressure-compatible part live in `Range(G_h)` and assemble only the residual on
the predictor support.

Implementation audit.  On the FCCD face-flux branch, the relevant discrete
space is face-native: `G_h` is the FCCD face pressure gradient and `D_h` is the
wall-control-volume divergence used by the FCCD PPE matrix-free operator.  The
projection operator must therefore use the same retained wall rows; the raw
FCCD boundary-zero `face_divergence` is a different operator and is not
PPE-identical.

Face-native residual audit.  Recasting the residual as
`face(f_b/rho) + (1/rho)_f G_f((rho-rho_ref)Phi_g)` passes the constant-density
nonuniform-grid cancellation test, so the coordinate/metric part of the
formula is correct.  It nevertheless worsens the ch13 debug run.  This points
to a missing pressure-family closure: once the predictor carries only the
residual, the pressure unknown must carry the hydrostatic jump
`(rho_l-rho_g)Phi_g` in addition to the capillary jump.

## 3. Why Naive Remedies Fail

The recent PoC ladder rejects several tempting ideas:

1. **Late corrector-only balance**  
   reduced-pressure and hydrostatic-corrector proxies do not beat the best
   predictor-side branch.

2. **Face-density-only buoyancy assembly**  
   moving `ρ` from nodes to faces changes the numbers, but not in the right way.

3. **Scalar stabilisation of the buoyancy branch**  
   changing only the time treatment of `B` misses the point, because the
   unstable object is not `B` alone but the *assembled* state `u_pred`.

4. **Single-stage isotropic repair**  
   `y-only` assembly is strong, `x-only` is weak, but `y-only + x-post` is much
   better than `y-only + x-assembly`. So the missing signal does not live in one
   uniform stage.

Therefore the right question is not “how do we damp buoyancy?” but

> how do we assemble a predictor state such that the velocity update remains
> well balanced against pressure-like forces and does not inject a spurious
> gradient component into the discrete divergence/pressure closure?

Equivalently:

> how do we keep the gradient-compatible part of gravity inside the
> pressure-robust closure while assembling the interface-local residual on the
> same discrete support as the momentum predictor?

## 4. Literature Survey and Its Implications

### 4.1 Variable-density projection

**Almgren et al. (1998)** and **Guermond–Salgado (2009)** show that
variable-density incompressible flow is a *same-space closure* problem:
the pressure Poisson equation, the velocity correction, and the density-weighted
operators must remain consistent at the discrete level.

Implication for us:

> the relevant object is not the continuous PDE alone but the
> `D_h β_h G_h` closure seen by the intermediate state.

### 4.2 Staggered projection and discrete pressure consistency

**Brown–Cortez–Minion (2001)** show on staggered grids that spatial placement
and boundary-consistent projection are essential; wrong-locus pressure balance
shows up as spurious divergence and velocity error.

Implication:

> if the buoyancy-carrying predictor substate is built on a different effective
> support than the pressure/divergence closure, the corrector cannot repair the
> mismatch for free.

### 4.3 Pressure-robustness / gradient-robustness

The pressure-robustness literature, especially **Linke–Merdon–Neilan**,
formalizes a key fact:

> gradient fields should not pollute the velocity error.

Two body forces are velocity-equivalent if they differ by a gradient. A scheme
that is not pressure-robust allows gradient-type forcing to contaminate the
velocity update.

Implication:

> in the buoyancy branch, the part of the force that is locally
> pressure-compatible must be prevented from entering the velocity update as an
> effective spurious acceleration.

This is the mathematically clean interpretation of the in-repo observation that
shallow hydrostatic/reduced-pressure patches are not enough: the issue is not
merely “subtract more pressure”, but the lack of a *discrete gradient-robust
predictor assembly*.

### 4.4 Multiphase mass-momentum consistency

**Rudman (1998)** and **Raessi–Pitsch (2012)** emphasize that at large density
ratios the key difficulty is not only interface transport, but *consistent mass
and momentum transport*. Small inconsistencies become catastrophic when density
jumps are large.

Implication:

> the buoyancy predictor cannot be designed independently of the level-set/CLS
> band that defines `ρ(ψ)`; the repair must live on the same interface support
> as the transported material state.

### 4.5 Balanced-force and well-balanced multiphase formulations

**François et al. (2006)** and **Kumar–Natarajan (2017)** show that pressure,
surface tension, and gravity must be discretized in the same family when
quiescent equilibrium is to be preserved. Kumar–Natarajan are especially
important here: they explicitly stress both

- consistent discrete mass/momentum transport, and
- similar discretization of gravity and surface-tension force terms.

They also note that gravity need not literally be written as the gradient of a
scalar everywhere, but must still be represented in a discretely balanced way.

Implication:

> for ch13, the buoyancy predictor must be well balanced **on the interface band
> and in the same stencil family as the later pressure-sensitive closure**, even
> if the final implementation is not a pure hydrostatic reconstruction.

### 4.6 Hyperbolic well-balanced analogies

The shallow-water literature (e.g. **Audusse et al.**, **Kurganov–Petrova**)
provides the mathematical archetype:

> equilibrium-preserving source treatment is local, nonlinear, and tied to the
> same reconstruction family as the flux.

Implication:

> a buoyancy repair that succeeds only on the full 3×3 interface band is not an
> ad hoc oddity; it is exactly the kind of *local equilibrium reconstruction*
> that well-balanced balance-law methods also require.

## 5. Mathematical Reformulation

Let `I₁` denote the full two-axis one-cell dilated interface band. We regard the
explicit buoyancy increment

\[
\delta \mathbf{u}_B = \Delta t\,\mathbf{b}(\psi)
\]

as the raw forcing substate.

We now postulate a local decomposition on `I₁`:

\[
\delta \mathbf{u}_B
=
\delta \mathbf{u}_{B,\nabla}
+
\delta \mathbf{u}_{B,\perp},
\]

where

- `δu_{B,∇}` is the locally gradient-compatible part (pressure-like),
- `δu_{B,⊥}` is the genuinely velocity-driving residual.

The redesign goal is not to annihilate `δu_B`, but to ensure that the
predictor/viscous/projection chain sees the right part at the right stage:

1. the dominant **vertical** part of the local mismatch is corrected during
   predictor assembly;
2. the residual **horizontal/cross-component** coupling is corrected in the
   state seen by `V(u_pred)`.

This matches the PoC verdicts:

- `y-only` assembly captures most of the beneficial signal;
- x-side assembly patches are weak;
- x-side post-stage repair is strong.

## 6. Derived Discrete Design Principles

The literature plus experiments imply five admissible principles.

### P1. Same-locus closure

The buoyancy-carrying substate must be repaired on the same effective support as
the pressure/divergence closure that later sees `u_pred`.

### P2. Interface-band locality

The repair must act on `I₁`, not globally and not only on the strict
`0<ψ<1` set. The successful branch depends on the full two-axis dilated band.

### P3. Pressure robustness in the predictor

The predictor should be insensitive to locally gradient-compatible buoyancy
content. In practice this means the buoyancy-carrying substate must be built in
a form that does not leak pressure-like gradients into the velocity update.

### P4. Multidimensional coupling

The required repair is not separable into edge-only, corner-only, x-only, or
simple linear weights. This is a genuinely multidimensional local equilibrium.

### P5. Stage separation

The dominant vertical imbalance is born in assembly; the residual horizontal
coupling becomes important at `V(u_pred)`. Therefore one single uniform repair
operator is not mathematically indicated by the evidence.

## 7. The Resulting Method Class

The admissible cure is a **stage-split, pressure-robust, well-balanced buoyancy
predictor**:

\[
\mathbf{u}_{B}^{\dagger}
=
T_y^{I_1}\!\left(\mathbf{u}^n + \Delta t\,\mathbf{b}(\psi^n)\right),
\]

\[
\mathbf{u}_{\mathrm{pred}}^{(0)}
=
\mathcal{A}\!\left(
\mathbf{u}^n,\,
\mathbf{C}^n,\,
\mathbf{V}(\mathbf{u}^n),\,
\mathbf{u}_{B}^{\dagger}
\right),
\]

\[
\mathbf{u}_{\mathrm{pred}}^{(1)}
=
S_x^{I_1}\!\left(\mathbf{u}_{\mathrm{pred}}^{(0)}\right),
\]

followed by

\[
\mathbf{u}_\star
=
\mathbf{u}^n
+
\Delta t\left(
\mathbf{C}^n
+
\tfrac12 \mathbf{V}(\mathbf{u}^n)
+
\tfrac12 \mathbf{V}\!\left(\mathbf{u}_{\mathrm{pred}}^{(1)}\right)
+
\mathbf{b}(\psi^n)
\right).
\]

The practical interpretation is:

- `T_y^{I₁}` carries the well-balanced vertical predictor repair,
- `S_x^{I₁}` restores the missing cross-component coupling before the viscous
  evaluator amplifies it.

## 8. What This Excludes

The present theory excludes the following as final cures:

- buoyancy-only implicitness without assembly redesign,
- reduced-pressure or hydrostatic split used as shallow patch,
- face-density-only buoyancy re-evaluation,
- late witness additions,
- scalar relaxation or CFL tuning,
- strict-interface-only reconstruction.

These may alter the numbers but do not satisfy the combined requirements of
pressure-robustness, well-balancedness, and same-locus predictor closure.

## 9. Literature Used

- Almgren, Bell, Colella, Howell, Welcome (1998), *A conservative adaptive projection method for the variable density incompressible Navier–Stokes equations*, JCP.  
  https://www.sciencedirect.com/science/article/abs/pii/S0021999198958909
- Brown, Cortez, Minion (2001), *Projection method III: Spatial discretization on the staggered grid*.  
  https://web.math.princeton.edu/~weinan/pdf%20files/projection%20method%20iii.pdf
- Guermond, Salgado (2009), *A splitting method for incompressible flows with variable density based on a pressure Poisson equation*.  
  https://people.tamu.edu/~guermond/PUBLICATIONS/guermond_salgado_jcp_2009.pdf
- Dodd, Ferrante (2014), *A fast pressure-correction method for incompressible two-fluid flows*.  
  https://www.doddm.com/publications/2014-jcp-md-af.pdf
- Raessi, Pitsch (2012), *Consistent mass and momentum transport for simulating incompressible interfacial flows with large density ratios using the level set method*.  
  https://citeseerx.ist.psu.edu/document?doi=706532ceb28452ce02d44da8026db1e0d1f8397b&repid=rep1&type=pdf
- Rudman (1998), *A volume-tracking method for incompressible multifluid flows with large density variations*.  
  https://research.monash.edu/en/publications/a-volume-tracking-method-for-incompressible-multifluid-flows-and-/
- François et al. (2006), *A balanced-force algorithm for continuous and sharp interfacial surface tension models within a volume tracking framework*, JCP.  
  https://doi.org/10.1016/j.jcp.2005.08.004
- Patel, Natarajan (2017), *A novel consistent and well-balanced algorithm for simulations of multiphase flows on unstructured grids*.  
  https://doi.org/10.1016/j.jcp.2017.08.047
- Linke, Merdon, Neilan (2019), *Pressure-robustness in quasi-optimal a priori estimates for the Stokes problem*.  
  https://arxiv.org/abs/1906.03009
- Akbas, Gallouët, Gassmann, Linke, Merdon (2020), *A gradient-robust well-balanced scheme for the compressible isothermal Stokes problem*.  
  https://doi.org/10.1016/j.cma.2020.113181

## 10. Verdict

The mathematically and physically justified solution method is now:

> build a stage-split buoyancy predictor that is simultaneously
> interface-band-local, pressure-robust, mass-momentum-consistent, and
> well-balanced, with vertical repair in assembly and horizontal coupling repair
> before `V(u_pred)`.

This is the narrowest redesign class consistent with both the literature and
the full in-repo hypothesis ladder.

An important negative result must be recorded as well. A direct predictor-side
implementation of the decomposition

\[
\rho \mathbf{g} = -\nabla(\rho\Phi_g) + \Phi_g \nabla\rho
\]

was tested by removing the discrete gradient-compatible part from the predictor
velocity update and retaining only the interface-local residual in the repaired
buoyancy substate. In the current solver this did **not** outperform the best
existing branches. Hence the decomposition is theoretically correct, but a
naive direct substitution into the predictor assembly is insufficient. The
pressure-compatible part must be co-designed with the later pressure closure,
not merely discarded from the predictor.
