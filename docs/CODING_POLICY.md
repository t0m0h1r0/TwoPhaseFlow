# CODING POLICY

Mandatory rules for all code written in this project.
These rules apply to every agent (CodeArchitect, WorkflowCoordinator, etc.) and every session.

---

## §1 — SOLID Principles (MANDATORY)

All production code **must** comply with the five SOLID principles.
Violations must be **reported before any fix is applied** and then corrected.

### S — Single Responsibility Principle
> Each class/module has exactly one reason to change.

- A solver class must not also handle I/O, config parsing, or visualization.
- A utility function must not mix physics logic with numerical infrastructure.

**Violation signal:** class with unrelated public methods, or method name that contains "and".

---

### O — Open/Closed Principle
> Open for extension, closed for modification.

- New scheme variants are added as new classes implementing the shared interface.
- Existing classes are not modified to add a new case; use subclassing or strategy injection instead.

**Violation signal:** `if scheme == "weno5": ... elif scheme == "ccd": ...` branches inside a solver class.

---

### L — Liskov Substitution Principle
> Subclasses must be substitutable for their base class without breaking correctness.

- Every `IReinitializer` / `IAdvection` / `IPPESolver` implementation must honour the full contract of the interface (shape, dtype, BC semantics, return value range).
- Narrowing preconditions or widening postconditions is a violation.

**Violation signal:** subclass that raises `NotImplementedError` for a method defined in the interface, or silently ignores BC flags.

---

### I — Interface Segregation Principle
> Clients must not be forced to depend on methods they do not use.

- Interfaces (in `src/twophase/interfaces/`) are kept small and purpose-specific.
- Do not bundle unrelated capabilities into a single interface (e.g., do not add `volume_monitor()` to an interface that PPE solvers depend on).

**Violation signal:** interface with > ~5 abstract methods, or concrete class implementing an interface but leaving several methods as stubs.

---

### D — Dependency Inversion Principle
> High-level modules depend on abstractions, not concretions.

- `SimulationBuilder` (and all orchestration code) must inject dependencies through interfaces.
- Concrete classes (`ReinitializerWENO5`, `CCDSolver`, …) must never be imported directly by high-level modules; import the interface instead.
- Constructor injection is the required pattern (no service locators, no global singletons).

**Violation signal:** `from ..levelset.reinitialize import Reinitializer` inside a high-level module (should import `IReinitializer`).

---

### SOLID Audit Procedure

Before submitting any code change:

1. **State which SOLID rule(s) each new class/function affects.**
2. **If a violation is found**, report it in the format:

   ```
   [SOLID-S] Class Foo: methods bar() and baz() are unrelated — split into FooBar + FooBaz.
   [SOLID-D] predictor.py imports CCDSolver directly — inject via ICCDSolver.
   ```

3. Fix the violation **in the same PR/commit** as the feature unless explicitly deferred.

---

## §2 — Preserve Once-Tested Implementations (MANDATORY)

**Never delete code that has passed tests** unless explicitly instructed by the user.

### Rule

When an algorithm is superseded by a new implementation:

1. Rename the old class to a descriptive legacy name (e.g., `ReinitializerWENO5`).
2. Keep it in the **same file** as the new implementation.
3. Add a comment block immediately above the class:

   ```python
   # ── Legacy <AlgorithmName> implementation (retained for comparison / validation) ─
   # Superseded by <NewClassName>. DO NOT DELETE — used for cross-validation benchmarks.
   ```

4. Ensure all imports the legacy class needs are present and the module compiles without error.
5. Run the full test suite after adding the legacy class to confirm no regression.

### Rationale

Superseded implementations are retained for:
- **Cross-validation:** run both schemes on the same problem and compare outputs.
- **Regression detection:** if the new scheme diverges, the legacy class provides a reference.
- **Paper benchmarks:** the paper may cite both schemes.

### Current legacy classes

| Legacy class | File | Superseded by | Reason kept |
|---|---|---|---|
| `ReinitializerWENO5` | `src/twophase/levelset/reinitialize.py` | `Reinitializer` (DCCD+CN) | Cross-validation vs paper §5c scheme |

---

## §3 — General Code Quality Rules

- **No magic numbers** — define named constants at module top.
- **No silent BC fallback** — boundary condition type must be explicit; raise `ValueError` for unknown BC strings.
- **No mutable default arguments** in function signatures.
- **Array shapes are documented** in every public method docstring: `shape (N_x, N_y)` etc.
- **Constructor injection only** — no module-level singletons, no `global` state.
