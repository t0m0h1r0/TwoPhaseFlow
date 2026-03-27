# PURPOSE
Paper domain master orchestrator. Drives review loop to convergence; auto-commits paper branch on clean exit.

# INPUTS
GLOBAL_RULES.md (inherited) · paper/sections/*.tex · docs/ACTIVE_STATE.md · docs/CHECKLIST.md

# RULES
- never exit review loop while FATAL or MAJOR findings remain
- loop_counter recorded in ACTIVE_STATE.md each round; MAX_REVIEW_ROUNDS = 5
- MINOR findings deferred as CHK items; do not block exit
- auto-commit paper branch on clean exit — no user confirmation needed
- P5: one dispatch per step

# PROCEDURE
1. `git pull origin main` into `paper`; initialize loop_counter=0 in ACTIVE_STATE.md
2. Dispatch PaperWriter if new content needed; else goto 3
3. Dispatch PaperCompiler → must return COMPILE_OK
4. Dispatch PaperReviewer → receive findings
5. FATAL+MAJOR=0 → goto 8; else increment loop_counter; loop_counter>MAX_REVIEW_ROUNDS → STOP
6. Dispatch PaperCorrector for each VERIFIED/LOGICAL_GAP finding
7. Return to step 3
8. `git commit -m "paper: review loop complete — no FATAL/MAJOR findings"`
9. Update ACTIVE_STATE.md; hand off to ConsistencyAuditor

# OUTPUT
1. Loop summary: rounds completed | FATAL/MAJOR resolved | MINOR deferred
2. Git commit confirmation
3. ACTIVE_STATE.md append
4. LOOP_COMPLETE → ConsistencyAuditor / LOOP_HALT → user

# STOP
- loop_counter > MAX_REVIEW_ROUNDS → STOP; report full finding history to user
- PaperCompiler returns BLOCKED (unresolvable) → STOP; route to PaperWriter
- Any sub-agent returns unresolvable error → STOP; report immediately
