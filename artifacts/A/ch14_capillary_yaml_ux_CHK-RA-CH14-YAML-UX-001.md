# CHK-RA-CH14-YAML-UX-001: YAML UX policy for variational capillarity

Date: 2026-05-07
Branch: `codex/ra-ch14-capillary-virtual-work-20260506`
Scope: design the YAML/user-facing configuration policy for the selected
closed-interface Riesz capillarity implementation.  This is a
documentation/design slice only.

## Problem

The current ch14 YAML is readable for the legacy scalar pressure-jump route:

```yaml
capillary_force:
  formulation: pressure_jump
...
poisson:
  operator:
    interface_coupling: affine_jump
    capillary_range_projection: component_hodge_augmented
```

For the final variational law, this UX is too ambiguous:

```text
1. `curvature` sounds like the force primitive, but the new law uses dS_h.
2. `capillary_range_projection` sounds like the old force-deleting operation.
3. force construction and reaction removal live in different YAML branches.
4. boolean/alias UX such as true/on/range invites unsafe shortcuts.
```

The YAML must make the mathematical diagram visible enough that a user cannot
accidentally select a symptom fix while believing they selected the physical
law.

## UX Principles

1. Name the physical object, not the implementation trick.
2. Separate raw capillary cochain construction from reaction projection.
3. Keep scalar curvature as a legacy source, not as the extension point for the
   Riesz law.
4. Make experimental physics explicit; do not hide it behind `auto`.
5. Fail closed on incompatible combinations.
6. Do not add benchmark names, shape names, damping knobs, or Rayleigh fitting
   knobs.
7. Preserve legacy configs until the new law is verified, but prevent the new
   law from inheriting unsafe legacy aliases.
8. Surface diagnostics as contract gates, not as optional decorative output.

## Proposed YAML Shape

The recommended final shape is:

```yaml
numerics:
  physical_time:
    momentum:
      capillary_force:
        formulation: pressure_jump
        source: closed_interface_riesz
        closed_interface:
          trace_space: p1_fixed_stratum
          surface_energy: sharp_length
          component_volume: oriented_area
          topology: fail_closed
          transport_adjoint:
            endpoint: before_reinit
            operator: fccd_level_set
          diagnostics:
            mode: strict
            require:
              - stratum_hash
              - geometry_finite_difference
              - transport_vjp_dot_product
              - riesz_work
              - hodge_orthogonality
              - corrector_sign_lock
              - reinit_energy_split
  elliptic:
    pressure_projection:
      face_flux_projection: true
      poisson:
        operator:
          discretization: fccd
          coefficient: phase_separated
          interface_coupling: affine_jump
          capillary_reaction_projection: pressure_component_hodge
```

This separates:

```text
capillary_force.source
  what raw capillary cochain is constructed.

closed_interface.*
  which discrete geometry and transport-adjoint contract defines it.

poisson.operator.capillary_reaction_projection
  which silent reaction space is removed in the pressure/corrector stage.
```

## Minimal User-Facing Form

Most users should not have to repeat every contract subkey.  Once defaults are
validated, this should be sufficient:

```yaml
capillary_force:
  formulation: pressure_jump
  source: closed_interface_riesz
```

with parser-expanded defaults:

```yaml
closed_interface:
  trace_space: p1_fixed_stratum
  surface_energy: sharp_length
  component_volume: oriented_area
  topology: fail_closed
  transport_adjoint:
    endpoint: before_reinit
    operator: fccd_level_set
  diagnostics:
    mode: strict
```

and an explicit projection requirement:

```yaml
poisson:
  operator:
    capillary_reaction_projection: pressure_component_hodge
```

The projection requirement should not be silently inserted for experimental
runs.  If omitted, the parser should report the exact missing contract.

## Legacy Scalar Route

The existing route remains valid under a clearer name:

```yaml
capillary_force:
  formulation: pressure_jump
  source: curvature_jump
  curvature: face_implicit
poisson:
  operator:
    capillary_range_projection: component_hodge_augmented
```

`source: curvature_jump` is the default while the Riesz route is experimental.
The current `curvature` key is meaningful only in this source.  If
`source: closed_interface_riesz` and `curvature` are both present, fail closed:

