# CHK-RA-CH14-PRESSURE-ADJOINT-REMEDY-DECISION-001

## Question

The pressure-adjoint RCA identified a pressure face representative defect:

```text
G_FCCD = G_var + Z,
G_var = -M_A^{-1} D_f^T W_p,
D_f Z = 0,  Z != 0.
```

Two theorem-grade remedies were left open:

1. expose a variational face corrector `G_var`, possibly while reusing the
   existing scalar PPE solve when the scalar operator is identical;
2. redesign the FCCD pressure face API so `pressure_fluxes` itself returns the
   variational pressure representative.

The task is to decide which route is physically and mathematically preferable.
Implementation convenience, damping, tuning, benchmark branches, curvature
caps, smoothing, or fallback schemes are not admissible decision criteria.

## Governing Principle

Pressure is a Lagrange multiplier for incompressibility.  Given the face
velocity space `V_f`, kinetic-energy metric `M_A`, pressure test metric `W_p`,
and divergence constraint `D_f`, the discrete pressure projection is the KKT
system for

```text
minimize_u  1/2 ||u - u*||_{M_A}^2
subject to  D_f u = 0.
```

The Euler-Lagrange equations give

```text
M_A (u - u*) + D_f^T W_p p = 0,
u = u* - M_A^{-1}D_f^T W_p p.
```

Therefore the pressure face reaction is not chosen by a standalone pressure
gradient formula.  It is uniquely determined by the adjoint of the exact
divergence constraint used by the velocity projection:

```text
G_var = -M_A^{-1}D_f^T W_p.
```

Any other face representative with the same divergence,

```text
G_alt = G_var + Z,   D_f Z = 0,
```

still satisfies the scalar PPE but no longer solves the kinetic-energy
minimization problem unless `Z=0` or a physically justified metric is provided
that makes `G_alt` the Riesz adjoint.  This is not a cosmetic property: for any
admissible face velocity `w in ker(D_f)`,

```text
<G_var p, w>_{M_A} = 0,
<G_alt p, w>_{M_A} = <Zp, w>_{M_A},
```

so a nonzero `Z` makes pressure do work on admissible incompressible motions.
That is incompatible with incompressible mechanics and with the capillary
Hodge energy theorem.

## Hypotheses

| id | Hypothesis | Verdict | Reason |
|---|---|---|---|
| H1 | The production object should be whichever pressure face map gives the smoothest or highest-order pointwise pressure gradient. | rejected | Pressure is a constraint force; its face representative is fixed by the Riesz adjoint of `D_f`, not by pointwise gradient aesthetics. |
| H2 | Reusing current `G_FCCD` is acceptable because `D_f G_FCCD` gives a symmetric scalar PPE. | rejected | Scalar symmetry only proves the pressure equation is self-adjoint; it does not prove that the returned face correction is energy-orthogonal to `ker(D_f)`. |
| H3 | A capillary-only variational corrector is enough. | rejected as production SSoT | It can prove the formula, but keeping two pressure face maps lets projection, capillary Hodge, diagnostics, and UCCD coupling disagree about what pressure force means. |
| H4 | A first-class variational pressure complex `(D_f,M_A,W_p,G_var,L_var)` is sufficient. | supported | It is exactly the KKT system of the discrete kinetic-energy projection and makes pressure work vanish on admissible velocities. |
| H5 | FCCD `pressure_fluxes` should be redesigned to return `G_var`. | supported | This makes the public pressure-face API match the theorem, so every caller shares the same pressure reaction. |
| H6 | The variational route is a low-order fallback. | rejected | `G_var` is the discrete adjoint of the chosen `D_f`; if fourth-order FCCD is required, the fourth-order object must be an SBP/variational pair `(D_f,G_var)`, not an independently chosen face gradient. |
| H7 | If existing scalar `D_f G_FCCD` equals `D_f G_var`, the old scalar solve may be reused. | conditionally supported | Reusing the scalar solve is valid only as an algebraic consequence of operator equality.  The face correction still must be `G_var`. |
| H8 | If existing scalar `D_f G_FCCD` differs from `D_f G_var`, using old PPE plus `G_var` is acceptable. | rejected | Then the corrected velocity would not satisfy the same divergence equation.  The PPE operator must also become `L_var = D_f G_var`. |
| H9 | A nonlocal metric can justify current `G_FCCD`. | not selected | Algebraic existence is not enough.  The metric must be SPD, kinetic-energy meaningful, coefficient-compatible, GPU-local enough, and tied to CCD/FCCD/UCCD work pairings. |
| H10 | Diagonal metric retuning is a safe compromise. | rejected | The RCA already showed the best diagonal metric leaves `~9.46e-02` residual at N32. |
| H11 | The best API is to leave `pressure_fluxes` as a pressure-gradient utility and add another variational utility for capillarity. | rejected | It preserves the ambiguity that caused the residual: the codebase would have two pressure reactions with the same scalar pressure. |
| H12 | The best API is to make `pressure_fluxes` mean the variational pressure reaction, and add a separate diagnostic name for raw FCCD face gradients if needed. | supported | This matches the physical role of pressure in projection and makes non-adjoint gradients visibly non-production diagnostics. |

