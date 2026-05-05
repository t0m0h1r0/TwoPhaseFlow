# CHK-RA-WIKI-CURATION-001 — Wiki Curation Review

## Scope

Reviewed `docs/wiki` active retrieval content for stale, disproven, or
superseded information.  The review focused on wiki entries that could mislead
future ResearchArchitect/code/paper work if read as current policy.

## Findings And Actions

| Finding | Severity | Action |
|---|---|---|
| `docs/wiki/INDEX.md` claimed 315 entries while the wiki already contained 316 cards before this task. | MAJOR | Recomputed inventory after adding `WIKI-X-041`; index now records 317 entries and Cross-Domain 41. |
| Old WENO5/DCCD CLS transport guidance conflicted with the current paper's FCCD face-flux CLS contract. | MAJOR | Refreshed `WIKI-T-065` and `WIKI-X-031`; downgraded `WIKI-T-013` to REFERENCE and marked old DCCD reading historical. |
| `WIKI-X-032` presented an older WENO5/CN eight-phase algorithm as STABLE. | MAJOR | Marked `WIKI-X-032` SUPERSEDED by `WIKI-X-041` with a front-page curation note routing to paper §11 / `WIKI-T-101` / `WIKI-X-040`. |
| `WIKI-X-020` still routed sharp-interface pressure work through the older Ridge-Eikonal/GFM/HFE/IIM chain with Approach-B historical FD-probe context. | MAJOR | Marked `WIKI-X-020` SUPERSEDED and routed active work to affine-jump / projection-native face-space contracts. |
| `WIKI-X-014` and `WIKI-E-023` could be read as imposing a global `rho <= 20` density-ratio limit, contradicting current §14/V6 evidence. | MAJOR | Marked `WIKI-X-014` SUPERSEDED; added a bounded-reading note to `WIKI-E-023`. |
| `WIKI-E-030` remained indexed as `[OPEN]` despite CLOSED status and H-01 BF-residual verdict. | MAJOR | Updated title/index/tags and added a curation note preserving chronology as resolved evidence. |
| `WIKI-L-009` pointed to obsolete interface paths and called `DissipativeCCDAdvection` paper-primary. | MAJOR | Updated interface paths to owning subpackages and marked `FCCDLevelSetAdvection` paper-current. |
| `WIKI-T-058` exposed FD Hessian probe wording without a current-policy guardrail. | MINOR | Added curation note: Approach B is historical CHK-159 evidence only, not a production path. |

## Retention Policy

No wiki file was deleted.  Historical and negative knowledge remains available
for provenance, but active retrieval now starts at `WIKI-X-041` and
`WIKI-X-040`.  SUPERSEDED or REFERENCE cards must be read through their
front-page curation notes before being used.

## Validation

- `find docs/wiki -maxdepth 2 -type f -name 'WIKI-*.md' | wc -l` -> 317.
- Targeted stale scans checked WENO/DCCD/OPEN/density-limit/interface-path
  signatures; remaining matches are curation notes or superseded historical
  content.
- `git diff --check` passed.

## SOLID-X

Docs/wiki/artifact/ledger only.  No production code boundary changed, no tested
code deleted, and no FD/WENO/PPE fallback introduced.
