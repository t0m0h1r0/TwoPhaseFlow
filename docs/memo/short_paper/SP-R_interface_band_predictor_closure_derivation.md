# SP-R — Interface-Band Predictor Closure: NS × LS × CFD Derivation for Buoyancy-Driven Assembly

Date: 2026-04-25  
Status: ACTIVE  
Author: ResearchArchitect

## 1. Abstract

This note formalises the ch13 rising-bubble failure and its most promising cure
as a single mathematical object.

The central claim is:

> the numerically dangerous object is not buoyancy alone, nor pressure alone,
> nor projection alone, but the **raw intermediate predictor state**
> `u_pred` assembled before the CN viscous evaluation `V(u_pred)`; the leading
> defect is a **buoyancy-driven, interface-band-localised mismatch** in that
> state.

The note connects:

1. the one-fluid incompressible Navier–Stokes equations,
2. conservative level-set / diffuse-interface representation,
3. the CFD predictor–projection algorithm actually used in this repo,
4. the empirical fact that the strongest stabilising signal appears only when a
   **two-axis dilated interface-band repair** is applied to the buoyancy-carrying
   predictor substate.

The resulting design principle is not “add another witness term” but:

> assemble and regularise the buoyancy-carrying predictor substate on the same
> interface-local family that the closure-sensitive viscous/projection path
> expects.

## 2. Continuous Governing Problem

We work with the one-fluid incompressible two-phase model

\[
\rho(\psi)\left(\partial_t \mathbf{u} + \nabla\cdot(\mathbf{u}\otimes\mathbf{u})\right)
= -\nabla p + \nabla\cdot\bigl(2\mu(\psi)\mathbf{D}(\mathbf{u})\bigr)
+ \rho(\psi)\mathbf{g} + \mathbf{f}_\sigma,
\qquad
\nabla\cdot\mathbf{u}=0,
\]

with

\[
\mathbf{D}(\mathbf{u}) = \tfrac12\left(\nabla \mathbf{u} + (\nabla \mathbf{u})^T\right).
\]

The material properties are supplied by a conservative level-set variable
`psi in [0,1]`:

\[
\rho(\psi)=\rho_l + (\rho_g-\rho_l)\psi,
\qquad
\mu(\psi)=\mu_l + (\mu_g-\mu_l)\psi.
\]

The surface-tension force is localised to the interface band:

\[
\mathbf{f}_\sigma = \sigma\kappa\nabla \psi
\quad \text{(CSF / pressure-jump equivalent family in one-fluid form).}
\]

### 2.1 Physical equilibrium and the difficulty of gravity

At the continuous level, hydrostatic equilibrium satisfies

\[
-\nabla p_h + \rho\mathbf{g} \approx 0.
\]

Hence one may write

\[
p = \pi + p_h,
\]

with `pi` a reduced pressure. But this cancellation is only useful if the
**discrete** pressure gradient, density weighting, and buoyancy assembly are
constructed on compatible stencils and at compatible state locations.

This is exactly where the current ch13 failure lives.

## 3. Level-Set / CLS Connection

The interface is represented by a conservative level-set field `psi`, advected
by

\[
\partial_t \psi + \nabla\cdot(\psi \mathbf{u}) = 0,
\]

with reinitialisation used to maintain a regularised interface profile.

Define the strict diffuse-interface support

\[
I_0 = \{x: 0 < \psi(x) < 1\}.
\]

The current successful numerical clue is *not* tied to `I_0` itself, but to a
**dilated interface band** `I_1` constructed by adding a one-cell neighbourhood
in both coordinate directions.

Let `\mathcal{N}_x` and `\mathcal{N}_y` denote one-cell neighbour expansions in
x and y. Then the active repair band is

\[
I_1 = I_0 \cup \mathcal{N}_x(I_0) \cup \mathcal{N}_y(I_0).
\]

The recent probe ladder establishes:

- strict `I_0` alone is insufficient,
- x-only dilation is insufficient,
- y-only dilation is insufficient,
- the useful signal appears only with the **full two-axis band** `I_1`.

So the numerical defect is not point-interface local; it is **narrow-band
local**.

## 4. CFD Time-Split Formulation

Let

