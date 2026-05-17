---
ref_id: WIKI-X-057
title: "Ch14 Capillary Session Lessons: YAML Ownership, Route Hygiene, and Failure Preservation"
domain: cross-domain
status: ACTIVE
tags: [ch14, capillary, yaml_contract, route_hygiene, failure_ledger, output_contract, old_data]
sources:
  - path: artifacts/A/ch14_capillary_yaml_time_owned_outputs_CHK-RA-CH14-VAR-063.md
    description: "Final corrected YAML-owned capillary run and output contract"
  - path: docs/wiki/experiment/WIKI-E-064.md
    description: "Baseline PASS and screened graph-q FAIL"
  - path: docs/wiki/cross-domain/WIKI-X-056.md
    description: "Origin-reset handoff protocol"
  - path: experiment/ch14/config/ch14_capillary.yaml
    description: "Canonical Ch14 capillary YAML"
depends_on:
  - "[[WIKI-X-056]]"
  - "[[WIKI-E-064]]"
  - "[[WIKI-T-178]]"
consumers:
  - domain: experiment
    usage: "Use before rerunning Ch14 capillary data or accepting figures"
  - domain: code
    usage: "Use before editing canonical YAML, plot output, or route flags"
  - domain: paper
    usage: "Use before replacing Chapter 14 figures or prose"
compiled_by: ResearchArchitect
compiled_at: 2026-05-17
---

# Ch14 Capillary Session Lessons: YAML Ownership, Route Hygiene, and Failure Preservation

## Knowledge Card

The most important session lesson is that a correct theory can still be
misrepresented by a thin YAML, stale output data, or an accidental old route.
For Ch14 capillary, the canonical config file is an executable contract, not a
shortcut launcher.

The corrected `experiment/ch14/config/ch14_capillary.yaml` must own:

```text
grid
interface
physics
run.time.final
run.time.cfl = 1.0
numerics
output.snapshots.times
output.figures
diagnostics
initial_condition
initial_velocity
boundary_condition
```

It must not replace physical output times with step counts, hide `dt` in the
YAML, omit `interface` or `numerics`, or let an experiment script silently
choose a different route.

## Failure Ledger

| Failure or correction | Preserved lesson |
|---|---|
| Screened graph-q projection failed on the source branch | Keep it as negative evidence for q/phi state splitting; do not keep repairing it by inertia. |
| YAML was reduced too far | A canonical experiment config must show the numerical route, not only a few runtime knobs. |
| Fixed `dt` appeared in the canonical YAML | The capillary experiment is specified by `cfl=1.0`; derived `dt` belongs to the run report. |
| Output timing was treated as step based | Paper snapshots are physical-time outputs at YAML-owned times. |
| `phi`, velocity, and pressure outputs were missing | Chapter 14 acceptance requires the fields that diagnose the route, not only scalar curves. |
| Plot axes differed between velocity and pressure snapshots | Snapshot series must share axis limits/ticks when they are compared as fields. |
| Old result directories remained | Delete local and remote Ch14 results before a route-defining rerun. |
| Paper figures were generated outside the YAML contract | Chapter 14 figures must be produced by the YAML output path. |

## Route-Hygiene Checks

Before accepting a Ch14 capillary run, check all of the following:

```text
config filename is experiment/ch14/config/ch14_capillary.yaml
interface.state_space is active_geometry_capillary
run.time.cfl is 1.0
run.time.dt is absent
output.snapshots.times is present
output figures include phi, velocity, and pressure
experiment/ch14/results/ch14_capillary is absent after clean rerun
result NPZ stores phi/u/v/pressure snapshots on the same node grid
```

The run command should be the YAML-owned route:

```text
make cycle EXP=experiment/ch14/diagnose_phase_region_capillary_graph_steps.py ARGS='--config experiment/ch14/config/ch14_capillary.yaml'
```

## Stop Conditions

Stop and audit the route when:

- a plot looks right but does not come from the canonical YAML output;
- the run reuses old data after a route correction;
- `psi` figures are used where the accepted contract says `phi`;
- a config edit removes `interface`, `numerics`, diagnostics, or field outputs;
- `force_admissible=0` is ignored when interpreting a reduced graph run as a
  production force-coupled result.
