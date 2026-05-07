# CHK-RA-CH14-PROBLEM-LOCALIZE-001 - Efficient Problem-Localization Probes

Date: 2026-05-07
Branch: `codex/ra-ch14-capillary-virtual-work-20260506`

## Goal

Identify the shortest route to the remaining ch14 capillary/reinit problem.
Avoid more long T-runs until the algebraic/theorem branches are separated.

The efficient strategy was to run local deterministic N=32 offline probes on
existing operators and saved fields:

1. actual transport endpoint VJP check;
2. Hodge projection solve accuracy check;
3. production metric replacement check;
4. projection algebra check through exact pinned solves;
5. reinit defect classification from existing diagnostics.

No production numerical behavior was changed.

## Probe 1: Actual Transport VJP

Question:

```text
Does the current trace-Riesz cochain represent dS_h for the actual
FCCD face-velocity transport endpoint q_T?
```

Method:

```text
psi0 = N32 ch14 ellipse
q_+(dt) = FCCDLevelSetAdvection.advance_with_face_velocity(psi0, +u_f, dt)
q_-(dt) = FCCDLevelSetAdvection.advance_with_face_velocity(psi0, -u_f, dt)
FD(u) = [S_h(q_+(dt)) - S_h(q_-(dt))] / (2 dt)
Pred(u) = - <M_f c_trace, u_f>
```

The same fixed trace surface functional `S_h` and current
`closed_interface_trace_riesz_cochain` were used.  Reinit, grid rebuild, and
mass correction were excluded to isolate the physical transport endpoint.

Result:

| velocity | `Pred` | `FD` as `dt -> 0` | unsigned residual |
|---|---:|---:|---:|
| trig_1_2 | `-1.716e-03` | `-6.233e-01` | `0.995` |
| trig_2_1 | `4.232e-02` | `2.688e-01` | `0.728` |
| trig_2_3 | `-3.004e-02` | `-1.544e-01` | `0.674` |
| trig_3_2 | `-6.919e-02` | `-5.773e-01` | `0.786` |
| trig_3_4 | `5.330e-02` | `7.230e-01` | `0.863` |
| normalized surface acceleration | `-3.381e-01` | `9.333e-01` | O(`0.47`) even ignoring sign |
| normalized volume reaction | `3.806e-01` | `-1.019e+00` | O(`0.46`) even ignoring sign |

The finite-difference values were stable across `dt=1e-5,3e-5,1e-4`.

Verdict:

```text
SUPPORTED: the current C_K/P1 trace velocity map is not the VJP of the actual
FCCD physical transport endpoint q_T.
```

This is the main theorem-level cause.  The old unit tests prove internal
adjointness of `C_K` to its own pullback, not that `C_K = d(q_T)` for
production transport.

## Probe 2: Hodge Projection Solve Accuracy

Question:

```text
Is trace-Riesz static-current worsening partly caused by the Hodge projection
solve, independent of the cochain definition?
```

First, the analytic sparse divergence matrix used by the trace Hodge code was
checked against production `div_op.divergence_from_faces`:

```text
periodic D consistency: err 7.105e-15, rel 1.819e-16
wall     D consistency: err 7.105e-15, rel 1.819e-16
```

So the matrix assembly itself is not the mismatch.

Then the solve was checked on the N32 trace-Riesz static field.  The current
implementation uses sparse LSMR on the singular normal equation:

```text
normal_matrix = D M_f^{-1} D^T
normal_matrix p = D c
```

Result:

| solve | iterations | residual norm | `||D h||_inf` |
|---|---:|---:|---:|
| current/default LSMR | `1089` | `1.161e+00` | `2.074e-01` |
| tight LSMR, maxiter 20000 | `20000` | `2.569e-01` | `3.507e-02` |
| pinned sparse direct solve | n/a | n/a | `2.145e-14` |

The saved production diagnostics show the same issue:

```text
trace static N32/T1 capillary_hodge_divergence_linf max = 1.264e-02
trace oscillating N32/T1 capillary_hodge_divergence_linf max = 3.372e-02
component route static N32/T1 capillary_hodge_divergence_linf max = 3.324e-11
component route oscillating N32/T1 capillary_hodge_divergence_linf max = 3.285e-09
```

Verdict:

```text
SUPPORTED: the trace-Riesz Hodge projection is not solving the pressure-range
projection accurately enough.  This is a near-term, high-leverage defect.
```

