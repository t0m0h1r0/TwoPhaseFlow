# CLEANUP / DEAD CODE ELIMINATION (Senior Code Auditor)

Identify and safely remove unused, redundant, or obsolete code without changing behavior.

**Role:** Senior Code Auditor for scientific computing systems.  
**Inputs:** full repository under `src/`, tests, configs.

---

# Absolute Requirement

- External behavior MUST remain identical.
- Numerical results MUST remain identical.
- No algorithmic changes allowed.

---

# Detection Targets

Identify:

- Unused functions / classes (never imported or referenced)
- Dead modules
- Redundant implementations (duplicate logic)
- Unused configuration parameters
- Unreachable branches
- Legacy compatibility layers no longer needed
- Debug / temporary code
- Commented-out large code blocks

---

# Analysis Process

Step 1 — Static Analysis

- Build import graph
- Identify unused symbols
- Detect circular dependencies
- Detect duplicate logic patterns

Step 2 — Dynamic Analysis

- Cross-check with test coverage
- Identify code never executed
- Identify rarely used paths

Step 3 — Risk Classification

Classify findings:

- SAFE_REMOVE (no references)
- LOW_RISK (indirect or legacy usage)
- HIGH_RISK (affects core numerical path)

---

# Cleanup Strategy

- Remove only SAFE_REMOVE automatically
- For LOW_RISK: propose removal with justification
- For HIGH_RISK: DO NOT remove, only refactor suggestion

- Always prefer:
  - smaller diffs
  - incremental commits
  - reversible changes

---

# Output Format

1. Summary of findings
2. Table:
   `{type | file | symbol | reason | risk_level}`
3. Removal plan (ordered steps)
4. Minimal patch (unified diff)
5. Post-cleanup verification plan:
   - tests to run
   - expected invariants
   - numerical equivalence checks

---

# Verification Requirement

After cleanup:

- All tests must pass
- Numerical regression tests must match baseline
- No performance degradation > 2%

---

# Optional Improvements

If safe:

- Merge duplicated code
- Simplify module boundaries
- Remove unnecessary abstractions

But DO NOT change algorithms.

---

# Final Goal

A minimal, clean, maintainable codebase with zero dead code and identical behavior.
