# WIKI-X-021: N-Scaling of the H-01 Mixed-Metric Residual — 128² Parasitic Blow-up (CHK-173)

## Context

[WIKI-X-018](WIKI-X-018.md) identified **H-01** (mixed CCD-node / FVM-face metric of the CSF-PPE-corrector chain) as the structural cause of late-time blow-up on non-uniform grids at $N = 64$. The Balanced-Force residual $|\text{BF}_\text{res}|$ measured there (≈ 884 on Exp-1 step 1) was taken as an absolute figure; the question of how the residual **scales with the grid refinement parameter $N$** was left implicit.

CHK-173 closes that gap. The same fullstack configuration (`ch13_04_capwave_fullstack_alpha2`, $\alpha_\text{grid}=2$, FCCD + Ridge-Eikonal + GFM + HFE) passes at $N = 64$ to $T = 8$ ([CHK-160](../../02_ACTIVE_LEDGER.md) C7 PASS), but **blows up at $N = 128$ at $t \approx 0.014$ (step 126)** with the classic parasitic-current signature: KE climbing $4.3 \times 10^{-7} \to 1.02 \times 10^{6}$, volume conservation at machine precision, deformation almost unchanged.

This cross-domain entry establishes that **H-01's residual is not $N$-independent** — it grows at least linearly with $N$ through the CCD metric factor $J = 1/h_\text{phys}$ — and refutes two attempted remediation paths (Option A and Option C) that tried to sidestep the [WIKI-X-018](WIKI-X-018.md) R-1.5/R-1 programme.

## Scaling law

### CCD metric chain

