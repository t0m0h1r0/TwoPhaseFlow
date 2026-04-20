# WIKI-X-018: H-01 Remediation Map — G^adj Metric Unification via FCCD

## Context

[WIKI-E-030](../experiment/WIKI-E-030.md) confirmed **H-01** as the unique primary cause of the late-time blow-up on non-uniform grids: the pressure-gradient operator $\mathcal{G}^{\text{adj}}$ (introduced in [WIKI-T-044](../theory/WIKI-T-044.md)) lives on the FVM face metric, while $\sigma\kappa\nabla\psi$ remains on the node-centred CCD metric. The Balanced-Force residual $|\text{BF}_\text{res}|$ is then $\mathcal{O}(\Delta x^2)\cdot|d(\log J)/dx|$, measured at ≈ 884 on Exp-1 step 1.

[ACTIVE_LEDGER](../02_ACTIVE_LEDGER.md) CHK-152 records the open action item: *"G^adj と σκ∇ψ を同一メトリクス空間に統一 (将来タスク)"*. This cross-domain entry maps the action item to concrete candidate remediations.

## Remediation options

| Option | Method | Where it lives | BF order | Code impact | Status |
|---|---|---|---|---|---|
| **R-0** (current) | Mixed metric: $\mathcal{G}^{\text{adj}}$ on face, CCD on node | [`ns_pipeline.py:381`](../../../src/twophase/simulation/ns_pipeline.py#L381) | $\mathcal{O}(h^2)$ residual | no change | ✗ (drives late blow-up) |
| **R-1** | FCCD unified on face (*recommended PoC*) | **SP-A / [WIKI-T-046](../theory/WIKI-T-046.md)** | $\mathcal{O}(h^4)$ | new operator class; node-face layout | **candidate**; PoC pending |
| **R-2** | Node-centred $\mathcal{G}$ restoration via Jacobian-weighted face → node interpolation | project research option | likely $\mathcal{O}(h^2)$ with large constant | moderate | not drafted |
| **R-3** | Full IIM reprojection post-corrector | [WIKI-T-034](../theory/WIKI-T-034.md) | $\mathcal{O}(h^4)$ variational | large (variational Hodge projection) | long-range |

**Preferred path**: R-1. Rationale:

- R-1 aligns $\mathcal{G}p$ and $\nabla\psi$ on the same face locus *by construction*; no auxiliary interpolation is required.
- R-1 inherits the Chu–Fan (1998) combined-compact derivation, keeping the compact-stencil property that motivated the original CCD choice.
- R-1 is a drop-in replacement for `_fvm_pressure_grad` in the corrector stage; the CCD-node path can remain for transport until the node-face hybrid decision is made.
- R-2 retains the metric mismatch at higher implementation cost.
- R-3 is structurally cleaner but requires a full variational solve at each corrector step.

## PoC gate

Adoption of R-1 is gated on the three PoCs enumerated in [WIKI-T-046](../theory/WIKI-T-046.md):

- **PoC-1** (1D $\mathcal{O}(h^4)$ convergence)
- **PoC-2** (BF residual reduction on the WIKI-E-030 benchmark) — **this is the decisive measurement**
- **PoC-3** (non-uniform stretched-grid derivation and verification)

## Mode implications

If PoC-2 demonstrates $|\text{BF}_\text{res}|$ reduction from the current $\mathcal{O}(h^2)$ to $\mathcal{O}(h^4)$ on the Exp-1 setting, the paper revision mode selection is triggered:

- **Mode α**: R-1 adopted as a §8b correction path only. §04/§08 collocated commitment is preserved; R-1 is described as "an alternative face-locus operator used exclusively for the non-uniform corrector".
- **Mode β**: R-1 replaces the node-centred pressure gradient entirely. §04/§08 are rewritten as "node-face hybrid", and the CCDSolver is retained only for the level-set transport.
- **Mode γ**: R-1 is combined with SP-B ([WIKI-T-047](../theory/WIKI-T-047.md) / [WIKI-T-048](../theory/WIKI-T-048.md)) to become the new core of the two-phase framework.

The pivot decision is deferred to the post-PoC review.

## Cross-references

- Root cause: [WIKI-T-045](../theory/WIKI-T-045.md), [WIKI-E-030](../experiment/WIKI-E-030.md)
- Current operator: [WIKI-T-044](../theory/WIKI-T-044.md)
- Proposed replacement: [WIKI-T-046](../theory/WIKI-T-046.md) / [SP-A](../../memo/short_paper/SP-A_face_centered_upwind_ccd.md)
- Balanced-Force principle: [WIKI-T-004](../theory/WIKI-T-004.md)
- Companion topology track: [WIKI-X-019](WIKI-X-019.md)
