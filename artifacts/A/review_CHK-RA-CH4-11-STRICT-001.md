# CHK-RA-CH4-11-STRICT-001 Review

Scope: Chapters 4--11 paper narrative, notation, structure, and latest-stack consistency.

Policy: repeat strict reviewer rounds until no MAJOR+ findings remain or the round count exceeds 20.

## Round 1 Verdict: FAIL

MAJOR-1 -- Chapter 7 made the standard capillary closure look like CSF again.

Evidence: §7 tables and headings described the standard surface-tension path as "affine jump face cochain + 値域射影 CSF" and "ジャンプ分解 CSF". This contradicted the current §9/§11 stack, where water--air two-phase capillarity is a pressure-jump face cochain projected into the PPE/corrector range, not a CSF body force.

Remediation: Rewrote §7 terminology to "affine pressure-jump face cochain + 値域射影" and kept CSF only as the rejected/reduced body-force model.

MAJOR-2 -- Chapter 6 blurred reduced CSF face-flux logic with the standard pressure-jump path.

Evidence: §6.0/§6.2 used `pressure/CSF/convective flux` as the generic FCCD face-locus contract. That made FCCD Option B look like the standard two-phase capillary closure rather than a reduced CSF diagnostic and pure-FCCD boundary construction.

Remediation: Reframed Option B/C as role-specific: UCCD6 remains standard bulk momentum, reduced CSF uses FCCD face flux for pressure/capillary/convective co-location, and the standard pressure-jump route uses the same-locus comparison for capillary face cochains and canonical face correction.

MAJOR-3 -- Chapter 10/11 still contained process-language traces.

Evidence: "現行", "switch 診断", "実装ガイド", and "cadence tuning" made parts of the nonuniform-grid and full-step narratives read like change history rather than final paper contracts.

Remediation: Replaced process wording with paper-facing terms: verified paths became "本稿で検証する経路" / "縮約検証経路"; reinitialization guidance became "比較経路条件" and "再初期化頻度の調整".

## Round 2 Verdict: FAIL

MAJOR-4 -- Chapter 8 still promoted `DC k=3` to a standard closure element.

Evidence: §8d/§8e stated "GFM/affine-jump + HFE + DC k=3 + range projection" as the standard BF closure. This conflicted with §9d, where the closure contract is the DC residual criterion and `k=3` is only a practical component-verification cap.

Remediation: Replaced the standard closure phrase with "DC 残差契約" and explicitly scoped fixed `k=3` to the component-test practical upper bound, not the BF/PPE accuracy contract.

MAJOR-5 -- Chapter 6's scheme table still placed one-fluid PPE beside affine-jump PPE.

Evidence: §6b listed "一括 PPE または affine-jump PPE + capillary range projection" under pressure/capillary closure, which weakened the chapter-level distinction between reduced contrast routes and the current two-phase standard.

Remediation: Rewrote the table row: the two-phase standard is affine-jump PPE + capillary range projection; one-fluid PPE is only a reduced/contrast path. The footnote now ties the observed orders to the DC residual contract, with `k=3` only as an observed practical cap.

## Round 3 Verdict: PASS

MAJOR+ findings: 0.

Targeted rescans found no remaining chapter-4--11 hits for obsolete standard-route phrases: `値域射影 CSF`, `ジャンプ分解 CSF`, `pressure/CSF`, `一括 PPE または affine-jump`, `DC k=3`, `現行`, `実装ガイド`, `switch 診断`, `V[0-9] 診断`, `RCA`, `TBD`, or `未完`.

Stop condition reached at Round 3: no MAJOR+ findings remain.

## Validation

- `git diff --check`: PASS.
- `make -C paper`: PASS (`paper/main.pdf`, 246 pages).
- `paper/main.log` fatal/error/undefined-reference/undefined-citation/overfull/underfull scan: PASS.

[SOLID-X] Paper/review/bookkeeping only; no `src/twophase/`, experiment script, config, or result change; no tested implementation deleted; no FD/WENO/PPE fallback, damping/CFL workaround, curvature cap, smoothing, masked-output fallback, or alternate pressure scheme introduced.
