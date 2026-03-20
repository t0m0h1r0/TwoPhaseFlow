# **SYSTEM INSTRUCTIONS & CONTEXT**

## **1\. Project Overview**

* **Project:** High-order CFD solver for gas-liquid two-phase flow.  
* **Languages:** Python (Implementation), LaTeX (Specification).  
* **Core Tech:** Compact Finite Difference (CCD), Level Set Method (CLS), Projection Method, Variable Density Navier-Stokes.  
* **Current Architecture:** Fully refactored to component injection via SimulationBuilder.  
* **Directory Structure:** \* paper/ : Mathematical specification & theoretical textbook. File names must reflect the latest paper structure.  
  * src/ : Production Python implementation (src/twophase/).  
  * docs/ : System prompts and project state.

## **2\. Claude's Default Behavior**

Whenever a new session starts, you MUST:

1. Silently absorb docs/99\_PROMPT.md, docs/ARCHITECTURE.md, docs/LATEX\_RULES.md, and docs/ACTIVE\_STATE.md. When a math verification task is detected, also load docs/13\_MATH\_VERIFY.md.
2. Understand the current state.
3. Await the user's specific workflow instruction or prompt file execution.  
4. NEVER reference deleted directories (e.g., base/).  
5. Ensure any proposed architectural changes align with the strict rules in ARCHITECTURE.md and docs/LATEX\_RULES.md.

## **3\. Strict Language Policy**

* **English ONLY:** Reasoning, git commits, docstrings, and standard markdown files (like this one).  
* **Japanese (or English):** Inline code comments. When in doubt, Japanese is the first choice for code comments to ensure intent is clear.  
* **Japanese ONLY:** The actual content of the LaTeX manuscript (paper/\*.tex) and review outputs targeting the paper.

## **4\. Workflow Prompt Map**

When the user specifies a workflow or assigns a role, adopt that persona strictly. The workflow tools are assumed to be located in docs/ (or similarly mapped based on the prompt catalog).

* **Code Workflows:** CODE\_MASTER, CODE\_DEVELOP, CODE\_VERIFY, CODE\_REFACTOR.
* **Paper Workflows:** PAPER\_EDITOR, PAPER\_REVIEW, LATEX\_ENGINE.
* **Verification Workflow:** MATH\_VERIFY — independent re-derivation of equations, coefficients, and matrix structures (docs/13\_MATH\_VERIFY.md). Invoke when the user asks to verify, re-derive, or audit a formula/scheme (e.g. "verify this", "re-derive", "check if this is wrong", "assume it is wrong and verify").