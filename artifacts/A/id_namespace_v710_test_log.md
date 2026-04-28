# Two-Worktree CHK Collision Test — v7.1.0 Verification Log

Date: 2026-04-28
Worktree: `worktree-ra-meta-id-namespace`
HEAD at test: `fedad58` (Step 7 commit; lint targets installed)

## Goal

Verify that worktree-namespaced ID scheme (Option A, plan §Decision)
eliminates the *semantic* CHK collision that historically forced manual
renumber at merge. Compare against legacy `CHK-NNN` (max+1) scheme as
control.

## Setup

```
git branch test-id-base HEAD          # scratch base off worktree HEAD
git worktree add /tmp/wt-test-base test-id-base
git worktree add /tmp/wt-test-a -b test-id-a test-id-base
git worktree add /tmp/wt-test-b -b test-id-b test-id-base
```

## Case 1 — v7.1.0 namespaced (TEST-A vs TEST-B)

| Worktree | Branch     | id_prefix | Row added              |
|----------|------------|-----------|------------------------|
| A        | test-id-a  | TEST-A    | `\| CHK-TEST-A-001 \| ...` |
| B        | test-id-b  | TEST-B    | `\| CHK-TEST-B-001 \| ...` |

Merge sequence into `test-id-base`:

```
$ git merge --no-ff test-id-a -m "merge A"          # rc=0, fast clean
$ git merge --no-ff test-id-b -m "merge B"
Auto-merging docs/02_ACTIVE_LEDGER.md
CONFLICT (content): Merge conflict in docs/02_ACTIVE_LEDGER.md
```

**Conflict is purely textual** (both branches appended to EOF; identical region).
Resolution: accept both lines as-is — **no renumber required, no human judgment
beyond "keep both"**.

```
$ make lint-ids
OK: no duplicate v7.1.0-namespaced IDs in docs/02_ACTIVE_LEDGER.md
$ grep -c '| CHK-TEST-' docs/02_ACTIVE_LEDGER.md
2
```

**Result**: PASS. IDs structurally distinct (`TEST-A` vs `TEST-B` prefix).
Trivial textual merge resolution. lint-ids exits 0.

## Case 2 — Legacy `CHK-NNN` control (max+1 scheme)

To demonstrate the historical pain point, we replay the same merge with
both worktrees emitting legacy form. Each independently picks `max+1`
from the same baseline (CHK-255 → CHK-256).

| Worktree | Branch    | Row added                                             |
|----------|-----------|-------------------------------------------------------|
| A        | legacy-a  | `\| CHK-256 \| ... LEGACY contention worktree A ...`  |
| B        | legacy-b  | `\| CHK-256 \| ... LEGACY contention worktree B ...`  |

Merge sequence:

```
$ git merge --no-ff legacy-a -m "merge legacy A"   # rc=0
$ git merge --no-ff legacy-b -m "merge legacy B"
CONFLICT (content): Merge conflict in docs/02_ACTIVE_LEDGER.md
# resolve: keep both lines as test (mirroring naïve human resolution)
$ git commit -am "merge legacy B (RESOLVED: keep both — but ID is duplicated!)"
$ grep -nE '\| CHK-256' docs/02_ACTIVE_LEDGER.md
281:| CHK-256 | ... LEGACY contention worktree A — naive max+1 |
282:| CHK-256 | ... LEGACY contention worktree B — naive max+1 |
```

**Result**: SEMANTIC COLLISION. Two distinct CHKs both labeled `CHK-256`.
Without out-of-band human renumber + downstream reference fix, the ledger
permanently violates ID uniqueness. This is the historical pattern
documented in plan §Context (CHK-246, CHK-161→167, CHK-225→226, etc.).

Note: `make lint-ids` does NOT flag this case — by design, legacy bare
`CHK-NNN` is grandfathered (forward-only migration). Schema validation in
HAND-03 (`kernel-roles.md` §SCHEMA EXTENSIONS v7.1.0) is the gate that
should prevent post-cutover agents from emitting legacy form.

## Summary

| Property                    | v7.1.0 namespaced | Legacy max+1 |
|-----------------------------|-------------------|--------------|
| ID uniqueness across merges | Structural        | Empirical (broken when parallel) |
| Merge conflict on EOF append| Yes (textual)     | Yes (textual + semantic) |
| Conflict resolution         | Trivial (keep both) | Requires renumber + ref-fix |
| `make lint-ids` post-merge  | rc=0 (PASS)       | rc=0 only because legacy is grandfathered |
| Renumber work               | Zero              | Mandatory                  |

The v7.1.0 scheme achieves the design goal: **eliminate renumber work at
merge time**. Textual merge conflicts on EOF append remain (line-based
git semantics) but are now mechanical to resolve.

## Cleanup

```
git worktree remove --force /tmp/wt-legacy-a /tmp/wt-legacy-b /tmp/wt-test-base
git branch -D test-id-base legacy-a legacy-b
```
