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

## **3. Whole-Paper Consistency Review Checklist**

> These rules were distilled from FATAL errors found *after* 22+ EDITOR sweeps.
> Each item captures a class of bug that recurred because no explicit rule existed for it.
> Apply this checklist whenever a CRITIC or EDITOR pass is run.

---

### 3-A. Scheme-Change Propagation

**Rule:** When a core numerical scheme description changes (e.g., Chorin → AB2+IPC, 前進Euler → AB2), **every file that mentions the old scheme must be updated** — not just the primary chapter.

**Mandatory propagation targets for any time/space accuracy claim:**

| File | What to check |
|------|--------------|
| `00_abstract.tex` | Summary table rows (time integration, bottleneck accuracy) |
| `01_introduction.tex` | Overview bullet list (`\textbf{時間積分：}` etc.) + chapter-overview table (tab:chapter_overview) |
| Primary chapter body | The defining section itself |
| Accuracy summary table | Every row listing the scheme's order |
| `11_conclusion.tex` | Per-chapter summary bullet + accuracy balance paragraph |
| Appendix | Any section citing the scheme or its order |

**Trigger:** Any edit that changes an O(Δtⁿ) order, replaces a named scheme, or renames a method.
**How to verify:** `grep -r "Chorin\|前進 Euler\|O(\\Delta t)"` across all `sections/*.tex` after the change.

---

### 3-B. Paired `\ref` / `\label` Audit

**Rule:** Every `\ref{X}` (or `\eqref{X}`) added to any file must have a matching `\label{X}` **somewhere** in the compiled document. Adding a `\ref` without verifying the `\label` exists is a build-breaking error.

**Procedure after adding any `\ref{sec:foo}` or `\ref{eq:bar}`:**
1. `grep -r "\\label{sec:foo}" paper/sections/` — must return exactly one hit.
2. If zero hits → add `\label{sec:foo}` at the appropriate location before committing.
3. If two hits → remove the duplicate (LaTeX will multiply-defined warning).

**Common source of missing labels:** A warnbox or resultbox is rewritten to reference a new `sec:` label that does not yet exist in the target section (e.g., `\ref{sec:ipc_derivation}` added to `08b_ccd_poisson.tex` but `\label{sec:ipc_derivation}` not yet placed in `04b_time_schemes.tex`).

---

### 3-C. Intermediate-Step Accuracy Audit

**Rule:** In Taylor expansion derivations (especially in appendices justifying O(hᵏ) claims), **every intermediate step must be individually correct** — not just the final conclusion.

**Failure pattern:** The final conclusion "error is O(h²)" can be correct even when an intermediate step wrongly claims "O(h⁶)" for a quantity that is only O(h²). Pedagogically, wrong intermediate steps mislead readers who want to understand the derivation.

**Checklist for each Taylor expansion:**
- Write out the full expansion for each term separately.
- State the order of **each** term before combining.
- The stated order of an *arithmetic average* of two values at $x ± h/2$ is only O(h²) from the midpoint, **not** O(h⁶), even if each value was computed with O(h⁶) CCD accuracy (the averaging introduces an O(h²) centering error — see appendix_numerics §app:rc_precision for the fixed derivation).
- Only claim O(hⁿ) for an expression after verifying the coefficient of the leading error term.

---

### 3-D. Multi-Site Parameter Consistency

**Rule:** When a numerical parameter (ε_tol, Δτ_opt, C_τ, Δτ_par, etc.) is mentioned in multiple sections with constraints or recommended values, **all mentions must be mutually non-contradictory**.

**Failure pattern:** One section states "X = 10⁻⁸ does not satisfy the condition" while another section recommends "X = 10⁻⁸ as the example value." Both can appear in the same file after incremental edits.

**How to check:** For each parameter P that appears in a `resultbox` or `warnbox`, grep all sections for P and read every occurrence in sequence. Ask: is there any pair of sentences that assert contradictory constraints?

**Parameters in this paper requiring cross-section consistency:**

| Parameter | Defined/constrained in | Referenced in |
|-----------|----------------------|---------------|
| `ε_tol` | `08_pressure.tex` (eq:etol_physical) | `08_pressure.tex` (box:dtau_impl), `09_full_algorithm.tex` |
| `Δτ_opt` | `08_pressure.tex` (eq:dtau_opt) | `appendix_proofs.tex` (sec:dtau_derive) |
| `Δτ_par` (CLS) | `03_levelset.tex` | `03_levelset.tex` warnbox |
| Time accuracy order | `04b_time_schemes.tex` (tab, sec:time_accuracy_table) | `00_abstract.tex`, `01_introduction.tex`, `08b_ccd_poisson.tex`, `11_conclusion.tex` |

---

### 3-E. Bootstrap Requirement for Circular Dependencies

**Rule:** Any algorithm that requires input X which is itself derived from the algorithm's output must explicitly describe the **initialization sequence** (bootstrap) that breaks the circularity.

**Failure pattern:** The 2D non-uniform grid algorithm requires φ to compute ω(φ), but φ is defined on the grid — circular. Without an explicit "compute φ on uniform grid first" note, implementers are stuck.

**Checklist:** For each algorithm box (`algbox`) in the paper:
- Identify every input quantity.
- For each input, ask: "Is this quantity available before this algorithm runs for the first time?"
- If no → document the bootstrap: (1) initial uniform-grid estimate, (2) full algorithm using that estimate, (3) optional re-run when input changes significantly.

---

### 3-G. `\texorpdfstring` in Numbered Section Titles (MANDATORY)

