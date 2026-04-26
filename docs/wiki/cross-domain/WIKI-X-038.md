---
ref_id: WIKI-X-038
title: "Theory-First CFL and Time-Integration Policy: SSPRK3 Scope, AB2 Risk, and IMEX-BDF2 Production Path"
domain: cross-domain
status: ACTIVE
superseded_by: null
sources:
  - path: docs/memo/cfl_theory_clarification.md
    description: "Theory-first CFL clarification while paper text is under revision"
  - path: docs/memo/short_paper/SP-Y_cfl_time_integration_policy.md
    description: "Short paper deriving the CFL budget and time-integrator hierarchy"
  - description: "Shu and Osher (1988), JCP 77, 439--471"
  - description: "Gottlieb, Shu and Tadmor (2001), SIAM Review 43, 89--112"
  - description: "Denner and van Wachem (2015), JCP 285, 24--40"
  - description: "Denner and van Wachem (2022), JCP 449, 110788"
  - description: "Lele (1992), JCP 103, 16--42"
  - description: "Visbal and Gaitonde (2002), JCP 181, 155--185"
depends_on:
  - "[[WIKI-X-007]]"
  - "[[WIKI-X-023]]"
  - "[[WIKI-X-024]]"
  - "[[WIKI-X-025]]"
  - "[[WIKI-X-026]]"
  - "[[WIKI-X-030]]"
  - "[[WIKI-X-031]]"
  - "[[WIKI-X-032]]"
consumers:
  - domain: code
    usage: "Reference for `dt_max` and future timestep diagnostics"
  - domain: paper
    usage: "Replacement source for suspect CFL/time-integration prose during revision"
  - domain: experiment
    usage: "ch13 stability audit checklist before calling alpha>1 runs production-stable"
  - domain: theory
    usage: "Integrator-selection gate for FCCD/UCCD6/CLS operators"
compiled_by: ResearchArchitect
verified_by: null
compiled_at: 2026-04-25
---

# Theory-First CFL and Time-Integration Policy

## Thesis

TVD-RK3, scalar CFL, and capillary-wave time scales are separate stability
objects.  They must not be collapsed into a single statement such as
"CFL=0.10 with TVD-RK3 is stable."  The safe policy is:

```text
CLS/psi transport:
  SSPRK3 may be used as an explicit RK integrator, but TVD is not guaranteed
  unless the spatial operator is forward-Euler contractive.

NS production:
  prefer IMEX-BDF2 projection with explicit extrapolated UCCD6/FCCD convection,
  true implicit viscosity, semi-implicit surface tension, and BF-consistent PPE.

Non-uniform compact grids:
  scalar h_min CFL is necessary but insufficient; require operator-level
  spectrum/pseudospectrum or an energy estimate.
```

## 1. Non-negotiable CFL formulas

For two-dimensional explicit advection,

```text
Lambda_adv = max|u| / h_x,min + max|v| / h_y,min
dt_adv     = C_adv / Lambda_adv.
```

The common shortcut

```text
C_adv h_min / max(max|u|, max|v|)
```

is not the multidimensional CFL bound and can be too large by a factor of two
for diagonal flow.

For explicit diffusion,

```text
dt_nu = 1 / (2 nu_max (h_x,min^-2 + h_y,min^-2)).
```

For capillary waves,

```text
dt_cap = C_wave sqrt((rho_l + rho_g) h_min^3 / (2 pi sigma)),
C_wave ≈ 0.1--0.3.
```

Runtime rule: unless a separate documented override is added, `run.time.cfl`
is `C_wave` for `dt_cap`.  The capillary coefficient must not be hard-coded.
Otherwise a YAML that states `cfl: 0.10` can still run the surface-tension
block at `C_wave = 0.25`, which is a 2.5x larger capillary-wave timestep and
breaks the user's stated CFL contract.

The production budget is therefore

```text
dt <= min(dt_adv, dt_nu_if_not_truly_implicit, dt_cap, dt_operator).
```

`dt_operator` is the missing strict bound for compact non-uniform grids, wall
closures, AB2 momentum convection, FCCD face fluxes, and UCCD6 hyperviscosity.

## 2. SSPRK3 scope

SSPRK3 preserves strong stability only if the forward-Euler spatial step already
has the desired contractivity.  CCD/FCCD/DCCD operators are high-order compact
operators and are not automatically monotone or TVD.  Thus:

