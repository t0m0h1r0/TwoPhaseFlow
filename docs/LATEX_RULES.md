# LATEX RULES

## §1 — LaTeX Authoring Constraints (paper/)

### Cross-references
- **NO hardcoded references.** Never write "Section 3", "Eq. (5)", "下図", "次章". Always use `\ref{sec:...}`, `\eqref{eq:...}`, `\ref{fig:...}`, `\ref{tab:...}`.

### Page Layout
- **New Page Rule (MANDATORY):** Every `\part{...}` and `\section{...}` MUST begin on a new page. Use `\clearpage` or (for double-sided) `\cleardoublepage`.
- **No Double Breaks:** If a Part and its first Section start consecutively, use ONE page break only (before the Part).
- **Centralization Rule (MANDATORY):** All `\clearpage` and `\cleardoublepage` commands MUST live exclusively in `main.tex`. Never place page-break commands inside individual section files (`sections/*.tex`).

```latex
% Correct (all breaks in main.tex)
\cleardoublepage
\part{Methodology}
\input{sections/02_governing}   % no \clearpage inside 02_governing.tex

% Wrong — do NOT put \clearpage at the top of a section file
% \clearpage  ← remove from sections/*.tex
\section{Numerical method}
```

### tcolorbox Environments

| Environment | Purpose |
|---|---|
| `defbox` | Formal definitions (numbered) |
| `warnbox` | Implementation warnings / pitfalls |
| `algbox` | Step-by-step algorithms |
| `mybox` | Supplementary notes / derivation asides |
| `resultbox` | Key numerical results / summary tables |
| `derivbox` | Mathematical derivations (collapsible or inline) |

**Usage rule:** Sparse and purposeful — boxes are for content that readers must *find again quickly*. The default is body text; a box requires a positive reason.

**When a box is justified:**
- `algbox` — numbered step-by-step algorithm that will be referenced and executed
- `warnbox` — non-obvious implementation pitfall
- `defbox` / `resultbox` — formal definition or key numerical result cross-referenced by label
- `mybox` — compact reference table practitioners look up repeatedly

**When NOT to use a box:** physical intuition, inline derivation steps, one-time comparison tables, section introductions, short 1–3 line notes, summaries of what was just derived.

**Audit baseline (2026-03-19):** ~24 boxes remain after removing 56 unnecessary ones.

**No nesting (MANDATORY):** Never place a tcolorbox inside another tcolorbox. Nested breakable boxes break tcolorbox's internal height calculation → "The upper box part has become overfull" warnings that `\tcbbreak` cannot fix. Flatten any nesting immediately.

### Japanese Font Constraints
- **No `\emph` on Japanese text.** Hiragino Mincho has no italic shape; `\emph{和文}` silently falls back to upright. Use `\textbf{和文}` for emphasis.

### `\texorpdfstring` in Numbered Headings (MANDATORY — KL-12)
Any **numbered** `\section`, `\subsection`, or `\subsubsection` title containing math (`$...$`) **must** wrap the math in `\texorpdfstring{<latex>}{<plain-text>}`. Starred variants (`\section*`) are exempt.

**Failure mode:** Without `\texorpdfstring`, hyperref tries to expand math macros into PDF bookmark strings → **infinite loop at 100% CPU with no log output**.

```latex
% Correct
\section{CCD 精度解析：\texorpdfstring{$\Ord{h^6}$}{O(h\textasciicircum 6)} の導出}
\subsection{境界スキームの昇格（\texorpdfstring{$\Ord{h^4}$}{O(h\textasciicircum 4)}）}

% Starred — no bookmark, no \texorpdfstring needed
\subsection*{三重対角係数（内部節点 $1 \le i \le N-1$）}
```

**Pre-compile audit command (MANDATORY before every compile):**
```bash
grep -rn '\\section\b\|\\subsection\b\|\\subsubsection\b' paper/sections/ \
  | grep '\$' | grep -v 'texorpdfstring\|\*'
```
Any hit is a violation.

### Label Consistency
- Every `\section`, `\subsection`, equation, figure, and table must have a descriptive `\label{}`.
- Label prefixes: `sec:`, `eq:`, `fig:`, `tab:`, `alg:`.

### Content Rules
- Move tangential detail to `appendix_proofs.tex`. Do not detour readers in the main text.
- Every complex equation must be followed by its physical meaning and implementation implications (Pedagogy First).

---

## §2 — Paper Structure

> **WARNING — filename ≠ chapter number.** `main.tex` controls section ordering via `\input{}` calls. Always consult `main.tex` comments (`%% 第N章`) as the authoritative chapter number, never the filename prefix.