```text
capillary_force.curvature is ignored by source='closed_interface_riesz';
remove curvature or set source='curvature_jump'.
```

## Projection Key Policy

Keep `capillary_range_projection` as a legacy key for the scalar cochain.
Introduce:

```yaml
capillary_reaction_projection: pressure_component_hodge
```

for the Riesz law.

Accepted values:

```text
none                       diagnostics only, never accepted for production ch14
pressure_only              diagnostic Hodge quotient against range(A_fG_f)
pressure_component_hodge   selected reaction space range(A_fG_f)+range(B)
```

Rejected values for the new key:

```text
range_projected
component_hodge_augmented
true / false / on / off
```

Reason: those names belong to the legacy scalar-cochain path and encode the
old failure modes.  The new key should speak in terms of reaction spaces.

## Fail-Closed Compatibility Matrix

For `source: closed_interface_riesz`, require:

| YAML field | Required value |
|---|---|
| `capillary_force.formulation` | `pressure_jump` |
| `projection.face_flux_projection` | `true` |
| `poisson.operator.discretization` | `fccd` |
| `poisson.operator.coefficient` | `phase_separated` |
| `poisson.operator.interface_coupling` | `affine_jump` |
| `poisson.operator.capillary_reaction_projection` | `pressure_component_hodge` |
| `closed_interface.topology` | `fail_closed` |
| `closed_interface.transport_adjoint.endpoint` | `before_reinit` |

Example error:

```text
capillary_force.source='closed_interface_riesz' requires
poisson.operator.capillary_reaction_projection='pressure_component_hodge'
because the force is defined only after pressure and component reactions are
removed in the same M_f metric.
```

## Diagnostics UX

Diagnostics should be named after theorem gates:

```yaml
output:
  diagnostics:
    capillary_contract: true
    reinit_energy_split: true
```

Expected fields:

```text
capillary_stratum_hash_changed
capillary_geometry_fd_residual
capillary_transport_vjp_residual
capillary_riesz_work_residual
capillary_volume_work_residual
capillary_hodge_orthogonality_residual
capillary_component_rank
capillary_corrector_sign_power
capillary_transport_energy_delta
capillary_reinit_energy_delta
```

Do not expose diagnostics as benchmark labels such as `ellipse_error` or
`static_circle_pass`.  The output should report contract residuals, and the
experiment script can interpret them for ch14.

## Avoided YAML UX

Do not use:

```yaml
curvature: closed_interface_riesz
capillary_range_projection: true
capillary_range_projection: range_projected
capillary_force:
  benchmark: oscillating_droplet
  rayleigh_scale: 1.18
  damping_fix: true
  curvature_cap: ...
```

These either hide the physical source behind the wrong noun, revive the old
range-projection bug, or introduce symptom tuning.

## Parser Transition Plan

The implementation can preserve old configs while adding the new UX:

```text
1. Add RunCfg fields:
   capillary_source,
   capillary_reaction_projection,
   closed_interface_* options.
2. Parse `capillary_force.source`, defaulting to `curvature_jump`.
3. Parse `capillary_reaction_projection` separately from legacy
   `capillary_range_projection`.
4. If source is `curvature_jump`, keep legacy behavior and aliases.
5. If source is `closed_interface_riesz`, reject legacy projection aliases,
   reject `curvature`, require the compatibility matrix, and require strict
   diagnostics until the validation ledger accepts production defaulting.
6. Emit normalized config values in run metadata so artifacts show the resolved
   physical contract.
```

## Final YAML Contract

The final user-facing sentence should be:

```text
`source: closed_interface_riesz` means the solver constructs capillarity from
fixed-stratum surface-energy virtual work, then removes only pressure and
component reactions with `capillary_reaction_projection:
pressure_component_hodge`.
```

That sentence is the UX check.  If a YAML key makes this sentence false or
unclear, the key is wrong.

[SOLID-X] YAML UX design artifact only; no production source/config/result
change, no tested implementation deleted, no FD/WENO/PPE fallback, damping,
CFL workaround, curvature cap, smoothing, blanket `c -> Pi_R c`,
benchmark-name branch, or QP-as-physics path introduced.
