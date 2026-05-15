# CHK-RA-CH14-AO-FASTVOL-072

## User Question

Why do near-careless implementation mistakes happen even when the theory is
already established, why did review miss them, and what prevents recurrence?

## Root Cause

The root cause is not absence of physics or mathematics.  It is that the
established theory was treated as prose during implementation and review,
instead of being converted into a complete equation-to-code contract.

The repeated pattern was:

1. Review checked the modified file locally, not the entire path from equation
   to high-order operator, low-order/base operator, RHS transform, corrector,
   builder/factory, YAML, runner, diagnostics, and tests.
2. A3 traceability named the headline equation but did not force every
   coefficient, sign, gauge, metric, boundary path, time level, and epoch to be
   represented in code and tests.
3. Missing context could fall back to an older default law, hiding the error
   until an integrated run crossed the wrong route.
4. Diagnostics and production YAML could differ in pressure-history or grid
   preparation defaults, so a diagnostic pass was not always evidence for the
   production route.
5. GPU optimization review focused on D2H/H2D and launch counts before proving
   ownership, aliasing, and grid/rebuild epoch contracts.

## Why Review Failed

The review was not adversarial enough.  It asked "is this patch plausible?"
instead of "where else must this theory object appear, and what fails if that
place is wrong or missing?"

For established theory, a review must actively try to falsify the patch by
checking operator identity, context threading, nonuniform/periodic/cut-face
paths, interface-tracking rebuild epochs, diagnostic parity, and fail-close
behavior.

## Prevention

Added wiki memory:

- `docs/wiki/code/WIKI-L-046.md`
- `docs/wiki/INDEX.md` active retrieval gate

The new gate requires a contract table before coding established theory:

- theory symbol and discrete object;
- producer and all consumers;
- nonuniform metric and boundary paths;
- time level and invalidation epoch;
- backend residency and synchronization boundaries;
- fail-close condition;
- smallest regression that catches the violation.

## Practical Coding Rule

Before editing, say:

> What is the discrete object, who owns it, who consumes it, and what fails
> closed if it is missing?

If that cannot be answered, implementation has not started yet.
