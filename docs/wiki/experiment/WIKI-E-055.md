---
ref_id: WIKI-E-055
title: "Capillary-Wave RCA Requires Energy and Mode Diagnostics, Not Max Deviation Alone"
domain: experiment
status: ACTIVE
superseded_by: null
tags: [capillary_wave, ch14, energy_audit, diagnostics, rca]
sources:
  - path: docs/memo/CHK-RA-CAPWAVE-N32T8-RCA-001.md
    description: "N32 T8 capillary-wave RCA and energy/mode reinterpretation"
depends_on:
  - "[[WIKI-X-039]]"
  - "[[WIKI-X-043]]"
  - "[[WIKI-T-077]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-05
---

# Capillary-Wave RCA Diagnostics

## Knowledge Card

For capillary waves, a maximum vertical deviation is not the signed Fourier
amplitude of the target mode.  A run can show a decaying or correctly restoring
fundamental mode while still failing through high-wavenumber interface wrinkle
growth and surface-energy creation.

The RCA diagnostic stack should therefore include:

- signed target-mode amplitude;
- high-mode amplitudes;
- interface length or discrete surface energy;
- kinetic plus surface-energy trend;
- curvature-cap events and cut-face source behavior.

## Consequences

- Do not infer wrong Young-Laplace sign from max-deviation growth alone.
- A static affine jump check does not certify dynamic capillary energy
  compatibility.
- Curvature caps are diagnostic guards; passing by cap/smoother tuning is not
  an acceptance criterion.
- Nonuniform-grid controls should be compared against uniform controls before
  blaming reinitialization or time step.

## Paper-Derived Rule

Judge capillary-wave RCA by the capillary energy/mode budget, not by one
amplitude diagnostic.
