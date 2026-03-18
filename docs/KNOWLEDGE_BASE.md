# **ARCHITECTURE & DEVELOPMENT RULES**

## **1. System Architecture (src/twophase/)**

* **backend:** Numpy/CuPy hardware abstraction via xp = backend.xp. NEVER hardcode numpy.
* **config:** Hierarchical pure data classes (SimulationConfig composed of GridConfig, FluidConfig, NumericsConfig, SolverConfig). Sub-configs are the single source of truth.
* **interfaces:** Abstract Base Classes strictly enforce contracts (IPPESolver, IReinitializer, ICurvatureCalculator, etc.).
* **simulation:** Coordination logic. TwoPhaseSimulation is the executor, SimulationBuilder is the constructor.

## **2. SOLID Design & Construction Rules**

* **No Direct Instantiation of Simulation:** TwoPhaseSimulation.**init** has been deprecated/deleted. The simulation MUST be built using SimulationBuilder(cfg).build().
* **Dependency Injection:** Components (e.g., Reinitializer, CurvatureCalculator, RhieChowInterpolator) must be injected via constructors. SimulationBuilder orchestrates this injection.
* **Open-Closed Principle (OCP):** Do not modify TwoPhaseSimulation to add new solvers. Create a new class extending IPPESolver and register it in ppe_solver_factory.py.
* **Single Responsibility Principle (SRP):** Boundary conditions, diagnostics, and I/O (CheckpointManager) must remain completely decoupled from the core numerical solvers.
* **No Global Mutable State:** State (rho, u, p, phi) must be passed explicitly to functions.

## **3. Implementation Constraints**

* **Dimension Agnostic:** Code should support ndim = 2 or 3 gracefully where possible.
* **Vectorization:** Heavy preference for vectorized array operations. Avoid Python for loops over grid points.
* **Testing:** Every new feature requires a pytest (preferably Method of Manufactured Solutions - MMS validation) checking L1, L2, L∞ norms.
* **Algorithm Sync:** The codebase must actively track the paper's theoretical developments. New logic added to the paper must be implemented.
* **Default vs. Alternative Logic:** The fundamental calculation scheme described in the paper must be the default behavior. Alternative logics (discussed in columns or appendices) should also be implemented but MUST be switchable via the configuration system.
* **Code Comments:** Code comments can be in Japanese or English. Japanese is the primary choice when in doubt to maximize readability for the author.

## **4. LaTeX Authoring Constraints (paper/)**

* **NO Hard-coded or Relative References:** Never write "Section 3", "Eq. (5)", or relative terms like "下図 (the figure below)", "次章 (the next chapter)". ALWAYS use cross-reference commands: \ref{sec:...}, \eqref{eq:...}, \ref{fig:...}.
* **File Management:** File names must mirror the latest paper structure. If a file becomes too large or difficult to manage, proactively split it into sub-section units.
* **Readability & Layout:**

  * **New Page Rule for Parts/Sections (MANDATORY):** The start of every new Part (`\part{...}`) or Section (`\section{...}`) MUST begin on a **new page**. Use `\clearpage` or, for double-sided layouts, preferably `\cleardoublepage`.
  * **Unified Handling When Both Start Together:** If a Part and its first Section begin consecutively, **do NOT insert multiple page breaks**. Use a **single page break only** (e.g., place `\cleardoublepage` before the Part and do not add another `\clearpage` before the Section). This avoids unnecessary blank pages and header/footer inconsistencies.
  * **Rationale & Operational Guideline:** Enforcing consistent page breaks improves document structure, readability, and navigation in both PDF and print formats. At most one entity (typically the Part) should be responsible for page breaking. Avoid redundant or stacked page break commands.
  * **LaTeX Examples:**

```
% Start of a new Part (with page break)
\cleardoublepage
\part{Methodology}

% First section under the Part (no additional page break)
\section{Governing equations}
```

```
% Starting a section on a new page independently
\clearpage
\section{Numerical method}
```

* **Note:** For front matter and main content transitions, consider `\frontmatter` / `\mainmatter` depending on the template.
* Move tangential, overly detailed, or non-essential explanations to an Appendix. Do not force the reader down unnecessary side-paths in the main text.
* Standardize the use of visual boxes (e.g., tcolorbox, warnbox, algbox). Use them consistently and sparingly (e.g., only for governing equations or specific "column" style notes). Avoid a chaotic mix of multiple colors and box types which makes reading unpleasant.
* **Label Consistency:** Every section, equation, figure, and table must have a consistent and descriptive \label{}.
* **Pedagogy First:** Equations must be followed by physical meaning and algorithmic/implementation implications.