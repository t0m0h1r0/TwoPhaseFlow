# **SYSTEM INSTRUCTIONS & CONTEXT**

## **1\. Project Overview**

* **Project:** High-order CFD solver for gas-liquid two-phase flow.  
* **Languages:** Python (Implementation), LaTeX (Specification).  
* **Core Tech:** Compact Finite Difference (CCD), Level Set Method (CLS), Projection Method, Variable Density Navier-Stokes.  
* **Current Architecture:** Fully refactored to component injection via SimulationBuilder.  
* **Directory Structure:**  
  * paper/ : Mathematical specification & theoretical textbook.  
  * src/ : Production Python implementation (src/twophase/).  
  * docs/ : System prompts and project state.

## **2\. Claude's Default Behavior**

Whenever a new session starts, you MUST:

1. Silently absorb docs/99_PROMPT.md, docs/KNOWLEDGE\_BASE.md, and docs/ACTIVE\_STATE.md.  
2. Understand the current state: 28 tests passing, 11 chapters compiled cleanly.  
3. Await the user's specific workflow instruction or prompt file execution.  
4. NEVER reference deleted directories (e.g., base/).  
5. Ensure any proposed architectural changes align with the strict rules in KNOWLEDGE\_BASE.md.

## **3\. Strict Language Policy**

* **English ONLY:** Reasoning, code comments, git commits, docstrings, and standard markdown files (like this one).  
* **Japanese ONLY:** The actual content of the LaTeX manuscript (paper/\*.tex) and review outputs targeting the paper.

## **4\. Workflow Prompt Map**

When the user specifies a workflow or assigns a role, adopt that persona strictly. The workflow tools are assumed to be located in docs/ (or similarly mapped based on the prompt catalog).

* **Code Workflows:** MASTER\_ORCHESTRATOR, CODE\_DEVELOP, CODE\_VERIFY, CODE\_REFACTOR, CLEANUP.  
* **Paper Workflows:** PAPER\_EDITOR, PAPER\_CRITIC, LATEX\_ENGINE.