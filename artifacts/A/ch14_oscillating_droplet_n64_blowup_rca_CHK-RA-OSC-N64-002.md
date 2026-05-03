# CHK-RA-OSC-N64-002 — N=64 oscillating-droplet blowup RCA

Date: 2026-05-03
Branch: `ra-oscillating-droplet-n64-20260503`

## Question

The `N=64`, period-one, alpha-4, every-step fitted-grid oscillating droplet
blew up at `t=0.01753`. The user asked for theory-first hypotheses and
explicit falsification, with no small ad hoc fix.

## Theoretical frame

For a Rayleigh-Lamb-like capillary mode, the stiff scale is controlled by
surface tension and curvature:

- capillary-wave stability: `dt = O(sqrt(rho h^3 / sigma))`
- pressure jump: `[p] = sigma kappa`
- curvature-error amplification: a local curvature error becomes a pressure
  jump error multiplied by `sigma`
- mode frequency scale: `omega^2 ~ sigma / (rho R^3)`

The checked N64 ellipse has semi-axes `a=0.055`, `b=0.045`, area-equivalent
radius `sqrt(ab)=0.04975`, and minimum radius of curvature
`b^2/a=0.03682`. On the alpha-4 fitted grid the recorded `h_min` is about
`5.94e-03`, so the minimum curvature radius is only about `6.2 h_min`.
That is a marginal regime for a pressure-jump, high-density-ratio, moving-grid
closure. The uniform-grid diameter is only about `6.4` cells, so the case is
also small in the coarse-grid sense.

## Hypotheses and controls

All controls used:

```bash
make cycle EXP=experiment/ch14/probe_oscillating_droplet_n64_hypotheses.py ARGS="..."
```

The probe ran to `T=0.02` unless the runner BLOWUP guard stopped it.

| Case | Hypothesis tested | Result | Interpretation |
|---|---|---:|---|
| `base_alpha4` | Reference route | BLOWUP at `t=0.0175309`; `max KE=5.466e+08`; `max bf=1.438e+12` | Failure reproduced. |
| `cfl_0p05` | Capillary dt alone is too large | Completed; `max KE=1.042e-03`; `max bf=1.918e+03` | Smaller dt suppresses nonlinear runaway, but does not remove the geometric source term. |
| `sigma_0` | Surface tension is the energy source | Completed in one step; zero KE/BF | Capillary forcing is necessary. |
| `sigma_water` | Period-one sigma is too stiff | Completed; `max KE=3.353e-06`; `max bf=1.703e+02` | High sigma is a major amplifier. |
| `rho_equal` | Density jump/PPE coefficient jump is primary | Completed; `max KE=2.563e-03`; `max bf=1.924e+03` | High density ratio is a major amplifier. |
| `mu0_no_visc_dc` | Viscous DC causes blowup | BLOWUP at `t=0.0175338`; `max KE=3.781e+08` | Viscous DC is falsified as primary cause. |
| `static_grid` | Every-step ALE remap causes blowup | BLOWUP earlier at `t=0.013217`; `max bf=6.001e+12` | ALE remap is not primary; static fitted metric is worse here. |
| `alpha2_dynamic` | alpha-4 metric concentration is primary | Completed; `h_min=9.17e-03`; `max KE=3.905e-04` | Strong support: weakening metric concentration stabilizes. |
| `uniform_grid` | Nonuniform geometry/metric closure is primary | Completed; `h_min=1.5625e-02`; `max KE=2.312e-04` | Nonuniform/fitted closure is an amplifier. |
| `circle_static` | Small area alone causes failure | Completed; `max KE=4.913e-04` | Small radius alone is insufficient; oscillatory curvature matters. |
| `small_amp` | Elliptic perturbation curvature is too strong | Completed; same area scale, weaker axes; `max KE=4.728e-04` | Strong support: curvature amplitude/resolution is decisive. |
| `drop_1p5x` | Droplet under-resolution is primary | Completed; `max KE=3.586e-04` | Strong support. |
| `drop_2x` | Droplet under-resolution is primary | Completed; `max KE=2.106e-04` | Strong support. |

Local pulled summary:

```bash
python experiment/ch14/probe_oscillating_droplet_n64_hypotheses.py --plot-only
```

## Diagnosis

Primary cause:

The N64 period-one ellipse is under-resolved for the adopted high-density-ratio
pressure-jump route. The dangerous quantity is not merely total droplet area;
it is the combination of small minimum curvature radius, high `sigma=0.811133`,
high density ratio, and alpha-4 fitted-grid geometry. This combination injects
a balanced-force residual that remains moderate early but enters a nonlinear
runaway near `t=0.0175`, where `bf_residual_max` jumps to `O(1e12)` and kinetic
energy crosses the BLOWUP guard.

Secondary factors:

- High sigma is necessary in the tested route: `sigma_0` and `sigma_water`
  both remove the early blowup.
- The density jump is a strong multiplier: `rho_equal` stabilizes the same
  shape and sigma to `T=0.02`.
- Alpha-4 fitting is too aggressive for this geometry at N64:
  `alpha2_dynamic` and `uniform_grid` complete, while `static_grid` worsens.
- The nominal capillary CFL is not a proof of stability in this under-resolved
  pressure-jump regime: `cfl_0p05` completes, but this is a symptom control,
  not a root-cause fix.

Falsified causes:

- Viscous defect correction is not primary; removing viscosity/DC still blows up.
- Volume loss is not primary; failing cases have volume drift around `1e-06`.
- Every-step remap alone is not primary; static fitted grid fails earlier.

## Consequence

The mathematically consistent remedy is not a hidden CFL clamp or a damping
patch. The benchmark parameters must satisfy a resolution contract such as:

- minimum curvature radius resolved by enough local grid intervals,
- pressure-jump capillary mode resolved at the chosen `sigma` and density ratio,
- fitted-grid alpha chosen from that resolution budget,
- period-one forcing used only after the geometry is sufficiently resolved.

For N64, the current `a=0.055`, `b=0.045`, `sigma=0.811133`, alpha-4 route is
outside that contract. The tested stable directions are larger droplet,
smaller perturbation amplitude, weaker alpha, lower sigma, equal density, or
smaller timestep. Only the first three are genuine geometry-resolution fixes
for this benchmark family; lowering dt alone is not an acceptable root fix.

[SOLID-X] No SOLID violation found. This checkpoint adds an experiment probe
and evidence artifact only; no solver/operator/builder boundary was changed,
and no tested implementation was deleted.
