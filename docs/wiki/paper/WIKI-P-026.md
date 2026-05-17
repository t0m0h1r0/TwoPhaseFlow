---
ref_id: WIKI-P-026
title: "Paper Reviews Must Separate Reduced Diagnostics From Standard Execution Claims"
domain: paper
status: ACTIVE
tags: [paper_review, narrative, phase_region, benchmark_claims, terminology]
sources:
  - path: artifacts/A/review_CHK-RA-PAPER-COVER-14P2-002.md
    description: "Cover-through-14.2 strict review record"
  - path: paper/sections/00_abstract.tex
    description: "Front-matter benchmark claim boundary"
  - path: paper/sections/11e_ao_fast_state_space.tex
    description: "PhaseRegion owner/measure/chart adoption boundary"
  - path: paper/sections/13e2_ao_capillary_split_gate.tex
    description: "V11 integration gate"
  - path: paper/sections/14_benchmarks.tex
    description: "Chapter 14 benchmark reading frame"
  - path: paper/sections/14a_capillary_wave.tex
    description: "Reduced capillary-wave chart diagnostic"
  - path: paper/sections/14b_oscillating_droplet.tex
    description: "Closed-chart short-time pass and one-period standard-execution boundary"
depends_on:
  - "[[WIKI-P-019]]"
  - "[[WIKI-P-021]]"
  - "[[WIKI-P-022]]"
  - "[[WIKI-P-023]]"
  - "[[WIKI-P-025]]"
consumers:
  - domain: paper
    usage: "Use before broad paper review after adding reduced diagnostics or route-boundary evidence"
compiled_by: ResearchArchitect
compiled_at: 2026-05-17
---

# Paper Reviews Must Separate Reduced Diagnostics From Standard Execution Claims

## Knowledge Card

When a new reduced diagnostic is added to the manuscript, front matter must not
summarize it as if it were already part of the same standard pressure/velocity
execution path.  The paper should keep three claims separate:

1. What the reduced diagnostic proves.
2. What the standard execution path proves.
3. What remains unconnected or unaccepted.

For the Chapter 14 PhaseRegion update, the safe narrative is:

- PhaseRegion graph/closed-curve chart diagnostics show owner/measure/energy
  consistency for capillary restoration.
- Force coupling into PPE and velocity correction remains a distinct adoption
  boundary.
- The one-period oscillating droplet standard execution is finite but not an
  accepted closed-interface volume result.

## Review Gate

Before closing a broad paper review after benchmark or route evidence changes:

- Scan the abstract and roadmap for over-broad phrases such as "same standard
  configuration" when the evidence mixes reduced diagnostics and standard
  execution.
- In every formula-heavy section, verify that the prose states which object
  owns the state, which quantity is measured, which quantity is transported or
  updated, which pressure/work/force object is being constrained, and which
  diagnostic is used for acceptance.
- Treat implementation keys and route-management words as paper smells unless
  they are the actual reproducibility object being documented.
- Keep exact config or code keys only when the paper reader needs them, and
  attach a Japanese explanation next to the key.

## Terminology Gate

Use reader-facing terms in visible prose:

- `グラフチャート`, `閉曲線チャート`, `ゲージ`, `境界アトラス`
- `標準実行経路`, `採用境界`, `不合格として停止`
- `面量`, `射影後の面履歴`, `力連成未接続`

Avoid leaving unexplained English route terms such as `production runtime`,
`fail-close`, `admission gate`, `graph chart`, or `force-admission` in
manuscript prose.

## Validation Gate

For a paper-only review closure, run:

```text
git diff --check
make -B -C paper
rg -n -e 'LaTeX Warning' -e 'Package .* Warning' -e 'Overfull \\hbox' \
  -e 'Underfull \\hbox' -e 'Missing character' \
  -e 'Undefined control sequence' -e 'Emergency stop' -e 'Fatal error' \
  -e 'LaTeX Error' -e 'Citation .* undefined' -e 'Reference .* undefined' \
  paper/main.log
```

The log scan should return no matches.
