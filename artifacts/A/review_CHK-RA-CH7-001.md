# CHK-RA-CH7-001 strict narrative review

Scope: `paper/sections/07_time_integration.tex` with targeted consistency checks against Chapter 9 pressure-jump closure and Chapter 13 V7 time-accuracy diagnostics.

## Round 1 verdict: FAIL

### MAJOR-1: Chapter 7 did not carry the latest capillary closure

Chapter 7 still described surface tension mainly as "PPE 内蔵ジャンプ分解 CSF".  That no longer represented the current research content: Chapter 9 defines the canonical pressure-jump closure as an affine jump face cochain plus range projection / Hodge closure, and Chapter 13 validates the range-projected pressure-jump stack.  Leaving Chapter 7 at the older CSF wording made the time-integration chapter read as if raw jump insertion were the final formulation.

Fix: rewrote the surface-tension section title and narrative around `affine jump face cochain + 値域射影 CSF`, added the face-cochain range-projection relation, and clarified that this is an algebraic closure in the same `D_f A_f G_f` complex rather than a new physical model or alternate force route.

### MAJOR-2: The chapter overclaimed full second-order accuracy

Chapter 7 stated the whole adopted configuration as `O(Delta t^2)`, while Chapter 13 V7 records the actual two-phase capillary coupled-stack diagnostic as final local slope `1.59` and Type-D / interface-band-limited.  This was a narrative and logic conflict: the chapter's design-order language hid the latest measured limitation.

Fix: recast the accuracy section as "design order vs effective order"; kept `O(Delta t^2)` for smooth/homogeneous NS blocks, but added the capillary coupled domain row and tied the effective order to §13 V7 (`slope 1.59`, Type-D interface-band limitation).

### MINOR-1: "低次 FD Poisson" wording weakened the no-alternate-route contract

The DC summary said the high-order CCD Poisson residual is corrected by "低次 FD Poisson".  In context it meant a low-order auxiliary correction operator, but the wording could be mistaken for a fallback PPE route.

Fix: changed the phrase to "低次補助 Poisson" while retaining the high-order residual fixed-point contract.

## Round 2 verdict: PASS

No MAJOR-or-higher findings remain in Chapter 7 after remediation.

Checks:

- Chapter 7 now references the current affine jump / range-projection capillary closure.
- The global order claim is no longer presented as unconditional; smooth-domain design order and capillary coupled-stack effective order are separated.
- Trial-and-error / version-history language is not introduced.
- `git diff --check` passed.
- `make -C paper` passed and produced `paper/main.pdf` (246 pages).
- `paper/main.log` scan found no fatal/error/undefined-control matches and no overfull boxes.
