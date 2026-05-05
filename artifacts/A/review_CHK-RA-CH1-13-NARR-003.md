# Review CHK-RA-CH1-13-NARR-003

Session: `CHK-RA-CH1-13-NARR-003`
Agent: ResearchArchitect
Branch: `ra-ch1-13-narr-review-r3-20260505`
Base: `main` at `ed7ef445`
Scope: `paper/sections/01*.tex`--`paper/sections/13*.tex`

## Verdict

PASS AFTER FIX. The strict rereview found one MAJOR narrative/logic drift after
the latest §14 face-space work: Chapters 1, 11, 12, and 13 still described the
reference stack mainly as FCCD/HFE/pressure-jump PPE/DC, while §9b/§14 had made
projection-native face velocity and affine pressure-history face acceleration
part of the actual discrete contract. The fixed narrative now carries the same
contract from the introduction through the algorithm and verification chapters.

## Findings And Fixes

### RA-CH1-13-NARR-003-01: §14 stack identity was missing face-space closure

Finding: Chapter 1 presented the technical core as CCD curvature, split PPE/DC,
and CCD gradient; Chapter 11 transported CLS with nodal velocity in the algorithm
summary; and Chapter 13's official §14 stack list omitted projection-native
face closure and affine pressure-history faces. A reviewer would read this as
two competing algorithms: the newer §9b/§14 face-space contract and an older
node-gradient / abbreviated stack.

Fix: Rewrote the Chapter 1 core claim and failure-mode response around FCCD
face flux/pressure gradient, HFE curvature, oriented pressure-jump split PPE/DC,
projection-native canonical face velocity, and affine-jump pressure-history
face acceleration. Updated Chapter 11's operator map, 7-stage table, CLS
transport equation, and pressure-history note so the algorithm consumes
canonical face velocity and preserves pressure history in face space. Updated
Chapter 13's formal stack list and V6/V7/V9 narratives to include the same
projection and pressure-history contract.

### RA-CH1-13-NARR-003-02: Bridge and summary tables used stale shorthand

Finding: Chapter 12's U-to-V bridge, U6 verification correspondence, V6 figure
note, V9 figure note, and the Chapter 13 error budget still used shortened
phrases such as `FCCD/HFE/pressure-jump/分相 PPE/DC stack`. Those were not false
in isolation, but they hid the new invariant that makes the current stack
different from the older pressure-jump-only wording.

Fix: Normalized the shorthand to `FCCD, HFE, pressure-jump PPE/DC,
projection-native face closure, affine pressure-history faces` where the table
or paragraph is specifically naming the §14 stack. The wording now leaves
generic CCD/FCCD/UCCD6 family references untouched where they are not stack
identity claims.

### RA-CH1-13-NARR-003-03: V1 figure note blurred the projection identity

Finding: The V1 vorticity figure note said `AB2 + PPE 射影`, while the adjacent
V1-b text explicitly treats the temporal sweep as AB2 predictor + non-incremental
standard PPE projection, not production IPC/rotational projection.

Fix: Rewrote the note to `AB2 predictor + standard PPE 射影`, matching the V1-b
Type-A revised criterion.

## Review Rounds

- Round 1: MAJOR found; §14 stack identity drift and nodal/face transport drift.
- Round 2: fixed root contract; stale-notation scan passed, but abbreviated stack summaries remained.
- Round 3: fixed Ch13 V6/V9/error-budget short forms; no new MAJOR.
- Round 4: fixed Ch12 bridge/U6 and long slash-chain notation; no new MAJOR.
- Round 5: final rereview and validation found no MAJOR+ findings; stop condition met before round 10.

## Validation

- `git diff --check` PASS.
- Targeted stale scan PASS for old V10 wording, raw `\bm{x}`/`\bm{u}`/`\bm U`,
  `\epsilon`, `TVD--RK3`, `IMEX--BDF2`, `AB2+IPC`, `AB2 + PPE`, and stale
  abbreviated §14 stack claims.
- `make -C paper` PASS; output `paper/main.pdf`, 242 pages.
- `paper/main.log` diagnostic tail scan found no `LaTeX Warning`, `Overfull`,
  `Underfull`, `Text page`, `Undefined control sequence`, or `Emergency stop`
  entries.

## SOLID-X

Paper/audit-only change. No production code boundary changed, no tested code
deleted, no FD/WENO/PPE fallback introduced, and no experiment data or figures
were modified.
