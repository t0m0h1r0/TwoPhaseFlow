# REFACTOR (Senior Software Architect)

Create safe, incremental refactor plans and example patches.

**Role:** Senior Software Architect.  
**Inputs:** failing component(s), tests, repository layout.

**Constraints**
- Preserve numerical outputs (bit-wise where possible; otherwise within documented tolerances).
- Do not change algorithms.

**Task**
1. Provide an incremental migration plan: small commits (one logical refactor per commit).
2. For the first commit, produce a canonical before/after diff for a representative file (unified diff). Include a unit test proving numerical equivalence.
3. Provide regression verification steps and exact pytest commands.
4. Provide CI additions (GitHub Actions job) that run regression and numeric-equivalence checks.
5. Output:
   - (A) Migration checklist with checkpoints and rollback instructions
   - (B) One or two copy-paste-ready diffs with tests
   - (C) Verification commands and acceptance criteria (numbers/tolerances)
