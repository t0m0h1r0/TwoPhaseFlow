---
ref_id: WIKI-T-041
title: "Third-Order Time Integration: AB3 + Richardson-CN + Rotational IPC"
domain: T
status: PROPOSED
superseded_by: null
sources:
  - path: docs/memo/2026-04-18_third_order_time_integration.md
    git_hash: null
    description: "Full design note: route analysis, equations, theorems, risks, BibTeX"
consumers:
  - domain: L
    description: "ab2_predictor.py — future AB3 extension (history buffer + coefficient)"
  - domain: L
    description: "cn_advance/richardson_cn.py — already O(Δt³); activate via cn_mode='richardson_picard'"
  - domain: L
    description: "coupling/velocity_corrector.py — rotational pressure update"
  - domain: E
    description: "Future exp11_30 — rotational IPC TGV convergence"
  - domain: A
    description: "paper/sections/05_time_integration.tex — future §5 extension"
depends_on:
  - "[[WIKI-T-003]]: Variable-Density Projection Method (current IPC + AB2 + CN baseline)"
  - "[[WIKI-T-033]]: Extended Crank–Nicolson × CCD (Richardson-CN, Padé-(2,2))"
  - "[[WIKI-X-007]]: CFL budget (advective, capillary, cross-viscous)"
  - "[[WIKI-T-030]]: DGR blowup mechanism (fold cascade — unaffected by Route B, but constrains reinit choice)"
tags: [time-integration, AB3, Richardson-CN, rotational-IPC, third-order, projection-method, Guermond-Shen, Karniadakis]
compiled_by: ResearchArchitect
verified_by: null
compiled_at: 2026-04-18
---

## Key Finding

