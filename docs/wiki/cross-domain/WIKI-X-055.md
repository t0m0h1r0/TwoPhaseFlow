---
ref_id: WIKI-X-055
title: "Theory-First Deliberation Best Practices"
domain: cross-domain
status: ACTIVE
tags: [deliberation, rca, hypothesis_design, falsification, experiment_planning, implementation_review, theory_first]
sources:
  - path: docs/wiki/cross-domain/WIKI-X-051.md
    description: "Mandatory theory-first RCA and countermeasure protocol"
  - path: docs/wiki/cross-domain/WIKI-X-054.md
    description: "Ch14 active-geometry capillary session synthesis"
  - path: docs/wiki/code/WIKI-L-046.md
    description: "Theory-established implementation review gate"
  - path: docs/02_ACTIVE_LEDGER.md
    description: "Long-session record of repeated hypothesis/falsification, redesign, implementation, and paper-update loops"
depends_on:
  - "[[WIKI-X-051]]"
  - "[[WIKI-X-054]]"
  - "[[WIKI-L-046]]"
consumers:
  - domain: code
    usage: "Use before implementing a fix after ambiguous or repeated failures"
  - domain: experiment
    usage: "Use before choosing whether to rerun long experiments or add short diagnostic probes"
  - domain: paper
    usage: "Use before converting trial results into chapter claims"
compiled_by: ResearchArchitect
compiled_at: 2026-05-16
---

# Theory-First Deliberation Best Practices

## Knowledge Card

The best deliberation pattern from the Chapter 14 active-geometry capillary
session is:

```text
Symptom
  -> violated physical/mathematical contract
  -> broad hypothesis matrix
  -> discriminating probes
  -> falsified shortcuts and supported root cause
  -> multiple contract-restoring remedies
  -> smallest implementation
  -> component gate
  -> integration gate
  -> paper/wiki update
```

Do not jump from symptom to patch.  The fastest route was repeatedly the one
that spent a short time writing the hypothesis table and then chose the
smallest probe that could kill several hypotheses at once.

## Best Practices

### 1. Convert the Symptom Into a Contract Question

Bad starting question:

```text
How do we make the run survive?
```

Good starting questions:

```text
Which equation, invariant, space, metric, boundary condition, or time level is
being violated?
Which discrete object is the symptom measuring?
```

For example, "pressure is too high" is not a contract.  It becomes useful only
after deciding whether the pressure object is raw cell pressure, Hodge
representative, affine jump coordinate, pressure history coordinate, or plotted
absolute value.

### 2. Name the Discrete Object Before Naming the Fix

Every theory-first discussion should identify:

- object type: node, cell, face, graph height, pressure coordinate, HFE jump,
  face cochain, or scalar diagnostic;
- owner: YAML/front-door scheme, solver, grid epoch, phase state, or pressure
  runtime;
- metric: nonuniform width, face length, Hodge weight, density resistance, or
  cut-face coefficient;
- time level: predictor, pressure solve, corrector, rebuild, checkpoint, or
  plot snapshot;
- backend boundary: GPU array, CPU diagnostic, or explicit scalar report.

If these are unknown, a proposed fix is not yet meaningful.

### 3. Build the Hypothesis Matrix Before Running Long Experiments

The useful matrix columns are:

| Column | Purpose |
|---|---|
| Hypothesis | One possible contract violation |
| Theory prediction | What must happen if it is true |
| Probe | Smallest test that distinguishes it |
| Expected falsifier | Observation that kills it |
| Cost | Fast component probe, short integration run, or long benchmark |
| Verdict | supported, falsified, or still open |

Long experiments are allowed only when they answer a hypothesis that cannot be
settled by a component or short stage-chain probe.

### 4. Prefer Probes With High Discrimination

Good probes isolate a contract boundary:

- uniform vs nonuniform grid;
- static grid vs first rebuild vs moving rebuild;
- flat interface vs non-static wave;
- pressure-coordinate vs face-acceleration history;
- CPU oracle vs GPU production route;
- high-order operator vs low-order DC base;
- context present vs context absent fail-close;
- plot-only postprocessing vs raw numerical result.

A probe that only says "the full run still looks bad" is weak unless the
previous component gates are already closed.

### 5. Preserve Negative Knowledge

A falsified hypothesis is an asset.  Record it so the next session does not
repeat it.  Especially preserve rejected shortcuts:

- micro-offsets;
- CFL, damping, smoothing, curvature caps;
- extra iterations without convergence theory;
- solver-family substitution;
- hidden CPU/GPU fallback;
- disabling nonuniform grids or interface-following rebuilds;
- plotting changes that hide the measured object.

Negative knowledge belongs in the wiki even when it should not enter the paper.

### 6. Separate Diagnosis, Remedy Design, Implementation, and Paper Claims

Do not mix these phases:

1. **Diagnosis:** identify the violated contract.
2. **Remedy design:** compare multiple ways to restore it.
3. **Implementation:** apply the smallest selected remedy.
4. **Verification:** close component and integration gates.
5. **Paper update:** write only what the verified gates support.
6. **Wiki update:** preserve failed hypotheses, controls, and trial history.

The session improved once paper claims stopped being inferred directly from
Chapter 14 plots and were instead routed through U12/V11 gates.

### 7. Use Counterfactual Design Reviews

Before accepting a design, actively ask:

- What wrong route would still pass this test?
- What hidden fallback would make the result look successful?
- What producer/consumer pair is not covered?
- Does a nonuniform, periodic, wall, cut-face, or rebuild path escape?
- Does GPU optimization change ownership, metric, or synchronization order?
- Does the YAML let the user express the right choices while hiding internal
  implementation names?

This is where many "careless" implementation errors become visible before
they are coded.

### 8. Make the Exit Criteria Explicit

A deliberation loop should stop only when one of these happens:

- a root contract violation is identified and reproduced by a small probe;
- all cheap hypotheses are falsified and the next probe genuinely requires a
  longer run;
- the proposed fix would change the paper route or solver family, requiring
  explicit design approval;
- the remaining question is documentation/paper alignment rather than solver
  behavior.

Without exit criteria, repeated experiments become motion rather than progress.

## Compact Checklist

Before editing after a failure, answer:

```text
1. What contract should hold?
2. What exact discrete object violated it?
3. What hypotheses explain the violation?
4. What is the cheapest discriminating probe?
5. Which hypotheses are falsified?
6. What remedies restore the contract?
7. What shortcut remedies are forbidden?
8. What regression would have caught this?
9. What component/integration/paper gates must change?
```

If any answer is missing, continue deliberation before implementation.

