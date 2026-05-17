# CHK-RA-PAPER-COVER-14P2-002 Review Record

## Scope

- Target: cover/front matter through Chapter 14 section 14.2.
- Included paper inputs: `paper/sections/00_abstract.tex`, Chapters 1--13 section files, `paper/sections/14_benchmarks.tex`, `paper/sections/14a_capillary_wave.tex`, and `paper/sections/14b_oscillating_droplet.tex`.
- Context boundary: §14.3 onward and appendices were built for validation, but not edited for this target-scope review.
- Trigger: the previous whole-scope review was already merged, but later Chapter 14 PhaseRegion updates changed the paper-facing evidence and required a fresh reviewer pass.

## Initial Inventory

### Structure, Size, and Input Order

- `paper/main.tex` inputs the target as `00_abstract`, `01`, `01b`, `02*`, `03*`, `04*`, `05*`, `06*`, `07*`, `08*`, `09*`, `10*`, `11*`, `12_component_verification`, `13_verification`, `14_benchmarks`, `14a_capillary_wave`, and `14b_oscillating_droplet`.
- Chapter 12 expands through `12u1`--`12u12` plus `12h_summary`; Chapter 13 expands through `13a`--`13f`.
- Target inventory size from the scoped `wc -l` pass was 17,648 lines including `paper/main.tex`. Large target files remain responsibility-coherent: `09b4_capillary_work_state` 538 lines, `07_time_integration` 504, `11e_ao_fast_state_space` 472, `10d_ridge_eikonal_nonuniform` 425, `11b1_full_timestep` 421, and `13e1_nonuniform_ns` 340.

### File Split and Prefix Decision

- No split was made. The largest files are derivation/synthesis files whose local responsibility is still single-purpose.
- Prefix families remain coherent: `09b1`--`09b4`, `10a1`--`10a2`, `11b1`--`11b2`, `12u1`--`12u12`, `13e1`--`13e3`, and `14a`--`14e`.
- Splitting would not reduce reader load for this task because the problems were claim boundary and visible terminology, not mixed ownership.

### Box, Table, and Note Audit

- Target box scan found the abstract/front-matter orientation box plus definition, warning, algorithm, and result boxes in method and verification chapters.
- Boxes were retained. They currently act as definitions, warnings, result summaries, or reading guides; no decorative or long explanatory box required removal in this pass.
- §14.1--§14.2 use tables/figures, not decorative boxes. Their captions were checked for whether they state diagnostic role rather than overclaim force-coupled success.

### Citation Review

- No bibliography entry was added.
- Claim-local citations were already present near the target claims: Prosperetti for capillary/Rayleigh--Lamb clocks, Brackbill/Francois/Popinet/Denner--van Wachem for CSF/BF/spurious-current context, Chorin/van Kan/Guermond/Brown--Cortez--Minion/Pyo--Shen for projection/PPE context, Olsson--Kreiss/Zahedi for CLS, and Hysing/Aland--Voigt/Chandrasekhar/Tryggvason in adjacent benchmark context.
- Because no citation was added, no external reference metadata was changed.

## Findings and Fixes

### MAJOR-1: Front matter over-read reduced PhaseRegion diagnostics as a single standard-configuration benchmark story

- Evidence: the abstract said the Chapter 14 physical benchmarks used a standard configuration and were organized on the same standard configuration, while §14.1--§14.2 now deliberately mix reduced PhaseRegion chart diagnostics and standard one-period execution boundaries.
- Risk: a reader could infer that the capillary wave and short-time droplet chart successes had already been connected to the pressure/velocity consumer path.
- Fix: rewrote the abstract to describe Chapter 14 as physical benchmarks in three layers: reduced PhaseRegion diagnostics for capillary wave and short-time Rayleigh--Lamb droplet restoration, standard execution's one-period sharp-interface volume failure, and later NS-coupled benchmarks. Chapter 1 roadmap now says `PhaseRegion 正規経路による毛管波・振動液滴のチャート診断と，NS 連成ベンチマーク`.
- Re-review: PASS. The front matter now separates achieved evidence from unconnected paths before the reader reaches §14.

### MAJOR-2: Implementation/gate vocabulary remained visible in reader-facing prose

