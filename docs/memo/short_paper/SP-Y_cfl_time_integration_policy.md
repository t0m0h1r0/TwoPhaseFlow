# SP-Y — Theory-First CFL Budget and Time-Integration Policy for Two-Phase CCD/FCCD/UCCD6 Solvers

**Date**: 2026-04-25
**Status**: ACTIVE / design correction
**Related**:
[docs/memo/cfl_theory_clarification.md](../cfl_theory_clarification.md),
[WIKI-X-038](../../wiki/cross-domain/WIKI-X-038.md),
[WIKI-X-025](../../wiki/cross-domain/WIKI-X-025.md),
[WIKI-X-026](../../wiki/cross-domain/WIKI-X-026.md),
[WIKI-X-032](../../wiki/cross-domain/WIKI-X-032.md)

---

## Abstract

The previous time-step discussion mixed three different ideas: the SSP/TVD
property of Shu--Osher RK3, the scalar Courant number used in code, and the
physical capillary-wave time scale.  These are not interchangeable.  SSPRK3 is
not a stability proof for a non-monotone compact spatial operator; AB2 has no
finite imaginary-axis stability interval and therefore cannot stabilise a
purely central/skew compact advection operator by taking a smaller positive
Courant number; and a scalar `h_min / max|u|` estimate is not the
multidimensional CFL condition.

This short paper fixes the stability budget.  The runtime CFL must be written
as a sum of axis-wise rates, capillarity must be controlled by the
Denner--van Wachem wave-resolution scale, and compact non-uniform grids need an
operator-level spectral or energy argument beyond scalar CFL.  The recommended
production time integrator is therefore not "TVD-RK3 for the NS system".  The
near-term production design should be an IMEX-BDF2 projection scheme: explicit
extrapolated UCCD6/FCCD convection, truly implicit diffusion, semi-implicit
surface-tension coupling, and a balanced-force variable-density projection.
SSPRK3 remains acceptable for scalar CLS transport as an explicit RK method, but
not as a global NS stability certificate.

---

## 1. What SSPRK3 actually guarantees

For a semi-discrete equation

```text
dq/dt = L(q),
```

the Shu--Osher third-order scheme has stages

```text
q1      = qn + dt L(qn)
q2      = 3/4 qn + 1/4 (q1 + dt L(q1))
q^{n+1} = 1/3 qn + 2/3 (q2 + dt L(q2)).
```

Its SSP coefficient is 1.  Therefore it preserves a convex strong-stability
property only if the forward-Euler step

```text
q + dt L(q)
```

already has that property under the same step-size bound.  If `L` is a compact
CCD/FCCD/DCCD operator that is dispersive, non-monotone, or not
forward-Euler contractive, the phrase "TVD-RK3" does not imply TVD or nonlinear
stability.

For the linear scalar test `y' = lambda y`, SSPRK3 has stability polynomial

```text
R(z) = 1 + z + z^2/2 + z^3/6,     z = dt lambda.
```

Two constants matter:

```text
|Im z| <= sqrt(3)       for purely imaginary eigenvalues,
-2.5127 <= Re z <= 0   for negative real eigenvalues.
```

These are absolute-stability bounds, not SSP/TVD bounds.

---

## 2. Why AB2 is not enough for compact momentum advection

AB2 applied to `y' = lambda y` obeys

```text
r^2 - (1 + 3z/2) r + z/2 = 0.
```

The method is stable only when both roots lie in the unit disk.  Its stability
region is tangent to the imaginary axis at the origin; there is no non-zero
interval of stable purely imaginary `z`.  A central or skew-Hermitian compact
advection operator has eigenvalues close to the imaginary axis, so AB2 alone is
not a stability mechanism for momentum convection.  It must be paired with
enough negative-real damping from viscosity, upwind/hyperviscosity, or an
operator-specific IMEX proof.

This is the main reason the production NS time integrator should not be
justified by the scalar SSPRK3 discussion.  The scalar interface-transport
integrator and the variable-density momentum projection integrator are different
objects.

---

## 3. Correct multidimensional CFL budget

For two-dimensional explicit advection, the necessary Courant rate is the
axis-wise sum

```text
Lambda_adv = max|u| / h_x,min + max|v| / h_y,min,
dt_adv     = C_adv / Lambda_adv.
```

