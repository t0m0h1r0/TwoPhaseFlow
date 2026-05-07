# CHK-RA-CH14-GENERAL-IMPL-UX-001

Date: 2026-05-07

Scope: implementation method and YAML/UX policy for the risk-closed general
capillary residual framework.  This is not a static-droplet scheme.  The
implementation must preserve physical drive for oscillating droplets and other
noncritical systems, while eliminating or fail-closing theorem defects.

## Design Target

Production should expose one structure-preserving capillary contract:

```text
active endpoint q_c
  -> variational cochains s,B from E_h,C_h,T_h,M_A
  -> pressure/constraint saddle using G_A,D_f,M_A
  -> corrected face cochain c_corrected = s - B mu
  -> same FCCD projected face state
  -> UCCD convection and CCD viscosity.
```

The key UX rule is that users select the theorem, not benchmark behavior.
There must be no `static_droplet_fix`, no `circle_balance`, no damping option,
and no "quiet residual" switch.

## Current Seam

The current code already has a usable seam:

- `ns_step_services.solve_ns_pressure_stage` detects
  `capillary_force_source == "closed_interface_riesz"`;
- it builds a closed-interface cochain;
- it sends `corrected_capillary_components` to both PPE RHS and
  `pressure_fluxes(..., capillary_jump_components=...)`;
- `config_run_operator_sections.py` already rejects combining this source with
  scalar curvature and rejects `capillary_range_projection` for this route;
- diagnostics already report capillary face/Hodge/component quantities.

The main implementation gap is not the seam.  The gap is theorem closure:

```text
closed_interface_riesz_cochain currently uses its own face_mass_components;
the production theorem requires active pressure-adjoint M_A from G_A.
```

Therefore the first code change must not be a new force.  It must be a
diagnostic and metric-identification layer.

## Implementation Stages

### Stage 1: Risk Diagnostics, No Force Change

Add a theorem diagnostic object, for example:

```text
GeneralResidualTheoremDiagnostics
```

with scalar outputs:

```text
capillary_theorem_regular_stratum
capillary_theorem_endpoint_equivalent
capillary_theorem_pressure_adjoint_residual
capillary_theorem_energy_vjp_residual
capillary_theorem_constraint_vjp_residual
capillary_theorem_constraint_rank
capillary_theorem_saddle_divergence_linf
capillary_theorem_saddle_constraint_linf
capillary_theorem_sign_power_residual
capillary_theorem_fccd_uccd_ccd_closed
capillary_theorem_auxiliary_energy_delta
capillary_theorem_auxiliary_constraint_delta
```

This stage observes the active run and can fail a validation, but it does not
change velocity.  It should be cheap by default and expandable with probe
counts.

### Stage 2: Active `M_A` Extraction

Introduce an active metric provider tied to the implemented pressure action:

```text
capillary_pressure_adjoint_face_weights(
    xp, div_op, rho, pressure_flux_kwargs
) -> list[face weights]
```

The existing `_capillary_face_hodge_weights` logic is the natural starting
point, but it should become a named theorem utility rather than a diagnostic
private helper.  It must use the same affine-jump inverse density and face
measure as `pressure_fluxes`.

Acceptance gate:

```text
<G_A p,w>_{M_A} - <p,D_f w>_{W_p} ~= 0
```

for random, smooth, interface-localized, divergence-free, and
component-reaction-like probes.

### Stage 3: VJP-Correct Cochain Builder

Refactor the cochain builder to accept the active metric:

```text
closed_interface_riesz_cochain(
  ...,
  face_weight_components=active_M_A,
  endpoint_psi=q_c,
)
```

or introduce a new explicit builder:

```text
general_variational_face_cochain(...)
```

The builder should return:

```text
surface_acceleration s
constraint_accelerations B_i
surface_force_covector M_A s
constraint_force_covectors M_A B_i
vjp_diagnostics
stratum_diagnostics
```

For the current scope, `E_h=sigma S_h` and `C_h=component volume`.  The API
should allow later constraints without changing the pressure-stage shape.

### Stage 4: Coupled Saddle Through Actual `G_A`

Promote `capillary_external_component_saddle_projection` into the theorem
saddle implementation, but tighten the algebra:

```text
L_A(c): solve D_f G_A p_c = D_f c
Z_A(c)=c-L_A(c)
C_ij = B_i^T M_A Z_A(B_j)
r_i  = B_i^T M_A Z_A(s)
C mu = r
c_corrected = s - B mu
h = Z_A(c_corrected)
```

The symmetric `Z_i^T M_A Z_j` shortcut is allowed only when pressure
orthogonality has been proven for the active operator.

The pressure stage must continue to pass the exact same `c_corrected` to:

```text
rhs += D_f(c_corrected)
pressure_fluxes(..., capillary_jump_components=c_corrected)
```

### Stage 5: CCD/FCCD/UCCD Closure Checks

Add identity checks around the existing face-native path:

```text
state.pressure_correction_face_components
state.pressure_accel_face_components
state.projected_face_components
```

Acceptance:

```text
projected face state contains the same h that passed the saddle,
UCCD receives projected faces,
CCD viscosity receives velocity reconstructed from projected faces.
```

