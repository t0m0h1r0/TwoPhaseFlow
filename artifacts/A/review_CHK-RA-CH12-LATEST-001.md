# CHK-RA-CH12-LATEST-001 Review

## Round 1

Verdict: FAIL (MAJOR findings present)

- MAJOR-1: U4 was titled and routed as Ridge--Eikonal while the tested primitive is Godunov pseudo-time Eikonal + DGR. This blurred two distinct geometry mechanisms and weakened the chapter structure.
- MAJOR-2: U7 treated FD2 mismatch as a checked item. Because mismatch is an operator-policy violation and the 1-step metric has low discriminatory power, presenting it as pass-level evidence undermined the DCCD/CCD pressure-gradient policy.
- MAJOR-3: U6 allowed the one-batch smoothed-Heaviside PPE high-density sweep to read like a successful high-density route when one parameter combination reached tolerance. The chapter must use it only as a route guard supporting phase-separated PPE+HFE.
- MAJOR-4: U2 and the bridge table used "current/standard PPE" wording for the FVM Neumann test. That made the reduced single-phase/BF PPE look like the latest pressure standard, conflicting with the pressure-jump phase-separated stack.
- MAJOR-5: U3 said D1--D4 activate sequentially for nonuniform grids, but the actual smooth probe only activates D4 while D1--D3 remain round-off zero. The narrative had to match the measured diagnostic.

Response:

- Renamed/rerouted U4 as Godunov Eikonal + DGR and explicitly separated Ridge--Eikonal single-shot diagnostics.
- Recast U7 mismatch as a negative control and removed it from positive pass logic.
- Recast U6-a as a route guard: high-density one-batch PPE remains outside the guaranteed primitive even if residuals improve for one parameter set.
- Reworded U2 as reduced Neumann FVM--PPE for single-phase/reduced BF paths and kept pressure-jump phase-separated PPE as the latest high-density standard.
- Corrected U3 D1--D4 wording to say the smooth probe validates D4 activation and D1--D3 non-activation.

## Round 2

Verdict: FAIL (MAJOR finding present)

- MAJOR-1: The U-to-V bridge still listed U7 as a direct primitive for the high-density pressure-jump stack. Since U7 is a reduced BF/CSF one-step test and its mismatch mode is explicitly a negative control, this could still make the latest stack look supported by the reduced route.

Response:

- Rewrote the bridge so the pressure-jump stack inherits U6/U8/U9, while U7 is named only as a reduced BF contrast.

## Round 3

Verdict: PASS (MAJOR+ findings: 0)

Targeted scans:

- No remaining positive-pass wording for FD2 mismatch.
- No remaining "current/standard PPE" wording that promotes reduced Neumann FVM--PPE to the latest high-density standard.
- U6 one-batch PPE wording is route-guard only.
- U7 is limited to reduced BF contrast when mentioned near V6/V7/V9 pressure-jump stack.
- U3 D1--D4 text now matches the measured smooth-probe behavior.
