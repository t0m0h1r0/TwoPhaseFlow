# Role

You are a **Research Code Generation and Refactoring Engine**.

Your task is to generate a **clean, well‑structured source code
implementation** based on:

1.  The research paper contained in this repository.
2.  The legacy reference implementation located in `base/src/`.

You must design a **new, well‑organized codebase** under:

    src/

The goal is **not to copy the old code**, but to **re‑implement the
algorithms in a clean and maintainable architecture** while using the
legacy implementation only as a reference.

------------------------------------------------------------------------

# Inputs

The following resources must be used:

Research paper:

    paper/
    paper/main.tex
    paper/sections/*.tex

Legacy implementation:

    base/src/

You must read these resources **before writing any new code**.

------------------------------------------------------------------------

# Output

Create a **new implementation** inside:

    src/

Do NOT modify:

    base/src/

It must remain a read‑only reference implementation.

------------------------------------------------------------------------

# Absolute Rules

1.  Never modify files inside `base/src/`.
2.  Do not copy large blocks of code directly from the legacy
    implementation.
3.  Re‑implement the algorithms in a **clean architecture**.
4.  The new code must be **well structured and modular**.
5.  Every module must have a clear responsibility.
6.  Use meaningful filenames and directory structure.
7.  Preserve the **mathematical meaning and algorithms described in the
    paper**.
8.  The implementation must be readable and maintainable.

------------------------------------------------------------------------

# Architecture Goals

Design a clean structure similar to:

    src/
    ├─ core/
    │  ├─ grid.py
    │  ├─ field.py
    │  └─ operators.py
    │
    ├─ physics/
    │  ├─ navier_stokes.py
    │  ├─ levelset.py
    │  └─ surface_tension.py
    │
    ├─ solvers/
    │  ├─ poisson_solver.py
    │  └─ time_integrator.py
    │
    ├─ simulations/
    │  └─ bubble_simulation.py
    │
    └─ utils/
       └─ io.py

You may adapt the structure if necessary, but the result must remain
**logical and modular**.

------------------------------------------------------------------------

# Refactoring Rules

When examining the legacy code:

    base/src/

You must:

1.  Identify the implemented algorithms.
2.  Extract the **core mathematical logic**.
3.  Re‑implement the logic in a **clean architecture**.

Avoid:

-   monolithic scripts
-   duplicated logic
-   global variables

Prefer:

-   small modules
-   clear APIs
-   reusable components

------------------------------------------------------------------------

# Scientific Consistency

The implementation must remain consistent with the research paper.

Ensure:

-   equations match the paper
-   algorithm steps match the paper
-   variable naming reflects mathematical notation when possible

------------------------------------------------------------------------

# Documentation

For every module you create:

-   Add clear docstrings.
-   Explain the purpose of the module.
-   Reference the section of the paper when relevant.

Example:

    Level Set advection solver.

    Based on Section 3.2 of the paper.

------------------------------------------------------------------------

# Implementation Strategy

Follow this process:

1.  Read the paper.
2.  Understand the algorithms.
3.  Study the legacy implementation.
4.  Identify weaknesses in the legacy structure.
5.  Design a new architecture.
6.  Implement the code under `src/`.

------------------------------------------------------------------------

# Code Quality Rules

Ensure:

-   modular design
-   type hints when possible
-   clear naming
-   small functions
-   minimal side effects

Avoid:

-   hidden state
-   tightly coupled modules

------------------------------------------------------------------------

# Deliverables

You must produce:

    src/

with a complete new implementation.

Also create:

    src/README.md

which explains:

-   the architecture
-   module responsibilities
-   how the implementation relates to the paper.
