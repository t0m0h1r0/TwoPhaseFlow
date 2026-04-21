---
ref_id: WIKI-X-027
title: "Reinitialization Semantics: Physical Time vs Pseudo Time, φ/ψ Role Separation, and the Three Meanings of Iteration"
domain: cross-domain
status: PROPOSED  # Design principle; stop-criterion PoC pending
superseded_by: null
sources:
  - description: Internal research memo on reinitialisation semantics and iteration meaning (2026-04-22)
  - description: "Olsson, E. & Kreiss, G. (2005). A conservative level set method for two-phase flow. JCP 210, 225–246."
  - description: "Sussman, M., Smereka, P. & Osher, S. (1994). A level set approach for computing solutions to incompressible two-phase flow. JCP 114, 146–159."
  - description: "Sussman, M. & Fatemi, E. (1999). An efficient, interface-preserving level set redistancing algorithm. SIAM J. Sci. Comput. 20(4), 1165–1191."
  - description: "Zhao, H. (2005). A fast sweeping method for Eikonal equations. Math. Comp. 74, 603–627."
  - description: "McCaslin, J. O. & Desjardins, O. (2014). A localized reinitialization for the conservative level set method. JCP 262, 408–426."
  - description: "Various consistent / anchoring CLS reinit refinements (2015 / 2017 / 2019 / 2023)."
depends_on:
  - "[[WIKI-T-007]]: Conservative Level Set (CLS): Transport, Reinitialization, Mass Conservation"
  - "[[WIKI-T-010]]: Interface Mathematical Proofs (Newton, Eikonal, CLS Fixed-Point)"
  - "[[WIKI-T-027]]: CLS Reinitialization Mass Conservation: Problem Analysis"
  - "[[WIKI-T-028]]: CLS-DCCD Conservation Theory: Root Cause Analysis and Unified Reinitialization"
  - "[[WIKI-T-030]]: Operator-Split Defect, DGR Theory, and Hybrid Reinitialization"
  - "[[WIKI-X-019]]: Topology-Freedom vs Metric-Rigidity: ξ/φ Role Separation"
  - "[[WIKI-X-020]]: Unified Interface-Tracking & Sharp-Interface PPE Chain"
consumers:
  - domain: future-impl
    description: "Reinit stop-criterion upgrade: displacement + mass, not linear residual"
  - domain: experiment
    description: "Quantify over-reinit mass drift on ch13 capillary wave at α=1.5"
  - domain: theory
    description: "Formalise iteration hierarchy: τ-pseudo / FMM-sweep / Krylov-Newton"
tags: [reinitialization, pseudo_time, physical_time, level_set, conservative_level_set, eikonal, fast_marching, fast_sweeping, iteration_semantics, design_principle]
compiled_by: ResearchArchitect
compiled_at: "2026-04-22"
---

# Reinitialization Semantics

## Thesis

> **Reinitialisation is geometry quality control, not time evolution. It runs
> in *pseudo-time* $\tau$, not physical time $t$. The convergence criterion
> is *interface displacement and mass change*, not linear-solver residual.
> Mistaking reinit iteration for Krylov iteration is the single most common
> design error in high-order two-phase solvers.**

Two adjacent disciplines — NS time integration (physical $t$, Krylov solvers
inside) and level-set reinitialisation (pseudo $\tau$, Hamilton–Jacobi solvers
inside) — *look* similar but are semantically distinct. Getting the semantics
right determines whether mass drifts, curvature blows up, or interfaces wander.

## 1. Two time axes, two variables

| Axis | Role | Discrete form |
|---|---|---|
| physical time $t$ | advection of the interface | hyperbolic PDE: $\psi_t + \nabla\cdot(\psi\mathbf u) = 0$ (CLS) or $\phi_t + \mathbf u\cdot\nabla\phi = 0$ (classical LS) |
| pseudo time $\tau$ | geometry restoration after advection | Hamilton–Jacobi PDE: $\phi_\tau + S(\phi^0)(|\nabla\phi| - 1) = 0$ (HJ reinit) or CLS AC-type reinit |

