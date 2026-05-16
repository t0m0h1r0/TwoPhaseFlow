# CHK-RA-CH1-14P2-001 Review Artifact

## Scope

- Target: manuscript body through §14.2.
- Included files: `paper/sections/00_abstract.tex`, Chapter 1--13 section files, `paper/sections/14_benchmarks.tex`, `paper/sections/14a_capillary_wave.tex`, and `paper/sections/14b_oscillating_droplet.tex`.
- Surrounding check: `paper/main.tex` input order, Chapter 12/13 sub-inputs, `docs/01_PROJECT_MAP.md` paper section map, box usage, major citation placement, visible stale/implementation terms, and split-prefix consistency.
- Worktree: `.claude/worktrees/codex-ra-paper-review-ch1-14p2-20260516`.
- Branch: `codex/ra-paper-review-ch1-14p2-20260516`.
- id_prefix: `RA-CH1-14P2`.

## Review Units and Rounds

| Unit | Files | Rounds | Result |
|---|---|---:|---|
| Front matter + Chapter 1 | `00_abstract`, `01_introduction`, `01b_classification_roadmap` | 2 | PASS, MAJOR+ 0 |
| Chapters 2--3 | governing equations, surface tension, nondimensionalization, CLS and Ridge--Eikonal files | 1 | PASS, MAJOR+ 0 |
| Chapters 4--6 | CCD family, reinitialization, per-variable spatial schemes | 1 | PASS, MAJOR+ 0 |
| Chapters 7--9 | time integration, BF, split PPE/HFE/DC/capillary work state | 2 | PASS, MAJOR+ 0 |
| Chapters 10--11 | grid, full algorithm, state contracts, active-geometry capillary state space | 2 | PASS, MAJOR+ 0 |
| Chapters 12--13 | component verification and integrated verification | 2 | PASS, MAJOR+ 0 |
| Chapter 14 through §14.2 | benchmark common setup, capillary wave, oscillating droplet | 2 | PASS, MAJOR+ 0 |
| Whole target scope | 00 through §14.2, map/box/citation/prefix consistency | 2 | PASS, MAJOR+ 0 |

No unit reached the 20-round cap.  No BLOCKER or MAJOR finding remains after the recorded fixes.

## Initial Inventory

### Structure and Inputs

- `paper/main.tex` inputs the target in the order `00`, `01`, `01b`, `02*`, `03*`, `04*`, `05*`, `06*`, `07*`, `08*`, `09*`, `10*`, `11*`, `12_component_verification`, `13_verification`, `14_benchmarks`, `14a_capillary_wave`, `14b_oscillating_droplet`.
- Chapter 12 expands through `12u1`--`12u12` and `12h_summary`.
- Chapter 13 expands through `13a`--`13d`, `13e1`, `13e2`, and `13f`.
- `docs/01_PROJECT_MAP.md` had stale paper section rows: missing `03d`, `05a`, `07b`--`07d`, `11e`, and the `14a`--`14e` split family.  Fixed in this task.

### File Responsibility and Split Decision

- Largest target files remain within the recent split policy: `09b4_capillary_work_state.tex` (538 lines), `07_time_integration.tex` (504), `11e_ao_fast_state_space.tex` (442), `10d_ridge_eikonal_nonuniform.tex` (425), `01b_classification_roadmap.tex` (394), `01_introduction.tex` (381).
- No new split was made.  The only file above 500 lines, `09b4_capillary_work_state.tex`, is a tightly coupled variational capillary-work/state-space derivation; splitting it would force the reader to chase one pressure/work object across files.
- Prefix families are consistent: `09b1`--`09b4`, `10a1`--`10a2`, `11b1`--`11b2`, `12u1`--`12u12`, `13e1`--`13e2`, and `14a`--`14e`.

### Box Audit

Target-scope scan found 37 `tcolorbox` entries.  They are retained because they function as short definitions, warnings, algorithm summaries, result summaries, or acceptance criteria:

- Definition/role boxes: §2 variable/sign convention, §3 ψ--φ mapping, §7 common-flux time order, §11 ledger model.
- Warning boxes: §4 boundary scheme, §6 FCCD/TVD-RK3 CFL, §7 TVD-RK3 and startup, §8/§9 BF/PPE non-claims, §10 nonuniform-grid constraints.
- Algorithm boxes: §4 DCCD filter, §5 Ridge--Eikonal/ξ-SDF procedures.
- Result/summary boxes: §3 direct-curvature result, §4 accuracy vs spurious currents, §9 pressure-closure choice, §12 U1--U12 summary.

No box was converted or removed in this task; the current remaining boxes are purposeful after the prior box audit pass.

### Citation Review