Using

```text
C_adv h_min / max(max|u|, max|v|)
```

is not the multidimensional CFL condition.  For diagonal flow on an isotropic
grid it is too large by a factor of two.

For explicit diffusion in 2-D,

```text
dt_nu = 1 / (2 nu_max (h_x,min^-2 + h_y,min^-2)).
```

On an isotropic grid this reduces to `h^2/(4 nu_max)`.  A truly implicit
negative-definite Crank--Nicolson or BDF2 diffusion solve can remove this
stability restriction for the diffusion block.  A one-step Picard or explicit
trapezoid approximation does not provide the same proof.

For capillary waves,

```text
dt_cap = C_wave sqrt((rho_l + rho_g) h_min^3 / (2 pi sigma)),
C_wave ≈ 0.1--0.3.
```

In the runtime configuration the scalar key `run.time.cfl` is the only
dimensionless user safety coefficient.  Therefore, when `sigma > 0`, the same
value must be used as `C_wave` in the capillary-wave bound unless a future
configuration introduces an explicitly named and documented override.  A
hard-coded value such as `C_wave = 0.25` violates the written CFL contract:
`cfl: 0.10` would still advance at the 0.25 capillary coefficient whenever the
initial advective rate is small.  This is not a harmless implementation detail;
for a water--air capillary wave it multiplies the physical wave-resolution
timestep by 2.5 and can move the update outside the stable/resolved part of the
coupled compact operator.

This is a physical wave-resolution scale, not only an explicit-CSF stability
bound.  Implicit surface tension removes a spurious stiff eigenvalue, but if the
short capillary wave is part of the resolved dynamics, the time step must still
resolve it to obtain the correct wave phase and damping.

The necessary production budget is therefore

```text
dt <= min(dt_adv, dt_nu_if_not_truly_implicit, dt_cap, dt_operator).
```

`dt_operator` denotes additional restrictions from the actual compact operator:
wall closures, non-uniform metrics, FCCD face fluxes, UCCD6 hyperviscosity, and
projection coupling.

---

## 4. Non-uniform compact grids require operator-level certification

On a uniform periodic grid, Fourier symbols can be used to place the scaled
eigenvalues `dt lambda_j` inside an RK or multistep stability region.  On a
wall-bounded or non-uniform compact grid, the operator is generally non-normal.
The smallest spacing `h_min` is only a necessary scale.  It does not bound
transient growth caused by metric variation, boundary closure, or projection
inconsistency.

The strict certification options are:

1. prove a discrete energy estimate for the coupled operator;
2. compute the actual spectrum and pseudospectrum of the semi-discrete block;
3. run a resolution/CFL sweep as empirical evidence, explicitly labelled as
   empirical rather than a theorem.

For ch13-like non-uniform two-phase runs, scalar CFL and capillary bounds should
be treated as necessary preconditions only.

Applied to the production ch13 YAMLs, both capillary-wave and rising-bubble
water--air cases should use the Level-2 momentum stack
`convection.time_integrator=imex_bdf2` with
`viscosity.time_integrator=implicit_bdf2`.  The old AB2+CN combination remains
acceptable as a short diagnostic baseline, but it is not the preferred long-time
or larger-CFL setting.  This change removes the explicit viscous restriction;
it does not enlarge the capillary wave-resolution bound.

---

## 5. Recommended time-integration hierarchy

### 5.1 Scalar CLS transport

Keep SSPRK3 or another explicit RK method for scalar `psi`/`phi` transport.
The statement should be:

```text
SSPRK3 is used as a third-order explicit RK integrator for CLS transport.
It is not claimed to prove TVD unless the chosen spatial operator is
forward-Euler contractive under the same bound.
```

The CFL is `dt_adv` from the axis-wise rate sum.  If FCCD flux transport is used
on non-uniform grids, an operator-level stability check is still required.

### 5.2 Production NS solver

Use an IMEX-BDF2 projection method:

```text
(3 u^{n+1} - 4 u^n + u^{n-1}) / (2 dt)
  + EXT2 A(u)
  = implicit V(u^{n+1})
    - grad p^{n+1}
    + semi-implicit surface tension
    + body force,

div u^{n+1} = 0.
```

where

