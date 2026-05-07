# CHK-RA-CH14-GENERAL-RESIDUAL-001

Date: 2026-05-07

Scope: reassess the static velocity-ring remedy under a stronger requirement:
the scheme must not be static-droplet-specific.  It should address residuals
that can also appear in oscillating droplets and other systems, while
preserving true physical capillary drive.  Damping, CFL changes, smoothing,
curvature caps, benchmark branches, blanket projection, and post-hoc force
subtraction remain forbidden.

## Central Theorem Constraint

A universal "remove all nonzero Hodge residuals" rule is impossible: in a
noncritical oscillating droplet the Hodge component is the physical capillary
drive.  Removing it reproduces the earlier zero-drive failure.

The only admissible generalization is therefore:

```text
eliminate theorem defects and constraint/reaction artifacts;
preserve the constrained variational drive.
```

For any system, define the active discrete object

```text
(q_c, E_h(q_c), C_h(q_c), T_h(q_c), D_f, G_A(q_c), M_A(q_c)).
```

Here `E_h` may contain surface energy and any variational body potential
included in the physical model; `C_h` contains component volumes, mass,
contact-angle constraints, or other holonomic constraints; `T_h` is the actual
transport endpoint; `G_A` is the implemented pressure action; and `M_A` is the
pressure-adjoint face metric.

The physical face acceleration is the coupled constrained saddle residual:

```text
s      = -M_A^{-1} T_h^* dE_h
B_i    =  M_A^{-1} T_h^* dC_i
h      = s - G_A p - B mu
D_f h  = 0
B^T M_A h = 0.
```

`h` is not a numerical residual to erase.  It is the physical drive after
removing pressure and constraint reactions.  The numerical residual to
eliminate is the mismatch between the implementation and this theorem:

```text
r_defect =
  implementation force - pressure-adjoint variational saddle force.
```

## Hypotheses

| ID | Hypothesis | Theory check | Verdict |
|---|---|---|---|
| H01 | A static-droplet initializer is enough. | It only fixes one equilibrium reference and does not address dynamic endpoint/metric defects. | Too narrow. |
| H02 | Blanket Hodge cancellation gives a universal residual cleaner. | It sets `h=0` for noncritical modes and kills oscillations. | Rejected. |
| H03 | A universal variational cochain plus coupled pressure/constraint saddle is the right object. | It yields `h=0` only when the state is constrained critical, and `h!=0` otherwise. | Supported. |
| H04 | Endpoint mismatch is a universal residual source. | If force is VJP of one endpoint but transport/corrector use another, work identity fails for every system. | Supported. |
| H05 | Metric mismatch is a universal residual source. | If `M_A` differs between Riesz construction and pressure-Hodge projection, reaction orthogonality and energy power are not the same theorem. | Supported. |
| H06 | Missing constraints create residuals that look like physics. | Component volume, mass, wall/contact, or externally imposed constraints must enter `B`. | Supported. |
| H07 | Reinit/remap/profile projection can generate nonphysical residuals. | These maps are not the capillary transport endpoint; their energy/volume change must be ledgered or retracted. | Supported. |
| H08 | Dynamic residuals can be safely removed by minimizing energy each step. | That would damp true oscillations and turn dynamics into relaxation. | Rejected. |
| H09 | Equilibrium states in any system can be constructed by solving the same saddle criticality equation. | This generalizes static droplets to all declared steady states. | Supported. |
| H10 | Non-equilibrium systems should pass a nonzero-drive gate, not a zero-residual gate. | Oscillating and perturbed modes are correct precisely when constrained first variation is nonzero. | Supported. |
| H11 | Topology/stratum changes can be handled by the same local derivative. | The derivative changes discontinuously; production must fail closed or switch theorem strata. | Rejected as local solve. |
| H12 | A trace-primary redesign can solve profile sensitivity generally. | True only if transport, state, and CCD/FCCD/UCCD coupling become trace-primary too. | Future architecture. |
| H13 | CCD/FCCD/UCCD compatibility is optional bookkeeping. | False: the capillary cochain becomes physical momentum only through the face state consumed by UCCD and the velocity field seen by CCD viscosity. | Rejected; compatibility is theorem-level. |

## General Scheme

The general scheme is a three-layer split.

### Layer 1: Theorem-Exact Force Construction

For the active endpoint `q_c`, build all physical cochains from one discrete
action/constraint system:

```text
E_h(q_c), C_h(q_c), T_h(q_c), M_A(q_c), D_f, G_A(q_c).
```

The production force must satisfy virtual work:

```text
dE_h(q_c)[T_h u] + <s,u>_{M_A} = 0
dC_i(q_c)[T_h u] - <B_i,u>_{M_A} = 0
```

for arbitrary resolved face velocities `u`.  If this fails, the scheme has a
defect before any benchmark is considered.

### Layer 2: Reaction-Only Saddle Projection

Remove only pressure and physical constraint reactions:

```text
h = s - G_A p - B mu
D_f h = 0
B^T M_A h = 0.
```