The solver is globally $\mathcal{O}(\Delta t^2)$ in time because NS-side operators
(AB2 convection, IPC pressure split, CN viscous) rate-limit the CLS advection's
$\mathcal{O}(\Delta t^3)$ ([paper §5 lines 153–172](../../../paper/sections/05_time_integration.tex#L153-L172)).
Near high-$\mu$-ratio interfaces, explicit cross-viscous drops the local order to $\mathcal{O}(\Delta t^1)$.

**Route B** — AB3 convection + Richardson(Picard-CN) viscous + AB3 cross-term extrapolation + Rotational-IPC
pressure — lifts the whole system to $\mathcal{O}(\Delta t^3)$ velocity / $\mathcal{O}(\Delta t^{5/2})$ pressure ($L^2$)
with **~50 lines of new library logic**, reusing the already-shipped `RichardsonCNAdvance`
([[WIKI-T-033]]) and preserving the Peaceman–Rachford ADI tridiagonal structure.

Alternative routes (KIO BDF3, SDIRK3) are rejected: both require coupling $u^*$–$v^*$ in
the implicit viscous system, destroying the ADI Thomas-law advantage that is the basis of
the project's current GPU performance (CHK-119 `A_inv_dev` cache).

## Rate-Limiter Taxonomy

| # | Operator | Current | Proposed | Change |
|---|---|---|---|---|
| 1 | CLS advection (TVD-RK3) | $\mathcal{O}(\Delta t^3)$ | $\mathcal{O}(\Delta t^3)$ | unchanged |
| 2 | NS convection | $\mathcal{O}(\Delta t^2)$ (AB2) | $\mathcal{O}(\Delta t^3)$ | **AB3** |
| 3 | NS viscous diagonal | $\mathcal{O}(\Delta t^2)$ Picard-CN | $\mathcal{O}(\Delta t^3)$ | **Richardson(Picard-CN)** (already coded) |
| 4 | NS viscous cross-term | $\mathcal{O}(\Delta t^1)$ explicit | $\mathcal{O}(\Delta t^3)$ | **AB3 extrapolation on RHS** |
| 5 | Pressure splitting | $\mathcal{O}(\Delta t^2)$ IPC | $\mathcal{O}(\Delta t^{5/2})$ $p$ / $\mathcal{O}(\Delta t^3)$ $\mathbf{u}$ | **Rotational IPC** |
| 6 | ADI sweep | $\mathcal{O}(\Delta t^2)$ PR | $\mathcal{O}(\Delta t^2)$ (kept) | absorbed in IPC error |

## AB3 Convection

Replace the AB2 coefficient $(3/2, -1/2)$ with AB3 $(23/12, -16/12, 5/12)$:
$$
\mathbf{N}^{n+\frac{1}{2}} = \tfrac{23}{12}\mathcal{C}^n - \tfrac{16}{12}\mathcal{C}^{n-1} + \tfrac{5}{12}\mathcal{C}^{n-2},
\qquad \mathcal{C}^k := \mathbf{u}^k\!\cdot\!\nabla\mathbf{u}^k.
$$

Startup ramp: FE (step 0) → AB2 (step 1) → AB3 (step ≥ 2). AB3 is zero-stable (Dahlquist root condition)
so the startup $\mathcal{O}(\Delta t^2)$ error decays geometrically, asymptotic $\mathcal{O}(\Delta t^3)$
restored by step ~5.

## Richardson-CN Diagonal Viscous

Existing `RichardsonCNAdvance` (selected via `config.numerics.cn_mode="richardson_picard"`):
$$
\Phi_R \;=\; \frac{4\,\Phi_{\Delta t/2}\circ\Phi_{\Delta t/2} - \Phi_{\Delta t}}{3}, \qquad \Phi_h := \text{Picard-CN step of size } h.
$$
Heun base is non-symmetric, so Richardson extrapolation lifts order by $+1$ (not $+2$ as for
symmetric CN). Achieves $\mathcal{O}(\Delta t^3)$ for $\partial_t u = \nu\nabla^2 u$ (verified in
[[WIKI-T-033]] test suite, slope 3.01).

## AB3 Cross-Derivative Extrapolation

Currently $\mathcal{D}_{\mathrm{c}}$ is evaluated at time $n$ only, producing $\mathcal{O}(\Delta t^1)$
truncation near high-$\mu$-ratio interfaces ([paper §11f line 190–194](../../../paper/sections/11f_time_integration.tex#L190-L194)).
AB3 extrapolation:
$$
\mathbf{D_c}^{n+\frac{1}{2}} = \tfrac{23}{12}\mathcal{D}_{\mathrm{c}}^n - \tfrac{16}{12}\mathcal{D}_{\mathrm{c}}^{n-1} + \tfrac{5}{12}\mathcal{D}_{\mathrm{c}}^{n-2}.
$$
Extends the paper's existing recommendation ([§5 line 141](../../../paper/sections/05_time_integration.tex#L141):
"AB2 extrapolation is recommended") to AB3. **Restores $\mathcal{O}(\Delta t^3)$** near smoothed
interfaces of width $\varepsilon$ (smooth $\mu\in C^\infty$ via Heaviside regularization).

## Rotational IPC Pressure Correction (Guermond–Shen 2003)

The standard IPC corrector is
$$
\mathbf{u}^{n+1} = \mathbf{u}^* - \frac{\Delta t}{\rho^{n+1}}\nabla(\delta p),\qquad p^{n+1} = p^n + \delta p.
$$
**Rotational update** replaces the pressure formula:
$$
\boxed{\ p^{n+1} \;=\; p^n + \delta p \;-\; \nu_{\mathrm{eff}}\,\nabla\!\cdot\mathbf{u}^*\ },\qquad
\nu_{\mathrm{eff}} := \mu^{n+1}/\rho^{n+1}.
$$
The additional term $-\nu_{\mathrm{eff}}\nabla\!\cdot\mathbf{u}^*$ removes the artificial pressure
boundary layer that limits standard IPC to $\mathcal{O}(\Delta t^2)$.

**Theorem** (Guermond & Shen, *SIAM J. Numer. Anal.* 41, 2003, Thm 3.1):
for smooth $\mathbf{u}\in H^3(\Omega)$, the rotational scheme achieves
$\|\mathbf{u}-\mathbf{u}^n\|_{L^2} \leq C\Delta t^3$ and $\|p-p^n\|_{L^2} \leq C\Delta t^{5/2}$,
provided convection & viscous discretisations are $\mathcal{O}(\Delta t^3)$.

## ADI Preservation

Route B keeps all upgrade terms on the RHS of the Peaceman–Rachford sweep
([paper appD](../../../paper/sections/appD_predictor_adi.tex#L49-L64)):
- AB3 convection → RHS assembly only
- AB3 cross-visc → RHS assembly only (explicit extrapolation)
- Richardson-CN → same tridiagonal LHS operator, called 3× per step
- Rotational IPC → pointwise scalar update, no solve

Thomas-law $\mathcal{O}(N)$ sweep preserved. GPU-cached `A_inv_dev` (CHK-119) directly reusable.

## CFL Budget Update

AB3 has a smaller absolute-stability region than AB2 (Hairer–Wanner §III.3):

| Scheme | Real-axis bound | Advective CFL |
|---|---|---|
| AB2 (current) | $[-1, 0]$ | $C_{\mathrm{CFL}} \leq 0.5$ |
| AB3 (proposed) | $[-6/11, 0]$ | $C_{\mathrm{CFL}} \leq 0.275$ |

**Proposed operational**: $C_{\mathrm{CFL}} = 0.25$ (0.55× reduction from the current $0.45$).
Capillary CFL ($\Delta t_\sigma \propto h^{3/2}$) and cross-viscous CFL ($C_{\mathrm{cross}} \approx 0.22$) are
unaffected ([[WIKI-X-007]]).

## Startup and History Buffers

| Step | Conv | $\mathcal{D}_c$ | Diag visc | Corrector |
|---|---|---|---|---|
| $n=0$ | FE | FE | Picard-CN | IPC std |
| $n=1$ | AB2 | AB2 | Richardson-CN | IPC rotational |
| $n\geq 2$ | AB3 | AB3 | Richardson-CN | IPC rotational |

Additional memory: $\mathcal{C}^{n-1}, \mathcal{C}^{n-2}, \mathcal{D}_{\mathrm{c}}^{n-1}, \mathcal{D}_{\mathrm{c}}^{n-2}$
= $4\,N_xN_y\,d$ reals. At $N=256$, 2D: ~4 MB (negligible vs PPE matrix).

## Risks and Open Questions

**R1 — AB3 imaginary-axis stability (High, quantified).** AB3 has zero stability on $i\mathbb{R}$;
capillary modes need dissipation from DCCD filter ($\varepsilon_d$). Mitigation: $C_{\mathrm{CFL}}=0.25$.

**R2 — Rotational term at $\mu_l/\mu_g \gg 1$ (Medium).** $\nu_{\mathrm{eff}}=\mu/\rho$ varies
$\sim 10^2$ across water–air interface, amplifying $\nabla\!\cdot\mathbf{u}^*$ residual in pressure field.
Mitigation: harmonic-mean $\nu_{\mathrm{eff}}$, or $\nu_g$-uniform (Guermond–Shen original).

**R3 — Richardson substep freezing (Low, bounded).** 3 CN calls all use frozen $\mu^n$, $\rho^n$.
Introduced error is $\mathcal{O}(\Delta t^2)$, does not contaminate $\mathcal{O}(\Delta t^3)$ order.

**R4 — $\mathcal{D}_{\mathrm{c}}$ history startup (Low).** Step 1 uses AB2 on $\mathcal{D}_{\mathrm{c}}$;
$\mathcal{O}(\Delta t^2)$ startup error decays under AB3 root condition.

**R5 — DGR blowup under $\sigma>0$ (Known, [[WIKI-T-030]]).** Route B does not alter interface-fold
mechanism. **Must use hybrid reinit** (CHK-133 default).

**Q1** — Does CLS–NS operator-split coupling degrade to $\mathcal{O}(\Delta t^2)$ at this
higher-order regime? Conjecture: no (TVD-RK3 + pre-updated $\psi^{n+1}$ before $\rho,\mu,\kappa$
evaluation), but formal proof is open.

**Q2** — Rotational IPC $L^\infty$ pressure remains $\mathcal{O}(\Delta t^2)$; relevant for
Laplace-pressure static droplet tests. Monitor during validation.

**Q3** — Path to $\mathcal{O}(\Delta t^4)$: Richardson on symmetric (fully-implicit) CN base
lifts order by $+2$ ([[WIKI-T-033]] §Padé-(2,2)), combined with AB4 convection + Richardson
rotational IPC. ~3–4× Route B effort.

## Implementation Roadmap

**Theory-only** at present. Estimated implementation (future CHK):

| Change | File | Lines |
|---|---|---|
| AB3 coefficient + history | `src/twophase/time_integration/ab2_predictor.py` | ~15 |
| $\mathcal{D}_{\mathrm{c}}$ AB3 buffer | `src/twophase/ns_terms/viscous.py` | ~20 |
| Rotational IPC | `src/twophase/coupling/velocity_corrector.py` | ~10 |
| Config flag `time_order=3` | `src/twophase/config.py` | ~5 |
| Verification exp11_30 (TGV @ AB3+Rot-IPC) | `experiment/ch11/exp11_30_third_order_tgv.py` | ~150 |

Total: ~50 lines library + one new experiment.

## Relationship to Prior Wiki Entries

- [[WIKI-T-003]] — current baseline (IPC + AB2 + CN). This entry upgrades all three.
- [[WIKI-T-033]] — designed Richardson-CN / Padé-(2,2) for viscous operator alone. This entry
  combines Richardson-CN with AB3 + Rotational IPC for full NS upgrade.
- [[WIKI-T-030]] — DGR blowup under $\sigma>0$. Route B inherits the hybrid-reinit requirement.
- [[WIKI-X-007]] — CFL budget. CFL table updated in §CFL Budget above.
- [[WIKI-E-005]], [[WIKI-E-013]] — experimentally confirmed current $\mathcal{O}(\Delta t^2)$.
  Future exp11_30 will re-verify at $\mathcal{O}(\Delta t^3)$.

## Assumptions

- Smooth velocity field $\mathbf{u}\in H^3(\Omega)$ (Guermond–Shen hypothesis for rotational IPC).
- Smoothed Heaviside interface (width $\varepsilon = O(h)$) so $\mu\in C^\infty$ and AB3 cross-term
  extrapolation preserves $\mathcal{O}(\Delta t^3)$.
- Hybrid reinit used ([[WIKI-T-030]] mandate for $\sigma>0$ capillary).
- DCCD filter active ($\varepsilon_d \geq 1/8$) for AB3 imaginary-axis dissipation.
- Low-to-moderate density ratio ($\rho_l/\rho_g \leq 10$); high-$\rho$ regimes require split-PPE
  path ([paper §12h](../../../paper/sections/12h_error_budget.tex)) separately.