- `C(u^n)` denote the explicit convection branch,
- `B(psi^n)` denote the explicit buoyancy branch,
- `V(u)` denote the viscous operator,
- `P_\beta` denote the variable-density projection with `\beta = 1/\rho`.

Then the current CN predictor in the code has the algebraic form

\[
\mathbf{u}_{\text{pred}}^{\text{raw}}
= \mathbf{u}^n + \Delta t\left(\mathbf{E}^n + \mathbf{V}(\mathbf{u}^n)\right),
\qquad
\mathbf{E}^n = \frac{\mathbf{R}_{\mathrm{exp}}^n}{\rho}
= C(\mathbf{u}^n) + B(\psi^n) + \cdots.
\]

Then the CN / trapezoidal closure uses

\[
\mathbf{u}_\star
= \mathbf{u}^n + \Delta t\left(
\mathbf{E}^n + \tfrac12\mathbf{V}(\mathbf{u}^n) + \tfrac12\mathbf{V}(\mathbf{u}_{\text{pred}}^{\text{raw}})
\right),
\]

followed by projection

\[
\mathbf{u}^{n+1} = P_\beta(\mathbf{u}_\star).
\]

The key point is structural:

> `u_pred^raw` is the first fully assembled state that combines explicit
> buoyancy, explicit convection, and viscous history **before** the closure
> operator `V(\cdot)` is re-evaluated.

That is why defects that are weak in isolated branches can become dominant only
at this assembled state.

## 5. Formal Defect Decomposition

Let the ideal closure-compatible intermediate state be `u_pred^*`. Then define

\[
\mathbf{u}_{\text{pred}}^{\text{raw}}
= \mathbf{u}_{\text{pred}}^\star + \delta \mathbf{u}_{I,B},
\qquad
\mathrm{supp}(\delta \mathbf{u}_{I,B}) \subset I_1.
\]

Here:

- `delta u_{I,B}` is the buoyancy-driven interface-band mismatch,
- the subscript `I,B` emphasises that it is both interface-band-local and
  buoyancy-carrying.

Evaluating the viscous closure on the raw state gives

\[
\mathbf{V}(\mathbf{u}_{\text{pred}}^{\text{raw}})
= \mathbf{V}(\mathbf{u}_{\text{pred}}^\star)
+ \mathcal{L}_V[\delta \mathbf{u}_{I,B}]
+ \mathcal{N}_V(\delta \mathbf{u}_{I,B}),
\]

where `\mathcal{L}_V` is the Fréchet linearisation of the viscous operator and
`\mathcal{N}_V` collects higher-order terms.

The experiments show that the visible instability channel is carried mostly by
pressure/divergence-sensitive diagnostics:

\[
\texttt{ppe\_rhs},\qquad \texttt{bf\_residual},\qquad \texttt{div\_u}.
\]

Therefore the dominant part of `\mathcal{L}_V[\delta u_{I,B}]` is not arbitrary;
it couples strongly into the closure-sensitive subspace that later interacts
with projection.

## 6. Why Mass Conservation Does Not Fail First

The CLS transport equation remains conservative at leading order, so the bubble
volume error is not the first signal. In symbols,

\[
\frac{d}{dt}\int_\Omega \psi\,dV = -\int_{\partial\Omega} \psi\,\mathbf{u}\cdot\mathbf{n}\,dS,
\]

which is zero under the usual wall/periodic assumptions.

Hence the early failure is not primarily a level-set mass-loss event. Instead,
it is the **NS closure** that breaks first:

\[
\mathbf{u}_{\text{pred}}^{\text{raw}} \xrightarrow{V(\cdot)} \mathbf{u}_\star
\xrightarrow{P_\beta} \mathbf{u}^{n+1}
\]

with the instability already seeded before projection is applied.

## 7. Operator-Theoretic Statement of the Repair

Let `\mathcal{T}_{I_1}` denote the interface-band repair operator acting on a
vector state. The empirically useful branch can be written as

\[
\widetilde{\mathbf{u}}_B
= \mathcal{T}_{I_1}\left(\mathbf{u}^n + \Delta t\,B(\psi^n)\right),
\]

and the repaired predictor assembly becomes