## Decision Theorem

For a fixed production divergence `D_f`, kinetic metric `M_A`, and pressure
metric `W_p`, the pressure reaction compatible with incompressible mechanics is
unique:

```text
G_pressure = -M_A^{-1}D_f^T W_p.
```

Consequently:

1. A remedy that uses `G_var` only in one capillary-specific path is not a
   complete production theory.  It is a useful validation scaffold, but it
   leaves the global pressure contract ambiguous.
2. A remedy that redesigns `pressure_fluxes` so its production face output is
   `G_var` is the correct system-level decision.
3. Reusing the existing FCCD scalar PPE solve is allowed only after proving
   `D_f G_FCCD = D_f G_var` on the physical quotient and with the active
   nonuniform, density, and affine-jump coefficients.  If that equality fails,
   the scalar PPE operator must be changed to `L_var = D_f G_var` as well.

Thus the clean choice is:

```text
Adopt the variational pressure complex as the production theorem;
make FCCD pressure_fluxes expose that variational representative.
```

In short: the defining formula comes from option 1 (`G_var`), but the correct
production boundary is option 2 (FCCD pressure API redesign).  Treating option
1 as a capillary-only side path is not sufficient.

## Why This Is Not a Small Patch

Changing the face representative from `G_FCCD` to `G_var` is not a numerical
trick.  It changes the implementation back to the discrete d'Alembert principle:
the corrected velocity is the closest admissible velocity in kinetic energy.

The current code shows the split explicitly:

```text
divergence_from_faces(face_components) -> D_f face_components
pressure_fluxes(p, rho, pressure_gradient="fccd") -> coeff * face_gradient(p)
```

The first object defines the constraint.  The second currently supplies a
separately designed compact face gradient.  In the continuum these are adjoints
by integration by parts; in the discrete they are adjoints only if the SBP/Riesz
identity is proven.  The RCA showed it is not true for the present FCCD face
representative.

The physical repair is therefore to derive the face pressure reaction from the
first object, not to tune the second object until droplets look quiet.

## CCD/FCCD/UCCD Compatibility

The CCD-family compatibility criterion favors the API redesign route.

- `D_f` remains the face-native divergence used by FCCD projection.
- `G_var` is the transpose-adjoint of that same `D_f`, so the pressure
  correction stays in the same face complex consumed by UCCD and viscosity.
- The capillary Hodge projector, component saddle constraints, pressure
  projection, and diagnostics all see the same pressure range.
- A capillary-only variational corrector would force UCCD and diagnostics to
  reason about one pressure map while the projection code may still apply
  another.

If higher-order compact accuracy is needed beyond the current `D_f`, the right
path is not to preserve a non-adjoint face gradient.  It is to construct a new
compact mimetic pair `(D_f^{(4)}, G_f^{(4)})` with

```text
M_A G_f^{(4)} = -D_f^{(4)T} W_p,
L^{(4)} = D_f^{(4)}G_f^{(4)}.
```

That is an FCCD variational redesign, not a fallback.

## GPU Consequences

The selected route is also the only one with a clean GPU story.

- `G_var` is a local transpose application of the production divergence stencil
  plus diagonal metric factors.  It can be implemented with fused face kernels
  and axis-local reductions.
- The scalar solve uses `L_var = D_f G_var`; if existing `L_FCCD` is proven
  equal, no new solve operator is needed.
- A nonlocal metric proof would likely require dense or broad-stencil metric
  applications unless a new sparse SPD metric is derived.  That is not a
  production default without a separate theorem.
- Keeping separate pressure maps makes GPU optimization fragile because the
  optimized fast path and the diagnostic/capillary path can silently diverge.

## Required Gates Before Implementation

The decision implies the following fail-close gates.

```text
G0. Define the physical pressure/face quotient explicitly for periodic axes.
G1. Implement or expose G_var = -M_A^{-1}D_f^T W_p for the active divergence.
G2. Verify <G_var p,w>_M + <p,D_f w>_W = 0 to roundoff.
G3. Verify the production scalar PPE operator is L_var = D_f G_var.
    If current L_FCCD differs, replace the scalar operator too.
G4. Verify affine-jump and phase-separated coefficients use the same M_A
    factors in both G_var and the capillary/component saddle.
G5. Verify component saddle constraints:
        D_f h = 0,
        B^T M_A h = 0,
        <G_var p,h>_M_A = 0.
G6. Only after G0-G5, rerun static and oscillating droplets.
```

These gates prevent the tempting but invalid half-fix: solving one pressure
equation while applying the face correction of another.

## Verdict

The mathematically correct object is the variational pressure complex.  As an
implementation policy, the better of the two routes is the FCCD variational API
redesign: production `pressure_fluxes` should return the Riesz-adjoint pressure
reaction `G_var`, or be renamed/split so that non-adjoint compact pressure
gradients cannot be used as projection forces.

The standalone variational face corrector is still valuable as the first
operator gate and as the defining formula.  It should not remain a capillary
side path.  Once validated, it should become the production pressure-face
representative shared by PPE projection, capillary Hodge projection, component
saddles, diagnostics, and CCD/FCCD/UCCD coupling.
