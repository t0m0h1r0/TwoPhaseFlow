# CHK-RA-CH14-VARIATIONAL-PRESSURE-IMPL-UX-001

## Purpose

Translate the variational pressure-complex theorem into an implementation and
YAML UX plan.  This is a design checkpoint only; no production source behavior
is changed here.

The production principle is:

```text
pressure force = kinetic-metric Riesz adjoint of the production divergence
G = M^{-1}D^T W
L = D G
pressure_face_reaction(p; c) = Gp - c
```

The implementation must prevent the old failure mode: solving a scalar PPE
with one pressure face representative and applying another representative to
the velocity/capillary Hodge path.

## Implementation SSoT

Introduce a first-class pressure complex object, conceptually:

```text
PressureComplex(
    divergence: D,
    face_metric: M,
    pressure_metric: W,
    quotient: periodic/gauge/active-face rules,
    sign_convention: subtractive_projection,
)

apply_D(face_components)        -> nodal divergence
apply_G(pressure, rho, ...)     -> variational pressure reaction faces
apply_L(pressure, rho, ...)     -> apply_D(apply_G(pressure))
face_weights(rho, ...)          -> M diagonal on active face DOFs
pressure_weights()              -> W on physical pressure DOFs
apply_shifted_reaction(p, c)    -> apply_G(p) - c
```

This can initially live close to the existing divergence/PPE stack rather than
as a sweeping architecture rewrite:

```text
src/twophase/simulation/pressure_complex.py          new focused helpers
src/twophase/simulation/divergence_ops.py            expose variational reaction faces
src/twophase/ppe/fccd_matrixfree.py                  certify/route L = D G
src/twophase/simulation/interface_projection_diagnostics.py
                                                     use complex weights and G
src/twophase/simulation/ns_step_services.py          call shifted variational reaction
```

The old `div_op.pressure_fluxes(...)` name may remain for call-site stability,
but its contract must be narrowed:

```text
pressure_fluxes(...) returns the production variational pressure reaction
faces used by projection.
```

Raw compact gradients must not be production pressure forces.  If still useful
for diagnostics or reconstruction, expose them under an unmistakable name such
as:

```text
raw_compact_pressure_gradient_faces(p, ...)
```

or keep them inside `FCCDSolver.face_gradient` without routing them through
projection/capillary APIs.

## Stepwise Implementation Plan

### Step 0: Operator-Gate Harness

Build a small deterministic operator-gate harness before changing droplet
behavior.  It should instantiate the active grid, boundary condition, density
coefficient, and interface-coupling mode, then test:

```text
G0 quotient: pressure images, face images, gauge, and active faces are explicit;
G1 Green identity: <Gp,w>_M - <p,Dw>_W = 0;
G2 scalar identity: PPE.apply(p) = D(Gp);
G3 positivity: <p,Lp>_W = ||Gp||_M^2 >= 0;
```

The first target is CPU deterministic probes; GPU repeats after CPU exactness.
No droplet output should be interpreted before these gates pass.

### Step 1: Face and Pressure Weights

Promote the current diagnostic metric logic into a production helper:

```text
face_measure Q_f:
    d_face(axis) * transverse_face_area

inverse_density alpha_f:
    phase_density harmonic coefficient
    phase_separated active coefficient
    affine_jump active coefficient

M_f = Q_f / alpha_f on active faces
W_p = nodal control volume on physical pressure nodes
```

Fail-close conditions:

- `alpha_f <= 0` cannot be part of an SPD metric.
- phase-separated zero-coupling faces must be removed from the active face
  space or rejected until the quotient graph is explicit.
- unrestricted periodic image arrays are not valid metric spaces.

### Step 2: Variational `G` Kernels

Implement `apply_G` as the transpose application of the actual production
divergence:

```text
apply_G(p):
    pW = W * p on physical pressure DOFs
    covector_faces = D^T pW on physical face DOFs
    return M^{-1} covector_faces
```

For current wall/FVM-like divergence rows, this is local and axis-wise.  For
periodic rows, operate on unique physical pressure nodes and unique face DOFs,
then write synchronized storage images.  For future compact divergence, the
same rule applies; the transpose may be line-local rather than nearest-neighbor.

