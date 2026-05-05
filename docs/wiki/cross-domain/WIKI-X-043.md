---
ref_id: WIKI-X-043
title: "RCA Artifacts Falsify Shortcuts Before Authorizing Fixes"
domain: cross-domain
status: ACTIVE
superseded_by: null
tags: [rca, negative_evidence, root_cause, ch14, tuning, diagnostics]
sources:
  - path: artifacts/A/ch14_problem_shortcut_hypotheses_n64_CHK-RA-OSC-N64-013.md
    description: "Problem-shortcut hypothesis map for N64 static droplet"
  - path: docs/memo/CHK-RA-CAPWAVE-N32T8-RCA-001.md
    description: "Capillary-wave N32 T8 RCA and theory-first next gates"
  - path: artifacts/A/ch14_oriented_interface_stress_design_CHK-RA-CH14-012.md
    description: "No shortcut list for oriented interface-stress redesign"
depends_on:
  - "[[WIKI-X-039]]"
  - "[[WIKI-X-040]]"
  - "[[WIKI-X-042]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-05
---

# RCA Shortcut Discipline

## Knowledge Card

RCA artifacts are not tuning menus.  They are falsification ledgers.  A proposed
fix is admissible only if it restores a violated mathematical contract, not
merely if it improves a plot, kinetic energy trace, or short-run survival.

For capillary/interface failures, the repeated pattern is:

```text
state the equilibrium or energy identity
list plausible shortcuts
falsify symptom-only explanations
keep negative evidence
promote only contract-restoring fixes
```

## Consequences

- Smaller `dt`, stronger smoothing, lower curvature cap, and alpha tuning are
  not root fixes unless they restore a named invariant.
- Diagnostics may isolate a causal link without becoming production code.
- Falsified hypotheses should remain indexed so the same shortcut is not
  rediscovered.
- A pass on static/manufactured algebra is insufficient when the dynamic energy
  or transport loop still creates work.

## Paper-Derived Rule

Before editing solver behavior, require the RCA artifact to name the invariant
being restored and the shortcuts already falsified.
