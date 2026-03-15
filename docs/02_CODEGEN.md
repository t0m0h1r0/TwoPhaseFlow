# CODE GENERATION PROTOCOL

You are implementing numerical algorithms from a research paper.

The paper located in `paper/` is the **authoritative specification**.

Your task is to implement the algorithms in `src/`.

---

# Implementation Principles

1. Follow the equations in the paper exactly.
2. Prefer clarity over micro-optimizations.
3. Do not introduce algorithmic changes unless explicitly instructed.
4. Implementation must follow the repository architecture.

---

# Numerical Implementation Rules

Finite difference operations must:

- support arbitrary `ndim`
- avoid hardcoding dimensions
- use the backend abstraction (`xp`)

Level set operations must preserve:

- mass conservation
- interface smoothness

---

# Coding Standards

- Python ≥ 3.9
- vectorized operations preferred
- minimal dependencies

---

# Required Output Format

When implementing a feature:

1. Explain the numerical method briefly
2. Show the implementation
3. Indicate which equation in the paper it corresponds to