---
ref_id: WIKI-L-039
title: "GPU Utilization Probes Must Bound Output Without Changing the Route"
domain: code
status: ACTIVE
superseded_by: null
tags: [gpu, profiling, probes, output, affine_jump, ch14]
sources:
  - path: artifacts/A/ch14_capillary_affine_gpu90_CHK-RA-GPU90-001.md
    description: "512x512 affine-jump GPU90 utilization probe"
  - path: artifacts/A/ch14_capillary_n32_t10_gpuopt_CHK-RA-GPU90-002.md
    description: "N32/T10 affine GPU route measurement"
depends_on:
  - "[[WIKI-L-037]]"
  - "[[WIKI-L-038]]"
  - "[[WIKI-L-026]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-05
---

# GPU Utilization Probe Hygiene

## Knowledge Card

GPU utilization probes should isolate the GPU-heavy numerical route from
host-side output dilution without changing the scientific route being measured.
The admissible pattern is:

- keep the production numerical stack unchanged;
- bound grid size, final time, or `max_steps` in a probe config;
- disable nonessential serialization and plotting, for example `save_npz:
  false`, empty snapshots, and empty figures;
- place measurement-only YAML under probe scope rather than silently retuning
  the production benchmark.

The GPU90 artifacts show two useful cases.  A large bounded affine-jump probe
reached near-saturated GPU utilization, while a smaller N32/T10 route still
achieved high utilization after output dilution was removed.  In both cases,
algorithmic loosening, tolerance changes, or route changes were rejected as
performance shortcuts.

## Consequences

- A profiling probe can change measurement envelope, not physics or solver
  semantics.
- `output.save_npz: false` belongs in runner/output handling; numerical kernels
  should not know about profiling convenience.
- Probe YAMLs should be clearly separate from production configs and excluded
  from broad benchmark sweeps.
- If GMRES matvecs remain the hotspot after output is removed, the next work is
  algebra-preserving kernel fusion or GPU-resident Krylov work, not scientific
  route relaxation.

## Paper-Derived Rule

Measure GPU performance with bounded, output-light probes that preserve the
same affine-jump/FCCD/HFE/UCCD route.  Do not buy utilization by changing the
algorithm under test.