\[
\mathbf{u}_{\text{pred}}^{\text{repair}}
= \widetilde{\mathbf{u}}_B
+ \Delta t\left(C(\mathbf{u}^n) + \mathbf{V}(\mathbf{u}^n) + \cdots\right).
\]

The observed hierarchy is:

1. `\mathcal{T}_{I_1}` on the buoyancy-carrying substate helps,
2. applying only face-mapping without `I_1` does not help,
3. using only strict `I_0` does not help,
4. x-only or y-only dilation does not help,
5. late witness corrections do not help.

This implies that the useful object is not just a witness like
`\nabla\cdot u_pred`, nor just a mapped state value, but a **composed,
interface-band-localised buoyancy predictor state**.

## 8. Commutator Interpretation

The above can be expressed as a non-commuting assembly problem. Let

\[
\mathcal{A}_B(\mathbf{u}^n) = \mathbf{u}^n + \Delta t\,B(\psi^n),
\]

and let `\mathcal{T}_{I_1}` be the interface-band repair operator. Then the
useful signal comes from

\[
\mathcal{T}_{I_1}\circ \mathcal{A}_B,
\]

not from the unrepaired branch `\mathcal{A}_B` nor from repairing after the
full state has been decomposed into unrelated pieces. The failed branches imply
that the commutator

\[
[\mathcal{T}_{I_1}, \mathcal{A}_B] \neq 0
\]

is numerically significant.

Likewise, if `\Pi_x` and `\Pi_y` denote x-only and y-only band dilations, the
probe ladder shows

\[
\mathcal{T}_{\Pi_x(I_0)} \not\approx \mathcal{T}_{I_1},
\qquad
\mathcal{T}_{\Pi_y(I_0)} \not\approx \mathcal{T}_{I_1}.
\]

Only the full two-axis band captures the required local geometry.

## 9. Connection to Variable-Density Projection Theory

This result is consistent with classical staggered/variable-density projection
literature:

- the important object is not merely the PPE, but the **same-space closure** of
  predictor, pressure gradient, and density weighting,
- large density ratio makes assembly inconsistency more dangerous,
- well-balanced forcing requires gravity/pressure/viscous response to be
  assembled on compatible geometric families.

Our current finding sharpens that general statement for this repo:

> the closure defect is created at predictor assembly time, in the buoyancy
> branch, on a two-axis dilated interface band.

## 10. Derived Engineering Principle

The mathematically consistent redesign target is therefore:

> construct the buoyancy-carrying predictor substate directly on the
> closure-compatible interface-band family before evaluating `V(u_pred)`.

This is stronger than “repair the full state later” and more informative than
“add another witness term.”

## 11. Practical Corollaries

### Corollary 1 — Why reduced-pressure fixes underperform

Corrector-side reduced-pressure or hydrostatic patches modify the state too
late. They do not remove `delta u_{I,B}` before it is amplified through
`V(u_pred)`.

### Corollary 2 — Why face-density-only assembly underperforms

Changing the density evaluation locus alone does not change the geometric
support of the predictor defect. The support `I_1` still matters.

### Corollary 3 — Why strict-interface repair underperforms

The harmful mismatch extends beyond `I_0` into neighbouring cells. The repair
must therefore act on the full dilated band `I_1`, not just the strict
interface set.

## 12. Present Best Formulation

The current best mathematical reading of the problem is:

\[
\boxed{
\text{ch13 blowup }\approx
\text{buoyancy-driven two-axis interface-band mismatch in } u_{\mathrm{pred}}^{\mathrm{raw}}
\text{, amplified by } V(u_{\mathrm{pred}})
}
\]

and the current best cure class is:

\[
\boxed{
\text{interface-band-localised buoyancy-aware predictor assembly}
}
\]

## 13. Cross-links

- Existing predictor diagnosis: `docs/memo/short_paper/SP-Q_buoyancy_driven_predictor_assembly.md`
- Literature survey and PoC ladder: `docs/memo/short_paper/SP-P_face_canonical_projection_survey.md`
- Theory wiki predecessor: `docs/wiki/theory/WIKI-T-072.md`
- Experiment verdict log: `docs/wiki/experiment/WIKI-E-031.md`
- Redesign spec: `docs/memo/ch13_11_buoyancy_predictor_redesign_spec.md`