```text
EXT2 A(u) = 2 A(u^n) - A(u^{n-1}).
```

The projection must use the same face coefficient, gradient, divergence, and
surface-force representation as the pressure equation.  This scheme is the best
near-term compromise:

- BDF2 is A-stable for the implicit blocks;
- explicit convection remains cheap and GPU-friendly;
- the pressure solve remains a projection rather than a fully coupled JFNK;
- capillary and non-uniform-grid constraints remain visible instead of being
  hidden behind the word "TVD".

### 5.3 Stiffer regimes

If IMEX-BDF2 is not enough, move to one of:

```text
IMEX-SDIRK2 / ARK2:
  stronger implicit treatment of viscosity and surface tension;
  still cheaper than a fully coupled solve.

Fully coupled Radau IIA or equivalent implicit RK:
  reserved for extreme density ratio, low Weber number, thin films, or cases
  where projection splitting dominates.
```

---

## 6. Implementation consequences

Immediate corrections:

1. Runtime CFL must use the directional Courant sum.
2. Capillary time-step control must use `run.time.cfl` as `C_wave`, not a
   hard-coded coefficient.
3. Capillary time-step control must be explicitly reported as `dt_cap`.
4. "TVD-RK3 stable" must never be used as a justification for the full NS step.
5. ch13 non-uniform runs need operator-level evidence before being called
   theoretically stable.

Deferred implementation work:

1. implement a true implicit diffusion block, not a Picard-only surrogate;
2. implement IMEX-BDF2 predictor/projection state with restart/startup policy;
3. add a compact-operator spectral audit for FCCD/UCCD6 on the actual grid;
4. add diagnostics reporting `dt_adv`, `dt_nu`, `dt_cap`, and `dt_operator` when
   available.

### 6.1 2026-04-27 implementation addendum: grid-independent YAML policy

The scalar YAML setting is now a multiplier on the fixed theory budget.  The
production form is

```yaml
run:
  time:
    cfl: 1.0
```

where `1.0` expands to the fixed dimensionless constants

```text
C_adv = 0.10,   C_cap = 0.05,   C_visc = 1.0.
```

To make the run more conservative, use a smaller multiplier such as
`cfl: 0.5`; do not rewrite the operator constants in YAML.

The timestep is then computed from operator-specific candidates:

```text
dt_adv = C_adv / Σ_i(max |u_i| / h_i),
dt_nu  = C_visc / (2 ν_max Σ_i h_i^{-2})     for explicit viscosity,
dt_cap = C_cap sqrt((ρ_l + ρ_g) h_min^3 / (2πσ)).
```

The multiplier applies only to explicitly constrained candidates.  Therefore
explicit advection/transport, the current explicit capillary response, and
explicit viscosity are scaled; `crank_nicolson` and `implicit_bdf2` viscosity
remove the explicit viscous CFL candidate.  This is not an instruction to
enlarge the capillary step; it is the opposite: the dimensionless constants are
fixed by theory/verification, and changing `NX`, `NY`, or non-uniform
stretching only changes `h_i`, `h_min`, and the measured velocity maxima.  A
refined-grid failure under the same policy is therefore not solved by retuning
YAML CFL.  It is evidence for one of:

1. a non-uniform compact-operator spectral bound not captured by scalar `h_min`;
2. a capillary/curvature energy-law defect;
3. projection tolerance or splitting error becoming active after refinement;
4. a limiter switch from capillary to advection or viscosity.

The runner records `dt_advective`, `dt_viscous`, `dt_capillary`,
`dt_limiter_code`, `h_min`, and `advective_rate` when step diagnostics are
enabled.  These quantities are the required audit trail for grid sweeps.

---

## 7. References

- Shu and Osher (1988), *Journal of Computational Physics* 77, 439--471.
- Gottlieb, Shu and Tadmor (2001), *SIAM Review* 43, 89--112.
- Brackbill, Kothe and Zemach (1992), *Journal of Computational Physics* 100,
  335--354.
- Denner and van Wachem (2015), *Journal of Computational Physics* 285, 24--40.
- Denner and van Wachem (2022), *Journal of Computational Physics* 449, 110788.
- Lele (1992), *Journal of Computational Physics* 103, 16--42.
- Visbal and Gaitonde (2002), *Journal of Computational Physics* 181, 155--185.
