---
ref_id: WIKI-E-070
title: "Ch14 PhaseRegion Experiment Readiness Gate"
domain: experiment
status: ACTIVE
tags: [ch14, phase_region, experiment_readiness, gate, negative_knowledge]
sources:
  - path: artifacts/A/ch14_experiment_readiness_gate_CHK-RA-CH14-VAR-023.md
    description: "Step 0 evidence freeze, acceptance sheet, and next experiment gates"
  - path: docs/wiki/experiment/WIKI-E-064.md
    description: "Baseline capillary PASS and screened graph-q FAIL evidence"
  - path: docs/wiki/code/WIKI-L-054.md
    description: "Boundary/nonuniform atlas audit and remaining graph F0 blocker"
depends_on:
  - "[[WIKI-E-064]]"
  - "[[WIKI-E-069]]"
  - "[[WIKI-L-054]]"
consumers:
  - domain: experiment
    usage: "Use before starting new Ch14 PhaseRegion capillary experiments"
  - domain: code
    usage: "Use before implementing nonuniform graph F0/F1 admission or runtime adapters"
compiled_by: ResearchArchitect
compiled_at: 2026-05-17
---

# Ch14 PhaseRegion Experiment Readiness Gate

## Knowledge Card

The experiment sequence is admitted only as a gate ladder:

```text
nonuniform graph F0
-> graph F1 low-mode KKT
-> closed-curve oracle
-> multi-component atlas
-> force oracle
-> runtime dry-run
-> micro stepping
-> T/8
```

The old screened q/phi runtime rebuild remains negative knowledge.  It must
not be repaired by looser tolerance, smoothing, damping, rebuild skipping, CFL
retuning, or hidden fallback.

## Acceptance Sheet

Every new oracle or probe must report:

- total and component volume;
- `q_T`, `Q_h(R_h)`, and residual `r`;
- mode amplitude/phase or equivalent shape coordinates;
- perimeter or surface energy;
- boundary attachment and phase role;
- nonuniform grid parameter and cell-capacity status when applicable;
- visualization path;
- `force_admissible`, defaulting to false until the force oracle passes.

## Next Gate

The immediate next target is a chart-specific nonuniform graph F0 admission
oracle.  The known blocker is that `project_column_height_to_graph` remains
uniform x-grid only.

This card does not authorize runtime force coupling or T/8.
