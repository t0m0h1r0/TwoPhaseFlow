# CHK-RA-PAPER-CH1-11-PPE-DC-001 — paper Chapters 1--11 PPE/DC contract update

## Request

Reflect the rising-bubble blow-up RCA and the production PPE defect-correction
fix into paper Chapters 1--11.

## Scope

Updated only paper-facing prose/equations in Chapters 1--11 and ledger
bookkeeping.  No solver source, experiment YAML, experiment result, figure, or
Chapter 12+ result text was changed in this paper update.

## Changes

- Chapter 1 now states that defect correction is not certified by fixed
  iteration count or fixed relaxation; accepted pressure corrections must
  reduce the active PPE residual.
- Chapter 6 scheme-role table now describes DC acceptance as residual contract
  plus residual-decreasing update, not fixed-count precision.
- Chapter 8 projection derivation now states that a residual-growing pressure
  correction is a nonphysical pressure-reaction acceleration, not a harmless
  unresolved linear-solver error.
- Chapter 9 capillary component saddle now uses the projected-Hodge metric
  `Z_A(B_i)^T M_A Z_A(B_j)` and `Z_A(B_i)^T M_A Z_A(s)` instead of mixing
  unprojected components with projected residuals.
- Chapter 9 defect-correction section now defines the residual-minimizing
  update

```text
alpha_* = <r, L_H delta p> / <L_H delta p, L_H delta p>
```

  and records fixed relaxation as a backtracking candidate rather than a
  production acceptance condition.
- Chapter 11 full algorithm now uses "residual-decreasing DC" in the operator
  map, overview table, and Step 6 update sequence.
- Existing section/caption title math hits were wrapped with `texorpdfstring`
  so the paper-rule pre-compile scan passes.  These are formatting-only PDF
  bookmark fixes.

## Negative Knowledge Preserved

The paper now explicitly rejects the following readings:

- more fixed-relaxation corrections as a production cure;
- fixed relaxation constants as physics or accuracy certification;
- pressure filtering, DCCD post-filters, curvature caps, or CFL shrinkage as
  cures for a residual-growing pressure projection;
- component saddle systems assembled in a metric that is positive only under an
  exact self-adjoint projection.

## Validation Plan

- `git diff --check` PASS
- section/caption math-title scan required by paper rules PASS
- `make -C paper` PASS (`paper/main.pdf`, 264 pages)
- final log scan for LaTeX warnings/errors/undefined references: no matches
  other than the existing cleveref first-aid notice
