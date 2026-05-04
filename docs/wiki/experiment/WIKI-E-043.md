---
ref_id: WIKI-E-043
title: "V9 Local-Epsilon Switch Is a No-Regression Stack Diagnostic"
domain: experiment
status: ACTIVE
superseded_by: null
tags: [chapter13, v9, local_epsilon, nonuniform_grid, stack_diagnostic, no_regression]
sources:
  - path: paper/sections/13e_nonuniform_ns.tex
    description: "V9 nominal/local epsilon switch diagnostic under the §14 stack"
  - path: paper/sections/13f_error_budget.tex
    description: "V9 stack-diagnostic row in the integrated accuracy table"
depends_on:
  - "[[WIKI-T-084]]"
  - "[[WIKI-T-103]]"
  - "[[WIKI-E-040]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-04
---

# V9 Local-Epsilon Switch Diagnostic

## Knowledge Card

V9 is not a proof that local epsilon improves every non-uniform run.  It is a
no-regression switch diagnostic under the §14 operator stack: FCCD/HFE/pressure
jump PPE must remain stable when nominal/local epsilon mode is toggled.

In the current short static-droplet probe, nominal and local modes coincide in
the direct-psi/HFE reduced path, so no superiority claim is made.

## Consequences

- V9 validates stack compatibility, not broad local-epsilon optimality.
- B/C overlap means the local mode did not manifest as an independent lever in
  this probe.
- CSF-path extrapolation is forbidden.
- Moving-interface, reinitialization-active, long-time non-uniform tests remain
  additional gates.

## Paper-Derived Rule

Use V9 as a switch safety diagnostic for the target stack, not as a marketing
claim for local epsilon.