**Rule:** Any **numbered** `\section`, `\subsection`, or `\subsubsection` title that contains math (`$...$`) **must** wrap the math in `\texorpdfstring{<latex>}{<plain-text>}`. Starred variants (`\section*`, `\subsection*`) are exempt because hyperref does not generate PDF bookmarks for them.

**Failure mode:** Without `\texorpdfstring`, hyperref tries to expand math macros (e.g., `\mathcal{O}`, `\bm{u}`, `\Delta\tau`) into a PDF bookmark string. Macros that recursively call math-mode commands cause hyperref's expansion engine to **loop infinitely at 100% CPU with no output**, with no error in the log. The document never finishes compiling.

**Observed instance (2026-03-23):** `\subsection{...（$\Ord{h^4}$）}` — `\Ord{}` expands to `\mathcal{O}(...)`, which hyperref cannot handle in PDF-string context → 18-minute infinite loop.

**Correct pattern:**
```latex
% Numbered — MUST use \texorpdfstring
\section{CCD 精度解析：\texorpdfstring{$\Ord{h^6}$}{O(h\textasciicircum 6)} の導出}
\subsection{境界スキームの昇格（\texorpdfstring{$\Ord{h^4}$}{O(h\textasciicircum 4)}）}

% Starred — no bookmark generated, no \texorpdfstring needed
\subsection*{三重対角係数（内部節点 $1 \le i \le N-1$）}
```

**Quick audit command:**
```bash
grep -rn '\\section\b\|\\subsection\b\|\\subsubsection\b' paper/sections/ \
  | grep '\$' | grep -v 'texorpdfstring\|\*'
```
Any hit is a violation.

---

### 3-F. Selection Guide Completeness

**Rule:** Whenever a section derives or presents **multiple variants** of a scheme, boundary condition, or solver (e.g., one-sided BC vs. ghost-cell BC; BiCGSTAB vs. pseudo-time; ADI vs. sweep), a **practical selection guide must conclude the section**.

**Failure pattern:** Multiple variants are derived and their properties noted, but no guidance is given on *which to choose when*. Readers are left without actionable information.

**Required format:** A short table or `mybox` at the end of the section with columns: "Situation | Recommended choice | Notes". See `05b_ccd_bc_matrix.tex` (box:ccd_bc_guide) and `08_pressure.tex` (tab:ppe_methods) as reference examples.

---

## **2. Paper Structure**

File-number prefixes now match chapter numbers. `main.tex` is authoritative for include order. Sub-files (`05b_`, `08b_`, `08c_`) are included without a `\clearpage` break — they continue their parent chapter.

| File | Chapter | Content |
|------|---------|---------|
| `00_abstract.tex` | Abstract | CCD-PPE O(h⁶), CLS, Dissipative CCD, Balanced-Force summary |
| `01_introduction.tex` | §1 Introduction | Background, 4 challenges (§1.2), novelty table (tab:method_comparison) |
| `02_governing.tex` | §2 | Variables, Two-Fluid → One-Fluid derivation, ψ-convention (liquid≈0, gas≈1) |
| `02b_csf.tex` | §2 cont. | CSF surface tension model, δ-function volume force, Balanced-Force preview |
| `02c_nondim_curvature.tex` | §2 cont. | Non-dimensionalization (Re/Fr/We), interface curvature κ |
| `03_levelset.tex` | §3 | Why CLS, conservative advection, reinitialization (Δτ=0.25Δs) |
| `03b_levelset_mapping.tex` | §3 cont. | ψ-φ mapping, logit inverse, curvature numerics & stabilization |
| `04_ccd.tex` | §4 | CCD motivation, definition, Eq-I & II coefficient derivations |
| `04b_ccd_bc.tex` | §4 cont. | Boundary schemes (O(h⁵)/O(h²)), block tridiagonal matrix structure |
| `04c_ccd_extensions.tex` | §4 cont. | Non-uniform grid (coord transform), 2D mixed derivatives, elliptic solver role |
| `04d_dissipative_ccd.tex` | §4 cont. | Dissipative CCD filter, S(ψ) derivation, ε_max design, spectral analysis |
| `05_advection.tex` | §5 | CLS advection: Dissipative CCD design rationale, instability analysis, filter theory |
| `05b_time_integration.tex` | §5 cont. | Time integration: TVD-RK3 (CLS), AB2+IPC (NS), Crank-Nicolson (viscous) |
| `05c_reinitialization.tex` | §5 cont. | CLS reinitialization (compression + diffusion), stability constraints (CFL) |
| `06_grid.tex` | §6 Grid & Discretization | Non-uniform interface-fitted grid, coordinate transform |
| `07_collocate.tex` | §7 | Rhie--Chow interpolation with ρⁿ⁺¹, Balanced-Force condition |
| `08_pressure.tex` | §8 Pressure Solver | Variable-density PPE derivation, FVM discretization, Rhie--Chow divergence, BC |
| `08b_ccd_poisson.tex` | §8 cont. | CCD-Poisson matrix structure, Balanced-Force consistency, method comparison |
| `08c_ppe_verification.tex` | §8 cont. | PPE solver unit tests (Test C-1, C-2, C-3) |
| `09_full_algorithm.tex` | §9 Full Algorithm | 7-step loop diagram (fig:ns_solvers), density interpolation |
| `10_verification.tex` | §10 | Error norms, grid convergence tests (curvature, parasitic currents) |
| `10b_benchmarks.tex` | §10 cont. | 4 benchmarks (stationary droplet, Zalesak, RT instability, rising bubble) + error budget |
| `11_conclusion.tex` | §11 Conclusion | Summary, Thomas solver (sequential sweep), future work |
| `appendix_proofs.tex` | Appendix | 1D One-Fluid proof, logit inverse derivation, Newton convergence, Δτ convergence rate |