This is not a fallback gradient.  The order of `G` is determined by the chosen
`D`.  If a higher-order pressure projection is required, the production target
is a higher-order SBP/Riesz pair `(D^{(4)},G^{(4)})`, not raw `face_gradient`.

### Step 3: Scalar PPE Pairing

Add a certification path:

```text
ppe_solver.apply(p) == div_op.divergence_from_faces(div_op.pressure_fluxes(p))
```

on the physical quotient and active coefficients.

If this equality passes for the old scalar FCCD operator, reuse the old solve
but apply the new variational face reaction after solving.  If it fails, route
the solver operator itself to:

```text
L_var(p) = D(G(p)).
```

The code must not permit:

```text
solve L_old p = rhs
apply u <- u - dt*G_var p
```

unless `L_old = D G_var` has passed the operator gate.

### Step 4: Affine Shift and Capillary Cochains

Unify all capillary/jump paths as a shift in the same reaction:

```text
pressure_face_reaction(p; c) = Gp - c
rhs contribution             = D(c)
velocity update              = u* - dt*(Gp - c)
```

For `closed_interface_riesz`, `c` is the component-corrected surface-energy
cochain.  For legacy Young-Laplace jump paths, `c` is the affine jump cochain.
The scalar RHS and face correction must use the same `D`, `G`, `M`, `W`.

The existing keyword `capillary_jump_components` should be renamed internally
or wrapped conceptually as `capillary_shift_components`; the old name can remain
as a deprecated YAML/internal alias only if it does not obscure the sign.

### Step 5: Component Saddle

Move the component saddle to the same pressure complex:

```text
X = [G, B_1, ..., B_k]
h = s - Xz
X^T M X z = X^T M s
```

Implementation can continue using PPE solves for the pressure block only if the
solver is certified as `L = D G`.  Diagnostics must report:

```text
div_linf                  ||D h||_inf
component_constraint      ||B^T M h||_inf
pressure_work_residual    ||<Gp,h>_M|| normalized
energy_power_residual     |dE[T h] + ||h||_M^2|
```

These are stronger and more interpretable than a shape-specific static droplet
velocity check.

### Step 6: Downstream CCD/FCCD/UCCD Boundary

The authoritative pressure-corrected object is the projected face state.  Nodal
reconstruction is downstream:

```text
face projection -> corrected face components -> reconstruct_nodes -> UCCD/viscosity
```

UCCD and viscosity must not reintroduce a different pressure range.  If they
need nodal states, they consume reconstruction of the already-projected face
state.  Raw compact pressure gradients remain diagnostic/reconstruction tools,
not constraint forces.

### Step 7: Validation Experiments

Only after operator gates:

1. FVM quotient baseline: adjoint and scalar identities roundoff.
2. FCCD variational path: adjoint and scalar identities roundoff.
3. Static droplet N32/T1: no shape classifier, use constrained-criticality
   residuals plus velocity/energy/volume.
4. Oscillating droplet N32/T1: nonzero admissible capillary drive and energy
   power identity.
5. N32/T10 visualization only after the short-run identities are clean.

## YAML UX Principles

YAML should express physics contracts, not implementation hacks.  Users should
not have to choose between raw gradient and variational force for production.

The recommended UX is:

```yaml
numerics:
  projection:
    poisson:
      operator:
        discretization: fccd
        coefficient: phase_separated
        interface_coupling: affine_jump
        pressure_force_contract: variational_adjoint
        scalar_operator_pairing: require_certified
        capillary_reaction_projection: pressure_component_hodge
```

Where:

```text
pressure_force_contract:
  variational_adjoint   production default; pressure_fluxes returns G=M^-1D^TW
  raw_compact_gradient  invalid for production projection; diagnostics only

scalar_operator_pairing:
  require_certified     fail if PPE.apply != D(Gp)
  variational_operator  force L = D(Gp)
```

Avoid adding `auto` here.  `auto` hid too much in earlier capillary projection
paths.  If a mode cannot be certified, fail close with a message naming the
violated theorem.

## Backward Compatibility Policy

Existing canonical CH14 YAMLs should migrate to:

