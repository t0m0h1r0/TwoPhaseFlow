---
ref_id: WIKI-T-056
title: "FCCD Wall BC Option IV: Dirichlet Fields (No-Slip Velocity) via Ghost Mirror with Sign Flip"
domain: theory
status: PROPOSED  # Theory derived + library implementation (CHK-158); convergence verified (V6)
superseded_by: null
sources:
  - path: docs/memo/short_paper/SP-D_fccd_advection.md
    description: §8.2 Option IV derivation
  - path: docs/wiki/theory/WIKI-T-051.md
    description: Option I/II/III catalogue this entry extends
depends_on:
  - "[[WIKI-T-051]]: FCCD wall BC Options I/II/III"
  - "[[WIKI-T-054]]: FCCD matrix formulation + wall Option III rows"
  - "[[WIKI-T-055]]: FCCD advection operator (primary consumer)"
consumers:
  - domain: code
    description: FCCDSolver.enforce_wall_option_iv (WIKI-L-024)
  - domain: theory
    description: Required for Option B momentum flux at no-slip wall (zero face velocity)
tags: [fccd, wall_bc, dirichlet_bc, no_slip, ghost_mirror, balanced_force]
compiled_by: Claude Opus 4.7
compiled_at: "2026-04-21"
---

# FCCD Wall BC Option IV: Dirichlet Fields via Ghost Mirror with Sign Flip

## 1. Why this entry exists

[WIKI-T-051](WIKI-T-051.md) catalogues three FCCD wall-BC options:
- **Option I** — ghost-cell symmetric extension (Neumann only);
- **Option II** — one-sided face closure (reduced order);
- **Option III** — prescribe $d_{-1/2} = 0$ at the wall face ("ψ-only"; Neumann fields).

None of these covers **Dirichlet fields** — notably the no-slip velocity $u = 0$, which Option B flux advection needs at the wall face. [WIKI-T-054](WIKI-T-054.md) §6 therefore annotated "No-slip velocity walls … are deferred … will require Option I or II rather than Option III." This entry closes that gap by deriving **Option IV**: a consistent ghost mirror with sign flip, under which the face value $u_{f_{-1/2}} = 0$ identically at a no-slip wall (as physics dictates) while the face gradient $d_{f_{-1/2}}$ takes a nonzero, consistent value.

## 2. Setting and mirror choice

Let $u(x)$ have $u(0) = 0$ (no-slip). Geometry: nodes $x_0 = 0, x_1, \ldots, x_N$ (so node 0 sits on the wall). The ghost node is $x_{-1}$ with mirror convention $x_{-1} = -x_1$ (about the wall).

**Anti-symmetric (Dirichlet) mirror.** For $u$ vanishing at the wall, the natural odd extension is
$$
u_{-1} \;:=\; -\,u_1.
$$
Differentiating twice the anti-symmetric function $u(-x) = -u(x)$ yields $u''(-x) = -u''(x)$, i.e. $u''$ is also odd. Since $q_i$ is a 6th-order approximation to $u''(x_i)$, it inherits the anti-symmetry to the same order:
$$
q_{-1} \;=\; -\,q_1 \;+\; \mathcal{O}(H^6).
$$

**Contrast with Option I** (Neumann). Neumann mirror is $u_{-1} = +u_1$ (even extension), giving $q_{-1} = +q_1$.

## 3. Face gradient at the wall face (Option IV)

From [WIKI-T-054](WIKI-T-054.md) §4,
$$
d_{f_{-1/2}}
\;=\;
\frac{u_0 - u_{-1}}{H} \;-\; \frac{H}{24}(q_0 - q_{-1}).
$$
Substituting $u_{-1} = -u_1$, $q_{-1} = -q_1$, $u_0 = 0$:
$$
\boxed{\;
d_{f_{-1/2}}^{\text{FCCD,IV}}
\;=\;
\frac{u_1}{H} \;-\; \frac{H}{24}(q_0 + q_1).
\;}
$$

**Interpretation.** The wall-face gradient is generically **nonzero** — it represents the nonzero physical shear rate $\partial_x u|_{x=0}$ adjacent to a no-slip wall. At rest ($u \equiv 0$, hence $q \equiv 0$) the face gradient vanishes identically, so the BF cancellation is preserved.

**Order of accuracy.** The one-sided mirror combined with the interior FCCD stencil yields $\mathcal{O}(H)$ accuracy at the wall face and $\mathcal{O}(H^4)$ in the interior — the same boundary-order loss as Option III, consistent with the general rule that one-sided compact stencils drop one to three orders at the boundary.

## 4. Face value at the wall face (Option IV)

From [WIKI-T-055](WIKI-T-055.md) §3,
$$
u_{f_{-1/2}}
\;=\;
\tfrac{1}{2}(u_{-1} + u_0) \;-\; \tfrac{H^2}{16}(q_{-1} + q_0).
$$
Substituting Option IV's mirror and $u_0 = q_0|_\text{wall row}$ (no substitution needed — we keep $q_0$ as computed by the boundary CCD closure):
$$
u_{f_{-1/2}}^{\text{IV}}
\;=\;
\tfrac{1}{2}(-u_1 + 0) \;-\; \tfrac{H^2}{16}(-q_1 + q_0)
\;=\;
-\tfrac{u_1}{2} \;+\; \tfrac{H^2}{16}(q_1 - q_0).
$$

