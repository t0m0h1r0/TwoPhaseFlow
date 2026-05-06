# CHK-RA-CH1-001 — Chapter 1 Strict Narrative Review

Date: 2026-05-06
Worktree: `.claude/worktrees/ra-ch1-narrative-review-20260506`
Branch: `ra-ch1-narrative-review-20260506`
Scope: `paper/sections/01_introduction.tex`, `paper/sections/01b_classification_roadmap.tex`

## Round 1 Verdict: FAIL

MAJOR-1 — Chapter 1 opened with too much downstream verification bookkeeping before the thesis was stable.
The first page mixed the paper's central claim, validation limits, future gates, CCD caveats, and glossary routing in one block. The result was technically dense but narratively unconvincing: the reader could not cleanly see that the chapter's root problem is face-space consistency across interface, pressure, force, and transport.

MAJOR-2 — Latest V7 result was stale in Chapter 1.
Chapter 1 reported V7 coupled-stack slope `1.48`, while the current Chapter 13 result is `1.59`. Because the introduction states the paper's present validated scope, this was a major currency and consistency error.

MAJOR-3 — DGR was still presented as part of the standard Chapter 5 path.
The chapter overview described "DGR band thickness correction" as if it were a standard method component. Current Chapter 5 defines DGR as diagnostic/comparison-only; the standard path is Ridge--Eikonal distance reconstruction plus Stage F volume closure.

MAJOR-4 — Roadmap voice and benchmark wording still carried draft/test language.
"Bridge textbook", "undergraduate implementation", and "Rayleigh--Taylor smoke" lowered the paper voice and blurred the distinction between verified research content and development/testing vocabulary.

MINOR-1 — The method comparison table overclaimed CLS shape sharpness.
The prose did not separate mass conservation from shape accuracy, despite V10 shape axes being Type-D / conditional.

MINOR-2 — The algorithm figure caption mentioned pressure-jump face data, but the diagram only showed curvature coupling.

## Round 1 Response

- Rewrote the opening thesis around one contract: interface position, material jumps, surface tension, pressure projection, velocity correction, and interface transport must close on the same face-space structure.
- Updated V7 to the current `1.59` slope and framed it as a coupled-stack result limited by capillary pressure-jump/projection interface-band error.
- Replaced DGR-as-standard wording with Ridge--Eikonal + Stage F as standard, and DGR as diagnostic positioning only.
- Removed draft/test voice from Chapter 1: no "教材", "学部生", "smoke", "future verification gate", or stale version-change language remains in the chapter.
- Added the mass/shape-axis distinction for CLS and changed table shape sharpness to conditional.
- Updated the algorithm figure to show pressure-jump face data flow (`J_p, a_f`) into PPE.

## Round 2 Verdict: FAIL (MINOR only)

No MAJOR+ findings remained. One minor presentation issue remained: the figure still underrepresented pressure-jump data flow after the prose fix.

## Round 2 Response

Added the missing `J_p, a_f` cross-system arrow and softened the CLS shape-sharpness table entry from "優" to "可--優".

## Round 3 Verdict: PASS

MAJOR+ findings: 0.

Validation:
- `git diff --check` PASS.
- Targeted Chapter 1 terminology scan PASS: stale `1.48`, `smoke`, `教材`, `学部生`, `future verification gate`, `DGR バンド厚補正`, `再初期化 PDE`, `物理的下限`, draft/version-change vocabulary absent.
- `make -C paper` PASS, producing `paper/main.pdf` (245 pages).
- `paper/main.log` scan PASS: no fatal/error/undefined-control/undefined-reference/overfull hits in the targeted scan.

[SOLID-X] Paper/docs only; no `src/twophase/`, experiment script, config, or result file changed. No tested implementation deleted. No FD/WENO/PPE fallback or alternate pressure scheme introduced.
