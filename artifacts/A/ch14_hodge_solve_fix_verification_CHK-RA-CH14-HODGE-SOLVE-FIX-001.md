# CHK-RA-CH14-HODGE-SOLVE-FIX-001 - Hodge Projection Solve Fix And Analytic Verification

Date: 2026-05-07

Scope: review implementation-level causes that can contaminate the capillary
Hodge diagnosis before changing the physical cochain theory.

## Problem

`CHK-RA-CH14-PROBLEM-LOCALIZE-001` separated two effects:

1. the trace-Riesz physical cochain still has a nonzero N32 static/dynamic
   residual that must be resolved at the transport-VJP/static-critical level;
2. the diagnostic Hodge projection itself was numerically contaminated because
   the normal equation
   `D_f M_f^{-1}D_f^T p = D_f c`
   was solved by applying LSMR directly to a singular pressure-gauge system.

The second effect is an implementation problem.  If `h=c-M_f^{-1}D_f^T p`
does not satisfy `D_f h=0` to roundoff, it is not a Hodge component and cannot
be interpreted physically.

## Fix

`src/twophase/coupling/closed_interface_riesz.py` now solves the normal equation
by pinning one pressure gauge before the direct solve:

```text
choose pin = argmax diag(D_f M_f^{-1}D_f^T)
set p_pin = 0
solve the reduced/gauge-fixed system
recover Pi_R c = M_f^{-1}D_f^T p
h = c - Pi_R c
```

This keeps the same `M_f,D_f` theorem object.  It changes only the numerical
solution of the gauge-null normal equation.

## Analytic Manufactured Range Gate

The finite-dimensional analytic check constructs

```text
p(x,y) = sin(2*pi*x) cos(3*pi*y)
       + 0.31 cos(pi*x + 0.2) sin(2*pi*y + 0.1)
c      = M_f^{-1} D_f^T p
```

Since `c` is exactly in the discrete pressure range by construction, the Hodge
part must be roundoff.

| quantity | value |
|---|---:|
| Hodge weighted L2 | `7.061307507637e-13` |
| recovered range Linf error | `2.273736754432e-12` |
| `||D_f h||_inf` | `7.275957614183e-11` |
| relative divergence residual | `7.673381434614e-16` |

## N32 Wall Trace Gate

The same projection is then applied to the real trace-Riesz N32 wall ellipse
cochain, including component-reaction removal.

| quantity | value |
|---|---:|
| corrected Hodge weighted L2 | `1.518271679206e-01` |
| `||D_f h||_inf` | `2.040131952263e-11` |
| component-reaction orthogonality | `2.602085213965e-18` |

The corrected Hodge norm is still nonzero, but now it is a legitimate
divergence-free quotient component.  This means the remaining problem is not
the Hodge projection algebra; it is the physical force-cochain/static-critical
construction.

## Tests

Remote-first validation:

```text
SSH_AUTH_SOCK=/private/tmp/codex-ssh-agent-test.sock make test \
  PYTEST_ARGS='twophase/tests/test_closed_interface_riesz.py twophase/tests/test_closed_interface_trace_riesz.py -q'
```

The repository test wrapper expanded this to the full CPU suite:

```text
610 passed, 32 skipped in 42.80s
```

## Verdict

The implementation-level projection error is fixed.  A pure analytic range
cochain is recovered to roundoff, and the N32 trace projection now satisfies
the same divergence and component orthogonality equations used by the theory.

This does not prove the capillary force is final.  It removes one contaminant
so the next evidence must focus on the true problem: building/verifying the
actual physical-transport endpoint VJP cochain and a discrete-critical static
trace gate, with reinitialization work kept out of capillary work.

[SOLID-X] Solver hygiene and tests only; no tested implementation deleted; no
FD/WENO/PPE fallback, damping/CFL workaround, curvature cap, smoothing,
benchmark branch, blanket `c -> Pi_R c`, or QP-as-physics route introduced.
