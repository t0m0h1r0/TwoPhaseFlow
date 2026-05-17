---
ref_id: WIKI-P-025
title: "Chapter 14.2 Evidence Must Come From Canonical ch14_capillary.yaml Outputs"
domain: paper
status: ACTIVE
tags: [chapter14, capillary, paper_figures, yaml_outputs, route_hygiene, phi]
sources:
  - path: paper/sections/14a_capillary_wave.tex
    description: "Chapter 14 capillary-wave section"
  - path: paper/figures/ch14_capillary_yaml/
    description: "YAML-generated Chapter 14 capillary figures"
  - path: docs/wiki/paper/WIKI-P-019.md
    description: "Chapter 14 PhaseRegion capillary benchmark paper contract"
  - path: docs/wiki/experiment/WIKI-E-084.md
    description: "Corrected YAML-owned one-period experiment"
depends_on:
  - "[[WIKI-P-019]]"
  - "[[WIKI-E-084]]"
  - "[[WIKI-X-057]]"
consumers:
  - domain: paper
    usage: "Use before editing Chapter 14.2 or replacing capillary figures"
  - domain: experiment
    usage: "Use to know which outputs are paper-facing"
compiled_by: ResearchArchitect
compiled_at: 2026-05-17
---

# Chapter 14.2 Evidence Must Come From Canonical ch14_capillary.yaml Outputs

## Knowledge Card

Chapter 14.2 must cite the canonical YAML-owned new route, not an ad hoc plot,
old production output, or legacy `psi` snapshot.  The accepted paper evidence
comes from:

```text
experiment/ch14/config/ch14_capillary.yaml
experiment/ch14/diagnose_phase_region_capillary_graph_steps.py
paper/figures/ch14_capillary_yaml/
```

The section should state that `ch14_capillary.yaml` owns the diagnostic grid,
`interface`, `numerics`, `cfl=1.0`, physical snapshot times, and outputs for
`phi`, velocity, pressure, scalar errors, and PhaseRegion summaries.

## Figure Contract

Use YAML-generated figures for:

```text
signed interface amplitude
volume drift
kinetic energy
phi snapshot series
velocity snapshot series
pressure snapshot series
PhaseRegion graph summaries
```

Do not cite `psi_t*.pdf` as the current paper-facing interface field.  The
paper-facing field is `phi`, because the YAML output contract explicitly names
it and the plotter now supports `snapshot_series.field = phi`.

## Text Contract

Avoid wording that implies the run is owned by a legacy runtime YAML.  The
paper wording should instead say that the canonical YAML owns the nonuniform
diagnostic grid and declares:

```text
active_geometry_capillary
q transport
column_height_graph gauge
face_hodge / FCCD pressure stack
```

The paper may cite the exact one-period metrics from WIKI-E-084, but it must
also retain the boundary that `force_admissible=0` keeps this as a reduced
graph-route validation rather than production force-coupled Ch14 dynamics.

## Validation Gate

After replacing Chapter 14.2 text or figures:

```text
make -B -C paper
rg -n "Fatal|Emergency stop|Undefined control sequence|LaTeX Error|File .* not found|Overfull|undefined references|LaTeX Warning:.*Rerun" paper/main.log
git diff --check
```

The log scan should return no matches.
