# CHK-RA-PAPER-002 paper format policy

## Scope

This policy applies to the main paper chapters `paper/sections/01*.tex` through `paper/sections/15*.tex` and is intended to make future reviewer findings reproducible. Appendices and generated artifacts are out of scope unless explicitly referenced by a chapter.

## Canonical format rules

1. **Reader-first structure**
   - Every chapter and major subsection should reveal its role from the heading alone: problem setting, method definition, verification target, result, limitation, or future work.
   - Verification chapters use a stable progression: purpose/criterion → setup → result figure/table → interpretation → residual limitation.
   - Headings avoid bare labels when a reader would have to infer the point from surrounding prose; prefer `対象：観点` or `対象と判断基準` forms.

2. **Chapter and section headings**
   - Japanese headings use full-width Japanese punctuation: `：` for topic/subtitle separation and `．` for sentence-style `\paragraph{...}` labels.
   - ASCII `:` and `.` are allowed only inside Latin abbreviations, code identifiers, file names, references, and mathematical notation.
   - Arabic numerals in Japanese headings/captions are separated from Japanese nouns/counters for readability (`2 次元`, `4 つ`, `1 タイムステップ`), except stable IDs (`U1`, `V10`), code identifiers, and mathematical notation.
   - Complex TeX/math in numbered headings should use `\texorpdfstring{...}{...}` when needed for clean PDF bookmarks; the build log is the acceptance check.

3. **Figure and table captions**
   - Captions start with the experiment/result ID when one exists, followed by full-width `：` (for example `U1-c：...`, `V10：...`).
   - Captions are centered globally and use compact caption line spacing. Local left/ragged caption setup is not used in chapter files.
   - Captions are self-contained: they identify the object, the metric or condition, and any interpretation needed to read the figure/table without searching nearby prose.
   - Placeholder status must be explicit. A table awaiting data is titled as acceptance criteria/status, not as completed results.
   - Multi-panel captions state the panel mapping or tested contrast before the interpretation sentence.
   - English shorthand is kept only for established technical terms. Reviewer-facing convenience words such as `trend`, `sweep`, `snapshot`, and `master summary` are written in Japanese unless the English term itself is the object of comparison.

4. **Table typography**
   - Table typography is controlled by named macros in `paper/preamble.tex`, not by ad hoc numeric `\arraystretch` / `\tabcolsep` values in chapter files.
   - Default tables use `\PaperTableSetup`: `\small`, `\tabcolsep=4pt`, `\arraystretch=1.12`.
   - Dense summary tables use `\PaperTableDenseSetup`: `\footnotesize`, `\tabcolsep=3pt`, `\arraystretch=1.02`.
   - Exceptionally long one-page summary tables may use `\PaperTableExtraDenseSetup`; the exception must be named explicitly rather than hidden as raw `\scriptsize`.

5. **Float placement and graphics**
   - Chapter figures and plots are PDF assets. Bitmap/vector image suffixes such as `.png`, `.jpg`, `.jpeg`, and `.svg` are not used from chapter `\includegraphics` commands.
   - Dense result groups and wide multi-panel verification layouts use float-page placement (`[p]`) when ordinary placement causes float warnings or poor continuity.
   - Normal prose-adjacent figures/tables keep the local convention unless the LaTeX log reports placement issues.

6. **Terminology and claims**
   - Terminology is chapter-consistent and cross-chapter-consistent; current canonical term for the capillary-wave benchmark is `毛管波`.
   - Achieved results, planned benchmarks, and pending computations are never mixed. §14 pending benchmark entries remain pending until numerical results are recorded.
   - Numeric summaries must match the source table/figure values in the same chapter or the cited upstream result section.

7. **Reviewer reproducibility**
   - Each format review records the exact audit commands, files changed, and residual accepted exceptions.
   - New findings use the `CHK-RA-PAPER-*` id prefix and are recorded in `docs/02_ACTIVE_LEDGER.md` plus an artifact under `artifacts/A/`.

## Reproducible audit commands

Run from the worktree root.

```bash
files=$(find paper/sections -maxdepth 1 -type f \( -name '01*.tex' -o -name '02*.tex' -o -name '03*.tex' -o -name '04*.tex' -o -name '05*.tex' -o -name '06*.tex' -o -name '07*.tex' -o -name '08*.tex' -o -name '09*.tex' -o -name '10*.tex' -o -name '11*.tex' -o -name '12*.tex' -o -name '13*.tex' -o -name '14*.tex' -o -name '15*.tex' \) | sort)
rg -n '\\(sub)?paragraph\{[^}]*\.' $files
rg -n '\\caption(\[[^]]*\])?\{[UV][0-9][^}]*:' $files
rg -n '\\caption\[[^]]*:' $files
rg -n '\\caption(\[[^]]*\])?\{[^}]*([一-龠ぁ-んァ-ヶ][0-9]|[0-9][一-龠ぁ-んァ-ヶ])' $files
rg -n '\\(section|subsection|subsubsection|paragraph|subparagraph)\*?\{[^}]*([一-龠ぁ-んァ-ヶ][0-9]|[0-9][一-龠ぁ-んァ-ヶ])' $files
rg -n '\\caption(\[[^]]*\])?\{[^}]*\b(stack|long-term|trend|sweep|snapshot|streamplot|master|multistep)\b' $files
rg -n '\\renewcommand\{\\arraystretch\}\{[0-9]|\\setlength\{\\tabcolsep\}\{[0-9]' $files
rg -n 'justification=RaggedRight|singlelinecheck=false' paper/preamble.tex $files
rg -n '\\includegraphics[^\n]*\{[^}]*\.(png|jpg|jpeg|svg)\}' $files
rg -n -F -e '毛細管波' -e '毛管波' paper/sections/01b_classification_roadmap.tex paper/sections/14_benchmarks.tex paper/sections/15_conclusion.tex
rg -n -F -e '計算完了次第掲載' -e '受入基準を満た' -e '実証された' paper/sections/14_benchmarks.tex paper/sections/15_conclusion.tex paper/sections/01b_classification_roadmap.tex
```
