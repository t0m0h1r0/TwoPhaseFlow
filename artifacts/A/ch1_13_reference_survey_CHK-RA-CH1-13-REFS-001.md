# CHK-RA-CH1-13-REFS-001 — Chapters 1--13 Reference Survey

## Scope

User request: enrich the citations in paper Chapters 1--13 through a literature survey.

Worktree: `.claude/worktrees/codex-ra-ch1-13-references-20260508`
Branch: `codex/ra-ch1-13-references-20260508`
Content commit: `118fae90` (`paper(refs): enrich ch1-13 citation grounding`)

## Survey Routing

The target was not to change the paper's mathematical claims, but to attach existing claims to the relevant literature:

- Compact/filtered finite differences: Lele 1992, Chu--Fan 1998, Gaitonde--Visbal 2000, Visbal--Gaitonde 2002.
- Balanced--Force and capillary pressure-jump treatment: Brackbill--Kothe--Zemach 1992, Fedkiw--Aslam--Merriman--Osher 1999, Kang--Fedkiw--Liu 2000, Francois et al. 2006, Popinet 2009, Denner--van Wachem 2015, LeVeque--Li 1994, Li et al. 2022.
- Projection/PPE and pressure boundary accuracy: Chorin 1968, van Kan 1986, Brown--Cortez--Minion 2001, Guermond et al. 2006, Pyo--Shen 2007.
- Nonuniform grid metric/GCL: Vinokur 1983, Thomas--Lombard 1979, Verstappen--Veldman 2003.
- Reinitialization and Eikonal primitives: Osher--Sethian 1988, Sussman et al. 1994/1999, Jiang--Peng 2000, Rouy--Tourin 1992, Sethian 1996, Zhao 2005.
- Verification and time integration: Roache 2002, Salari--Knupp 2000, Roy 2003, Shu--Osher 1988, Gottlieb--Shu 1998, Gottlieb--Shu--Tadmor 2001.

## Paper Edits

Added four bibliography entries:

- `ThomasLombard1979`
- `GaitondeVisbal2000`
- `GottliebShu1998`
- `GottliebShuTadmor2001`

Added targeted citation prose in:

- Chapter 4 fragments: `04c_dccd_derivation.tex`, `04e_fccd.tex`, `04f_face_jet.tex`
- Chapter 8 fragments: `08d_bf_seven_principles.tex`, `08e_fccd_bf.tex`
- Chapter 9 fragments: `09_ccd_poisson.tex`, `09f_pressure_summary.tex`
- Chapter 12 fragments: `12u2`, `12u3`, `12u4`, `12u6`, `12u9`, `12h_summary`
- Chapter 13 fragment: `13c_galilean_offset.tex`

Targeted audit after edits found no Chapter 1--13 section file without a `\cite`.

## Validation

- `git diff --check` PASS
- `rg --files-without-match -F "\\cite" paper/sections/01*.tex ... paper/sections/13*.tex` returned no files
- `make -C paper` PASS, rebuilt `paper/main.pdf` (253 pages)
- `rg -n "Warning|Error|Undefined|undefined|Overfull|Underfull|Text page" paper/main.log` returned no matches

## SOLID-X

Paper/bibliography only. No solver, experiment, config, or generated result behavior changed. No tested implementation deleted. No FD/WENO/PPE fallback, damping/CFL workaround, smoothing, curvature cap, benchmark branch, blanket projection, or QP-as-physics path introduced.
