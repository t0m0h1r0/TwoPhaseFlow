# CHK-RA-PAPER-002 reader-first format review

## Scope and intent

- Scope: `paper/sections/01*.tex` through `paper/sections/15*.tex`.
- Intent: not only remove inconsistent notation, but make headings/captions easier for a strict reviewer to follow without reading surrounding paragraphs.
- Policy: `artifacts/A/paper_format_policy_CHK-RA-PAPER-002.md`.

## Reviewer policy applied

- Headings must reveal role and topic from the heading alone.
- Japanese headings/captions use full-width punctuation (`：`, `．`) unless inside code/math/established Latin terms.
- U/V result captions use `ID：title` and should be self-contained.
- Arabic numerals attached to Japanese nouns/counters are spaced in headings/captions (`2 次元`, `4 つ`, `1 タイムステップ`) unless the token is an experiment ID or math/code.
- Reviewer-facing shorthand such as `trend`, `sweep`, `snapshot`, `streamplot`, `multistep`, and `master summary` is Japaneseized unless it is the comparison object itself.
- Pending §14 benchmark results stay explicitly pending; §15 must not promote them to completed achievements.

## Findings and fixes

| Finding | Reviewer issue | Fix |
|---|---|---|
| F-01 | Ch.1 failure-example headings mixed ASCII sentence punctuation and compact numbering, reducing scanability. | `失敗例 1--4`, `症状．`, `原因．`, `本稿の対処．`, and bridge paragraph punctuation normalized. |
| F-02 | Ch.1/2/8/9/10 headings had compact Japanese numerals (`4つ`, `2次元`, `1次元`, `5次`) that read unevenly across chapters. | Spaced Japanese numeral+noun headings (`4 つ`, `2 次元`, `1 次元`, `5 次`). |
| F-03 | Ch.11 pure-FCCD phase headings used ASCII `Phase N:` in Japanese headings. | Normalized to `Phase N：...`. |
| F-04 | U-caption delimiters still had ASCII `:` in a compound caption and optional short caption. | `U1-d：...` and `U4-a：...` normalized. |
| F-05 | Several U/V captions used reviewer-facing English shorthand (`trend`, `sweep`, `snapshot`, `streamplot`, `multistep`, `master`). | Captions rewritten as Japanese reviewer prose: `収束傾向`, `掃引`, `スナップショット`, `流線図`, `多ステップ診断`, `統合精度まとめ`. |
| F-06 | Caption punctuation mixed ASCII comma/parentheses in Japanese explanatory phrases. | Normalized representative caption punctuation around Japanese clauses and math fragments. |
| F-07 | §14/§15 status language needed re-check after format edits. | Confirmed pending §14 benchmark entries remain pending; §15 only claims V1--V10 integration achievements, not pending §14 physical benchmark completion. |

## Files updated by policy application

- Policy/review: `artifacts/A/paper_format_policy_CHK-RA-PAPER-002.md`, `artifacts/A/review_CHK-RA-PAPER-002.md`.
- Ch.1--2: `paper/sections/01_introduction.tex`, `paper/sections/01b_classification_roadmap.tex`, `paper/sections/02c_nondim_curvature.tex`.
- Ch.8--11: `paper/sections/08_collocate.tex`, `paper/sections/09_ccd_poisson.tex`, `paper/sections/09c_hfe.tex`, `paper/sections/10_grid.tex`, `paper/sections/10b_ccd_extensions.tex`, `paper/sections/11d_pure_fccd_dns.tex`.
- Ch.12--13 verification captions: `paper/sections/12u1_ccd_operator.tex`, `paper/sections/12u4_ridge_eikonal_reinit.tex`, `paper/sections/12u5_heaviside_delta.tex`, `paper/sections/12u6_split_ppe_dc_hfe.tex`, `paper/sections/12u7_bf_static_droplet.tex`, `paper/sections/12u8_time_integration.tex`, `paper/sections/13a_single_phase_ns.tex`, `paper/sections/13b_twophase_static.tex`, `paper/sections/13d_density_ratio.tex`, `paper/sections/13e_nonuniform_ns.tex`, `paper/sections/13f_error_budget.tex`.

## Reproducible audit commands and results

Run from worktree root unless noted.

```bash
files=$(find paper/sections -maxdepth 1 -type f \( -name '01*.tex' -o -name '02*.tex' -o -name '03*.tex' -o -name '04*.tex' -o -name '05*.tex' -o -name '06*.tex' -o -name '07*.tex' -o -name '08*.tex' -o -name '09*.tex' -o -name '10*.tex' -o -name '11*.tex' -o -name '12*.tex' -o -name '13*.tex' -o -name '14*.tex' -o -name '15*.tex' \) | sort)
rg -n '\\(sub)?paragraph\{[^}]*\.' $files
rg -n '\\caption(\[[^]]*\])?\{[UV][0-9][^}]*:' $files
rg -n '\\caption\[[^]]*:' $files
rg -n '\\caption(\[[^]]*\])?\{[^}]*([一-龠ぁ-んァ-ヶ][0-9]|[0-9][一-龠ぁ-んァ-ヶ])' $files
rg -n '\\(section|subsection|subsubsection|paragraph|subparagraph)\*?\{[^}]*([一-龠ぁ-んァ-ヶ][0-9]|[0-9][一-龠ぁ-んァ-ヶ])' $files
rg -n '\\caption(\[[^]]*\])?\{[^}]*\b(stack|long-term|trend|sweep|snapshot|streamplot|master|multistep)\b' $files
rg -n '\\includegraphics[^\n]*\{[^}]*\.(png|jpg|jpeg|svg)\}' $files
```

Result after commit `0a8781a`: all commands above returned no matches.

```bash
rg -n -F -e '毛細管波' -e '毛管波' paper/sections/01b_classification_roadmap.tex paper/sections/14_benchmarks.tex paper/sections/15_conclusion.tex
rg -n -F -e '計算完了次第掲載' -e '受入基準を満た' -e '実証された' paper/sections/14_benchmarks.tex paper/sections/15_conclusion.tex paper/sections/01b_classification_roadmap.tex
```

Result: `毛細管波` did not appear; `毛管波` remains canonical. Pending placeholders appear only in the roadmap/§14 pending benchmark context. `受入基準を満たした` applies to V1--V10 integration verification, not §14 physical benchmark completion.

## Validation

- `latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex` in `paper/`: OK; `paper/main.pdf` generated, 237 pages.
- Final `main.log` diagnostic grep for LaTeX warnings, package warnings, overfull/underfull boxes, missing characters, undefined controls, emergency/fatal errors, and `^!`: 0 hits.
- `git diff --check`: OK.
- `make lint-ids`: OK.

## SOLID audit

- `[SOLID-X]` paper/docs/review-only. No `src/twophase/` files or production module/class boundaries changed.

## Commits

- `0cd30e4` — `docs: define paper format policy`.
- `0a8781a` — `paper: apply reader-first format policy`.
- Ledger/review artifact commit follows this artifact.