It is not the only cause, because an exact projection still leaves a nonzero
static/dynamic residual, but it clearly contaminates the trace route.

## Probe 3: Exact Projection Size

Question:

```text
If the trace Hodge solve is made exact, does the problem disappear?
```

Using pinned sparse direct solves on the saved N32/T1 fields:

| field | exact corrected Hodge norm | exact `||D h||_inf` | current LSMR Hodge norm | current `||D h||_inf` | current/exact norm |
|---|---:|---:|---:|---:|---:|
| static trace NPZ | `2.017e-03` | `6.992e-16` | `7.998e-03` | `3.499e-02` | `3.966` |
| oscillating trace NPZ | `4.625e-03` | `9.227e-16` | `1.129e-02` | `4.931e-02` | `2.440` |

Verdict:

```text
The solve defect is large enough to explain much of the trace-Riesz static
worsening, but exact projection still does not make the trace cochain a
static/dynamic theorem-grade force.  After fixing the solve, the actual
transport VJP remains the main target.
```

## Probe 4: Production Metric Replacement

Question:

```text
Is arithmetic face density vs affine-jump production metric the primary
reason trace-Riesz fails?
```

The trace cochain was recomputed offline with production-style affine
`measure / alpha_f` weights.

Result:

| field | arithmetic exact Hodge | production-metric exact Hodge | beta arithmetic | beta production |
|---|---:|---:|---:|---:|
| static | `2.017e-03` | `2.044e-03` | `-2.233e-01` | `-2.227e-01` |
| oscillating | `4.625e-03` | `4.621e-03` | `-2.289e-01` | `-2.280e-01` |

Verdict:

```text
FALSIFIED AS PRIMARY: metric mismatch is a theorem violation and should be
cleaned up, but it is not the main numerical cause of the current N32 failures.
```

## Probe 5: Projection Algebra

The exact pinned projection gives `D h` at roundoff and the component
coefficient is well-defined.  The current non-orthogonality observed in the
trace route is therefore a consequence of the inaccurate LSMR projection solve,
not a separate failure of the one-component Gram projection formula.

Verdict:

```text
Projection algebra is not the first thing to redesign.  The solve must be made
accurate; then the cochain/VJP defect remains.
```

## Reinit Classification

Existing N32/T1 reinit diagnostics remain decisive:

```text
max |Delta S_reinit|      1.27103e-02
max reinit Linf delta     1.80338e-01
max zero-level movement   9.72e-03
zero-crossing changes     144
```

Verdict:

```text
Reinit/profile repair is a separate representation defect, but it is not the
sole force-side cause: no-reinit and static no-reinit probes still expose
incorrect capillary cochains.
```

## Prioritized Cause List

1. **Actual transport VJP mismatch**: current `C_K` is not `d(q_T)` for
   production FCCD face transport.  This is the deepest force-side cause.
2. **Trace Hodge solve failure**: current sparse LSMR projection leaves
   `D h = O(1e-2..1e-1)` instead of roundoff.  This is the fastest
   high-leverage defect to fix or eliminate as a contaminant.
3. **Reinit/profile projection work**: significant for reinit-on runs and must
   stay outside capillary work unless replaced by a physical-time conservative
   profile-control flux.
4. **Production metric mismatch**: real theorem cleanup, but not a primary
   N32 numerical driver in the measured probes.

## Recommended Next Step

The fastest path to problem isolation is:

```text
Step A: replace the trace Hodge projection solve in diagnostic/runtime path
        with a pinned/gauge-fixed solve or an equivalent robust SPD solver,
        then rerun static/oscillating N32/T1.

Step B: if static improves but dynamics remain wrong, implement the actual
        FCCD transport-endpoint VJP test as a permanent gate and construct
        c_sigma from that VJP, not from reconstructed-nodal P1 trace velocity.
```

This avoids wasting time on metric tuning, Rayleigh rescaling, CFL/damping, or
additional long horizon plots before the algebra is clean.

## Validation

Commands run:

```text
PYTHONPATH=src ../../../.venv/bin/python3 <offline VJP/Hodge probes>
git diff --check
```

[SOLID-X] Verification/docs only; no production force, PPE/corrector,
transport, reinit, YAML, damping, CFL, curvature cap, smoothing, fallback,
benchmark branch, blanket `c -> Pi_R c`, or QP-as-physics path was introduced.