The two never share the same timestep, and the two never share the same convergence criterion.

## 2. φ and ψ have different jobs

### Classical LS (Sussman–Smereka–Osher 1994)

- **$\phi$** (signed distance) is advected in *physical $t$*.
- Reinit PDE in *pseudo $\tau$* keeps $|\nabla\phi| \approx 1$.
- Normal $\mathbf n = \nabla\phi / |\nabla\phi|$ and curvature $\kappa = \nabla\cdot\mathbf n$ are computed directly from $\phi$.

### Conservative LS (Olsson–Kreiss 2005)

- **$\psi$** (smoothed Heaviside, $\psi \in [0,1]$) is advected *conservatively* in *physical $t$*: $\psi_t + \nabla\cdot(\psi\mathbf u) = 0$.
- Reinit restores the $\tanh$-profile in *pseudo $\tau$*.
- **$\phi$** is reconstructed from $\psi$ (e.g.\ $\phi = \varepsilon \log(\psi / (1-\psi))$) and used for curvature / normals — **more robust than differentiating $\psi$ directly**.

### Project convention (CLS path)

```
ψⁿ ──(physical t: advect, FCCD flux)──▶ ψ*
ψ* ──(pseudo τ: ridge-Eikonal reinit)──▶ ψⁿ⁺¹
(if needed) φⁿ⁺¹ = ε log(ψⁿ⁺¹ / (1-ψⁿ⁺¹))  and narrow-band FMM correction
κ, n_hat computed from reconstructed φⁿ⁺¹
```

This matches [WIKI-T-007](../theory/WIKI-T-007.md) and [WIKI-X-020](WIKI-X-020.md).

## 3. The three meanings of "iteration"

In the project's full solver pipeline, the word *iteration* refers to three semantically distinct things. Confusing them is the design error this note corrects.

| Meaning | PDE type | Stop criterion | Example in project |
|---|---|---|---|
| (a) Pseudo-time $\tau$ reinit | HJ / artificial-compression | $\max\bigl||\nabla\phi|-1\bigr|$; **$\Delta m$**; **$\Delta x_\Gamma$** | ridge-Eikonal loop (see [WIKI-T-027](../theory/WIKI-T-027.md)) |
| (b) Fast-marching / fast-sweeping | Eikonal $|\nabla\phi| = 1$ | Gauss–Seidel sweep visits stable | narrow-band distance reconstruction |
| (c) Krylov / Newton | elliptic linear system | $\|r\| / \|b\| < \varepsilon_{\text{lin}}$ | PPE solve (see [WIKI-X-025](WIKI-X-025.md)) |

**Rule**: never apply a stop criterion of type (c) to an iteration of type (a) or (b).

## 4. Critical design rule — "do not over-reinit"

A common pathology is reinitialising to *full convergence* every step, by analogy to a linear solve:

- Running HJ reinit to "machine precision $|\nabla\phi| = 1$" *moves the interface*.
- The interface motion during reinit is a pure numerical error: mass drops, $\kappa$ gets noisy, the BF residual ([WIKI-X-024](WIKI-X-024.md)) contaminates.

Correct stopping:

$$
\boxed{\;\text{stop reinit when}\;
\bigl|\Delta x_\Gamma\bigr| < \varepsilon_\Gamma,\;\;
\bigl|\Delta m\bigr| / m < \varepsilon_m,\;\;
\max\bigl||\nabla\phi| - 1\bigr| < \varepsilon_{\text{dist}}\;}
$$

with the first two dominating. Recent anchoring / interface-preserving reinit literature (2019 – 2023) confirms: interface preservation is the primary criterion, not eikonal residual.

## 5. When Eikonal-sweep (FMM/FSM) is used instead of pseudo-τ

For narrow-band distance reconstruction on a well-placed interface, **fast sweeping** (Zhao 2005) or **fast marching** is preferable to an HJ pseudo-time loop:

- FMM/FSM have near-optimal $O(N)$ or $O(N\log N)$ cost.
- They do not advect the interface at all — the zero level is frozen by construction.
- They produce a bona-fide distance function useful for $\kappa$ and $\mathbf n$.

