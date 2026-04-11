# docs/locks/ — Branch Lock Ephemeral Store (v5.1)

Introduced in meta v5.1.0 (Concurrency-Aware). See `prompts/meta/meta-ops.md §LOCK-ACQUIRE` / `§LOCK-RELEASE` and `docs/02_ACTIVE_LEDGER.md §4 BRANCH_LOCK_REGISTRY` for the canonical protocol.

## Purpose

Enables **structural** Git conflict avoidance when multiple Claude Code sessions run concurrently against this repository. A session MUST hold a lock on its working branch before any write; DOM-02 territory guard composes with this branch-level guard.

## Two-file model

- **Canonical registry** — `docs/02_ACTIVE_LEDGER.md §4 BRANCH_LOCK_REGISTRY` (YAML table, audit trail, survives as git history).
- **Ephemeral lock file** — `docs/locks/{branch_slug}.lock.json` (this directory).

The lock file is truth for the tool wrapper; the ledger is truth for humans. Any divergence between the two (lock file present + ledger absent, or vice versa) → **STOP-10 CONTAMINATION_GUARD**.

## File format (`{branch_slug}.lock.json`)

```json
{
  "branch": "dev/L/CodeArchitect/chk-106",
  "branch_slug": "dev-L-CodeArchitect-chk-106",
  "session_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "worktree_path": "../wt/f47ac10b/dev-L-CodeArchitect-chk-106",
  "holder_agent": "CodeArchitect",
  "acquired_at": "2026-04-11T09:30:00Z",
  "expires_at": "2026-04-12T09:30:00Z",
  "meta_version": "5.1.0"
}
```

`branch_slug` = `branch` with `/` replaced by `-` (filesystem-safe). All fields required.

## Lifecycle

1. **Acquire** (`LOCK-ACQUIRE branch={branch}`)
   - Compute `branch_slug` and candidate path `docs/locks/{branch_slug}.lock.json`.
   - Create the file **atomically** via `O_EXCL` (`open(..., 'x')`). If the file already exists → another session owns the lock → **STOP-10** and halt.
   - Append row to `docs/02_ACTIVE_LEDGER.md §4 BRANCH_LOCK_REGISTRY` (grouped commit with the first write under the lock).
   - Consumers of the branch are now guarded.

2. **Release** (`LOCK-RELEASE branch={branch}`)
   - Verify the on-disk lock file's `session_id` matches the releaser. Mismatch → **STOP-10 foreign lock force**.
   - Delete the file.
   - Strike-through / remove the §4 registry row (or set `released_at`).

3. **Stale recovery** (operational, human-initiated)
   - A lock with `expires_at` in the past (default TTL 24 h) is **stale**.
   - Do NOT auto-delete — a crashed session may have left real mutations on the branch.
   - Recovery procedure: human inspects the holding session's worktree + branch state, then runs `LOCK-RELEASE --force` which records an explicit stale-recovery entry in §4 with rationale.

## Guarantees

- **Mutual exclusion**: at most one session holds a given branch lock at any moment (`O_EXCL` provides the atomicity).
- **Audit**: §4 registry is git-tracked; every acquire/release is in history.
- **Crash-safe**: a crashed session leaves both the file and the §4 row. Neither is silently cleaned up.
- **Human override**: `--force` release is always available, with mandatory rationale in §4.

## What this directory does NOT do

- It is **not** a mutex for individual files inside a branch — DOM-01 / DOM-02 territory guards handle that layer.
- It is **not** a replacement for `git worktree` — worktrees provide the filesystem isolation; this directory provides the branch-ownership semaphore on top.
- It does **not** prevent pushes to `origin` — GIT-ATOMIC-PUSH handles the remote race via fetch + rebase.

## References

- `prompts/meta/meta-ops.md §LOCK-ACQUIRE` / `§LOCK-RELEASE`
- `prompts/meta/meta-ops.md §HAND-01..03` (envelopes carry `branch_lock_acquired` field)
- `prompts/meta/schemas/hand_schema.json` (canonical envelope schema)
- `prompts/meta/meta-core.md §φ4.1 Session-Isolated State`
- `prompts/meta/meta-core.md §A8.1 Worktree-First Parallelism`
- `docs/02_ACTIVE_LEDGER.md §4 BRANCH_LOCK_REGISTRY`
