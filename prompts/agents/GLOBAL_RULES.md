# GLOBAL RULES — All Agents (inherited; do not restate per agent)

A1  token economy: diff > rewrite; reference > duplicate; compact > verbose
A2  external memory only: docs/ACTIVE_STATE.md, CHECKLIST.md, ASSUMPTION_LEDGER.md,
    LESSONS.md, ARCHITECTURE.md — append-only, ID-based (CHK, ASM, LES)
A3  3-layer traceability: equation → discretization → code (mandatory)
A4  layer isolation: one agent = one layer; cross-layer edit forbidden unless authorized
A5  solver purity: infra must not alter numerical results; invariant under I/O, logging, config
A6  diff-first output: no full file unless required; explain only what changed
A7  backward compatibility: upgrade by mapping; never discard meaning without deprecation
A8  branch governance:
    - domains: paper → `paper`; code → `code`; prompt → `prompt`
    - each domain follows 3-phase lifecycle: DRAFT → REVIEWED → VALIDATED
    - auto-commit at each phase boundary; auto-merge `{branch} → main` on VALIDATED
    - commit format: `{branch}: {phase} — {summary}` (phase = draft | reviewed | validated)
    - merge format:  `merge({branch} → main): {summary}`
    - each domain merges to `main` independently — no cross-domain wait required
    - direct `main` edits forbidden unless explicitly authorized

P1  layer stasis: when editing one layer, all others are READ-ONLY
P5  single-action: one agent, one objective per step
P6  bounded loops: maintain retry counter; escalate on threshold breach; never loop silently

Universal stop triggers:
- layer violation → STOP immediately
- axiom conflict → STOP; report before acting
- unresolvable ambiguity → ask user; never guess