```yaml
pressure_force_contract: variational_adjoint
scalar_operator_pairing: require_certified
```

Legacy configs that omit `pressure_force_contract` can default to
`variational_adjoint` for `poisson.operator.discretization: fccd`, but with a
warning in diagnostics during the transition:

```text
defaulted pressure_force_contract to variational_adjoint;
raw FCCD face gradients are no longer production pressure forces.
```

Configs explicitly requesting raw compact gradients as projection force should
raise, not silently run:

```text
poisson.operator.pressure_force_contract='raw_compact_gradient' is diagnostic
only and cannot be used for production projection/capillarity.
```

This preserves tested code while preventing the known non-adjoint path from
being mistaken as valid physics.

## Diagnostics UX

Add a compact operator-contract section to experiment metrics:

```text
pressure_contract_green_residual
pressure_contract_scalar_pairing_residual
pressure_contract_positivity_min
pressure_contract_periodic_quotient_active
pressure_contract_active_face_fraction
capillary_contract_pressure_work_residual
capillary_contract_energy_power_residual
```

The important UX is the error message, not the knob.  Example fail-close text:

```text
Variational pressure contract failed:
  PPE.apply(p) differs from D(pressure_fluxes(p)) by 2.1e-1.
  This would solve one scalar pressure equation and apply a different face
  pressure reaction.  Set scalar_operator_pairing: variational_operator or
  implement/certify the FCCD scalar pair.
```

## File-Level Work Plan

1. `config_constants.py`, `config_run_poisson_sections.py`,
   `config_models.py`, and builder plumbing:
   parse `pressure_force_contract` and `scalar_operator_pairing` with
   fail-close validation.

2. `pressure_complex.py`:
   implement quotient-aware weights, active-face masks, Green identity probes,
   and `apply_G` for the current divergence rows.

3. `divergence_ops.py`:
   route `pressure_fluxes` to the variational reaction when the contract is
   `variational_adjoint`; expose raw FCCD gradient under a diagnostic-only name.

4. `fccd_matrixfree.py`:
   add scalar pairing certification and, if needed, an `L_var = D(Gp)` apply
   path.

5. `interface_projection_diagnostics.py`:
   replace diagnostic-local pressure weights with the pressure complex SSoT;
   add Green/scalar/positivity residuals.

6. `ns_step_services.py`:
   treat capillary/jump cochains as `capillary_shift_components`; ensure RHS
   and face correction use the same complex and sign convention.

7. Tests:
   add small operator tests before droplet tests:
   FVM wall/periodic, FCCD wall/periodic, phase-density, phase-separated
   fail-close, affine shift consistency, CPU/GPU parity where available.

## Risk Register

| risk | mitigation |
|---|---|
| Sign convention mismatch between `pressure_fluxes` and `apply_pressure_projection`. | Encode subtractive projection convention in function names/tests: `u_new = u_old - dt*(Gp-c)`. |
| Periodic image rows contaminate adjoint probes. | Test only physical quotient DOFs; storage images synchronized after operator application. |
| `phase_separated` zero faces make `M` non-SPD. | Active-face quotient or fail-close until disconnected active graph is explicit. |
| Old PPE scalar operator not equal to `D(Gp)`. | `require_certified` fails; `variational_operator` uses `L_var`. |
| Raw FCCD gradient accidentally remains in production. | Rename/split diagnostic API and make production `pressure_fluxes` contract variational. |
| GPU fast path diverges from theorem path. | Implement operator kernels from the same pressure complex helpers; diagnostics consume those helpers. |
| Nodal reconstruction interpreted as pressure orthogonality space. | State and test that orthogonality is on face space; nodal fields are downstream visualization/momentum inputs. |

## Verdict

The implementation should proceed by introducing a variational pressure complex
as the production SSoT.  YAML should expose only high-level physical contracts:

```text
pressure_force_contract: variational_adjoint
scalar_operator_pairing: require_certified | variational_operator
```

The default should be fail-close, not fallback.  Raw compact FCCD pressure
gradients may remain as diagnostics, but production projection, capillary
Hodge, component saddles, pressure history, and CCD/FCCD/UCCD coupling must all
share the same variational pressure reaction.