- allowed: "SSPRK3 is a third-order explicit RK method for scalar CLS transport";
- forbidden: "TVD-RK3 proves the full two-phase NS solver is TVD/stable."

The absolute-stability constants are still useful for linear audits:

```text
R(z) = 1 + z + z^2/2 + z^3/6
|Im z| <= sqrt(3)
-2.5127 <= Re z <= 0
```

## 3. AB2 risk

AB2 has characteristic equation

```text
r^2 - (1 + 3z/2) r + z/2 = 0.
```

Its stability region is tangent to the imaginary axis at the origin.  Therefore
pure central/skew compact advection is not made stable by AB2 at any positive
Courant number.  AB2 momentum convection needs enough negative-real damping or
an operator-specific proof.  This is the central new reason to avoid justifying
the NS production step by "TVD-RK3" language.

## 4. Recommended integrator hierarchy

| Subsystem | Recommended time integrator | Reason |
|---|---|---|
| Scalar CLS/psi transport | SSPRK3 or RK4 | Cheap explicit transport; TVD claim conditional |
| Production NS | IMEX-BDF2 projection | A-stable implicit blocks, cheap explicit convection |
| Stiffer surface-tension/viscous regimes | IMEX-SDIRK2 / ARK2 | Stronger implicit coupling with moderate cost |
| Extreme density ratio / low Weber / thin film | fully coupled Radau IIA or equivalent | Splitting error and capillary stiffness dominate |

## 5. IMEX-BDF2 production target

The near-term production equation should have the form

```text
(3 u^{n+1} - 4 u^n + u^{n-1}) / (2 dt)
  + EXT2 A(u)
  = implicit V(u^{n+1})
    - grad p^{n+1}
    + semi-implicit surface tension
    + body force,

div u^{n+1} = 0,

EXT2 A(u) = 2 A(u^n) - A(u^{n-1}).
```

The PPE and corrector must share the same face coefficient, gradient,
divergence, wall metric, and surface-force representation.  Otherwise the time
integrator may be stable for the wrong semi-discrete equation.

Current ch13 production policy: the capillary-wave and rising-bubble YAMLs both
use this Level-2 split, i.e. `imex_bdf2` for UCCD6 convection extrapolation and
`implicit_bdf2` for the CCD viscous block.  This is the right setting for
longer runs such as `T=8`, but it should not be interpreted as permission to
raise the capillary step beyond the Denner--van Wachem wave-resolution limit.

## 6. ch13 gate

A ch13 run should not be called theoretically stable merely because it uses an
arbitrary scalar `CFL=0.10`.  The production gate is now `run.time.cfl: 1.0`,
where `1.0` is the multiplier for the fixed theory constants.  Smaller values,
for example `0.5`, are allowed only as conservative multipliers.  Grid spacing
enters through the derived timestep candidates:

```text
dt_adv = C_adv / Σ_i(max |u_i| / h_i),
dt_nu  = C_visc / (2 ν_max Σ_i h_i^{-2})     for explicit viscosity,
dt_cap = C_cap sqrt((ρ_l + ρ_g) h_min^3 / (2πσ)).
```

Current policy constants are `C_adv = 0.10`, `C_cap = 0.05`, and
`C_visc = 1.0`.  The multiplier applies only to explicitly constrained
candidates: explicit advection/transport, the current explicit capillary
response, and explicit viscosity.  `crank_nicolson` and `implicit_bdf2`
viscosity remove the explicit viscous candidate.  Therefore changing `NX`,
`NY`, or non-uniform stretching should not require changing YAML CFL.  The
solver recomputes `h_i`, `h_min`, velocity maxima, and the active limiter.

The gate is:

1. report `dt_adv`, `dt_nu`, and `dt_cap`;
2. state the `C_cap` value used for capillarity and verify that it is fixed by
   policy, not retuned with grid count;
3. if `alpha > 1`, provide compact-operator spectral/energy evidence;
4. if AB2 momentum convection is active, place the scaled eigenvalues in the
   AB2 stability region or show sufficient damping;
5. if surface tension is active, respect the capillary wave-resolution scale;
6. keep SSPRK3 claims limited to scalar interface transport.

If a refined-grid run fails under the same `cfl: 1.0` theory multiplier, classify it
as an operator, curvature-energy, projection, or limiter-switch problem before
touching the YAML CFL coefficient.

## 7. Related short paper

See [SP-Y](../../memo/short_paper/SP-Y_cfl_time_integration_policy.md) for the
full derivation and implementation consequences.
