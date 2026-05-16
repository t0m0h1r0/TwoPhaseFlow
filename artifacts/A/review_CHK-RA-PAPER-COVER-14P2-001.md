# CHK-RA-PAPER-COVER-14P2-001 Review Record

## Scope

- Target: cover/front matter through Chapter 14 section 14.2.
- Included files: `paper/sections/00_abstract.tex`, Chapter 1--13 section files, `paper/sections/14_benchmarks.tex`, `paper/sections/14a_capillary_wave.tex`, and `paper/sections/14b_oscillating_droplet.tex`.
- Context checked: `paper/main.tex` input order, Chapter 12/13 nested inputs, prior whole-scope review artifacts, box usage, visible stale terms, citation placement, split-prefix families, and final paper build.
- Additional gate requested in this task: for each item, ask whether it belongs in the current chapter/section, another chapter, a box/table/note, an artifact/wiki, or outside the paper body.

## Initial Inventory

### Structure and Input Order

- `paper/main.tex` places the target as `00_abstract`, `01`, `01b`, `02*`, `03*`, `04*`, `05*`, `06*`, `07*`, `08*`, `09*`, `10*`, `11*`, `12_component_verification`, `13_verification`, `14_benchmarks`, `14a_capillary_wave`, and `14b_oscillating_droplet`.
- Chapter 12 expands through `12u1`--`12u12` plus `12h_summary`; Chapter 13 expands through `13a`--`13f`.
- The build still includes §14.3 onward and appendices, so validation was run on the full paper even though the review target ends at §14.2.

### File Responsibility and Split Decision

- No new split was made. The current target split families remain coherent: `09b1`--`09b4`, `10a1`--`10a2`, `11b1`--`11b2`, `12u1`--`12u12`, `13e1`--`13e2`, and `14a`--`14e`.
- The only large target files remain intentional derivation or synthesis files. Splitting them in this task would not reduce reader load because the problem found here was placement and visible terminology, not mixed file ownership.

### Box Audit

- The cover/front-matter box was re-opened because the new placement gate showed it was acting as a technical dashboard before the reader had entered the paper.
- Other target boxes were retained. Prior box audits and the current scan showed they function as definitions, warnings, algorithm summaries, or result summaries rather than decoration.
- The cover box is still retained, but its function is now a short reader orientation: the question the paper answers and the reading spine. Detailed scheme lists, measured rates, Type labels, and benchmark outcomes are left to the abstract and body.

### Citation Review

- No bibliography entry was added.
- No new claim-local citation gap was found. Existing claim sites near the target claims remain supported by the prior verified citation set: Prosperetti for capillary clocks, Brackbill/Francois/Popinet/Denner--van Wachem for CSF/BF/spurious-current context, Chorin/van Kan/Guermond/Brown--Cortez--Minion/Pyo--Shen for projection/PPE pressure context, Olsson--Kreiss/Zahedi for CLS, and Hysing/Aland--Voigt/Chandrasekhar/Tryggvason in later benchmark context.

## Findings and Fixes

### MAJOR-1: The cover carried body-level implementation and result details

- Evidence: `00_abstract.tex` title page had a dense table listing FCCD/CCD/UCCD6/DCCD, time schemes, pressure closure, measured rates, Type-D labels, and Chapter 14 outcomes.
- Placement issue: a cover should orient the reader to the research question and reading spine. Detailed scheme inventory belongs in the abstract, roadmap, method chapters, or verification chapters.
- Fix: replaced the technical table with a short statement of the question and reading spine: what interface quantity is preserved, which face position closes pressure/capillary/velocity correction, and how component/integrated/benchmark evidence separates achieved range from remaining limitations.
- Re-review: PASS. The cover now helps entry into the paper without preloading §9/§11/§13/§14 details.

### MAJOR-2: Abstract and benchmark sections still exposed internal gate vocabulary

- Evidence: visible prose used terms such as `投影済み面共鎖`, `Hodge 計量`, `標準物理経路`, and `未受理` in front matter or benchmark-facing text.
- Placement issue: the underlying mathematical objects belong in §11/§13 derivation and verification gates. The abstract and §14 benchmark prose should describe the reader-visible object as a face quantity, face flux, accepted boundary, or standard configuration.
- Fix: rewrote these expressions as `射影後の面フラックス量`, `格子再構築後も同じ仕事量`, `標準構成`, `採用条件を満たさない`, and `移動格子で保存する面量`.
- Re-review: PASS. Target-scope visible-term scans no longer find the implementation-facing wording.

### MINOR-1: §14 pressure graphics wording was over-specific

- Evidence: §14.1 used `圧力 Hodge 代表` in captions and surrounding text.
- Placement issue: Hodge construction is already defined in the method/verification chapters; §14 readers need to know that the plotted pressure is a representative pressure difference, not absolute pressure.
- Fix: reduced the figure caption and local prose to `圧力代表` while keeping the explanatory sentence that absolute pressure is not the plotted diagnostic.
- Re-review: PASS.

## Review Units and Rounds

| Unit | Rounds | Result |
|---|---:|---|
| Cover/front matter and abstract | 3 | PASS, MAJOR+ 0 |
| Chapter 1 introduction and roadmap | 2 | PASS, MAJOR+ 0 |
| Chapters 2--3 governing equations, surface tension, CLS | 1 | PASS, MAJOR+ 0 |
| Chapters 4--6 CCD, reinitialization, per-term spatial schemes | 1 | PASS, MAJOR+ 0 |
| Chapters 7--9 time integration, BF, PPE/HFE/DC/capillary work | 1 | PASS, MAJOR+ 0 |
| Chapters 10--11 grid, full algorithm, active-geometry state space | 1 | PASS, MAJOR+ 0 |
| Chapters 12--13 component and integrated verification | 2 | PASS, MAJOR+ 0 |
| Chapter 14 through §14.2 | 3 | PASS, MAJOR+ 0 |
| Part-level pass: methods to verification to benchmarks | 2 | PASS, MAJOR+ 0 |
| Whole target-scope pass | 2 | PASS, MAJOR+ 0 |

No unit reached the 20-round cap.

## Formula-Readability and Placement Result

- Front matter now gives the reader the research question before method inventory.
- Abstract still carries the main achieved/remaining outcomes, but removes local verification labels that are defined only later.
- §12/§13 keep the adoption-boundary language because those chapters are verification gates.
- §14 keeps formula-reading prose for capillary wave and Rayleigh--Lamb droplet, but no longer exposes `面共鎖` terminology in benchmark-facing prose.

## File Split, Prefix, Box, and Citation Decisions

- File split: none.
- Prefix normalization: none needed.
- Box changes: cover box retained but rewritten; no target body box removed.
- Citation additions: none.

## Validation

- `git diff --check` — PASS.
- Target visible-term scan — PASS for `投影済み面共鎖`, `面共鎖`, `Hodge 計量`, `標準物理経路`, `未受理`, `projection-native`, `face-space`, `production-stack`, and `solver-option`.
- `make -B -C paper` — PASS; `paper/main.pdf` regenerated at 279 pages.
- Final `paper/main.log` diagnostic scan — PASS; no LaTeX warnings, package warnings, overfull/underfull boxes, missing glyphs, undefined references/citations/control sequences, emergency stops, fatal errors, or raw TeX errors.

## Commits

- `be4aaf7e` — `docs(ledger): start cover to ch14.2 review`
- `9852878e` — `paper: simplify front matter and benchmark terminology`
