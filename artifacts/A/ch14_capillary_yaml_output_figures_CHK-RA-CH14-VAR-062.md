# CHK-RA-CH14-VAR-062 - Capillary YAML Output Figures for Paper 14.2

Date: 2026-05-17

Scope: replace the Chapter 14.2 capillary-wave paper figure source with the
figures emitted by the capillary-wave YAML output contract.

## Correction

The previous paper reflection used the reduced PhaseRegion graph diagnostic
summary figure as the Chapter 14.2 visual evidence.  That was not the right
paper-facing figure source for the capillary-wave benchmark section.

Chapter 14.2 now uses the files generated from the capillary-wave YAML output
contract:

```text
experiment/ch14/config/ch14_capillary.yaml
  -> base_config: legacy/ch14_capillary_legacy_runtime.yaml
  -> output.snapshots.times = [0, T/4, T/2, 3T/4, T]
  -> output.figures
```

The copied paper assets are:

```text
paper/figures/ch14_capillary_yaml/signed_interface_amplitude.pdf
paper/figures/ch14_capillary_yaml/volume_drift.pdf
paper/figures/ch14_capillary_yaml/kinetic_energy.pdf
paper/figures/ch14_capillary_yaml/psi_t0.000.pdf
paper/figures/ch14_capillary_yaml/psi_t0.012.pdf
paper/figures/ch14_capillary_yaml/psi_t0.023.pdf
paper/figures/ch14_capillary_yaml/psi_t0.035.pdf
paper/figures/ch14_capillary_yaml/psi_t0.047.pdf
paper/figures/ch14_capillary_yaml/velocity_t0.000.pdf
paper/figures/ch14_capillary_yaml/velocity_t0.012.pdf
paper/figures/ch14_capillary_yaml/velocity_t0.023.pdf
paper/figures/ch14_capillary_yaml/velocity_t0.035.pdf
paper/figures/ch14_capillary_yaml/velocity_t0.047.pdf
paper/figures/ch14_capillary_yaml/pressure_t0.000.pdf
paper/figures/ch14_capillary_yaml/pressure_t0.012.pdf
paper/figures/ch14_capillary_yaml/pressure_t0.023.pdf
paper/figures/ch14_capillary_yaml/pressure_t0.035.pdf
paper/figures/ch14_capillary_yaml/pressure_t0.047.pdf
```

## Paper Change

`paper/sections/14a_capillary_wave.tex` now states that visualizations are
restricted to YAML-generated output times and figures.  The section includes:

- YAML time-series figures for signed amplitude, volume drift, and kinetic
  energy;
- psi snapshots at `[0, T/4, T/2, 3T/4, T]`;
- velocity and pressure-gauge snapshots at the same YAML times.

The PhaseRegion reduced-route table remains the quantitative route check.
The pressure/velocity images are explicitly described as YAML-output
diagnostics, not as evidence that the PhaseRegion face force has been admitted
into production PPE/corrector.  `force_admissible=0` remains the boundary.

## Validation

```text
make -B -C paper
= PASS, main.pdf, 283 pages

rg -n "LaTeX Error|Undefined control sequence|File .* not found|Fatal error|Emergency stop|Overfull|undefined references|Reference .* undefined" paper/main.log
= no matches

git diff --check
= PASS
```

Rendered paper previews:

```text
/private/tmp/ch14_capillary_yaml_section-221.png
/private/tmp/ch14_capillary_yaml_section-222.png
/private/tmp/ch14_capillary_yaml_section-223.png
```

[SOLID-X] Paper/wiki/artifact/figure replacement only; no `src/twophase/`,
experiment code, YAML physical parameters, solver algorithm, CFL, damping,
smoothing, tolerance weakening, rebuild skipping, FD/WENO/PPE fallback, hidden
CPU fallback, production pressure/velocity force admission, main merge, branch
deletion, worktree removal, or origin push changed.
