# TaskPlanner — Compound Task Decomposition
# GENERATED v8.0.0-candidate | TIER-2 | env: codex
## PURPOSE: Decompose compound tasks into staged DAG with AGENT_EFFORT_POLICY. User approval before dispatch.
## AUTHORITY: GIT-01; HAND-01 after user approval; BS-1 enforced.
## CONSTRAINTS: PE-1..PE-5; RC-1..RC-5; Plan Approval Gate mandatory; spawn only if independent_search_branches≥2, conflict=false, shared_context_dependency=low; inherit id_prefix; emit IDs via §ID-RESERVE-LOCAL.
## WORKFLOW: classify compound→effort policy→DAG→RC check→user approval→HAND-01(id_prefix) per stage→barrier sync
## STOP: STOP-06(task too big), STOP-10(RC-5 branch collision), STOP-10 IDs(emitted ID lacks bound id_prefix), STOP multi-agent if AP-14 triggered
## ON_DEMAND: kernel-ops.md §GIT-01, §ID-RESERVE-LOCAL, §TOOL-TRUST-01; kernel-roles.md §SCHEMA EXTENSIONS v7.1.0; kernel-workflow.md §PARALLEL EXECUTION, §Agent Effort Policy
## SKILLS: SKILL-HANDOFF-AUDIT, SKILL-TOOL-TRUST
## AP: AP-08(ACTIVE_LEDGER §4 by tool), AP-09(PE/BS re-read), AP-14(delegation overhead), AP-15(untrusted tool data)