[`CCDSolver._apply_metric`](../../../src/twophase/ccd/ccd_solver.py#L587) applies

$$
\partial_x u = J \cdot \partial_\xi u, \qquad \partial_{xx} u = J^2 \cdot \partial_{\xi\xi} u + J \cdot (dJ/d\xi) \cdot \partial_\xi u, \qquad J = \frac{1}{h_\text{phys}}.
$$

Every CCD derivative therefore amplifies by a factor $J$. Under $N:64 \to 128$, $h_\text{phys}$ halves on the interface-fitted refined region, so $J$ doubles.

### CSF-PPE pipeline

The PPE RHS constructed in [`ns_pipeline.py:744`](../../../src/twophase/simulation/ns_pipeline.py#L744) is

$$
\text{rhs}_\text{PPE} \;=\; \underbrace{\frac{1}{\Delta t}\nabla_{\text{CCD}} \cdot u^\star}_{\text{single } J}
\;+\; \underbrace{\nabla_{\text{CCD}} \cdot \frac{\sigma \kappa_\text{CCD} \, \nabla_{\text{CCD}} H_\varepsilon}{\rho}}_{\text{three nested CCD derivatives}}.
$$

Each of the three factors in the CSF branch scales as $J$:

1. $\kappa_\text{CCD}$ uses CCD second-derivatives in [`curvature_psi.py:118`](../../../src/twophase/levelset/curvature_psi.py#L118) → $J$-scaled.
2. $\nabla_{\text{CCD}} H_\varepsilon$ is a CCD first-derivative → $J$-scaled; moreover $\varepsilon \propto h_\text{phys}$ (local-$\varepsilon$ field) adds an independent $J$ factor through $|\nabla H_\varepsilon| \propto 1/\varepsilon$.
3. The outer $\nabla_{\text{CCD}} \cdot$ → $J$-scaled.

Net: $\text{rhs}_\text{PPE}^{\text{CSF}} \propto J^3$. The corrector gradient $\nabla_{\text{FVM}} p$ has **no $J$ factor** (plain $(p_{i+1} - p_i)/d_\text{face}$). The H-01 residual

$$
|\text{BF}_\text{res}| \;=\; \bigl|\nabla_{\text{FVM}} p \;-\; f/\rho \bigr|
$$

therefore inherits the $J^3$ mismatch from the PPE RHS that constructed $p$.

### Empirical verification (V2 probes)

Step-1 diagnostics on `ch13_04_probe_{64,128}.yaml` (fullstack short run, $T_\text{final}=0.01$):

| Metric | $N=64$ | $N=128$ | Ratio | Predicted |
|---|---|---|---|---|
| `kappa_max` | 488 | 1020 | 2.09 | 2 (linear $J$) |
| `ppe_rhs_max` | 67 | 576 | 8.58 | 8 ($J^3$) |
| `bf_residual_max` | 9.8 | 44 | 4.5 | 2–8 |

The PPE-RHS ratio 8.58 matches the $J^3$ prediction to one significant digit.

## Attempted remediations

CHK-173 tested two paths that **avoided** the [WIKI-X-018](WIKI-X-018.md) R-1.5/R-1 recommendation. Both are recorded here as negative results.

| Option | Change | Rationale | $N=64$ | $N=128$ | Verdict |
|---|---|---|---|---|---|
| **Baseline (R-0)** | FVM PPE + FVM-grad + CCD-RHS | current production | PASS T=8 | blow at $t=0.014$ | $N$-unsafe |
| **Option A** | FVM PPE + **CCD-grad** + CCD-RHS | restore CCD consistency at corrector | div_u 0.42 → 2.64 (6.3× worse) | div_u 1.38 → 17.2 (12× worse) | **refuted** |
| **Option C** | **CCD iterative-ADI** PPE + CCD-grad + CCD-RHS (no LU per memory constraint) | full CCD consistency, no Kronecker LU | PPE residual 2.0e+3 @500 iter (tol 1e-8); `bf_res=218`, `div_u=0.88` | PPE residual 2.5e+4 @500 iter; `bf_res=857`, `div_u=2.66` | **refuted** |

### Why Option A fails

Breaking the projection identity $\mathcal{L}_\text{FVM} = \nabla_\text{FVM} \cdot \nabla_\text{FVM}$: FVM-PPE assumes the FVM gradient operator in the corrector. Substituting $\nabla_\text{CCD} p$ makes $\nabla_\text{CCD} \cdot (u^\star - (\Delta t/\rho) \nabla_\text{CCD} p) \neq \nabla_\text{FVM} \cdot u^\star$, so $\nabla \cdot u \neq 0$ after correction. This is the operator-consistency requirement of [WIKI-T-004](../theory/WIKI-T-004.md) §"Projection identity" applied at the gradient axis.

### Why Option C fails

[WIKI-T-024](../theory/WIKI-T-024.md) §"ADI failure" already theorised that the CCD residual evaluated against a 3-pt ADI-Thomas smoother does not converge: the smoother's eigen-decomposition does not align with the CCD operator's high-order stencil, leaving $\mathcal{O}(1)$ components undamped. The CHK-173 empirical residuals (2.0e+3 and 2.5e+4 after 500 iterations) are direct confirmation. Increasing `pseudo_maxiter` 10× would still not close the 9–12 digit gap to `tol=1e-8`; the smoother would have to be replaced (Krylov + CCD preconditioner, CG/BiCGStab).

## Relation to WIKI-X-018

WIKI-X-021 **extends**, does not replace, the [WIKI-X-018](WIKI-X-018.md) remediation map:

- The [WIKI-X-018](WIKI-X-018.md) R-1.5 path (`_fvm_pressure_grad` on $\psi$, node-face unification via FVM) remains the recommended immediate fix. CHK-173's $J^3$ scaling argument **strengthens** the case: as $N$ grows, the mixed-metric residual grows at least like $N$ (via $\kappa$) and likely like $N^3$ (via the full CSF pipeline), so the 64²-only diagnosis in WIKI-X-018 understates the problem.
- The [WIKI-X-018](WIKI-X-018.md) R-1 path (FCCD unified face operator, SP-A) is the long-term target. The $J^3$ scaling provides a second motivation: not just constant-factor accuracy improvement, but $N$-robustness.
- The "stay CCD-side" alternative (Option C in this entry) is **closed**: [WIKI-T-024](../theory/WIKI-T-024.md) predicts and CHK-173 confirms that no matrix-free CCD PPE iteration converges with the available smoothers.

The migration path is therefore unchanged from [WIKI-X-018](WIKI-X-018.md):

> R-1.5 (immediate, 3-line edit) → R-1 (SP-A / FCCD, when PoC succeeds).

## Constraint on "no-LU CCD PPE" design

A recurring user directive during CHK-173 was "stay CCD, avoid LU due to memory". The CHK-173 evidence constrains this as follows:

1. **Direct CCD Kronecker-LU** (`PPESolverCCDLU`): O(N⁴) memory, rejected.
2. **CCD residual + ADI smoother** (`PPESolverIterative(ccd,adi)`): does not converge — [WIKI-T-024](../theory/WIKI-T-024.md) + CHK-173.
3. **CCD residual + Gauss–Seidel smoother**: same eigen-mismatch, no reason to expect convergence.
4. **CCD residual + Krylov (CG/BiCGStab) with CCD preconditioner**: not implemented; open design question.
5. **FFT-based PPE with CCD modified wavenumbers**: restricted to periodic BC, incompatible with wall.

The practically available paths that are both *CCD-consistent* and *no-LU* are (4) and perhaps a dedicated compact multigrid. Neither is available in the current codebase; implementing one is out of scope for CHK-173.

## Cross-references

- Upstream cross-domain: [WIKI-X-018](WIKI-X-018.md) (H-01 remediation map, R-1.5/R-1)
- Downstream cross-domain: [WIKI-X-022](WIKI-X-022.md) (N-robust full-stack architecture — 10-method role map that uses the CHK-173 evidence as its motivating constraint)
- Balanced-Force principle: [WIKI-T-004](../theory/WIKI-T-004.md) (operator consistency)
- FVM reference methods: [WIKI-T-017](../theory/WIKI-T-017.md) (face-coefficient PPE, Rhie-Chow)
- CCD-PPE solver theory: [WIKI-T-024](../theory/WIKI-T-024.md) (DC+LU results, **ADI failure**) — the theoretical basis that predicts Option C's non-convergence
- CSF model error floor: [WIKI-T-009](../theory/WIKI-T-009.md)
- Non-uniform metric: [WIKI-T-057](../theory/WIKI-T-057.md) ($\sigma_\text{eff}/\varepsilon_\text{local}$), [WIKI-T-058](../theory/WIKI-T-058.md) (physical-space Hessian)
- Current code paths:
  - Mixed-metric production: [`ns_pipeline.py:168-171`](../../../src/twophase/simulation/ns_pipeline.py#L168) (FVM-grad on non-uniform wall, CCD-grad otherwise)
  - PPE RHS construction: [`ns_pipeline.py:735-744`](../../../src/twophase/simulation/ns_pipeline.py#L735)
  - CCD metric factor: [`ccd_solver.py:587-606`](../../../src/twophase/ccd/ccd_solver.py#L587)
  - FVM gradient operator: [`gradient_operator.py:71-118`](../../../src/twophase/simulation/gradient_operator.py#L71)

## CHK rows

| CHK | Delivery | Notes |
|---|---|---|
| CHK-152 | WIKI-X-018 (64²-scale H-01 remediation map) | Foundation |
| CHK-160 | ch13_04 fullstack $N=64$ $\alpha=2$ PASS | Baseline for $N$-scaling study |
| CHK-171 | 128² hires + velocity/pressure/psi evolution series | Exposed $N=128$ blow-up |
| **CHK-173** | **$J^3$ scaling evidence; Options A, C refuted** | **This entry** |
