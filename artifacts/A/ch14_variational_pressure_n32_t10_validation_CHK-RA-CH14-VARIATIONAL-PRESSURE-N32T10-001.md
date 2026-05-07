# CHK-RA-CH14-VARIATIONAL-PRESSURE-N32T10-001

## Scope

Ran the same variational pressure-reaction implementation as
CHK-RA-CH14-VARIATIONAL-PRESSURE-IMPL-N32T1-001 at N=32, T=10 for the
static and oscillating droplets, with psi/velocity/pressure visualization.

The checked-in canonical ch14 YAML files were not modified. Temporary untracked
run copies were created for N=32/T=10, pushed to the remote for execution, then
deleted locally and from the remote after results were pulled.

## Run Settings

Shared production settings:

```text
pressure_force_contract: variational_adjoint
scalar_operator_pairing: variational_operator
surface_tension.source: closed_interface_riesz
closed_interface.endpoint: conservative_psi
capillary_reaction_projection: pressure_component_hodge
```

Static droplet:

- grid: `32 x 32`
- final time: `10.0`
- reinitialization: disabled (`every_steps: 0`)
- snapshot interval: `1.0`
- result data:
  `experiment/ch14/results/_tmp_ch14_static_droplet_n32_t10_variational_pressure/data.npz`

Oscillating droplet:

- grid: `32 x 32`
- final time: `10.0`
- reinitialization: Ridge-Eikonal every step
- snapshot interval: `0.5`
- result data:
  `experiment/ch14/results/_tmp_ch14_oscillating_droplet_n32_t10_variational_pressure/data.npz`

## Results

Static droplet:

- final time: `10.0`
- completed steps: `1012`
- deformation first/final/min/max: `0.0 / 0.0 / 0.0 / 0.0`
- kinetic energy final/max: `3.870828046922476e-07` / `1.718185251024708e-06`
- volume drift final/max: `2.537919946541077e-15` / `2.918607938522238e-15`
- snapshot velocity Linf max: `5.438158165320723e-04`

Oscillating droplet:

- final time: `10.0`
- completed steps: `1035`
- signed deformation first/final/min/max:
  `7.617534118365688e-02 / -3.1759387184835566e-03 /
  -3.1759387184835566e-03 / 7.617534118365688e-02`
- kinetic energy final/max: `9.086702417949426e-04` / `9.498324928254748e-04`
- volume drift final/max: `6.364882880901561e-05` / `6.364882880901561e-05`
- snapshot velocity Linf max: `9.9799337866181e-03`
- Rayleigh-Lamb reference at `t=10`: `-1.0336869846852349e-02`
- final signed-deformation error vs `0.10 cos(0.167435 t)`: `7.160931128368792e-03`
- Linf signed-deformation error vs reference over the run: `2.933668296183478e-02`

## Visualization

- overview PNG:
  `artifacts/A/ch14_variational_pressure_n32_t10_overview.png`
- field snapshot PNG:
  `artifacts/A/ch14_variational_pressure_n32_t10_fields.png`
- combined PDF:
  `artifacts/A/ch14_variational_pressure_n32_t10_visualization.pdf`
- per-run snapshot PDFs:
  - `experiment/ch14/results/_tmp_ch14_static_droplet_n32_t10_variational_pressure/psi_t*.pdf`
  - `experiment/ch14/results/_tmp_ch14_static_droplet_n32_t10_variational_pressure/velocity_t*.pdf`
  - `experiment/ch14/results/_tmp_ch14_static_droplet_n32_t10_variational_pressure/pressure_t*.pdf`
  - `experiment/ch14/results/_tmp_ch14_oscillating_droplet_n32_t10_variational_pressure/psi_t*.pdf`
  - `experiment/ch14/results/_tmp_ch14_oscillating_droplet_n32_t10_variational_pressure/velocity_t*.pdf`
  - `experiment/ch14/results/_tmp_ch14_oscillating_droplet_n32_t10_variational_pressure/pressure_t*.pdf`

## Interpretation

The T=10 run confirms that the oscillating droplet is dynamically driven under
the variational pressure-reaction implementation; the old algebraic zero-drive
failure is not present. The signed deformation crosses through zero by T=10
and remains close in phase to the Rayleigh-Lamb reference at this horizon,
although the amplitude and reinit-coupled volume drift are not theorem-grade
closed.

The static droplet preserves volume and deformation over T=10, but has a small
nonzero velocity/kinetic-energy residual. This remains the finite-N static
criticality/cochain problem rather than a stability workaround target.

[SOLID-X] Validation/artifact only. No production solver/config behavior was
changed in this checkpoint, no tested code was deleted, and no FD/WENO/PPE
fallback, damping/CFL workaround, smoothing, curvature cap, benchmark branch,
blanket projection, or QP-as-physics route was introduced.
