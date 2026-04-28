# CHK-RA-CH12-001 — Chapter 12/13 ResearchArchitect Peer Review Memo

## Scope

- Role: ResearchArchitect dispatch to PaperReviewer.
- Session: `CHK-RA-CH12-001`.
- Worktree: `worktree-ra-ch12-13-review-retry-20260428`.
- Source fork: `/Users/tomohiro/Downloads/TwoPhaseFlow/.claude/worktrees/worktree-ch12-13-peer-review-20260428`.
- Reviewed scope: `paper/sections/12_*.tex`, `paper/sections/13_*.tex`, `experiment/ch12/exp_U*.py`, `experiment/ch13/exp_V*.py`, and stated result artifact paths.

## Deliverables

- `artifacts/A/review_ch12_researcharchitect_20260428.md`
- `artifacts/A/review_ch13_researcharchitect_20260428.md`
- This companion memo.

## Verdict Summary

| Chapter | Verdict | Findings | Primary reason |
| --- | --- | --- | --- |
| Chapter 12 | FAIL | 13 FATAL + 5 MAJOR + 5 MINOR | Summary rows and several U-test claims violate PR-5/A3 traceability between paper claims, scripts, and reproduced results. |
| Chapter 13 | FAIL | 11 FATAL + 4 MAJOR + 3 MINOR | V1-V10 repeatedly claim production CCD / IMEX-BDF2 / split-PPE / DC / HFE / Ridge-Eikonal paths that the reviewed scripts do not execute. |

## Key Cross-Cutting Risks

- Paper tables cite `experiment/ch13/results/V[1-10]_*/data.npz`, but this review checkout has no `experiment/ch13/results/` directory and no tracked result files under that path.
- Multiple chapter 13 scripts are reduced standalone probes, while the prose presents them as integrated production-pipeline verification.
- Chapter 12 and 13 both need explicit equation -> discretization -> code -> data contracts before paper edits or reruns are treated as submission evidence.

## Recommended Next CHKs

1. Define authoritative U1-U9 and V1-V10 contracts, including equation, algorithm path, script, result package, figure provenance, and pass/fail criterion.
2. Decide which reduced probes are acceptable as reduced probes and rewrite the paper claims accordingly; replace only tests that must be production-pipeline evidence.
3. Restore or regenerate auditable result packages, especially `experiment/ch13/results/V[1-10]_*/data.npz`, or correct the provenance statement to match the archived package actually available.
4. Re-run PaperReviewer after contract/provenance fixes and require 0 FATAL + 0 MAJOR for PASS.

## Status

ResearchArchitect/PaperReviewer review is complete. No paper or experiment implementation edits were made in this CHK because PaperReviewer owns review artifacts only.
