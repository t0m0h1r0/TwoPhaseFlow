# WIKI-X-018: H-01 Remediation Map — G^adj Metric Unification via FCCD

## Context

[WIKI-E-030](../experiment/WIKI-E-030.md) confirmed **H-01** as the unique primary cause of the late-time blow-up on non-uniform grids: the pressure-gradient operator $\mathcal{G}^{\text{adj}}$ (introduced in [WIKI-T-044](../theory/WIKI-T-044.md)) lives on the FVM face metric, while $\sigma\kappa\nabla\psi$ remains on the node-centred CCD metric. The Balanced-Force residual $|\text{BF}_\text{res}|$ is then $\mathcal{O}(\Delta x^2)\cdot|d(\log J)/dx|$, measured at ≈ 884 on Exp-1 step 1.

[ACTIVE_LEDGER](../02_ACTIVE_LEDGER.md) CHK-152 records the open action item: *"G^adj と σκ∇ψ を同一メトリクス空間に統一 (将来タスク)"*. This cross-domain entry maps the action item to concrete candidate remediations.

## Remediation options

| Option | Method | Where it lives | BF order (constant κ) | BF order (variable κ) | Code impact | Status |
|---|---|---|---|---|---|---|
| **R-0** (current) | Mixed metric: $\mathcal{G}^{\text{adj}}$ on face, CCD on node | [`ns_pipeline.py:381`](../../../src/twophase/simulation/ns_pipeline.py#L381) | $\mathcal{O}(h^2)$ residual | $\mathcal{O}(h^2)$ residual | no change | ✗ (drives late blow-up) |
| **R-1.5** (new, immediate) | Reuse `_fvm_pressure_grad` on $\psi$ — same operator as $\nabla p$ | [WIKI-T-052](../theory/WIKI-T-052.md), [WIKI-L-023](../code/WIKI-L-023.md) | **machine precision** | $\mathcal{O}(h^2)$ (= CSF model floor) | **3-line edit, guarded** | **proposed (immediate)** |
| **R-1** | FCCD unified on face (*recommended long-term*) | **SP-A** / [WIKI-T-046](../theory/WIKI-T-046.md) + [WIKI-T-050](../theory/WIKI-T-050.md) + [WIKI-T-051](../theory/WIKI-T-051.md) | machine precision | $\mathcal{O}(h^4)$ uniform / $\mathcal{O}(h^3)$ non-uniform | new operator class; node-face layout | **candidate**; PoC pending |
| **R-2** | Node-centred $\mathcal{G}$ restoration via Jacobian-weighted face → node interpolation | project research option | $\mathcal{O}(h^2)$ residual | $\mathcal{O}(h^2)$ large constant | moderate | not drafted |
| **R-3** | Full IIM reprojection post-corrector | [WIKI-T-034](../theory/WIKI-T-034.md) | machine precision | $\mathcal{O}(h^4)$ variational | large (variational Hodge projection) | long-range |

**Recommended deployment path**: R-1.5 → R-1 (when PoC succeeds). Rationale:

- **R-1.5 unblocks the immediate symptom.** [WIKI-E-030](../experiment/WIKI-E-030.md) blows up because of the operator-mismatch BF residual on quasi-equilibrium configurations. R-1.5 collapses that residual to machine precision for constant $\kappa$ via the existing helper — no new code path, no PoC gate, ready today.
- **R-1.5 is the algebraic baseline of R-1.** [WIKI-T-050](../theory/WIKI-T-050.md) §"Reduction to G^adj" shows that R-1's FCCD operator with $\mu \equiv \lambda \equiv 0$ recovers exactly the $G^{\text{face}}$ used by R-1.5. The future R-1 migration is therefore an *enhancement* of the R-1.5 operator, not a replacement.
- **R-1 remains the long-term target** because it raises BF accuracy on variable $\kappa$ from the CSF model floor $\mathcal{O}(h^2)$ to $\mathcal{O}(h^4)$ on uniform grids — relevant for sharp-feature benchmarks where the CSF floor is no longer the binding constraint.
- R-2 retains the metric mismatch at higher implementation cost — superseded by R-1.5.
- R-3 is structurally cleaner but requires a full variational solve at each corrector step.

## PoC gating (parallel, not sequential)

R-1.5 and R-1 are now decoupled and run in parallel:

### R-1.5 PoC (immediate, single run)

- **PoC-1.5** (CHK-155, deferred): implement Phase 1 of [WIKI-L-023](../code/WIKI-L-023.md) → run `ch13_02_waterair_bubble.yaml` to $T = 20$ on $\alpha = 1.5$. Pass criterion: no late blow-up; `bf_residual_max < 10^{-8}`.
- Effort: ~1 afternoon edit + 1 simulation run.
- Risk: near-zero (single guarded branch, bit-exact on all uniform/periodic configs).

### R-1 PoC (weeks-scale, three runs)

- **PoC-1** (1-D $\mathcal{O}(h^4)$ convergence on smooth data) — [WIKI-T-046](../theory/WIKI-T-046.md) §PoC-1.
- **PoC-2** (BF residual on the WIKI-E-030 benchmark) — **decisive measurement**. Compares R-1.5 vs R-1 on the same benchmark to determine whether the higher-order cancellation provides benchmark-relevant improvement.
- **PoC-3** (non-uniform stretched-grid convergence with prescribed $h_R/h_L$) — exercises [WIKI-T-050](../theory/WIKI-T-050.md) cancellation coefficients $\mu, \lambda, \nu$.

The two PoC tracks are independent. R-1.5 is **not blocked** by R-1's PoC; R-1's PoC is **not blocked** by R-1.5's deployment.

## Mode implications

If PoC-2 demonstrates a benchmark-relevant $|\text{BF}_\text{res}|$ reduction from R-1.5's $\mathcal{O}(h^2)$ to R-1's $\mathcal{O}(h^4)$ on the Exp-1 setting, the paper revision mode selection is triggered:

- **Mode α**: R-1 adopted as a §8b correction path only. §04/§08 collocated commitment is preserved; R-1 is described as "an alternative face-locus operator used exclusively for the non-uniform corrector". R-1.5 remains as the production fallback.
- **Mode β**: R-1 replaces the node-centred pressure gradient entirely. §04/§08 are rewritten as "node-face hybrid", and the CCDSolver is retained only for the level-set transport.
- **Mode γ**: R-1 is combined with SP-B ([WIKI-T-047](../theory/WIKI-T-047.md) / [WIKI-T-048](../theory/WIKI-T-048.md)) to become the new core of the two-phase framework.

If R-1's PoC fails or proves marginal (CSF floor is the binding constraint), **R-1.5 becomes the permanent solution** — the operator unification is achieved, and the residual $\mathcal{O}(h^2)$ accuracy matches the CSF model floor anyway (see [WIKI-T-052](../theory/WIKI-T-052.md) §"When R-1.5 is *not* enough").

The pivot decision is deferred to the post-PoC review.

## Advection-axis companion (CHK-158 — A-01)

The H-01 row above targets the **gradient-locus** mismatch: $\nabla p$ on the face metric but $\sigma\kappa\nabla\psi$ on the node metric. At non-zero velocity an analogous **advection-axis** mismatch — call it **A-01** — also contributes: node-centred $(\mathbf{u}\cdot\nabla)\mathbf{u}$ is evaluated at a different locus than the gradient terms, so the at-rest cancellation is not preserved once $\mathbf{u} \ne \mathbf{0}$ for quasi-static flows with varying $\kappa$.

| Axis | Source | Remediation | Status |
|---|---|---|---|
| H-01 (gradient) | R-0 node/face mismatch on $\nabla p$ vs $\sigma\kappa\nabla\psi$ | R-1.5 (`_fvm_pressure_grad` on $\psi$) / R-1 (FCCD on face) | R-1.5 SPEC [WIKI-L-023](../code/WIKI-L-023.md); R-1 library [WIKI-L-024](../code/WIKI-L-024.md) |
| **A-01 (advection)** | Node CCD advection vs face-locus pressure/capillary | **A-01-B (FCCD Option B, face flux divergence)** / A-01-C (Option C, node-output Hermite) | Library IMPLEMENTED [WIKI-L-024](../code/WIKI-L-024.md); theory [WIKI-T-055](../theory/WIKI-T-055.md); benchmark verification deferred |

**A-01-B is the advection analogue of R-1 on the gradient axis.** [WIKI-T-055](../theory/WIKI-T-055.md) §4.1 states the **BF-preservation theorem**: when momentum advection uses the Option B face-flux divergence on the same face locus as $\nabla p$ and $\sigma\kappa\nabla\psi$, the discrete residual of the full momentum equation is exactly zero at rest (and is $\mathcal{O}(H^4)$ at non-rest). A-01-B therefore **completes** the H-01 remediation: the full face-locus closure that H-01 alone (gradient only) does not reach.

A-01-C (Option C, node-output via Hermite reconstructor) is the backward-compatible variant: upgrades convection to $\mathcal{O}(H^4)$ without touching AB2 / PPE RHS / CSF / Rhie-Chow. It does *not* preserve BF exactly but is a low-risk drop-in.

Library-level the two axes share a **single** `FCCDSolver` instance per simulation: the LU factorisation of the underlying CCD system is computed once and reused for gradient, face value, divergence, and advection — see [WIKI-L-024](../code/WIKI-L-024.md) §2.1.

## Cross-references

- Root cause: [WIKI-T-045](../theory/WIKI-T-045.md), [WIKI-E-030](../experiment/WIKI-E-030.md)
- Current operator: [WIKI-T-044](../theory/WIKI-T-044.md)
- Immediate alternative: [WIKI-T-052](../theory/WIKI-T-052.md) (R-1.5 theory) + [WIKI-L-023](../code/WIKI-L-023.md) (impl roadmap)
- Long-term replacement: [WIKI-T-046](../theory/WIKI-T-046.md) (FCCD) + [WIKI-T-050](../theory/WIKI-T-050.md) (non-uniform algebra) + [WIKI-T-051](../theory/WIKI-T-051.md) (wall BC) / [SP-A](../../memo/short_paper/SP-A_face_centered_upwind_ccd.md)
- **A-01 advection axis**: [WIKI-T-055](../theory/WIKI-T-055.md) (FCCD advection operator; BF-preservation theorem) + [WIKI-T-056](../theory/WIKI-T-056.md) (Wall Option IV) + [WIKI-L-024](../code/WIKI-L-024.md) (library) + SP-D
- Balanced-Force principle: [WIKI-T-004](../theory/WIKI-T-004.md)
- CSF model error floor: [WIKI-T-009](../theory/WIKI-T-009.md), [WIKI-T-017](../theory/WIKI-T-017.md)
- Companion topology track: [WIKI-X-019](WIKI-X-019.md)
