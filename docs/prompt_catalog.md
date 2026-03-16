# Prompt Catalog

Last update: 2026-03-17

Navigation map for all workflow prompt files in `docs/`.
See `DOC_INDEX.md` for the canonical reading order.

---

## Naming Convention

Workflow prompts follow: `NN_ACTION.md`

- `NN` — two-digit sequence number for ordering
- `ACTION` — uppercase verb describing the operation

---

## Code Workflow Prompts

### [02_CODEGEN.md](02_CODEGEN.md)
**Purpose:** Implement numerical algorithms from `paper/` into `src/`.

**When to use:** You need to translate a paper equation or algorithm into Python code.

**Key constraints:** Follow equations exactly; support `ndim=2/3`; use `xp = backend.xp`; include tests.

**Output:** Summary + code patch with file path + test/validation instructions.

---

### [03_TESTGEN.md](03_TESTGEN.md)
**Purpose:** Generate numerical and unit tests for `src/` modules.

**When to use:** You need convergence tests, conservation tests, or regression tests.

**Test types:** Convergence/order (analytic functions), conservation properties, regression (fixed seeds).

**Output:** Purpose statement + pytest code + run instructions with expected outcome.

---

### [07_VERIFY.md](07_VERIFY.md)
**Purpose:** Verify that `src/` faithfully implements the algorithms described in `paper/`.

**When to use:** After a major implementation to confirm paper-to-code fidelity.

**Process (7 steps):**
1. Paper structure analysis
2. Implementation analysis
3. Paper-to-code mapping table
4. Missing implementation detection
5. Implementation fixes
6. Benchmark reproducibility
7. Final verification report

**Relationship:** Run before `10_EVALUATE.md` (VERIFY = structural match; EVALUATE = numerical correctness).

---

### [08_CLEANUP.md](08_CLEANUP.md)
**Purpose:** Safely identify and remove dead code, legacy compatibility layers, and obsolete code.

**When to use:** After refactoring when backward-compat code is no longer needed.

**Safety rules:** Never delete unless confirmed unused; check benchmarks, CLI, serialization.

**Process (8 steps):** Analysis → legacy detection → dead code → deletion candidates → plan → updated structure → cleaned code → verification.

---

### [09_REFACTORING.md](09_REFACTORING.md)
**Purpose:** Redesign architecture following SOLID principles without changing numerical results.

**When to use:** Architecture has grown complex, coupling is high, or extensibility is poor.

**Allowed changes:** Class/module structure, dependency injection, interfaces, directory layout.

**Forbidden changes:** Numerical algorithms, discretization schemes, boundary conditions.

**Process (6 steps):** Analysis → redesign → directory structure → migration → implementation → verification.

---

### [10_EVALUATE.md](10_EVALUATE.md)
**Purpose:** Verify numerical correctness of individual components using analytical/manufactured solutions.

**When to use:** A component may have a discretization bug; convergence order is wrong.

**Strategy:** Method of Manufactured Solutions (MMS), grid refinement (N=32/64/128/256), L1/L2/L∞ norms.

**Process (8 steps):** Components → solutions → experiment setup → error measurement → convergence test → diagnosis → fix → re-verification.

---

## Paper Workflow Prompts

### [11_WRITING.md](11_WRITING.md)
**Purpose:** Write Japanese LaTeX sections for `paper/`.

**When to use:** Adding new sections or expanding existing content in the manuscript.

**Rules:** Academic Japanese; define all variables before use; valid LaTeX only; reference paper equations.

---

### [12_REVIEW.md](12_REVIEW.md)
**Purpose:** Review the manuscript as a rigorous CFD professor.

**When to use:** After a writing pass to catch logical gaps, weak derivations, or missing validation.

**Role:** Distinguished professor specializing in computational methods; output in Japanese.

**Output:** Scan synthesis, verification gaps, weak logic, detailed critiques.

---

### [13_UPDATE.md](13_UPDATE.md)
**Purpose:** Expand `.tex` files with textbook-quality pedagogical depth.

**When to use:** A section is too terse, lacks step-by-step derivations, or would confuse readers.

**Constraint:** ZERO summarization; 100% technical depth preserved; expand, never condense.

---

### [14_STRUCTURAL_REVIEW.md](14_STRUCTURAL_REVIEW.md)
**Purpose:** Review the manuscript's overall structure, chapter order, figure/table placement.

**When to use:** Before or after a major writing pass to assess logical flow at chapter level.

**Output (Japanese):**
- 【現状の課題】Current structural flaws
- 【新章立て案】Revised TOC proposal
- 【構成・順序の変更指示】Section move instructions
- 【図表・レイアウトの改善案】Figure/table/layout improvements

**Relationship:** Run before `15_STRUCTURAL_UPDATE.md`.

---

### [15_STRUCTURAL_UPDATE.md](15_STRUCTURAL_UPDATE.md)
**Purpose:** Implement the structural revision agreed upon from `14_STRUCTURAL_REVIEW.md`.

**When to use:** After a structural review has produced a revised TOC and move instructions.

**Constraint:** Section-by-section rewrite; ZERO information loss; Japanese text.

---

### [16_FIX_REF.md](16_FIX_REF.md)
**Purpose:** Detect and replace all hard-coded section/figure/equation numbers with `\ref{}`/`\eqref{}`.

**When to use:** After structural rewrites where numbering may have shifted, or before final submission.

**Output:** Semantic label naming, full replacement list, updated `.tex` files.

---

## Prompt Relationships

```
Paper writing workflow:
  11_WRITING → 12_REVIEW → 13_UPDATE → 14_STRUCTURAL_REVIEW → 15_STRUCTURAL_UPDATE → 16_FIX_REF

Code development workflow:
  02_CODEGEN → 03_TESTGEN → 07_VERIFY → 10_EVALUATE

Maintenance workflow:
  08_CLEANUP (after refactoring)
  09_REFACTORING (when architecture degrades)
```

---

## Meta Prompts

### [99_PROMPT.md](99_PROMPT.md)
**Purpose:** Evolve and maintain the prompt system itself.

**When to use:** When prompts become stale, redundant, or the project has changed significantly.

**Process:** Repository analysis → prompt inventory → quality evaluation → optimization → naming → architecture → updates → catalog.