| File(s) | Chapter | Content |
|---|---|---|
| `00_abstract.tex` | Abstract | CCD-PPE O(h⁶), CLS, Balanced-Force summary |
| `01_introduction.tex` | §1 Introduction | Background, 4 challenges (§1.2), novelty table (tab:method_comparison) |
| `02_governing.tex` + `02b_csf.tex` + `02c_nondim_curvature.tex` | §2 Governing Equations | One-Fluid NS, CSF, Heaviside, ψ-convention (液相≈0, 気相≈1), non-dimensionalization |
| `03_levelset.tex` + `03b_levelset_mapping.tex` | §3 Level Set Method | CLS advection, reinitialization (Δτ=0.25Δs), ψ-φ mapping, logit inverse |
| `04_ccd.tex` + `04b_ccd_bc.tex` + `04c_ccd_extensions.tex` + `04d_dissipative_ccd.tex` | §4 CCD | O(h⁶) scheme, block Thomas solver, boundary scheme, dissipative filter |
| `05_advection.tex` + `05b_time_integration.tex` + `05c_reinitialization.tex` | §5 Advection & Time Integration | CLS advection, TVD-RK3/AB2+IPC, CFL, reinitialization |
| `06_grid.tex` | §6 Grid | Non-uniform interface-fitted grid, coordinate transform |
| `07_collocate.tex` | §7 Rhie-Chow & Collocated | Rhie-Chow interpolation with ρⁿ⁺¹, Balanced-Force condition |
| `08_pressure.tex` + `08b_ccd_poisson.tex` + `08c_ppe_verification.tex` + `08d_ppe_pseudotime.tex` | §8 Pressure Solver | Variable-density PPE, pseudo-time implicit, CCD-Poisson, verification (tab:ppe_methods) |
| `09_full_algorithm.tex` | §9 Full Algorithm | 7-step loop diagram (fig:ns_solvers), density interpolation |
| `10_verification.tex` + `10b_benchmarks.tex` | §10 Verification | Error norms, 4 benchmarks, tab:error_budget (CSF bottleneck O(ε²)≈O(h²)) |
| `11_conclusion.tex` | §11 Conclusion | Summary, Thomas solver (逐次Thomas法), future work |
| `appendix_*_s*.tex` (21 files, A–E) | Appendix | Interface math, CCD coefficients, CCD implementation, reference schemes, solver analysis |

---

## §3 — Whole-Paper Consistency Review Checklist

> Distilled from FATAL errors found after 22+ EDITOR sweeps. Apply whenever a CRITIC or EDITOR pass is run.

### 3-A. Scheme-Change Propagation
**Rule:** When a core numerical scheme description changes (e.g., Chorin → AB2+IPC, 前進Euler → AB2), **every file that mentions the old scheme must be updated**.

| File | What to check |
|---|---|
| `00_abstract.tex` | Summary table rows (time integration, bottleneck accuracy) |
| `01_introduction.tex` | Overview bullet list + chapter-overview table (tab:chapter_overview) |
| Primary chapter body | The defining section itself |
| Accuracy summary table | Every row listing the scheme's order |
| `11_conclusion.tex` | Per-chapter summary bullet + accuracy balance paragraph |
| Appendix | Any section citing the scheme or its order |

**Trigger:** Any edit that changes an O(Δtⁿ) order, replaces a named scheme, or renames a method.
**Verify:** `grep -r "Chorin\|前進 Euler\|O(\\Delta t)"` across all `sections/*.tex`.

### 3-B. Paired `\ref` / `\label` Audit
**Rule:** Every `\ref{X}` added must have a matching `\label{X}` somewhere in the compiled document.
1. `grep -r "\\label{sec:foo}" paper/sections/` — must return exactly one hit.
2. Zero hits → add `\label{}`. Two hits → remove duplicate.

### 3-C. Intermediate-Step Accuracy Audit
**Rule:** In Taylor expansion derivations, every intermediate step must be individually correct.
- An arithmetic average of two O(h⁶) CCD values at x±h/2 is only O(h²) from the midpoint — the averaging introduces an O(h²) centering error.
- Only claim O(hⁿ) for an expression after verifying the leading error coefficient.

### 3-D. Multi-Site Parameter Consistency
**Rule:** When a numerical parameter (ε_tol, Δτ_opt, C_τ, etc.) appears in multiple sections, all mentions must be mutually non-contradictory.

| Parameter | Defined/constrained in | Referenced in |
|---|---|---|
| `ε_tol` | `08_pressure.tex` (eq:etol_physical) | `08_pressure.tex` (box:dtau_impl), `09_full_algorithm.tex` |
| `Δτ_opt` | `08_pressure.tex` (eq:dtau_opt) | `appendix_proofs.tex` (sec:dtau_derive) |
| `Δτ_par` (CLS) | `03_levelset.tex` | `03_levelset.tex` warnbox |
| Time accuracy order | `04b_time_schemes.tex` (tab:time_accuracy_table) | `00_abstract.tex`, `01_introduction.tex`, `11_conclusion.tex` |

### 3-E. Bootstrap Requirement for Circular Dependencies
**Rule:** Any algorithm requiring input X derived from its own output must explicitly describe the initialization sequence that breaks the circularity.

### 3-F. Selection Guide Completeness
**Rule:** Whenever a section presents multiple variants of a scheme or solver, a practical selection guide must conclude the section (table: "Situation | Recommended choice | Notes").