No separate capillary velocity path should be introduced.

### Stage 6: Enforce Mode

Only after Stages 1-5 pass should YAML allow fail-close enforcement:

```text
capillary_force:
  residual_contract:
    mode: enforce
```

In enforce mode, failed theorem predicates raise a runtime error.  They do not
fall back to scalar curvature, range projection, smoothing, damping, or local
CPU diagnostic paths.

### Stage 7: Equilibrium Constructors

Equilibrium construction is optional and separate from the force law:

```text
initialization:
  equilibrium:
    method: variational_saddle
    target_constraints: component_volume
```

This is where a static droplet can be made quiet.  It must solve `h=0` and
`C=C0` using the same theorem object.  It is not a runtime correction and not
special to droplets.

## YAML / UX Policy

### Recommended Public Shape

Keep the existing top-level production selection:

```yaml
momentum:
  terms:
    surface_tension:
      formulation: pressure_jump
      source: closed_interface_riesz
```

Add an explicit contract block under the pressure operator or surface-tension
source.  The key should describe the theorem, not a benchmark:

```yaml
projection:
  poisson:
    operator:
      interface_coupling: affine_jump
      capillary_reaction_projection: pressure_component_hodge
      capillary_residual_contract:
        endpoint: conservative_psi
        metric: pressure_adjoint
        constraints: [component_volume]
        mode: diagnose
        fail_close: true
        probes:
          pressure_adjoint: standard
          vjp: standard
```

Default policy:

```text
mode: diagnose
fail_close: true for invalid combinations
fail_close diagnostics do not stop legacy runs unless mode=enforce
```

When mode is `production` or `enforce`, all A0-A9 gates must pass.

### Avoided UX

Reject these names and concepts:

```text
static_fix
circle_balance
rayleigh_lamb_mode
quiet_ring
remove_hodge
range_projected_for_closed_interface
fallback_curvature
smooth_until_static
```

These names encode the wrong model.  The UI should teach the user that the
scheme is a variational residual contract.

### Validation UX

Expose a compact verdict in logs:

```text
capillary_residual_contract: PASS diagnose
endpoint=conservative_psi metric=pressure_adjoint constraints=component_volume
pressure_adjoint=2.1e-12 energy_vjp=4.0e-11 saddle=7.5e-13 sign_power=3.2e-10
```

If failed:

```text
capillary_residual_contract: FAIL pressure_adjoint
action: fail_close
reason: active G_A is not M_A-adjoint to D_f under configured metric
```

No fallback suggestion should point to damping, smoothing, CFL, scalar
curvature, or range projection.  Suggested action should be diagnostic:

```text
check endpoint q_T/q_R ledger,
check affine metric extraction,
check pressure_fluxes range,
check constraint rank.
```

## Diagnostics Keys

Add diagnostics in groups:

```text
capillary_contract_pressure_adjoint_residual
capillary_contract_energy_vjp_residual
capillary_contract_constraint_vjp_residual
capillary_contract_saddle_divergence_linf
capillary_contract_saddle_constraint_linf
capillary_contract_sign_power_residual
capillary_contract_endpoint_energy_delta
capillary_contract_endpoint_constraint_delta
capillary_contract_fccd_uccd_ccd_closed
capillary_contract_failed_gate_code
```

Use numeric gate codes for time-series storage, plus textual failure reports in
logs/artifacts.

## GPU-First Policy

Production hot path must be backend-native:

```text
xp arrays for dS_h,dC_h,T_h^*,M_A dots,
device weighted reductions,
tiny constraint solve on device when practical,
host transfer only for scalar diagnostics.
```

Host-loop graph traversal and dense matrices remain diagnostics unless proven
identical and performance-acceptable.  A CPU-only fallback for production
geometry is not allowed.

## Validation Plan

1. Unit gates:
   - pressure adjointness on manufactured fields;
   - VJP work identity for random and structured velocities;
   - constraint VJP for component volume;
   - saddle removes manufactured pressure/constraint reactions.

2. Integration gates:
   - closed-interface route still drives N32 oscillating droplet;
   - constructed equilibrium releases from rest with zero face acceleration;
   - sampled noncritical "static-looking" state reports nonzero physical
     drive until constructed;
   - non-elliptic perturbation produces nonzero drive.

3. Closure gates:
   - PPE RHS and corrector use identical `c_corrected`;
   - projected face state carries `h`;
   - UCCD/CCD consume that same state.

4. Auxiliary gates:
   - reinit/remap/profile energy deltas are separate diagnostics;
   - endpoint-equivalence failures stop enforce mode.

## Implementation Verdict

The implementation is feasible if staged as diagnostics-first.  The first
production code should not attempt to quiet the ring.  It should identify the
active theorem object and prove or disprove the A0-A9 gates at runtime.

Once those pass, the same infrastructure can be used for static equilibria,
oscillating droplets, and other systems without shape-specific branching.

[SOLID-X] Design/UX only.  No production behavior changed; no tested code
deleted; no FD/WENO/PPE fallback, damping/CFL workaround, smoothing, curvature
cap, benchmark branch, blanket projection, or QP-as-physics path introduced.
