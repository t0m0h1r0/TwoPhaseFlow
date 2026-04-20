---
ref_id: WIKI-T-052
title: "R-1.5: Minimal FVM-Face σκ∇ψ Unification via Existing _fvm_pressure_grad"
domain: theory
status: PROPOSED  # Theory ready; implementation deferred to CHK-155
superseded_by: null
sources:
  - path: docs/wiki/cross-domain/WIKI-X-018.md
    description: H-01 Remediation Map — R-0/R-1/R-2/R-3 (R-1.5 added by this entry)
depends_on:
  - "[[WIKI-T-044]]: G^adj Face-Average Gradient (the operator R-1.5 reuses)"
  - "[[WIKI-T-046]]: FCCD (R-1's higher-order target)"
  - "[[WIKI-T-004]]: Balanced-Force Operator Consistency Principle"
  - "[[WIKI-T-009]]: CSF Model Error O(h^2) — accuracy floor argument"
  - "[[WIKI-T-017]]: FVM Reference: Rhie–Chow & Balanced-Force Accuracy"
  - "[[WIKI-T-045]]: Late Blowup Hypothesis Catalog — H-01 PRIMARY"
consumers:
  - domain: code
    description: WIKI-L-023 (R-1.5 implementation roadmap, Phase 1 = 3-line edit)
  - domain: cross-domain
    description: WIKI-X-018 (R-1.5 row added to remediation map)
  - domain: future-impl
    description: CHK-155 (implement Phase 1, run ch13_02 verification)
tags: [h01_remediation, balanced_force, fvm, immediate_fix, csf, bf_residual, research_proposal]
compiled_by: Claude Opus 4.7
compiled_at: "2026-04-20"
---

# R-1.5: Minimal FVM-Face σκ∇ψ Unification via Existing `_fvm_pressure_grad`

## Why this entry exists

[WIKI-X-018](../cross-domain/WIKI-X-018.md) catalogues four H-01 remediation options (R-0…R-3). The recommended path R-1 (FCCD, [WIKI-T-046](WIKI-T-046.md)) is **PoC-gated** and requires:

- a new operator class,
- non-uniform extension ([WIKI-T-050](WIKI-T-050.md)) and wall BC ([WIKI-T-051](WIKI-T-051.md)) algebra (the present round of theoretical work),
- 1-D, 2-D, and stretched-grid convergence verification.

Realistic timeline: weeks. Meanwhile the late blow-up of [WIKI-E-030](../experiment/WIKI-E-030.md) is reproducible and blocks any further capillary-wave benchmarking on $\alpha = 1.5$ stretching. This entry proposes **R-1.5** — an immediate-deployment alternative that:

