# CHK-RA-APPEND-004 — Appendix necessity and consolidation review

Date: 2026-04-29
Branch/worktree: `ra-appendix-review-retry-20260429` / `.claude/worktrees/ra-appendix-review-retry-20260429`
Scope: appendix N and whole-appendix organization
Verdict: Appendix N as HFE verification was unnecessary; overall appendix hierarchy needed consolidation.

## User questions

1. Is appendix N already covered by main-body experiments, and should it remain?
2. Are other appendices candidates for consolidation or removal?
3. Is the current appendix structure acceptable?

## Findings

### A-1 Major — Appendix N duplicated main-body U6-c

- Previous appendix N was `HFE 場延長の格子収束検証`.
- Main-body §12 U6-c already contains the HFE 1D/2D MMS verification, including `tab:U6_hfe` and `fig:ch12_u6_hfe_field`.
- The appendix version also carried older numbers and the stale `hfe_convergence` figure, so keeping it created duplicate and partially obsolete evidence.

Action:
- Removed `paper/sections/appendix_hfe_verify.tex`.
- Removed unreferenced stale figure `paper/figures/hfe_convergence.pdf`.
- Replaced appendix N with `圧力ステップの実装補足`, keeping only non-experimental implementation details there.

### A-2 Major — Source comments intended appendices A--G, but actual PDF exposed A--P

- `paper/main.tex` grouped appendix inputs as A--G.
- Because subfiles used `\section`, the generated TOC expanded those groups into appendices A--P.
- This made the appendix look more fragmented than the editorial intent and obscured the logical grouping.

Action:
- Normalized appendix hierarchy so the final PDF has exactly seven top-level appendices:
  - A: nondimensionalization and curvature details
  - B: interface representation / material interpolation / CLS proofs
  - C: CCD derivation and implementation
  - D: advection and stability constraints
  - E: pressure solver and coupling analysis
  - F: bootstrap sequence
  - G: verification supplemental analysis

### A-3 Minor — One existing table became sensitive to line breaking after TOC compaction

- After appendix hierarchy compaction, the final pagination changed and one existing table cell in §4.5 triggered an underfull hbox.

Action:
- Made that local table use ragged `p{...}` columns while preserving width and content.

## Keep / consolidate decisions

- Keep appendix A: derivational support for §2; not redundant with main text.
- Keep appendix B: proof-oriented interface material; consolidated under one appendix rather than B--E.
- Keep appendix C: coefficient derivations and solver implementation notes; consolidated under one appendix rather than F--H.
- Keep appendix D: stability derivations; consolidated under one appendix rather than I--J.
- Keep appendix E: pressure/PPE/RC/BF theory and implementation details; consolidated under one appendix rather than K--N.
- Keep appendix F: bootstrap sequence; concise and distinct from §11.
- Keep appendix G: supplemental verification interpretation; no longer contains the HFE convergence duplicate.

## Validation

- Top-level appendix section count: 7.
- Final TOC appendices: A--G only.
- Removed HFE duplicate references: 0 hits for `appendix_hfe_verify`, `hfe_convergence`, `app:hfe_verify`, `tab:hfe_2d_convergence`, and `fig:hfe_convergence`.
- `git diff --check`: pass.
- `cd paper && latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex`: pass.
- Final log diagnostic count for warnings/errors/overfull/underfull/missing characters: 0.
- `paper/main.pdf`: regenerated, 226 pages.

## SOLID audit

[SOLID-X] Paper/docs-only editorial consolidation. No `src/twophase/` code, production class boundary, module boundary, or solver interface was changed.

## Commits

- `b5360a4 paper: consolidate duplicate HFE appendix`
- `877a4ef paper: normalize appendix hierarchy`
