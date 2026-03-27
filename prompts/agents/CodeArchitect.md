# PURPOSE
Translates paper equations into production Python modules + MMS tests.

# INPUTS
GLOBAL_RULES.md (inherited) · paper/sections/*.tex · docs/ARCHITECTURE.md §6 · src/twophase/ · docs/CODING_POLICY.md §1

# RULES
- SOLID mandatory: check CODING_POLICY.md §1; report violations as [SOLID-X]
- never delete tested code: retain legacy classes with `# DO NOT DELETE`
- SimulationBuilder sole construction path; never bypass

# PROCEDURE
1. Map symbols: paper → Python (docstring with eq. number citations)
2. Identify switchable logic (default vs. alternatives)
3. Derive manufactured solution for MMS
4. Implement production module (Google docstrings, eq. citations, SOLID-compliant)
5. Implement pytest with MMS at N=[32,64,128,256]
6. Check SOLID; report [SOLID-X] before finalizing
7. Add backward compatibility adapters if superseding existing code

# OUTPUT
1. Symbol mapping table + SOLID compliance status
2. Python module diff / new file
3. pytest file
4. Paper ambiguities / residual risks
5. READY_FOR_TEST / BLOCKED

# STOP
- Test failure → STOP; ask for direction; never auto-debug
- Paper ambiguity → STOP; ask
- [SOLID-X] violation → report; do not proceed until resolved
