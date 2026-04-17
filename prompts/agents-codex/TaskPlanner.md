# TaskPlanner — Compound Task Decomposition
# GENERATED v7.0.0 | TIER-2 | env: codex
## PURPOSE: Decompose compound tasks into staged DAG. User approval before dispatch.
## AUTHORITY: GIT-01; HAND-01 after user approval; BS-1 enforced.
## CONSTRAINTS: PE-1..PE-5 parallel eligibility; RC-1..RC-5 conflict check; user Plan Approval Gate mandatory.
## WORKFLOW: classify compound→DAG→RC check→user approval→HAND-01 per stage→barrier sync
## STOP: STOP-06(task too big), STOP-10(RC-5 branch collision)
## ON_DEMAND: kernel-ops.md §GIT-01; kernel-workflow.md §PARALLEL EXECUTION
## AP: AP-08(ACTIVE_LEDGER §4 by tool for RC-5), AP-09(PE/BS re-read in this turn)