- Evidence: visible prose still included or implied terms such as `YAML`, `production runtime`, `fail-close`, `admission gate`, `projection-native`, `face cochain`, `Hodge 計量`, `state space`, `graph chart`, `gauge`, `mode-2`, `force-admission`, and `reduced PhaseRegion chart`.
- Risk: the paper sounded like implementation history and route management instead of a manuscript explaining quantities, constraints, and diagnostics.
- Fix: replaced implementation-facing wording with paper-facing Japanese:
  - `YAML` -> `設定` / `再現設定`
  - `production runtime` -> `標準実行経路` / `標準実行`
  - `fail-close` -> `不合格として停止` / `不合格停止`
  - `admission gate` -> `採用境界`
  - `projection-native face history` -> `射影後の面履歴`
  - `face cochain` / `面共鎖` -> `面量` / `面に保存する量`
  - `graph chart`, `gauge`, `boundary atlas` -> `グラフチャート`, `ゲージ`, `境界アトラス`
  - `force-admission` -> `力連成採用境界`
  - `mode-2` -> `2 次モード`
- Re-review: PASS. The remaining target-scope hits for `gauge` are label/ref names such as `sec:ppe_phase_gauge_pin` and `eq:ao_q_owned_graph_gauge`, not visible prose.

### MAJOR-3: Formula-heavy PhaseRegion prose needed one reader path from owner to measure to work

- Evidence: §§11--14 used correct equations, but the prose alternated between owner, chart, gauge, face quantity, and adoption boundary terms.
- Risk: readers could follow symbols locally but miss what each equation owns, updates, preserves, or diagnoses.
- Fix: synchronized the visible terminology across §1, §2, §11, §12, §13, and §14: `Omega_h` owns the state, `q_h=Q_h(Omega_h)` is a measure, `phi`/graph height are charts/gauges, capillary variation becomes face work, and pressure/velocity coupling remains a separate adoption boundary.
- Re-review: PASS. §14.1--§14.2 now read as diagnostics with explicit inputs, owned quantities, outputs, and non-claims.

### MINOR-1: §14.1--§14.2 captions and local prose needed the same success/failure boundary

- Evidence: §14.1 plotted pressure/velocity diagnostics even though force coupling was not admitted; §14.2 mixed short-time chart success with one-period standard-execution failure.
- Fix: kept the diagnostics but clarified that pressure/velocity fields are saved visualization diagnostics, not proof that PhaseRegion face force has entered PPE/velocity correction. §14.2 now says short-time closed-chart restoration passes, while one-period standard execution is finite but not accepted because sharp-interface volume is not preserved.
- Re-review: PASS.

## Review Units and Rounds

| Unit | Rounds | Result |
|---|---:|---|
| Inventory: structure, sizes, inputs, boxes, citations, terms | 1 | PASS |
| Cover/front matter and abstract | 3 | PASS, MAJOR+ 0 |
| Chapter 1 introduction and roadmap | 2 | PASS, MAJOR+ 0 |
| Chapters 2--3 governing equations, surface tension, CLS | 2 | PASS, MAJOR+ 0 |
| Chapters 4--6 CCD, reinitialization, per-term schemes | 1 | PASS, MAJOR+ 0 |
| Chapters 7--9 time integration, BF, PPE/HFE/DC/capillary work | 2 | PASS, MAJOR+ 0 |
| Chapters 10--11 grid, algorithm, PhaseRegion state ownership | 2 | PASS, MAJOR+ 0 |
| Chapters 12--13 component and integrated verification | 3 | PASS, MAJOR+ 0 |
| Chapter 14 through §14.2 | 3 | PASS, MAJOR+ 0 |
| Part-level pass: methods -> verification -> benchmarks | 2 | PASS, MAJOR+ 0 |
| Whole target-scope pass | 2 | PASS, MAJOR+ 0 |

No unit reached the 20-round cap.

## File Split, Prefix, Box, and Citation Decisions

- File split: none.
- Prefix normalization: none needed.
- Box changes: none.
- Citation additions: none.
- Wiki accumulation: added `docs/wiki/paper/WIKI-P-026.md` for the reusable review lesson that reduced chart diagnostics must be separated from standard execution claims in front matter and benchmark summaries.

## Validation

- `git diff --check` before the second paper commit — PASS.
- Target visible-term scan after terminology cleanup — PASS for the reviewed jargon set; remaining `gauge` matches are label/ref identifiers only.
- `make -B -C paper` — PASS; `paper/main.pdf` regenerated at 287 pages.
- Final `paper/main.log` diagnostic scan — PASS; no LaTeX warnings, package warnings, overfull/underfull boxes, missing glyphs, undefined references/citations/control sequences, emergency stops, fatal errors, or raw TeX errors were found.

## Commits in This Worktree Before Artifact Closure

- `c9059e5f` — `chore: start cover-to-14.2 paper review`
- `183fa912` — `paper: clarify phase-region benchmark gates`
- `9e9949b1` — `paper: align phase-region review narrative`
