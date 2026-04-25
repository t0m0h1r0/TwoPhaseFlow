# SP-Q — Buoyancy-Driven Predictor Assembly in Variable-Density CN Projection

Date: 2026-04-25  
Status: ACTIVE  
Author: ResearchArchitect

## 1. Abstract

This note constructs a strict theory for the current ch13 rising-bubble
instability from the predictor side. The main claim is:

> the dominant defect is not a generic projection failure, nor a centered-vs-upwind
> issue, nor a late corrector inconsistency by itself; it is a
> **buoyancy-driven mismatch inside the raw intermediate velocity state**
> `u_pred`, localised to the interface band, and amplified when the CN viscous
> predictor evaluates `V(u_pred)`.

The note combines continuous variable-density NS theory, staggered/face
projection literature, and the in-repo PoC ladder. The resulting diagnosis is:

1. the unstable object is the **assembled intermediate predictor state**
2. the leading trigger is the **buoyancy-carrying explicit branch**
3. the sensitive region is the **interface band**
4. the failure becomes visible through **pressure/divergence-sensitive closure
   diagnostics** (`ppe_rhs`, `bf_residual`, `div_u`)

This explains why local witness additions, reduced-pressure proxies, and
hydrostatic or face-density-only patches did not solve the problem.

## 2. Problem Statement

The short-time rising-bubble failure on the static `α=2` FCCD stack does not
first appear as mass loss. The stronger signals are:

- `ppe_rhs_max`
- `bf_residual_max`
- `div_u_max`

while `volume_conservation` remains comparatively small.

Therefore the failing contract is not the CLS transport itself, but the
**predictor → PPE → corrector closure** in the variable-density NS stack.

The key engineering question is:

> which sub-assembly of the intermediate state `u_pred` injects the defect that
> later appears as projection/balanced-force blowup?

## 3. Continuous Formulation

We start from the one-fluid incompressible model

\[
\rho(\psi)\left(\partial_t \mathbf{u} + \nabla\cdot(\mathbf{u}\otimes\mathbf{u})\right)
= -\nabla p + \nabla\cdot(2\mu(\psi)\mathbf{D}(\mathbf{u}))
+ \rho(\psi)\mathbf{g} + \mathbf{f}_\sigma,
\qquad
\nabla\cdot\mathbf{u}=0.
\]

Here `ρ(ψ)` and `μ(ψ)` jump across the interface band, and gravity enters as a
body force aligned with the vertical axis.

At the continuous level, one may rewrite pressure as

\[
p = \pi + p_h,
\qquad
\nabla p_h \approx \rho \mathbf{g},
\]

with `π` a reduced pressure and `p_h` a hydrostatic component. Existing
literature supports such a split as a conditioning aid, but only when the
discrete predictor/corrector closure remains same-space and well balanced.

This matters because the continuous identity

\[
\rho \mathbf{g} - \nabla p_h \approx 0
\]

does **not** automatically survive discretisation in the interface band unless
all participating operators live on compatible stencils and state locations.

## 4. Discrete Predictor Assembly in the Current Stack

In the current implementation, the relevant CN predictor logic is explicitly
documented in `src/twophase/time_integration/cn_advance/picard_cn.py`.

The legacy Picard-CN path is algebraically a Heun / explicit trapezoid update:

\[
\mathbf{u}_{\text{pred}}
= \mathbf{u}^n
+ \Delta t \left(\mathbf{E}^n + \mathbf{V}(\mathbf{u}^n)\right),
\]

\[
\mathbf{u}_\star
= \mathbf{u}^n
+ \Delta t \left(\mathbf{E}^n + \tfrac12 \mathbf{V}(\mathbf{u}^n)
+ \tfrac12 \mathbf{V}(\mathbf{u}_{\text{pred}})\right),
\]

where, in code form,

\[
\mathbf{E}^n = \frac{\texttt{explicit\_rhs}}{\rho}
= \frac{\texttt{convective\_rhs} + \texttt{buoyancy\_rhs} + \cdots}{\rho}.
\]

Traceability:

- **Equation**: `u_pred = u^n + dt(explicit_rhs/rho + V(u^n))`
- **Discretisation**: explicit buoyancy branch + explicit viscous predictor
- **Code**: `src/twophase/time_integration/cn_advance/picard_cn.py`

The important structural fact is:

> `u_pred` is not a primitive field; it is an **assembled state** built from
> multiple contributions before `V(u_pred)` is evaluated.

So any interface-local mismatch that is weak in the separate branches may
become dynamically important only after the full assembly.

## 5. Interface-Band Closure Requirement

Let `I_ε` denote the interface band:

\[
I_\varepsilon = \{x : 0 < \psi(x) < 1\}
\quad \text{or equivalently} \quad
|\phi(x)| \lesssim \varepsilon.
\]

For stable variable-density predictor closure, three consistency conditions are
needed.

### C1. Same-space closure

The state seen by the pressure corrector, divergence witness, and density
weighting should close on the same discrete locus.

### C2. Interface-local state consistency

Inside `I_ε`, the state used in `V(u_pred)` must remain compatible with the
stencil family used later by the pressure/divergence closure.

### C3. Buoyancy/pressure well-balanced consistency

Any discrete cancellation between gravity and pressure-like compensation must be
constructed in the same assembly family as the intermediate predictor state
itself.

