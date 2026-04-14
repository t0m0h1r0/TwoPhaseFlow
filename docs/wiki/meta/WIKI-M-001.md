---
id: WIKI-M-001
title: "Agent Meta System: v5.1 Concurrency-Aware Worktree Model"
status: ACTIVE
created: 2026-04-11
updated: 2026-04-11
depends_on: []
---

# Agent Meta System: v5.1 Concurrency-Aware Worktree Model

## Motivation

The baseline meta system (≤ v5.0) ran all Specialist agents in a single shared branch,
serialising all writes via sequential dispatch from ResearchArchitect. v5.1 enables
**true parallel Specialist execution** — multiple T/L/E/A domain Specialists can work
concurrently because each operates in an isolated git worktree with a file-based branch
lock, and merges back to `main` via a rebase-aware atomic push.

## Feature Flag

```yaml
# prompts/agents-{env}/_base.yaml
concurrency_profile: legacy   # default — old single-branch behaviour unchanged
# concurrency_profile: worktree  # opt-in for parallel specialist sessions
```

When `legacy`, all v5.1 operators (GIT-WORKTREE-ADD, LOCK-ACQUIRE, GIT-ATOMIC-PUSH,
LOCK-RELEASE) are **no-ops** — the old GIT-04 raw push applies. Flip only when the
orchestrating session explicitly sets the flag.

## Architecture: T/L/E/A Nodes

Each Specialist domain maps to a Node role in the concurrency graph:

| Node | Domain | Branch pattern |
|------|--------|---------------|
| T-Node | TheoryArchitect | `dev/T/TheoryArchitect/{task_id}` |
| L-Node | CodeArchitect / RefactorExpert / LogicImplementer | `dev/L/{agent}/{task_id}` |
| E-Node | ExperimentRunner | `dev/E/ExperimentRunner/{task_id}` |
| A-Node | PaperWriter | `dev/A/PaperWriter/{task_id}` |

Nodes are independent — the T-Node and L-Node may write concurrently because they touch
disjoint scopes (`docs/memo/` vs `src/twophase/`).

## Protocol Sequence

```
1. GIT-WORKTREE-ADD  →  create .claude/worktrees/{slug}/ on branch dev/{Domain}/{agent}/{task_id}
2. LOCK-ACQUIRE      →  write docs/locks/{branch_slug}.lock.json (session_id, timestamp)
                         + append row to docs/02_ACTIVE_LEDGER.md §4 BRANCH_LOCK_REGISTRY
3. [Specialist body: P-E-V-A loop, max 5 iterations per φ5 Bounded Autonomy]
4. GIT-ATOMIC-PUSH   →  git fetch origin; git rebase origin/{base}; git push
                         STOP-11 on rebase conflict (lock retained; human resolves)
5. LOCK-RELEASE      →  delete docs/locks/{branch_slug}.lock.json
                         + update BRANCH_LOCK_REGISTRY row (status: RELEASED)
6. HAND-02 RETURN    →  branch_lock_acquired: false
```

## Lock File Schema (`docs/locks/{slug}.lock.json`)

```json
{
  "session_id": "<uuid-v4>",
  "branch": "dev/L/CodeArchitect/{task_id}",
  "acquired_at": "<ISO-8601>",
  "owner": "CodeArchitect"
}
```

## STOP Conditions (v5.1 only)

| Code | Trigger | Response |
|------|---------|----------|
| STOP-09 | Agent attempts to delete/overwrite base worktree directory | Hard stop; no recovery |
| STOP-10 | LOCK-ACQUIRE collision (lock exists, different session_id) OR LOCK-RELEASE without ownership | CONTAMINATION RETURN; human adjudicates |
| STOP-11 | GIT-ATOMIC-PUSH rebase step conflicts with `origin/{base}` | STOP-SOFT; `git rebase --abort`; lock retained; human resolves rebase, agent resumes |

STOP-09/10/11 only fire when `concurrency_profile == "worktree"`.

## BRANCH_LOCK_REGISTRY

Stored in `docs/02_ACTIVE_LEDGER.md §4`. Append-only log of all lock lifecycle events.
Acts as an audit trail for concurrent session debugging.

## Source

- `prompts/meta/meta-ops.md §GIT-WORKTREE-ADD`
- `prompts/meta/meta-ops.md §LOCK-ACQUIRE`
- `prompts/meta/meta-ops.md §LOCK-RELEASE`
- `prompts/meta/meta-ops.md §GIT-ATOMIC-PUSH`
- `prompts/meta/meta-ops.md §STOP CONDITIONS (STOP-09/10/11)`
- `prompts/agents-{env}/_base.yaml :: concurrency_profile`
- Merged: `a510e52` meta(v5.1): CHK-114

## Related entries

- [[WIKI-M-002]] v4.1 Protocol — Schema-in-Code + CoVe + JIT (companion optimization)
