---
ref_id: WIKI-E-064
title: "Capillary Runtime Baseline and Screened Graph-q Failure"
domain: experiment
status: ACTIVE
tags: [ch14, capillary_wave, screened_projection, q_phi_compatibility, negative_knowledge, visualization, fail_close]
sources:
  - branch: codex/ra-ch14-osc-droplet-eighth-20260516
    commit: b0d36536
    path: docs/wiki/experiment/WIKI-E-085.md
    description: "Source-branch experiment card preserved here before the branch is discarded"
  - path: artifacts/A/ch14_capillary_screened_graph_q_runtime_CHK-RA-CH14-OSC-EIGHTH-032.md
    description: "Exact runtime probe evidence and command log extracted from the source branch"
  - path: docs/wiki/theory/WIKI-T-174.md
    description: "State-ownership theory explaining why q/phi residual repair is not enough"
  - path: docs/wiki/cross-domain/WIKI-X-056.md
    description: "Origin-reset handoff protocol"
depends_on:
  - "[[WIKI-T-174]]"
  - "[[WIKI-X-056]]"
consumers:
  - domain: experiment
    usage: "Use before rerunning capillary-wave or oscillating-droplet probes after discarding the source branch"
  - domain: theory
    usage: "Use as concrete negative evidence for the q-primary plus phi-retrofit hybrid"
  - domain: code
    usage: "Use before promoting screened q/phi rebuild code to runtime"
compiled_by: ResearchArchitect
compiled_at: 2026-05-17
---

# Capillary Runtime Baseline and Screened Graph-q Failure

## Knowledge Card

This card preserves the concrete experiment knowledge from the unmerged branch
`codex/ra-ch14-osc-droplet-eighth-20260516`, where the original local card was
`WIKI-E-085`.  That branch may be discarded, so this main-side `WIKI-E-064`
keeps the facts without merging the unfinished runtime implementation.

The durable finding is two-sided:

```text
default GPU capillary-wave baseline: admitted short probe
screened graph-q runtime rebuild: fail-closed under strict q/phi tolerance
```

The failure is useful negative knowledge.  It rejects the simple idea that a
standalone smooth screened q/phi projection can be wired directly into the Ch14
runtime graph rebuild.

## Baseline Probe

Remote command:

```text
make cycle EXP=experiment/ch14/diagnose_capillary_direction.py ARGS='--config experiment/ch14/config/ch14_capillary.yaml --steps 2 --print-every 1 --plot-pdf experiment/ch14/results/capillary_direction_baseline.pdf'
```

Result: PASS.  The run reached step 2 and pulled the visualization PDF
`experiment/ch14/results/capillary_direction_baseline.pdf`.

Sampled values from the source branch artifact:

| Step | t | raw_accel_cos | balanced_accel_cos | compat_linf |
|---|---:|---:|---:|---:|
| 1 | `3.651782879273e-05` | `2.753533350606e+01` | `-2.753533350606e+01` | `0` |
| 2 | `5.575430939397e-05` | `-2.808607486070e+01` | `2.808607486070e+01` | `0` |

Reading: the admitted baseline remains useful as a regression control, but its
`compat_linf=0` must not be overread as proof that pre-rebuild transported `q`
is being preserved by a general q/phi projector.  [[WIKI-T-174]] records why
this can hide state-ownership ambiguity.

## Screened Graph-q Runtime Probe

Remote command:

```text
make cycle EXP=experiment/ch14/diagnose_capillary_direction.py ARGS='--config experiment/ch14/config/ch14_capillary.yaml --steps 2 --screened-q-phi-rebuild --print-every 1 --plot-pdf experiment/ch14/results/capillary_direction_screened_q_phi.pdf'
```

Result: FAIL before step 1 admission under the strict tolerance contract:

```text
GPU active q/phi compatibility projection did not converge; final residual 1.630e-08 exceeds tolerance 1.000e-11
```

Exploratory probes beyond that fail-close exposed the same chain:

1. Graph-gauge seed to transported `q` can require a topology-moving update,
   so fixed-sign screened projection is insufficient.
2. Active-set refresh can expose redundant periodic quotient Schur rows; those
   must be treated as consistent singular constraints, not as physical failure.
3. A loose topology carrier can still fail the nonlinear line search before
   reaching the hard `Q_h(phi)=q` tolerance.

The loose predictor path was not promoted.  Tolerance weakening is not an
admissible remedy.

## Practice

Do not promote a screened graph-q runtime rebuild merely because a standalone
closed-droplet or capillary-wave q/phi projection looks smooth.  Runtime graph
rebuild is at least the nonlinear constrained problem:

```text
min ||phi - phi_graph||^2_{M_ell} subject to Q_h(phi)=q_T
```

and [[WIKI-T-174]] says even that formulation must be subordinate to the larger
state-ownership decision: either interface configuration `Gamma_h` is primary
and `q=Q_h(Gamma_h)` is derived, or `q` is primary and capillary energy must be
defined directly in q-space.

## Negative Knowledge to Preserve

- The screened graph-q runtime route is not admitted on the extracted evidence.
- The failure is no longer explained by only a periodic seam bug.
- Hard residual failure must not be converted into looser tolerance.
- Line-search failure must not be hidden by rebuild skipping.
- A smooth plot is not enough; pre/post q, `Q_h(phi)`, symmetry, and energy
  must be checked before a long T/8 run.