The PoC ladder shows that the current stack violates some combination of C2 and
C3, but not in a way that is fixed by late corrector-only compensation.

## 6. Failure Mechanism

Write the raw intermediate state as

\[
\mathbf{u}_{\text{pred}}^{\text{raw}}
= \mathbf{u}_{\text{pred}}^\star + \delta \mathbf{u}_B,
\]

where:

- `u_pred^*` is the hypothetical interface-consistent state
- `δu_B` is the buoyancy-driven mismatch generated during assembly
- `supp(δu_B) \subset I_ε`

Then the viscous predictor sees

\[
\mathbf{V}(\mathbf{u}_{\text{pred}}^{\text{raw}})
= \mathbf{V}(\mathbf{u}_{\text{pred}}^\star)
+ \mathcal{L}_{\text{diag}}[\delta \mathbf{u}_B]
+ \mathcal{N}(\delta \mathbf{u}_B),
\]

where `L_diag` denotes the pressure/divergence-sensitive part of the linearised
viscous response and `N` collects higher-order terms.

The in-repo hypothesis campaign shows that:

- pure trace-only correction is insufficient
- pure nontrace-only correction is insufficient
- pure shear-only correction is insufficient
- axis-only correction is insufficient
- full diagonal-family correction is helpful but secondary
- the strongest signal comes from **repairing the interface-local assembled
  state itself**

This strongly suggests that the dangerous defect is not a late witness quantity
like `∇·u_pred` alone. Instead, it is embedded in the assembled **state/value**
that enters `V(u_pred)`.

## 7. Literature-Supported Reading

The literature surveyed in `SP-P` and `WIKI-T-071` supports the same
interpretation from three angles.

### 7.1 Variable-density projection consistency

Almgren et al., Brown–Cortez–Minion, and Guermond–Salgado all imply that
variable-density projection is a same-space closure problem, not just a PPE
solver problem.

### 7.2 Large density-ratio consistency

Rudman, Raessi–Pitsch, and Dodd–Ferrante emphasize that large density ratio
penalises **assembly inconsistency** more strongly than raw iteration count.

### 7.3 Well-balanced forcing

François, Popinet, and Kumar–Natarajan show that gravity, capillarity, and
pressure must be paired on the same geometric/discrete locus if equilibrium is
to remain well balanced.

Combined with the local experiments, this yields a stricter statement:

> the missing fix is not “more hydrostatic pressure” in the abstract; it is a
> predictor assembly in which the buoyancy-carrying intermediate state is
> generated on the same interface-local stencil/state family as the subsequent
> closure-sensitive operators.

## 8. Hypothesis Campaign and Verdicts

The recent hypothesis campaign can be summarised as follows.

| Hypothesis | Best probe | Verdict | Reading |
|---|---|---|---|
| centered FCCD/UCCD is the main culprit | flux / scheme probes | weak | not the main lever |
| TVD-RK3 is the main culprit | Picard vs Richardson comparison | weak | NS closure dominates |
| reduced-pressure corrector should fix it | reduced-pressure PoCs | reject | failure mode worsens |
| hydrostatic predictor split should fix it | hydrostatic PoCs | reject | weaker than buoyancy-local repair |
| face-density buoyancy assembly should fix it | face-density buoyancy PoC | reject | coefficient location alone is insufficient |
| previous-pressure co-balance should fix it | buoyancy-pressure predictor PoCs | reject | shallow co-balance fails |
| raw assembled `u_pred` is the unstable object | interface-local state repair | strongly supported | best diagnostic signal |
| leading trigger lies in buoyancy branch | buoyancy-local PoCs | strongly supported | strongest branch so far |
| secondary coupling with viscous predictor exists | buoyancy-viscous PoCs | supported | secondary but real |

The decisive pattern is:

> upstream partial repairs are weaker than repairing the fully assembled
> interface-local `u_pred`.

This is exactly what one expects if the defect is produced by the **assembly
composition**, not by any single upstream branch in isolation.

## 9. Present Best Diagnosis

The current best diagnosis is:

> the dominant instability is a **buoyancy-driven, interface-local mismatch in
> the fully assembled CN intermediate state `u_pred`**, with secondary coupling
> to the viscous predictor, and only indirect manifestation in the later
> pressure/divergence diagnostics.

This explains all major observations:

1. `g=0` strongly stabilises short probes
2. `sigma=0` does not remove the failure
3. reduced-pressure and hydrostatic late fixes do not cure it
4. the best signal appears when the assembled interface-local state is repaired
5. adding derived witnesses on top of that tends to over-correct

## 10. Design Consequence

The next structural redesign should not start from:

- more witness terms
- more relaxation
- more corrector-side hydrostatic compensation
- more shallow pressure-subtraction patches

It should start from:

> a **buoyancy-aware predictor assembly** that constructs the buoyancy-carrying
> intermediate state itself on an interface-local, closure-compatible stencil
> family before `V(u_pred)` is evaluated.

That is the smallest redesign direction that remains consistent with both the
literature and the experimental evidence.

## 11. Relation to Current Docs

- Survey background: `docs/memo/short_paper/SP-P_face_canonical_projection_survey.md`
- Literature-backed hypothesis matrix:
  `docs/memo/ch13_10_literature_backed_hypothesis_matrix.md`
- Experiment verdict log: `docs/wiki/experiment/WIKI-E-031.md`
- Theory wiki condensation: `docs/wiki/theory/WIKI-T-072.md`