- No new bibliography entry was added.
- Prior source-verified citation survey `artifacts/A/review_CHK-RA-CITE-SURVEY-001.md` already added claim-local sources for CLS/reinitialization, high-order compact CLS, balanced-force level-set positioning, consistent mass-momentum transport, and variable-density pressure-correction positioning.
- Current claim sites through §14.2 are adequately supported by the existing primary sources: Prosperetti for capillary-wave/Rayleigh--Lamb phase clocks, Brackbill/Francois/Popinet/Denner--van Wachem for CSF/BF/spurious-current context, Chorin/van Kan/Guermond/Brown--Cortez--Minion/Pyo--Shen for projection/PPE pressure context, Olsson--Kreiss/Zahedi and CCLS neighbors for CLS, and Hysing/Aland--Voigt etc. in the verification/benchmark context.
- Because no missing claim-local citation was found, no web/source verification was required during this pass.

## Findings and Fixes

### MAJOR-1: Static-droplet responsibility was inconsistent between Chapter 13 and Chapter 14

- Evidence: `paper/sections/13b_twophase_static.tex` said the V3 standard static droplet judgment used "the same Chapter 14 static droplet setting", while §14 explicitly says static circular droplets are handled in Chapter 13 and not duplicated.
- Risk: readers could think a Chapter 14 static benchmark still exists or that V3 is a duplicate of a missing benchmark.
- Fix: rewrote the V3 bridge so it says Chapter 13 absorbs the static-equilibrium pressure-jump auxiliary diagnostic to keep Chapter 14 focused on finite interface motion.

### MAJOR-2: §14.2 mixed a failed benchmark conclusion with implementation/run jargon

- Evidence: §14.2 used phrases such as `production-stack static gate`, `pressure-jump 仕事`, `periodic/interface-fitted`, `CFL multiplier`, `snapshot field`, `run`, `volume gate`, `saved snapshot`, `transport/dynamic grid rebuild/remap/profile retraction`, `bounded run`, and `P1 area`.
- Risk: the section's important conclusion is not a success claim; it is a clear non-acceptance result for one-period closed-interface volume.  Implementation-flavored words made that conclusion harder to read.
- Fix: replaced visible jargon with reader-facing Japanese, explained the Rayleigh--Lamb formula as capillary stiffness over effective inertia, and made the failed conservation judgment explicit as "finite and bounded, but not accepted".

### MAJOR-3: Current file map did not match the actual split structure

- Evidence: `docs/01_PROJECT_MAP.md` omitted `03d_ridge_eikonal`, `05a_ridge_eikonal_details`, `07b`--`07d`, `11e_ao_fast_state_space`, and the `14a`--`14e` split family.  The §14 description still referenced an older benchmark set.
- Risk: future reviewers could inspect the wrong files or miss the active-geometry and benchmark split responsibilities.
- Fix: updated the map rows to match the current `paper/main.tex` and nested Chapter 12/13 input structure.

### MINOR/NIT Cleanup

- Replaced `sub-system`, visible `cochain` fragments, `active 面計量`, and several English/jargon residues with Japanese equivalents where they appeared in reader-facing prose.
- Added a short physical reading of the capillary-wave dispersion relation: numerator as capillary stiffness, denominator as effective two-phase inertia.
- Reframed abstract/summary wording so Chapter 14 is described as applying the standard configuration and recording remaining limitations, not as a blanket success claim.

## Formula-Readability Review

- Chapters 2--3 already include "本章の数式の読み方" and separate transported state (`ψ`) from geometric measurement (`φ`, normals, curvature).
- Chapters 7--9 already route formula blocks through constraint/work quantities: pressure reaction, capillary work, HFE, DC residual, and diagnostic Hodge residuals.  The review fixed only terminology where English fragments interrupted that reading.
- Chapter 11 already frames the full algorithm as ledgers for interface, momentum, and pressure/work.  The review kept this structure and clarified the visible "cochain" terms.
- §14.1 and §14.2 now tell the reader how to read the two key benchmark formulas before presenting diagnostics: capillary wave and Rayleigh--Lamb are phase clocks and force-direction/inertia checks, not exact amplitude-return demands.

## Validation

Final validation:

- `git diff --check` — PASS.
- `make -B -C paper` — PASS; `paper/main.pdf` regenerated at 279 pages.
- Final `paper/main.log` diagnostic scan — PASS; no LaTeX/package/class warnings, undefined references/citations/control sequences, overfull/underfull boxes, fatal errors, emergency stops, or raw TeX errors were found.
- Target-scope stale-term/map scan through §14.2 plus `docs/01_PROJECT_MAP.md` — PASS for the reviewed terms: `production-stack`, `sub-system`, `projection-native`, `face-space`, `CFL multiplier`, `bounded run`, `saved snapshot`, `dynamic grid rebuild`, `profile retraction`, `pressure-jump 仕事`, `interface-fitted`, `profile restoration`, `active 面`, `sharp volume`, `sharp-corner`, `shape L1`, `folded filament`, and `3452 samples`.

## Commits

- `a19c5ea1` — `docs: start ch1-14p2 paper review worktree`
- `e0b643f0` — `paper: clarify ch1-14p2 review prose`
- final closure commit — `docs: close ch1-14p2 paper review`
