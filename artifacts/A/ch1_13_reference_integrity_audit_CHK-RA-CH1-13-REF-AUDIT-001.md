# CHK-RA-CH1-13-REF-AUDIT-001 — Citation Integrity Audit

## Scope

User request: strictly check whether the Chapters 1--13 citation enrichment introduced or left fake references.

Worktree: `.claude/worktrees/codex-ra-ch1-13-references-20260508`
Branch: `codex/ra-ch1-13-references-20260508`

Audit target:

- All citation keys added by commit `118fae90`.
- All citation keys used by `paper/sections/{01,02,...,13}*.tex`.
- DOI-bearing bibliography entries for those keys, checked against Crossref/title metadata and targeted publisher pages where needed.

## Findings

The audit found no remaining fake citation after correction, but it did find bibliography metadata that was false or DOI-misaligned:

- `Li2022` was not a real match for its title. Its DOI resolved to Bai--Li 2022, "Simulating compressible two-phase flows with sharp-interface discontinuous Galerkin methods based on ghost fluid method and cut cell scheme", not "Fully implicit jump-condition enforcement for sharp-interface two-phase flow". Replaced the cited source with real IIM survey `Li2003IIMOverview`.
- `AlandVoigt2019` mixed the Aland--Voigt bubble benchmark title with an unrelated 2019 DOI. Renamed to `AlandVoigt2012` and corrected year/volume/pages/DOI.
- Corrected DOI or metadata mismatches for `Stetter1978`, `ChuFan1998`, `CrandallLions1983`, `DennerVanWachem2015`, `PyoShen2007`, `GuermondQuartapelle1998`, and `Roy2003`.

## Corrections

- `paper/bibliography.bib`
  - Replaced fake `Li2022` with `Li2003IIMOverview`.
  - Renamed `AlandVoigt2019` to `AlandVoigt2012`.
  - Fixed DOI/metadata mismatches for the keys listed above.
- `paper/sections/08d_bf_seven_principles.tex`
- `paper/sections/08e_fccd_bf.tex`
- `paper/sections/09b_split_ppe.tex`
  - Replaced `Li2022` citations with `Li2003IIMOverview`.
- `paper/sections/13_verification.tex`
- `paper/sections/15_conclusion.tex`
  - Replaced `AlandVoigt2019` citations with `AlandVoigt2012`.
- `artifacts/A/ch1_13_reference_survey_CHK-RA-CH1-13-REFS-001.md`
  - Updated the survey-routing note from the false Li 2022 entry to Li 2003.

## Validation

- Chapter 1--13 citation-key extraction found no stale `Li2022` or `AlandVoigt2019`.
- Automated Crossref comparison for DOI-bearing citation keys used in Chapters 1--13 returned no remaining title, volume, issue, or page mismatches.
- `git diff --check` PASS.
- `make -C paper` PASS and rebuilt `paper/main.pdf` (253 pages).
- Final `paper/main.log` scan for `Warning|Error|Undefined|undefined|Overfull|Underfull|Text page` returned no matches.

## SOLID-X

Paper/bibliography/artifact/bookkeeping only. No solver, experiment, config, or generated result behavior changed. No tested implementation deleted. No FD/WENO/PPE fallback, damping/CFL workaround, smoothing, curvature cap, benchmark branch, blanket projection, or QP-as-physics path introduced.
