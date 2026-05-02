# CHK-RA-OSC-001 — Oscillating droplet instability root-cause investigation

Date: 2026-05-02
Branch: `ra-oscillating-droplet-20260502`

## Question

The Rayleigh-Lamb `n=2` oscillating droplet benchmark blew up in early runs.
The user asked whether the recently merged implicit-BDF2 viscous defect
correction (DC) path could be responsible, and requested a physics/math-first
hypothesis investigation.

## Governing theory

For a 2-D perturbed droplet

\[
r(\theta,0)=R(1+\epsilon\cos 2\theta),
\]

the inviscid Rayleigh-Lamb reference used for this code path is

\[
\omega_2 =
\sqrt{\frac{6\sigma}{(\rho_l+\rho_g)R^3}}.
\]

The explicit capillary timestep used by `twophase.simulation.ns_runtime_services`
is

\[
\Delta t_\sigma =
C_\sigma
\sqrt{\frac{(\rho_l+\rho_g)h_{\min}^3}{2\pi\sigma}},
\qquad C_\sigma=0.05.
\]

With the fitted-grid run reporting `h_min=2.5879e-02`,
`\rho_l=\rho_g=1`, and `\sigma=1`, this gives

\[
\Delta t_\sigma \simeq 1.1744\times 10^{-4}.
\]

The failing fixed step `dt=8.0e-4` was therefore `6.812x` the code's
capillary stability budget.

## Hypotheses and falsification

| Hypothesis | Theory expectation | Evidence | Verdict |
|---|---|---|---|
| H1: Viscous DC caused the blowup | DC can only affect runs selecting `viscosity.time_integrator=implicit_bdf2`; with `mu=0` and `forward_euler`, the viscous operator is explicit zero. | Runtime config printed `viscous_time_scheme=forward_euler`, `mu_l=mu_g=0`, predictor class `ExplicitViscousPredictor`. | Falsified for the observed blowup. |
| H2: Fixed `dt` violated capillary CFL | Surface-tension waves have `dt=O(h_min^{3/2})`; using a larger fixed step injects unstable capillary energy. | Fixed `dt=8e-4` blew up at `t=0.1168` in the equal-density no-DC case; replacing it with theory `cfl: 1.0` completed to `t=0.15`, `max(KE)=7.36e-02`, final volume drift `2.15e-04`. | Supported; primary cause. |
| H3: Viscous DC route is unstable even when explicitly selected | With `mu=0`, implicit-BDF2 Helmholtz reduces to identity; DC should return the explicit RHS and remain bounded under the same capillary CFL. | `ch14_oscillating_droplet_viscous_dc_probe` selected `ImplicitBDF2ViscousPredictor` and completed to `t=0.15`, `max(KE)=7.08e-02`, final volume drift `1.42e-04`. | Falsified. |
| H4: Reinitialization triggered the instability | Reinit can change interface mass/curvature; disabling it should remove a reinit-timed failure. | With `reinit_every=0`, fixed `dt=8e-4` still blew up at `t=0.1168`. | Falsified as primary; may affect sharpness. |
| H5: Dynamic fitted-grid remap triggered the instability | Per-step remap can inject interpolation error; static grid should delay or remove blowup. | Switching `schedule: 0` delayed failure compared with dynamic/high-density attempts but still blew up under fixed oversize `dt`. | Secondary at most. |
| H6: Density ratio stiffness was primary | High density ratio tightens pressure/material coupling; equal-density should remove the failure if primary. | Equal-density fixed `dt=8e-4` still blew up, only later than the `rho_l/rho_g=1000` run. | Secondary amplifier. |
| H7: PPE DC caused the instability | PPE DC is shared by no-DC and viscous-DC probes; if it were primary, theory-CFL runs should also fail. | Both theory-CFL runs completed to `t=0.15` with bounded KE and small volume drift. | Falsified for this failure. |
| H8: IMEX-BDF2 convection coupling caused instability | The DC probe necessarily uses `imex_bdf2` convection; if unstable, it should fail under the same CFL. | DC probe completed and produced similar KE/deformation scale to no-DC. | Falsified for short-time instability. |
| H9: Signed deformation diagnostic perturbed the solve | Diagnostics are post-step reductions and do not feed solver state. | Targeted `signed_deformation` test passed; changing diagnostic output cannot alter `psi,u,v,p`. | Falsified. |
| H10: Curvature cap changes benchmark fidelity | A hard cap can alter frequency/amplitude but should not cause CFL-scale blowup when `dt` respects capillary stability. | Stable theory-CFL runs report bounded flow despite active `kappa_max=8`. | Not primary; keep as accuracy caveat. |

## Validation commands

- `make test PYTEST_ARGS="-k signed_deformation -q"`: PASS.
- `make cycle EXP=experiment/run.py ARGS="--config ch14_oscillating_droplet"` with fixed `dt=8e-4`: blew up at `t=0.1168`; `KE=1.892e10`, volume drift `3.246e-01`.
- Same config with theory `cfl: 1.0`: PASS to `t=0.15`; `max(KE)=7.356e-02`, final volume drift `2.152e-04`.
- `make cycle EXP=experiment/run.py ARGS="--config ch14_oscillating_droplet_viscous_dc_probe"`: PASS to `t=0.15`; `max(KE)=7.083e-02`, final volume drift `1.415e-04`.
- `make test PYTEST_ARGS="-k implicit_bdf2_viscous_dc_zero_operator_matches_formula -q"`: PASS.
- `make test PYTEST_ARGS="-k implicit_bdf2_viscous_dc_reduces_high_residual -q"`: PASS.

## Conclusion

The observed oscillating-droplet blowup is not caused by the viscous DC
implementation. The failing runs selected no viscous DC path, and an explicit
viscous-DC probe with zero physical viscosity remained stable under the same
capillary CFL.

The primary cause is the fixed timestep violating the capillary-wave stability
law on the fitted grid by approximately `6.8x`. Density ratio, dynamic
nonuniform remap, and reinitialization can amplify the failure, but they do not
explain it without the capillary timestep violation.

[SOLID-X] No SOLID violation found. The investigation adds a diagnostic scalar
and YAML-level benchmark/probe configs; solver ownership and DC implementation
boundaries are unchanged.
