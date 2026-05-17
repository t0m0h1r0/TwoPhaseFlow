---
ref_id: WIKI-X-056
title: "Ch14 Capillary Origin-Reset Handoff Protocol"
domain: cross-domain
status: ACTIVE
tags: [ch14, origin_reset, handoff, capillary_wave, oscillating_droplet, theory_first, oracle_first, visualization]
sources:
  - path: docs/wiki/theory/WIKI-T-174.md
    description: "State-ownership theory for the next capillary route"
  - path: docs/wiki/cross-domain/WIKI-X-055.md
    description: "Theory-first deliberation protocol"
  - path: docs/wiki/experiment/WIKI-E-063.md
    description: "Current U12/V11 AO-Fast capillary split gates on main"
  - path: artifacts/A/ch14_origin_reset_handoff_CHK-RA-CH14-ORIGIN-RESET-001.md
    description: "Extracted handoff facts, negative evidence, and next-session prompt path"
depends_on:
  - "[[WIKI-T-174]]"
  - "[[WIKI-X-055]]"
  - "[[WIKI-E-063]]"
consumers:
  - domain: management
    usage: "Use to start a separate origin-reset session without importing failed implementation momentum"
  - domain: theory
    usage: "Use to keep state ownership, chart choice, and oracle acceptance explicit"
  - domain: experiment
    usage: "Use to require short visualized probes before long T/8 runs"
compiled_by: ResearchArchitect
compiled_at: 2026-05-17
---

# Ch14 Capillary Origin-Reset Handoff Protocol

## Knowledge Card

The next session should not resume by asking how to make the screened q/phi
runtime projection converge.  It should start from the capillary variational
problem and decide which discrete state owns the interface.  The previous
branch is valuable as negative evidence, but its implementation route should
not become the default assumption.

The handoff order is:

```text
1. Read WIKI-T-174, WIKI-X-055, and this card.
2. Treat branch codex/ra-ch14-osc-droplet-eighth-20260516 as evidence, not as
   mandatory implementation direction.
3. Choose the owned state: interface configuration Gamma_h or cell volume q.
4. Build the smallest capillary-wave oracle for that choice.
5. Visualize every oracle and short runtime probe.
6. Only then connect the route to Ch14 runtime and T/8 droplet experiments.
```

## Facts to Preserve

- A short GPU capillary-wave baseline probe on the oscillating-droplet branch
  passed and produced a PDF visualization.
- The screened graph-q runtime route failed under the hard q/phi compatibility
  tolerance while forming the topology carrier.
- Later exploratory probes showed topology movement, redundant periodic
  quotient constraints, and nonlinear line-search failure.
- Loose predictor tolerances were not promoted and must not be treated as a
  solution.
- The observed symptoms are consistent with a state-ownership mismatch: a
  transported `q` field may contain modes that are not representable by the
  chosen smooth graph/phi chart.

## Required Next-Session Deliverables

| Deliverable | Acceptance Rule |
|---|---|
| State ownership statement | Names `Gamma_h` or `q` as the owned object and derives the other as dependent. |
| Hypothesis matrix | Includes incompatible-q, q erasure, chart mismatch, metric mismatch, energy/transport split, and topology movement hypotheses. |
| Capillary-wave oracle | Gives force sign, symmetry, energy, and mode/phase diagnostics before runtime integration. |
| Closed-droplet chart plan | Uses the same variational principle as the capillary-wave chart. |
| Visualization | Produces plots for q, interface geometry, force/acceleration mode, energy, and symmetry residuals by default. |
| Runtime gate | Runs only after the oracle passes; failures are interpreted through the hypothesis matrix. |
| Wiki/artifact update | Preserves both positive results and falsified shortcuts. |

## Stop Conditions

Stop and redesign, rather than continuing implementation, when:

- no one can say whether `q` or `Gamma_h` owns the capillary state;
- a fix depends on tolerance weakening, smoothing, damping, CFL retuning, or
  rebuild skipping;
- the capillary-wave chart and closed-droplet chart use unrelated theory;
- a plot looks good but pre/post q, energy, and symmetry checks disagree;
- a long T/8 run is proposed before a small oracle closes the force/energy
  direction.

## Prompt Location

Use `docs/memo/ch14_origin_reset_next_session_prompt.md` as the starting prompt
for a separate ResearchArchitect session.
