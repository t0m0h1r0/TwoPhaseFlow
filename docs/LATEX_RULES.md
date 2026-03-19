# **LaTeX AUTHORING RULES**

## **1. LaTeX Authoring Constraints (paper/)**

### Cross-references
- **NO hardcoded references.** Never write "Section 3", "Eq. (5)", "下図", "次章". Always use `\ref{sec:...}`, `\eqref{eq:...}`, `\ref{fig:...}`, `\ref{tab:...}`.

### Page Layout
- **New Page Rule (MANDATORY):** Every `\part{...}` and `\section{...}` MUST begin on a new page. Use `\clearpage` or (for double-sided) `\cleardoublepage`.
- **No Double Breaks:** If a Part and its first Section start consecutively, use ONE page break only (before the Part). Do not insert another `\clearpage` before the Section.
- **Centralization Rule (MANDATORY):** All `\clearpage` and `\cleardoublepage` commands MUST live exclusively in `main.tex`. Never place page-break commands inside individual section files (`sections/*.tex`). Whether a section is first-in-part can only be determined from `main.tex`; scattering these commands across content files creates maintenance fragility.

```latex
% Correct (all breaks in main.tex)
\cleardoublepage
\part{Methodology}
\input{sections/02_governing}   % no \clearpage inside 02_governing.tex

\clearpage
\input{sections/03_levelset}    % no \clearpage inside 03_levelset.tex

% Wrong — do NOT put \clearpage at the top of a section file
% \clearpage  ← remove from sections/*.tex
\section{Numerical method}
```

### tcolorbox Environments

| Environment | Purpose |
|------------|---------|
| `defbox` | Formal definitions (numbered) |
| `warnbox` | Implementation warnings / pitfalls |
| `algbox` | Step-by-step algorithms |
| `mybox` | Supplementary notes / derivation asides |
| `resultbox` | Key numerical results / summary tables |
| `derivbox` | Mathematical derivations (collapsible or inline) |

**Usage rule:** Sparse and purposeful — boxes are for content that readers must *find again quickly* or that would be missed if buried in prose. The default is body text; a box requires a positive reason.

**When a box is justified:**
- `algbox` — numbered step-by-step algorithm or verification procedure that will be referenced and executed
- `warnbox` — non-obvious implementation pitfall (e.g. asymmetry of A_L ≠ A_R, sign convention valid across all chapters, denominator clamp to avoid division-by-zero)
- `defbox` / `resultbox` — formal definition or key numerical result that is *cross-referenced by label* from other sections or files
- `mybox` — only for CFL/timestep constraint formulas or other compact reference tables that practitioners look up repeatedly

**When NOT to use a box (use body text instead):**
- Physical intuition / motivational explanation ("why we choose X") — write as a paragraph
- Derivation steps shown inline — use numbered equations with `\label`
- Comparison tables that appear once and are never cross-referenced — use a regular `\begin{table}` environment
- Chapter/section introductions — use a plain opening paragraph
- Short notes (1–3 lines) that are a natural continuation of the surrounding text — inline with `\textbf{Note:}` or `\noindent\textbf{...}`
- Summaries of what was just derived — write as a closing sentence
- Content that duplicates a nearby numbered equation — do not re-box it

**Audit result (2026-03-19):** A full pass found 80 boxes; 56 were removed as unnecessary. The paper now has ~24 boxes. Before adding any new box, verify it cannot be expressed as body text.

**No nesting (MANDATORY):** Never place a tcolorbox inside another tcolorbox. Nested breakable boxes break tcolorbox's internal height calculation, producing "The upper box part has become overfull" warnings that `\tcbbreak` cannot fix. When supplementary notes are needed inside a box, fold them into prose (`\textbf{Note:}` etc.). If a sub-algorithm box is required, place it as an independent box *after* the parent box and reference it from the text. Flatten any nesting found in existing files immediately.

### Japanese Font Constraints
- **No `\emph` on Japanese text.** Hiragino Mincho (and most Japanese fonts) have no italic shape; `\emph{和文}` triggers "Font shape undefined" warnings and falls back silently to upright. Use `\textbf{和文}` for emphasis on Japanese text.

### Label Consistency
- Every section, equation, figure, and table must have a descriptive `\label{}`.

### Content Rules
- Move tangential detail to `appendix_proofs.tex`. Do not detour readers in the main text.
- Every equation must be followed by its physical meaning and implementation implications (Pedagogy First).

## **2. Paper Structure**

File-number prefixes now match chapter numbers. `main.tex` is authoritative for include order. Sub-files (`05b_`, `08b_`, `08c_`) are included without a `\clearpage` break — they continue their parent chapter.

| File | Chapter | Content |
|------|---------|---------|
| `00_abstract.tex` | Abstract | CCD-PPE O(h⁶), CLS, WENO5, Balanced-Force summary |
| `01_introduction.tex` | §1 Introduction | Background, 4 challenges (§1.2), novelty table (tab:method_comparison) |
| `02_governing.tex` | §2 Governing Equations | One-Fluid NS, CSF, Heaviside, ψ-convention (液相≈0, 気相≈1) |
| `03_levelset.tex` | §3 Level Set Method | CLS advection, reinitialization (Δτ=0.25Δs), logit inverse |
| `04_time_integration.tex` | §4 Time Integration | WENO5 + TVD-RK3, CFL, Godunov LF flux |
| `05_ccd.tex` | §5 CCD | O(h⁶) scheme, boundary scheme (O(h⁵)/O(h²)), block Thomas solver |
| `05b_ccd_extensions.tex` | §5 cont. | Non-uniform grid (coord transform), 2D mixed derivatives, elliptic solver role |
| `06_grid.tex` | §6 Grid & Discretization | Non-uniform interface-fitted grid, coordinate transform |
| `07_collocate.tex` | §7 Rhie-Chow & Collocated | Rhie-Chow interpolation with ρⁿ⁺¹, Balanced-Force condition |
| `08_pressure.tex` | §8 Pressure Solver | Variable-density PPE derivation, FVM discretization, pseudo-time implicit |
| `08b_ccd_poisson.tex` | §8 cont. | CCD-Poisson matrix structure, Balanced-Force consistency, method comparison |
| `08c_ppe_verification.tex` | §8 cont. | CCD-Poisson solver unit tests (Test C-1, C-2, C-3) |
| `09_full_algorithm.tex` | §9 Full Algorithm | 7-step loop diagram (fig:ns_solvers), density interpolation |
| `10_verification_metrics.tex` | §10 Verification | Error norms, tab:error_budget (CSF bottleneck O(ε²)≈O(h²)) |
| `11_conclusion.tex` | §11 Conclusion | Summary, Thomas solver (逐次Thomas法), future work |
| `appendix_proofs.tex` | Appendix | 1D One-Fluid proof, logit inverse derivation, Newton convergence, Δτ convergence rate (sec:dtau_derive) |