1. **Reuses the existing `_fvm_pressure_grad` helper** (already used for $\nabla p$ in the corrector — see [`ns_pipeline.py:381`](../../../src/twophase/simulation/ns_pipeline.py#L381)) for $\nabla \psi$ in the CSF body force,
2. Achieves **machine-precision Balanced-Force consistency for constant $\kappa$**,
3. Is **3 lines of code** ([WIKI-L-023](../code/WIKI-L-023.md) Phase 1),
4. Is a **strict precondition** for FCCD: any face-locus operator (R-1) reduces to R-1.5's $\mathcal{O}(H^2)$ residual when its cancellation coefficients are dropped (see [WIKI-T-050](WIKI-T-050.md) §"Reduction to G^adj").

R-1.5 is therefore not a competitor to R-1; it is the **bridge** that makes the system safe while R-1's PoC runs.

## Definition

Let $G^{\text{face}}$ denote the existing face-average gradient implemented by `_fvm_pressure_grad`:

$$
\bigl(G^{\text{face}} u\bigr)_i \;=\; \frac{1}{2}\!\left[\frac{u_{i+1} - u_i}{d_f^{(i)}} + \frac{u_i - u_{i-1}}{d_f^{(i-1)}}\right] \qquad (1 \le i \le N-1),
$$
$$
\bigl(G^{\text{face}} u\bigr)_0 \;=\; \bigl(G^{\text{face}} u\bigr)_N \;=\; 0 \qquad (\text{wall Neumann}),
$$

with $d_f^{(i)} = x_{i+1} - x_i$ ([WIKI-T-044](WIKI-T-044.md)).

**R-1.5 prescription.** In the CSF assembly ([`ns_pipeline.py` Step 2 ~L753–767](../../../src/twophase/simulation/ns_pipeline.py#L753)), replace

$$
f_x \;=\; \sigma\, \kappa \cdot \underbrace{\partial_x \psi\big|_{\text{CCD, node-metric}}}_{\text{R-0 (current)}}
\quad\Longrightarrow\quad
f_x \;=\; \sigma\, \kappa \cdot \underbrace{\bigl(G^{\text{face}} \psi\bigr)}_{\text{R-1.5 (proposed)}}
$$

under the **same activation guard** that already gates `_fvm_pressure_grad` in the corrector:

```
if not self._grid.uniform and self.bc_type == "wall":
    use G^face          # R-1.5 path
else:
    use CCD             # legacy path (uniform grid or periodic BC)
```

The corrector pressure-gradient path is **unchanged**: it continues to use `_fvm_pressure_grad`. The result is that, under the guard, both $\nabla p$ and $\nabla \psi$ in the corrector are evaluated by the **same operator**:

$$
u^{n+1} \;=\; u^* \;-\; \frac{\Delta t}{\rho}\, G^{\text{face}} p \;+\; \frac{\Delta t}{\rho}\, \sigma\,\kappa\, G^{\text{face}} \psi.
$$

## Mathematical properties

### BF residual: machine precision for constant κ

The Balanced-Force residual at a node $i$ is

$$
\text{BF}_{\text{res}}(i) \;:=\; \bigl(G^{\text{face}} p\bigr)_i \;-\; \sigma\,\kappa(i)\,\bigl(G^{\text{face}} \psi\bigr)_i.
$$

For a **circular interface in equilibrium** with constant curvature $\kappa(i) \equiv \kappa_0$ and pressure jump $p = \sigma \kappa_0 \psi + \text{const}$ (Laplace law), substitution gives

$$
\text{BF}_{\text{res}}(i) \;=\; G^{\text{face}}(p - \sigma\kappa_0 \psi)_i \;=\; G^{\text{face}}(\text{const})_i \;=\; 0 \quad \text{(machine precision)}.
$$

This holds **identically**, independent of grid spacing, because the linear operator $G^{\text{face}}$ annihilates constants exactly. Compare:

| Scheme | $\text{BF}_{\text{res}}$ on equilibrium static droplet (constant $\kappa$) |
|---|---|
| R-0 (current, mixed metric) | $\mathcal{O}(\Delta x^2) \cdot \|d\!\log J/dx\|$ — measured 884 on Exp-1 step 1 |
| **R-1.5 (this entry)** | **machine precision (zero by linearity)** |
| R-1 (FCCD) | machine precision (same argument; higher order on smooth $\kappa$) |

### Order of accuracy on variable κ

For non-constant curvature $\kappa(x)$, the residual is

$$
\text{BF}_{\text{res}}(i) \;=\; \sigma \cdot \bigl[\,G^{\text{face}}(\kappa\,\psi)_i - \kappa(i)\,G^{\text{face}}(\psi)_i\,\bigr] \;=\; \mathcal{O}(\Delta x^2 \cdot \|\nabla \kappa\| \cdot \|\nabla \psi\|).
$$

This is **inside the existing CSF model error floor** $\mathcal{O}(\Delta x^2)$ documented in [WIKI-T-009](WIKI-T-009.md) and [WIKI-T-017](WIKI-T-017.md): the CSF formulation itself contributes $\mathcal{O}(\Delta x^2)$ from regularising the Dirac-delta interface forcing. Reducing the BF operator-mismatch contribution below that floor would not improve solution accuracy; it would be over-engineering.

The constant-$\kappa$ machine-precision result is the relevant figure of merit because the late blow-up of [WIKI-E-030](../experiment/WIKI-E-030.md) was triggered by a quasi-equilibrium configuration ($T \approx 12$, residual capillary motion), not by sharp curvature gradients.

### Backward compatibility on uniform grids and periodic BC

The activation guard `not self._grid.uniform and self.bc_type == "wall"` keeps R-1.5 dormant on:

- **uniform grids**: $G^{\text{face}}$ and CCD agree to leading order ($G^{\text{face}}$ is $\mathcal{O}(h^2)$, CCD is $\mathcal{O}(h^6)$ — using CCD here is strictly better);
- **periodic BC**: CCD is well-behaved without a wall closure, and the existing benchmark suite under periodic BC does not exhibit H-01 symptoms.

Existing experiment results on uniform grids and periodic BCs are therefore **bit-for-bit unchanged** by R-1.5.

### Reduction relationship to R-1 (FCCD)

The non-uniform FCCD operator of [WIKI-T-050](WIKI-T-050.md) is

$$
D^{\text{FCCD,nu}} u_f \;=\; \underbrace{\frac{u_i - u_{i-1}}{H}}_{=\,G^{\text{face,1pt}} u_f} \;-\; \mu(\theta) H \tilde u''_f \;-\; \lambda(\theta) H^2 \tilde u'''_f.
$$

Setting both cancellation coefficients to zero yields the per-face one-sided difference, and averaging this to the node (via the ½-weighted average in `_fvm_pressure_grad`) recovers exactly $G^{\text{face}}$. Hence:

- **R-1.5 = R-1 with $\mu \equiv \lambda \equiv 0$ and node-centred averaging.**
- R-1.5 saves one order of accuracy ($\mathcal{O}(H^2)$ vs $\mathcal{O}(H^4)$) for the cost of zero implementation work (the helper exists).
- When R-1's PoC succeeds, the per-face cancellation terms are added on top of the same algebraic structure; R-1.5 becomes the $\mu = \lambda = 0$ degenerate baseline — no rework of the surrounding code is needed.

## Risk analysis

| Risk | Likelihood | Mitigation |
|---|---|---|
| Order reduction breaks transport-step accuracy | None | R-1.5 modifies only the CSF body force. Level-set transport ([WIKI-T-036](WIKI-T-036.md)) still uses CCD. |
| Uniform-grid regression | None | Activation guard preserves CCD path on uniform grids — bit-exact. |
| Periodic-BC regression | None | Activation guard preserves CCD path on periodic BC. |
| PPE residual change | Low | PPE RHS still uses CCD divergence on the new $f_x$ — projection-consistency stance is unchanged from R-0. R-1.5 targets BF only, not PC. |
| 2-D corner cells (two walls meeting) | Low | $G^{\text{face}}$ already handles corners in `_fvm_pressure_grad` — R-1.5 reuses the same indexing. |
| Hidden coupling with HFE / curvature filter | Low | $\kappa$ is computed from $\psi$ via the same CCD path as before; only the post-multiplication factor changes. |
| Hidden coupling with CN viscous step | None | Viscous step is independent of $\sigma$ branch. |

The risk profile is dominated by zeros — by design, R-1.5 only changes one expression in one branch.

## When R-1.5 is *not* enough

R-1.5 reduces BF residual to the CSF model floor $\mathcal{O}(\Delta x^2)$ but does **not** address:

- **Spurious currents from the CSF model itself.** These persist at $\mathcal{O}(\Delta x^2)$ and are independent of operator choice; addressed by [WIKI-T-009](WIKI-T-009.md), [WIKI-T-025](WIKI-T-025.md) (C/RC).
- **Transport-step accuracy.** The level-set evolution remains $\mathcal{O}(\Delta x^6)$ via CCD; R-1.5 only changes the corrector branch.
- **Higher-order BF for sharp-feature benchmarks.** When PoC measurements show that $\mathcal{O}(\Delta x^2)$ BF is the dominant error in a specific benchmark, R-1 (FCCD) becomes mandatory. R-1.5 is a stopgap, not a permanent solution for $\mathcal{O}(\Delta x^4)$ targets.

## Decision matrix: R-1.5 vs R-1

| Criterion | R-1.5 | R-1 (FCCD) |
|---|---|---|
| BF residual on constant $\kappa$ | machine precision | machine precision |
| BF residual on smooth $\kappa$ | $\mathcal{O}(h^2)$ | $\mathcal{O}(h^4)$ (uniform) / $\mathcal{O}(h^3)$ (non-uniform) |
| Implementation work | 3-line edit ([WIKI-L-023](../code/WIKI-L-023.md)) | new operator class + wall BC + non-uniform algebra |
| PoC effort | Phase-1 verification on ch13_02 (1 run) | PoC-1, PoC-2, PoC-3 of WIKI-T-046 |
| Risk of regression | near-zero (guard) | moderate (new code path) |
| Permanent if accuracy floor is met | yes (CSF floor is $\mathcal{O}(h^2)$) | yes (above CSF floor) |
| Available now | yes (CHK-155 ready) | weeks-scale PoC |

**Recommended course.** Deploy R-1.5 immediately ([WIKI-L-023](../code/WIKI-L-023.md) Phase 1) to unblock $\sigma > 0$ non-uniform benchmarks. Keep the R-1 PoC programme in parallel; if R-1's PoC-2 demonstrates a benchmark-relevant accuracy improvement, upgrade R-1.5 → R-1 by adding the cancellation terms on top of the same operator skeleton.

## Effect on the [WIKI-X-018](../cross-domain/WIKI-X-018.md) remediation map

A new row is added between R-0 and R-1:

| Option | Method | BF residual | Code impact | Status |
|---|---|---|---|---|
| R-0 (current) | Mixed metric | $\mathcal{O}(h^2)$ residual | no change | ✗ (drives blow-up) |
| **R-1.5 (new)** | **Reuse `_fvm_pressure_grad` on $\psi$** | **machine precision (const $\kappa$); $\mathcal{O}(h^2)$ (variable $\kappa$)** | **3-line edit, guarded** | **proposed (immediate)** |
| R-1 | FCCD unified | $\mathcal{O}(h^4)$ uniform / $\mathcal{O}(h^3)$ non-uniform | new operator class | candidate (PoC-gated) |
| R-2 | Jacobian-weighted face → node | $\mathcal{O}(h^2)$ large constant | moderate | not drafted |
| R-3 | IIM reprojection | $\mathcal{O}(h^4)$ variational | large | long-range |

PoC gating is restructured to enable parallel exploration:

- **R-1.5 PoC** (immediate, 1 run): implement Phase 1 → run `ch13_02_waterair_bubble.yaml` to $T = 20$ → measure `bf_residual_max` and verify no late blow-up.
- **R-1 PoC** (weeks-scale, 3 runs): WIKI-T-046 PoC-1/2/3 as previously specified.

R-1.5 is **not** a substitute for R-1's PoC; it is an emergency-stable baseline that runs while the PoC programme proceeds.

## Verification programme (post-implementation, deferred to CHK-155)

The implementation roadmap is in [WIKI-L-023](../code/WIKI-L-023.md). The verification battery is:

1. **Static droplet equilibrium.** Verify `bf_residual_max → O(1e-14)` on $\alpha = 1.5$ stretched grid (compare R-0's 884).
2. **`ch13_02_sigma0` regression.** Verify zero behaviour change with $\sigma = 0$ (the guard is irrelevant when CSF is off, but bit-exact regression confirms no leakage into the predictor branch).
3. **`ch13_02_waterair_bubble` survival.** Run to $T = 20$ on $\alpha = 1.5$; verify no late blow-up.
4. **Convergence in N.** Repeat (3) at $N = 32, 64, 128$; verify stable scaling and no N-dependent regression.
5. **Uniform-grid regression.** Run a uniform-grid `ch13_*` config and confirm bit-exact reproduction of pre-R-1.5 results.

Items 1–5 are deferred to a separate worktree (CHK-155) per the present scope (theoretical compilation only).

## References

- [WIKI-T-044](WIKI-T-044.md) — `_fvm_pressure_grad` definition and PC proof
- [WIKI-T-046](WIKI-T-046.md), [WIKI-T-050](WIKI-T-050.md), [WIKI-T-051](WIKI-T-051.md) — R-1 (FCCD) target
- [WIKI-T-004](WIKI-T-004.md) — Balanced-Force operator-consistency principle
- [WIKI-T-009](WIKI-T-009.md), [WIKI-T-017](WIKI-T-017.md) — CSF model error floor
- [WIKI-T-045](WIKI-T-045.md), [WIKI-E-030](../experiment/WIKI-E-030.md) — H-01 root cause and reproduction
- [WIKI-X-018](../cross-domain/WIKI-X-018.md) — H-01 remediation map (this entry adds R-1.5 row)
- [WIKI-L-023](../code/WIKI-L-023.md) — implementation roadmap
- [`ns_pipeline.py`](../../../src/twophase/simulation/ns_pipeline.py) L381–395 (`_fvm_pressure_grad`), L753–767 (CSF assembly), L813–830 (corrector)