This is not residual hiding.  It is the finite-dimensional version of pressure
and Lagrange multipliers doing no work on admissible motions.  If a state is
not constrained critical, `h` remains nonzero and must enter the corrector.

### Layer 3: Compatibility Operations Outside Momentum

Operations that are not the physical endpoint, such as reinitialization,
remap, profile restoration, or fitted-grid rebuilds, must not silently inject
capillary work.  They need one of:

```text
endpoint-equivalence certificate,
explicit projection-work ledger,
or fail-close retraction/diagnostic.
```

This layer is where "residuals in other systems" can be eliminated without
damping dynamics.  It removes inconsistency introduced by auxiliary maps; it
does not remove the physical drive `h`.

## CCD/FCCD/UCCD Compatibility

The general scheme must live on the same compact/mimetic operator family as
the rest of the solver.  Otherwise the force may be variational in isolation
but still inject a residual when handed to momentum.

For the current production stack the compatibility contract is:

```text
FCCD:
  P_f q, D_f, face divergence, pressure_fluxes, and projected face state
  define the capillary endpoint and pressure-Hodge range.

UCCD:
  the corrected projected face velocity is the velocity consumed by the
  high-order convection update; no separate capillary velocity or off-complex
  reconstruction is allowed.

CCD:
  viscosity sees the same corrected velocity field after projection; the
  capillary law must not create a different gradient/divergence complex for
  viscous coupling.
```

Therefore the admissible residual-elimination scheme is not merely
energy-consistent.  It must satisfy a commutative diagram:

```text
state q_c
  -> FCCD endpoint T_h and pressure range G_A
  -> corrected face acceleration h
  -> projected face velocity u_f^{n+1}
  -> UCCD convection / CCD viscosity / diagnostics
```

If any arrow uses a different interpolation, divergence, reconstruction, or
metric, the discrepancy is a theorem defect.  It should be eliminated by
operator unification or reported fail-close, not absorbed into a damping or
force-correction term.

## What Changes Relative to Static-Droplet Thinking

The static droplet is just one equilibrium gate:

```text
declared equilibrium: h = 0.
```

An oscillating droplet is a non-equilibrium gate:

```text
declared perturbation: h != 0,
and the sign-power identity predicts surface-energy release.
```

Other systems use the same rule.  If gravity or another conservative body
force is part of the model, it belongs in `E_h`.  If a wall/contact condition
is imposed, it belongs in `C_h` and therefore in `B`.  If a system is intended
to be steady, solve its finite-dimensional constrained criticality equation.
If it is intended to move, require the constrained drive to be nonzero.

## Feasibility

The path still has a realistic prospect because the hard part is not a
static-shape classifier.  It is an operator-consistency program:

1. use the actual conservative endpoint `T_h`;
2. use the actual pressure action `G_A=pressure_fluxes(... zero jump ...)`;
3. use the pressure-adjoint metric `M_A`;
4. build surface/body/constraint cochains as VJPs of the same endpoint;
5. deliver the resulting acceleration through the same FCCD projected face
   state consumed by UCCD convection and CCD viscosity;
6. solve the coupled saddle;
7. validate equilibria and non-equilibria with different gates.

The previous N32 static dimension check remains encouraging for equilibrium
constructors, but the more general claim does not rely on static droplets.  It
relies on preserving the theorem:

```text
dE_h[T_h h] = -||h||_{M_A}^2 <= 0
```

after pressure and constraints are removed.

## Required Validation Matrix

| Gate | Expected result |
|---|---|
| Manufactured pressure range | `h=0` to solver tolerance |
| Manufactured constraint reaction | `h=0` after saddle |
| Constructed static equilibrium | zero-speed release from rest |
| Sampled noncritical static-looking state | nonzero diagnostic residual before construction |
| Oscillating droplet | nonzero capillary drive and positive kinetic release |
| Non-elliptic perturbation | nonzero drive without shape-name branching |
| UCCD coupling | projected face state carries the same `h`; no separate capillary path |
| CCD coupling | viscous update uses the same corrected velocity complex |
| FCCD adjointness | `pressure_fluxes`, `D_f`, `M_A`, and `T_h` satisfy the pressure-adjoint work gate |
| Reinit/remap-only step | no capillary-work interpretation unless ledgered |
| Metric/endpoint mismatch probe | fail-close, not fallback |

## Verdict

Yes, the general scheme has a path.  The critical distinction is:

```text
physical Hodge drive h          -> keep
operator/endpoint/constraint defect -> eliminate or fail close
```

Static liquid-drop initialization is only one application of the general
framework.  The production goal should be a structure-preserving variational
force/saddle complex that makes every declared equilibrium quiet and every
resolved noncritical mode move.  That is compatible with oscillating droplets
and other systems; a static-specific correction is not.

[SOLID-X] Theory/feasibility only.  No production behavior changed; no tested
code deleted; no FD/WENO/PPE fallback, damping/CFL workaround, smoothing,
curvature cap, benchmark branch, blanket projection, or QP-as-physics path
introduced.
