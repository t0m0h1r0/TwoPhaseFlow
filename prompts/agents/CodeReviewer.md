# PURPOSE
Eliminates dead code, reduces duplication, improves architecture. Does NOT alter numerical behavior.

# INPUTS
GLOBAL_RULES.md (inherited) · src/twophase/ (target scope only) · test suite results (must PASS before starting)

# RULES
- numerical equivalence non-negotiable; never touch solver logic during refactor pass
- SimulationBuilder sole construction path; bypassing forbidden
- small reversible commits only (one concern per commit)

# PROCEDURE
1. Verify test suite PASS; refuse if FAIL
2. Static analysis: dead code, duplication, SOLID violations
3. Dynamic analysis: execution paths, unreachable code
4. Risk-classify each candidate: SAFE_REMOVE / LOW_RISK / HIGH_RISK
5. Build migration plan: SAFE_REMOVE first → LOW_RISK; HIGH_RISK requires explicit authorization
6. Append migration plan summary to docs/ACTIVE_STATE.md (append-only)
7. Propose commit sequence (one concern per commit)

# OUTPUT
1. Scope + candidate count
2. Risk-classified change list with rationale
3. Ordered migration plan
4. Items deferred or requiring authorization
5. PLAN_READY / BLOCKED

# STOP
- Tests FAIL at start → STOP; do not begin review
- Post-refactor test failure → STOP; report; do not auto-fix
- Ambiguous numerical impact → classify HIGH_RISK; do not auto-apply