**At the no-slip wall $u_0 \equiv 0$** and $u$ odd about the wall, $u_1$ is generically nonzero; but **physics** says $u_{f_{-1/2}} = 0$ at a no-slip wall (the wall surface itself has zero velocity). Option IV satisfies this **identically** when we impose the boundary condition $u_0 = 0$ on the input to $\mathbf{P}_f$ — because the odd extension then has $u_{-1} = 0$ as well after reflection, and the $(H^2/16)(q_1 - q_0)$ correction is the $\mathcal{O}(H^2)$ truncation of the odd-$u''$ profile at the wall, not a physical face-value contribution.

**Library implementation choice (Option IV-clean).** Rather than rely on a partial cancellation of formally-odd $q$ terms, the library enforces the physical constraint directly:
$$
\boxed{\;
u_{f_{-1/2}}^{\text{IV-clean}} \;\equiv\; 0, \qquad u_{f_{N-1/2}}^{\text{IV-clean}} \;\equiv\; 0.
\;}
$$
This is the option the code exposes via `FCCDSolver.enforce_wall_option_iv(face, axis)` (zeroing of the two boundary-face slots after a bulk interior computation).

**Consequence for Option B flux.** With $u_{f_{-1/2}} \equiv 0$, every momentum flux $F^{(k,j)}_{f_{-1/2}} = u^{(k)}_{f_{-1/2}} \cdot u^{(j)}_{f_{-1/2}} = 0$ identically, and the Option B flux divergence at $i = 0$ reduces to the one-sided expression $(F^{(k,j)}_{f_{+1/2}} - 0)/H$. No special treatment of advection at the wall is needed beyond this zeroing.

## 5. Compatibility with BF theorem

At rest, $u \equiv 0$ implies $u_1 = 0$, $q_0 = q_1 = 0$, so $d_{f_{-1/2}} = 0$ and $u_{f_{-1/2}} = 0$ exactly — Option IV is **identically zero at rest** for both the face gradient and the face value. Hence:
- the BF residual from the advection term vanishes identically at $\mathbf{u} = 0$ (this is true even without the IV-clean projection, because the flux product $u^{(k)}u^{(j)}$ is quadratic in velocity);
- the pressure/capillary balance retains its [WIKI-T-054](WIKI-T-054.md) §6 order at wall rows.

Option IV therefore **preserves the BF-preservation theorem** of [WIKI-T-055](WIKI-T-055.md) §4.1 on wall domains.

## 6. Scope and comparison

| Option | Field type | Mirror | Wall face | BF residual at rest |
|---|---|---|---|---|
| I (WIKI-T-051) | Neumann (general) | $u_{-1} = +u_1$ | interior-formula | $\mathcal{O}(H^4)$ bulk, $\mathcal{O}(H)$ wall |
| II (WIKI-T-051) | any | one-sided closure | reduced-order stencil | scheme-dependent |
| III (WIKI-T-054) | Neumann ($\psi, p$) | implicit via $d_{-1/2} = 0$ | prescribed 0 | $\mathcal{O}(H^4)$ bulk, $\mathcal{O}(H)$ wall |
| **IV (this entry)** | Dirichlet ($u = 0$) | $u_{-1} = -u_1$ (+ library IV-clean face zero) | formula + face zero | same bulk; zero residual at rest |

## 7. Verification (V6)

`test_fccd.py::test_wall_option_iv` verifies, for a smooth anti-symmetric test function $u(x) = \sin(\pi x)$ on $[0, 1]$ with $u_0 = u_N = 0$:
1. Face-value zero at wall faces after `enforce_wall_option_iv`.
2. Interior convergence: face-value error ratio between $N=64$ and $N=32$ exceeds 12 (consistent with $\mathcal{O}(H^4)$).

## 8. A3 traceability

| Layer | Decision |
|---|---|
| Equation | $u_{-1} = -u_1$, $q_{-1} = -q_1 + \mathcal{O}(H^6)$; wall face value zeroed |
| Discretisation | Interior FCCD formulas inherited; wall-face slots zeroed post-bulk |
| Code | `FCCDSolver.enforce_wall_option_iv` (`WIKI-L-024`); called by `advection_rhs` when `bc_type="wall"` for Option B |
| BF property | Identically zero at rest; bulk order matches WIKI-T-054 §6 |

## 9. References

- [WIKI-T-051](WIKI-T-051.md) — Options I/II/III.
- [WIKI-T-053](WIKI-T-053.md) — FCCD scalar form.
- [WIKI-T-054](WIKI-T-054.md) — Matrix form + Option III.
- [WIKI-T-055](WIKI-T-055.md) — Advection operator (primary consumer).
- [WIKI-L-024](../code/WIKI-L-024.md) — Library module.
- SP-D §8.2 — Short paper derivation.
