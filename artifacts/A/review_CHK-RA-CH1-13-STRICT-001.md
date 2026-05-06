# CHK-RA-CH1-13-STRICT-001 Review Log

Scope: paper chapters 1--13, with adjacent consistency checks only where needed.

Policy:
- Worktree: `.claude/worktrees/codex-ra-ch1-13-strict-review-20260506`
- Branch: `codex/ra-ch1-13-strict-review-20260506`
- Main merge: forbidden until explicit user instruction; no-ff when instructed.
- Stop rule: repeat until no MAJOR+ findings remain or round count exceeds 20.

## Round 1

Verdict: FAIL before remediation; MAJOR findings present.

Findings:
- MAJOR-1: Chapter 1 stated the verified scope as V6/V7/V10 only, while the actual Chapter 13 contract is V1--V10 with V6/V7/V9 as the range-projected pressure-jump stack and V3/V5/V8 as CSF/BF reductions. This made the paper's opening claim narrower and less coherent than the latest research result.
- MAJOR-2: The learning roadmap jumped from component verification to multiphase benchmarks, omitting Chapter 13 integrated verification as the proof bridge from U1--U9 to V1--V10.
- MAJOR-3: Chapter 2's CSF/BF preview pointed readers to V6 for BF curvature/spurious-current suppression, conflating the CSF/BF reduced path with the high-density pressure-jump stack.
- MAJOR-4: Chapter 11 still explained V7's sub-second-order behavior as reinitialization cadence / curvature time-lag limited, contradicting the latest V7 narrative that identifies capillary pressure-jump / affine FCCD projection interface-band low regularity as the limiter.
- MINOR-1: Chapter 7 used "検証章" for Chapter 14 benchmark labels, making the Chapter 13 verification / Chapter 14 validation split ambiguous.
- MINOR-2: Chapter 13 used process-flavored wording ("現行", "lever") in V9 local-epsilon statements.

Remediation:
- Rewrote the Chapter 1 verified-scope paragraph and failure-example bridge so V1--V10, V3/V5/V8, V6/V7/V9, and V10-a/b are all placed in the correct proof roles.
- Inserted Chapter 13 as an explicit learning-roadmap step between component verification and benchmarks.
- Recast the Chapter 2 CSF/BF preview so CSF/BF reductions point to V3/V5/V8 and pressure-jump stack evidence points to V6/V7/V9.
- Replaced the stale Chapter 11 V7 explanation with the current interface-band low-regularity limiter.
- Renamed Chapter 7 references to Chapter 14 as "ベンチマーク章" and Chapter 13 V7 as the integrated-verification record.
- Removed process-flavored V9 wording from Chapter 13 captions and summary.

Targeted scans after remediation:
- `現行|lever|再初期化頻度と曲率の時間遅れ|検証章|V6：静止液滴 8-step|6ステップ`: PASS except the intentional Chapter 11 phrase "検証章の対応".

## Round 2

Verdict: FAIL before remediation; MAJOR traceability finding present.

Findings:
- MAJOR-5: U6-to-V traceability still named only V6/V7 in the HFE/DC primitive and downstream high-density stack notes, while Chapter 13 defines V6/V7/V9 as the measured range-projected pressure-jump stack family. This left V9 looking like a later side probe rather than part of the latest stack contract.

Remediation:
- Updated U6 and the V5/V8 bridge text to name V6/V7/V9 as the integrated behavior tied to the U6 primitive, while preserving V6/V7 as the density/time axes and V9 as the nominal/local switch boundedness diagnostic.

## Round 3

Verdict: FAIL before remediation; no MAJOR findings, wording cleanup required before pass.

Findings:
- MINOR-3: U2 used "現行" for the Neumann-gauge reduced PPE, which reads like version history rather than a paper-level contract.

Remediation:
- Replaced the U2 wording with "本稿の" so the statement names the adopted contract rather than the current implementation state.
