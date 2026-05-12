# CHK-RA-CH14-AO-FASTVOL-002 - AO-Fast approximation accuracy and DC theory

Date: 2026-05-11
Branch: `codex/ra-ch14-ao-fast-volume-20260511`
Worktree: `.claude/worktrees/codex-ra-ch14-ao-fast-volume-20260511`

## Scope

User request: prioritize theory, state the accuracy of any approximation, use
DC if it is useful, and advance the AO-Fast theory.

This is a theory/specification checkpoint.  It changes no solver source.

## Fixed-Stratum Accuracy Contract

On a regular SP-AO stratum, the sign pattern and edge-crossing pattern are
fixed.  For one active cell `C`, define

```text
gamma_C = min crossing-edge |phi_b - phi_a|,
m_C     = min node |phi_v|,
beta_C  = ||delta phi||_{infty,C} / min(gamma_C, m_C).
```

For `beta_C <= beta_* < 1`, the P1 cut geometry maps are smooth functions of
the local nodal gauge values.  The first-order frozen-stratum proposal obeys

```text
Q_h^S(phi+delta phi)_C
  = Q_h^S(phi)_C + J_q,C delta phi_C + R_Q,C,
|R_Q,C| <= C_Q |C| beta_C^2,

S_h^S(phi+delta phi)_C
  = S_h^S(phi)_C + dS_C delta phi_C + R_S,C,
|R_S,C| <= C_S |Gamma_C| beta_C^2.
```

The constants are local case-table/aspect-ratio/margin constants.  They do not
scale with the global number of cells.  If a second-order secant or Hessian
candidate is implemented, its advertised proposal accuracy is `O(beta_C^3)`.

These are proposal errors only.  The accepted state is still certified by exact
active-stratum recomputation of `Q_h` and `S_h`, hard `q` residuals, sign/case
margins, and projection-work ledgers.

## Defect-Correction Route

DC is useful for AO-Fast only as a residual-monotone nonlinear compatibility
iteration.  Define the exact physical-volume residual

```text
R(phi) = Q_h^S(phi) - q^-.
```

Let `P_0` approximate the inverse action of the active Schur operator
`J_A W_eta^{-1} J_A^T`, for example a frozen active-Schur inverse, warm-started
preconditioned solve, or component-block approximate inverse.  A DC proposal is

```text
delta phi_DC = -P_0 R(phi_k),
phi_trial(alpha) = phi_k + alpha delta phi_DC.
```

The step is accepted only if the exact residual decreases in physical units:

```text
||R(phi_trial(alpha))||_{H_C^{-1}} < ||R(phi_k)||_{H_C^{-1}}.
```

The scalar `alpha` may be chosen by a device-side line search or by the same
quadratic residual-minimization idea used in the PPE DC route, but the residual
being minimized is `Q_h-q`, not the frozen model residual.  Fixed-count DC is
therefore not acceptable.  If DC stagnates, AO-Fast escalates to the active
PCG/Newton projection or fails closed.

## CCD/DCCD/FCCD/UCCD Role

CCD-family operators remain valuable where the object is smooth:

```text
phi predictor,
screened gauge metric W_eta,
face-state reconstruction for delta_phi_pred(w),
pressure-adjoint and face-Hodge diagnostics,
smooth residual probes.
```

They are not valid substitutes for the discontinuous finite-volume carrier
`q/theta`, nor for `Q_h`, `J_q`, `T_q`, or `dS_h`.  The theory therefore uses
CCD-family operators as smooth auxiliary maps under exact geometric acceptance,
not as a hidden replacement for geometric conservation.

## Acceptance Theorem

AO-Fast preserves the SP-AO theory if every committed step satisfies:

```text
1. q is updated only by a conservative geometric swept-volume flux.
2. phi is accepted only after exact Q_h(phi)=q residual gates in physical q units.
3. any approximation has a declared local order and is used only before exact gates.
4. any DC step monotonically decreases exact Q_h-q residuals.
5. capillary/pressure work is measured in the same face-Hodge metric M_A.
6. all Krylov/DC iteration data remain device-resident except explicit ledger scalars.
```

Under these conditions, AO-Fast is a computational route for the same SP-AO
state space, not a new physics model and not a relaxed volume method.

## SOLID-X

Theory/specification artifact only.  No solver source, experiment result,
tested implementation deletion, FD/WENO/PPE fallback, damping/CFL workaround,
smoothing, curvature cap, benchmark branch, blanket projection,
QP-as-physics path, or hidden DCCD/UCCD damper introduced.
