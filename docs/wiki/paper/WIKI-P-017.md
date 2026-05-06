---
ref_id: WIKI-P-017
title: "Paper Build Hygiene: Zero-Warning Float Placement"
domain: paper
status: ACTIVE
superseded_by: null
tags: [paper, latex, build_hygiene, float_placement, warning_free]
sources:
  - path: paper/sections/12u7_bf_static_droplet.tex
    description: "U7 float placement fix for CHK-RA-PAPER-TEX-ZERO-001"
  - path: paper/main.log
    description: "Validated warning-free LaTeX build log after the fix"
  - path: docs/00_GLOBAL_RULES.md
    description: "KL-12 caption/heading math pre-compile scan rule"
  - path: docs/wiki/cross-domain/WIKI-X-041.md
    description: "Active retrieval gate for distinguishing current paper contracts from historical notes"
depends_on:
  - "[[WIKI-X-041]]"
  - "[[WIKI-P-015]]"
  - "[[WIKI-P-016]]"
consumers:
  - domain: paper
    usage: "Use before treating float-only page warnings as harmless residuals"
compiled_by: ResearchArchitect
compiled_at: 2026-05-06
---

# Paper Build Hygiene

## Knowledge Card

A warning-free paper build is part of the paper contract.  The recurring
`Text page ... contains only floats` warning can appear when several adjacent
tables/figures are constrained to `[!ht]`: LaTeX has too little placement
freedom, so it emits a text-page warning even though the content is purely
float material.

For clustered validation tables and figures, prefer widening the placement
specifier to `[!htbp]` on the affected floats before adding manual page breaks.
This preserves the section narrative and lets LaTeX choose a proper float page.

## Validated Instance

In CHK-RA-PAPER-TEX-ZERO-001, §12 U7 contained four consecutive floats:

- U7-a pressure-jump table;
- U7-b face-viscosity interpolation table;
- U7 summary figure;
- U7 parasitic-vortex figure.

Changing those four environments from `[!ht]` to `[!htbp]` removed the sole
remaining warning while preserving page count and manuscript content.

The same pass also made all caption math KL-12-clean by wrapping PDF-string
sensitive math fragments with `\texorpdfstring{...}{...}`.  This leaves printed
captions unchanged while making the pre-compile scan silent.

## Retrieval Rule

When TeX emits float-only page warnings, inspect the local float cluster first.
If the floats are semantically tied to one verification subsection, broaden
their placement with `p` before moving text, inserting `\clearpage`, or changing
the scientific wording.

For captions or headings with math, preserve the printed expression and add a
plain-text PDF-string fallback through `\texorpdfstring`.
