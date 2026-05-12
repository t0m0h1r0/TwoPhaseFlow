# CHK-RA-CH14-AO-FASTVOL-003 - paper Chapter 9 AO-Fast theory integration

Date: 2026-05-11
Branch: `codex/ra-ch14-ao-fast-volume-20260511`
Worktree: `.claude/worktrees/codex-ra-ch14-ao-fast-volume-20260511`

## Scope

Continuation of the AO-Fast theory work.  The goal was to carry the theory into
the corresponding paper location, not only the short paper and wiki.

Edited:

- `paper/sections/09b_split_ppe.tex`

## Integration Point

The insertion is in the capillary Riesz / component-volume reaction part of
Chapter 9, immediately after the paper establishes that pressure reaction
adjointness and common-flux conservation must share the same oriented face
complex.

This is the right location because AO-Fast is not a standalone numerical trick.
It is the computational realization of the same geometric compatibility and
face-Hodge work identities already used by the paper's pressure/capillary
framework.

## Added Theory

The paper now states the active-stratum route:

```text
A = { C : 0 < Q_h^S(phi)_C < |C| }
```

with one-face halo, periodic quotient, and wall ownership handled at table
construction time.  Full and empty cells are not recut unless the sign margin
requires it.

Approximation accuracy is explicit:

```text
beta_C = ||delta phi||_{infty,C}/min(gamma_C,m_C)

Q_h^S(phi+delta phi)_C
  = Q_h^S(phi)_C + J_q,C delta phi_C + R_Q,C,
|R_Q,C| <= C_Q |C| beta_C^2

S_h^S(phi+delta phi)_C
  = S_h^S(phi)_C + dS_C delta phi_C + R_S,C,
|R_S,C| <= C_S |Gamma_C| beta_C^2
```

The constants are local case/aspect-ratio/margin constants, not global-grid
constants.  Second-order candidates must demonstrate `O(beta_C^3)` on the same
stratum.  The paper also states that these orders are proposal accuracies, not
acceptance rules.

DC is stated as residual-monotone geometry compatibility iteration:

```text
R_A(phi) = Q_h^S(phi)_A - q^-_A,
delta phi_DC = -P_0 R_A(phi_k),

||R_A(phi_k + alpha delta phi_DC)||_{H_C^{-1}}
  < ||R_A(phi_k)||_{H_C^{-1}}.
```

Thus DC is acceptable only when it decreases the exact geometric volume
residual.  Fixed-count DC and hidden stabilization are excluded.

The CCD-family role is also stated: CCD/DCCD/FCCD/UCCD may be used for smooth
auxiliary maps (`phi` prediction, `W_eta`, face-state reconstruction,
pressure-adjoint diagnostics), but not to differentiate discontinuous
`theta_C` or replace `Q_h,J_q,T_q,dS_h`.

## Validation

- `git diff --check` PASS.
- Targeted TeX label scan for new `ao_fast_*` labels found no duplicates.
- Full paper build is run separately in this checkpoint before commit.

## SOLID-X

Paper theory/prose, artifact, wiki source link, and ledger only.  No solver
source, experiment result, tested implementation deletion, FD/WENO/PPE
fallback, damping/CFL workaround, smoothing, curvature cap, benchmark branch,
blanket projection, QP-as-physics path, or hidden DCCD/UCCD damper introduced.