Use FMM/FSM in preference to HJ pseudo-τ whenever the zero-isocontour location is already good and only the distance field needs repair. The project's narrow-band reinit pipeline follows this pattern ([WIKI-T-031](../theory/WIKI-T-031.md), [WIKI-X-020](WIKI-X-020.md)).

## 6. Never: reinit as Krylov residual

Anti-pattern: using GMRES / CG to drive the reinit PDE to zero residual. This is wrong because the reinit PDE is **non-linear Hamilton–Jacobi** and its "solution" is conditioned by interface location, not residual norm. The correct pseudo-τ stepping plus geometric stop criterion in §4 is the only consistent formulation.

## 7. Project-specific implementation checklist

1. **Separate data structures**: `psi` is the physical-time state; `phi_reinit` is the pseudo-τ / FMM output. Do not overwrite `psi` with reinit output except at explicit "blend-back" time.
2. **Reinit cadence**: every 1–5 advection steps by default (config `run.reinitialization.every`). Do not reinit every substep of RK3.
3. **Stop criterion** (per §4):
   - $|\Delta x_\Gamma| < 0.1 \varepsilon$ (interface displacement bounded)
   - $|\Delta m| / m < 10^{-4}$ (mass drift bounded)
   - $\max\bigl||\nabla\phi| - 1\bigr| < 10^{-2}$ (distance residual *secondary*)
4. **Curvature/normal always from reconstructed $\phi$**: never differentiate $\psi$ directly to get $\kappa$; use $\phi = \varepsilon \log(\psi/(1-\psi))$ (or equivalent $\tanh^{-1}$) then HFE smoothing ([WIKI-T-038](../theory/WIKI-T-038.md)).
5. **FMM/FSM path for narrow-band distance**: prefer over pseudo-τ loops when the zero isocontour is already well-placed.

## 8. Open questions

- **Q-R1** — Quantify mass drift vs reinit-iteration count on ch13 capillary wave ($N=128$, $\alpha=1.5$). Expected: a sharp knee where further iterations cost mass, not accuracy.
- **Q-R2** — Combining ridge-Eikonal (τ-pseudo) and FMM (sweep) — when does the hybrid beat either alone?
- **Q-R3** — Does semi-implicit surface tension ([WIKI-X-025 §3.1](WIKI-X-025.md#31-predictor)) change the required reinit cadence? Expected: yes, because implicit ST tolerates larger $\Delta t$, so more advection displacement accumulates per reinit.

## References

- [WIKI-T-007](../theory/WIKI-T-007.md) — CLS transport & reinit baseline.
- [WIKI-T-027](../theory/WIKI-T-027.md) — CLS reinit mass-conservation fix.
- [WIKI-T-028](../theory/WIKI-T-028.md) — CLS-DCCD conservation & unified reinit.
- [WIKI-T-030](../theory/WIKI-T-030.md) — operator-split defect / DGR / hybrid reinit.
- [WIKI-T-031](../theory/WIKI-T-031.md) — non-uniform grid CLS.
- [WIKI-T-038](../theory/WIKI-T-038.md) — HFE curvature smoothing.
- [WIKI-X-019](WIKI-X-019.md) — ξ/φ topology-freedom role separation (orthogonal axis).
- [WIKI-X-020](WIKI-X-020.md) — unified tracking + sharp PPE chain.
- [WIKI-X-025](WIKI-X-025.md) — time integration design (physical-$t$ side).
- Olsson & Kreiss (2005) *JCP* **210** — original CLS.
- Sussman, Smereka & Osher (1994) *JCP* **114** — classical LS for two-phase flow.
- Sussman & Fatemi (1999) *SISC* **20** — interface-preserving redistancing.
- Zhao (2005) *Math. Comp.* **74** — fast sweeping.
- McCaslin & Desjardins (2014) *JCP* **262** — localised CLS reinit.
- Consistent / anchoring CLS reinit literature (2015 / 2017 / 2019 / 2023).
