# CHK-RA-CH12-PARTII-001: Part II -> Chapter 12/13 Coverage Audit

Date: 2026-05-07
Branch: `codex/ra-ch12-partii-audit-20260507`
Worktree: `.claude/worktrees/codex-ra-ch12-partii-audit-20260507`

## Scope

User policy: Chapter 12 should contain unit/component tests only. Content that belongs in Chapter 13 should be written in Chapter 13; do not force all Part II content into Chapter 12.

Reviewed Part II chapters:

- Ch.4: CCD/DCCD/UCCD6/FCCD and face-jet primitives.
- Ch.5: CLS stages, Ridge--Eikonal, physical transport vs reinit projection split.
- Ch.6: per-variable operator assignment, momentum advection, full-stress viscosity.
- Ch.7: time integration, capillary work endpoint, IPC ordering.
- Ch.8: collocated pressure, BF principles, same-face pressure/capillary closure.
- Ch.9: pressure-jump PPE, HFE, DC, capillary Hodge/range projection, gauge.
- Ch.10: nonuniform grid, metric/FCCD/Ridge--Eikonal D1--D4 conditions.
- Ch.11: seven-step integrated NS update and pure FCCD DNS positioning.

Reviewed Chapter 12 U-series:

- U1: CCD/DCCD/UCCD6/FCCD.
- U2: CCD-Poisson and reduced FVM-PPE Neumann gauge.
- U3: nonuniform CCD/FCCD and D1--D4 metric diagnostics.
- U4: Godunov Eikonal and DGR comparison primitive.
- U5: Heaviside/delta moments and epsilon sensitivity.
- U6: DC route guard and HFE unit accuracy.
- U7: reduced BF static droplet one-step and face-mu interpolation.
- U8: TVD-RK3/EXT2/implicit-BDF2/3-layer BDF2 unit time tests.
- U9: DCCD-on-pressure negation.

## Findings

### F1: Chapter 12 scope mixed unit and integrated wording

Status: fixed in paper.

The original Chapter 12 purpose text mentioned the seven-step Predictor--PPE--Corrector algorithm while also limiting the target range to unit-testable primitives. This made Chapter 12 sound responsible for integrated algorithm coverage, which conflicts with the intended division: unit tests in Chapter 12, integrated tests in Chapter 13.

Patch:

- `paper/sections/12_component_verification.tex`
  - Clarified that Chapter 12 covers only Part II primitives separable into component tests.
  - Explicitly routed Ch.11 seven-step ordering, pressure-history face data, projection-native face velocity, capillary closure, and pressure-jump stack time evolution to Chapter 13.

### F2: Part II major-content coverage boundary was implicit

Status: fixed in paper.

Chapter 12 already had U1--U9 and a U-to-V bridge, but it did not explicitly map the major Part II claims into "unit-testable in Ch.12" vs "integration-only in Ch.13." This made it hard to tell whether missing items were omissions or deliberate routing.

Patch:

- Added `tab:partii_component_integration_boundary` in `paper/sections/12_component_verification.tex`.
- The table maps CCD/FCCD, CLS/Ridge--Eikonal, per-variable operator assignment, time integration, BF pressure, pressure-jump PPE/HFE/DC/capillary Hodge, nonuniform grid, and the Ch.11 full algorithm to the correct Ch.12 or Ch.13 verification lane.

### F3: Summary bridge under-specified Ch.13 responsibilities

Status: fixed in paper.

Chapter 12 summary did route several coupled effects to Chapter 13, but it did not list the full set now emphasized in Part II: face-state handoff, affine pressure-history faces, projection-native face velocity, and seven-step ordering.

Patch:

- `paper/sections/12h_summary.tex`
  - Revised opening summary to state that U1--U9 cover only unit-testable primitives.
  - Added next-chapter required effects for seven-step ordering and same-face data handoff.
  - Extended `tab:U_to_V_bridge` with rows for momentum/viscous NS residuals and seven-step face-data handoff.

## Experiment Decision

No new Chapter 12 experiments were required in this round.

Reason: the uncovered Part II items are integrated contracts by construction. Chapter 13 already contains V1--V10 coverage for:

- V6/V7/V9: range-projected pressure-jump stack, HFE, DC, capillary range projection, projection-native face closure, affine pressure-history faces.
- V10-a/b: FCCD/TVD-RK3 CLS transport, Ridge--Eikonal reinit, mass correction.
- V1/V2/V7: NS residual/time coupling.
- V3/V5/V8: BF static and spurious-current long-time behavior.

Adding these to Chapter 12 would blur the component/integration boundary and duplicate Chapter 13.

## Rounds

### Round 1

Result: findings F1--F3.

Action: revise Chapter 12 scope and bridge tables; no experiment rerun.

### Round 2

Post-patch review criterion:

- Does Chapter 12 only claim unit/component verification? Yes.
- Are integrated Part II constructs routed to Chapter 13? Yes.
- Are Part II major contents still traceable from Ch.12 U-tests into Ch.13 V-tests? Yes, via `tab:partii_component_integration_boundary` and `tab:U_to_V_bridge`.

Result: no remaining Chapter 12 overfill or omission finding under the user policy.

## Files Updated

- `artifacts/A/review_CHK-RA-CH12-PARTII-001.md`
- `docs/02_ACTIVE_LEDGER.md`
- `paper/sections/12_component_verification.tex`
- `paper/sections/12h_summary.tex`
