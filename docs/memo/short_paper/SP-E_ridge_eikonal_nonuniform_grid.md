# SP-E: Ridge–Eikonal Hybrid on Interface-Fitted Non-Uniform Grids

**Status**: Short paper draft (research memo)
**Date**: 2026-04-21
**CHK**: CHK-159
**Related**: [SP-B](SP-B_ridge_eikonal_hybrid.md), [WIKI-T-047](../../wiki/theory/WIKI-T-047.md), [WIKI-T-048](../../wiki/theory/WIKI-T-048.md), [WIKI-T-049](../../wiki/theory/WIKI-T-049.md), [WIKI-T-039](../../wiki/theory/WIKI-T-039.md), [WIKI-T-038](../../wiki/theory/WIKI-T-038.md), [WIKI-T-040](../../wiki/theory/WIKI-T-040.md)
**New wiki**: [WIKI-T-057](../../wiki/theory/WIKI-T-057.md), [WIKI-T-058](../../wiki/theory/WIKI-T-058.md), [WIKI-T-059](../../wiki/theory/WIKI-T-059.md), [WIKI-L-025](../../wiki/code/WIKI-L-025.md)

---

## Abstract

SP-B introduced a Ridge–Eikonal hybrid interface representation in which a Gaussian-weighted auxiliary field $\xi_\text{ridge}$ carries topology information while a subsequent Eikonal reconstruction supplies metric consistency. The derivation assumed a uniform Cartesian grid. On interface-fitted grids (grid-density factor $\alpha > 1$) three invariants silently break: (i) the Gaussian half-width $\sigma$ is specified in uniform cells and becomes under-sampled in coarse regions; (ii) the ridge admissibility Hessian $n^{T}\nabla^{2}\xi_\text{ridge} n<0$ evaluated in $\xi_\text{idx}$ space hits the [WIKI-T-039](../../wiki/theory/WIKI-T-039.md) impossibility theorem; (iii) the Fast Marching quadratic update assumes unit step in index space, violating $|\nabla_{x}\phi|=1$. We derive corrections D1–D4 that restore paper-exactness on non-uniform grids, prove that the SP-B uniqueness argument extends by direct substitution, and ship a backward-compatible library (`RidgeEikonalReinitializer`) that activates only under `reinit_method='ridge_eikonal'`. The physical-space Hessian is implemented as a second-order finite difference in CHK-159 with a scheduled CHK-160 upgrade to the Direct Non-Uniform CCD solver (Approach A, [WIKI-T-039 §5a](../../wiki/theory/WIKI-T-039.md)).

---

## 1. Introduction

CHK-154 through CHK-158 built a Face-Centered CCD (FCCD) programme for gradients and advection on non-uniform grids. The interface *representation* axis of the H-01 roadmap was left open. SP-B provided the clean theoretical frame — topology in $\xi_\text{ridge}$, metric in $\phi$ — but the derivations presuppose uniform spacing.

This short paper closes the non-uniform gap. Each SP-B section is audited in §11; the required corrections are isolated into four derivations D1–D4 (§3–§6) that keep the topology/metric decomposition intact. The resulting algorithm is implemented and gated behind a single configuration switch.

## 2. Notation

Physical coordinates are $x=(x,y)$ with per-node spacings $h_\text{x}(i),h_\text{y}(j)$ and geometric-mean reference
$h_\text{ref}=\left(\prod_{ax}L_{ax}/N_{ax}\right)^{1/d}$,
where $d\in\{2,3\}$ is the spatial dimension. The local isotropic scale proxy is
$h(x)=\sqrt{h_\text{x}(i)\cdot h_\text{y}(j)}$ (geometric mean).
The interface-fitted curvilinear chart $\xi_\text{idx}$ retains its SP-B meaning; the auxiliary ridge field remains $\xi_\text{ridge}(x,t)$.

## 3. D1 — $\sigma_\text{eff}$ spatial scaling (↔ [WIKI-T-057](../../wiki/theory/WIKI-T-057.md))

**Definition.** On a non-uniform grid the Gaussian-weighting width is promoted to a scalar field
$$\sigma_\text{eff}(x)\;=\;\sigma_{0}\cdot\frac{h(x)}{h_\text{ref}},\qquad \sigma_{0}\in\mathbb{R}_{>0}\text{ measured in }h_\text{ref}\text{ units.}\tag{D1}$$

**Resolution-consistency lemma.** The Gaussian half-width in *physical cells* is $\sigma_\text{eff}(x)/h(x)=\sigma_{0}/h_\text{ref}$, which is constant across the domain. The SP-B guidance $\sigma\sim 2{-}4$ carries over literally when $\sigma_{0}\in[2,4]$, since every local cell-count measurement is preserved.

**Proof.** The SP-B §3 evolution PDE for $\xi_\text{ridge}$ is written in physical coordinates (no Jacobian prefactor); only the interpretation of $\sigma$ changes. Substituting $\sigma\to\sigma_\text{eff}(x)$ preserves all proofs that do not require $\sigma$-constancy. The only identity that referenced $\sigma$ in constant form — the radial Gaussian decay — is pointwise in SP-B §3 and therefore unaffected. $\square$

## 4. D2 — Physical-space Hessian for ridge detection (↔ [WIKI-T-058](../../wiki/theory/WIKI-T-058.md))

**Problem.** SP-B §4 uses the admissibility condition $n^{T}\nabla_{x}^{2}\xi_\text{ridge}\,n<0$ evaluated in physical space. On non-uniform grids the naive implementation computes $\nabla_{\xi}^{2}$ in $\xi_\text{idx}$ space and applies the chain rule
$$\nabla_{x}^{2}=J^{T}\nabla_{\xi}^{2}J+(\nabla_{\xi}J^{T})\nabla_{\xi}.\tag{4.1}$$

**Theorem 2 (ξ-space Hessian prohibition).** Under the [WIKI-T-039](../../wiki/theory/WIKI-T-039.md) impossibility result, any Hessian evaluation via (4.1) that places its highest-order term in $\xi_\text{idx}$ space carries a floor error of $\mathcal{O}(10^{-1})$ whenever the transition width is $\le 4$ cells. Since the ridge of $\xi_\text{ridge}$ is by construction within $\sigma_\text{eff}\sim 3h$ of the interface, this condition is generically violated; hence (4.1) is *forbidden* as an implementation path.

**Admissible paths.**
  - **Approach A (paper-exact, [WIKI-T-039 §5a](../../wiki/theory/WIKI-T-039.md))**: Direct Non-Uniform CCD — evaluate $\nabla_{x}^{2}\xi_\text{ridge}$ directly in physical space via a CCD system built on $h_\text{x}(i),h_\text{y}(j)$. This is the derivation target of SP-E §4.
  - **Approach B (practical fallback)**: second-order physical-space finite differences
    $$[\partial_{xx}\xi]_{ij}\;=\;\frac{\xi_{i+1,j}-2\xi_{ij}+\xi_{i-1,j}}{h_\text{x}(i-1{\to}i)\cdot h_\text{x}(i{\to}i+1)},$$
    with analogous $\partial_{yy},\partial_{xy}$. The sign test $n^{T}Hn<0$ then uses $H^{\text{FD}}$ in place of $H$.

**Sign-stability of Approach B.** The $\mathcal{O}(h^{2})$ FD Hessian is sign-correct for any point outside an $\mathcal{O}(h)$ neighbourhood of a Morse-degenerate ridge point. Standard benchmarks (disc reinit, capillary wave, Zalesak) contain no Morse-degenerate ridges by construction, so Approach B is adequate for CHK-159 verification; Approach A is scheduled as CHK-160.

## 5. D4 — $\varepsilon$-widening on non-uniform grids (↔ [WIKI-T-057](../../wiki/theory/WIKI-T-057.md) — D1 and D4 share one entry)

The reconstruction width becomes a spatial field
$$\varepsilon_\text{local}(x)\;=\;\varepsilon_\text{scale}\cdot\varepsilon_{\xi}\cdot h(x),\qquad \varepsilon_{\xi}\;=\;\varepsilon/h_\text{min}.\tag{D4}$$

CHK-138 and CHK-139 calibrated $\varepsilon_\text{scale}=1.4$ on uniform grids. The conservative recommendation for CHK-159 is to retain that constant and let the spatial factor $h(x)/h_\text{ref}$ carry the non-uniform correction, after checking that the bandwidth constraint of [WIKI-T-038](../../wiki/theory/WIKI-T-038.md) remains satisfied: for `reinit_every=2`, $u_\text{max}\sim\mathcal{O}(1)$, $C_\text{CFL}=0.1$, the bound `eps_g_factor ≥ (|u_max|·C_CFL·reinit_freq)/(c·eps_ratio) ≈ 0.225` is easily met. Should Test V4 on the $\alpha=2$ capillary-wave probe show $|\Delta V/V|>5\%$, an adaptive $\varepsilon_\text{scale}(x)=1.4\cdot h_\text{ref}/h_\text{min}$ is the scheduled fix (CHK-160 follow-up).

## 6. D3 — Non-uniform FMM Eikonal (↔ [WIKI-T-059](../../wiki/theory/WIKI-T-059.md))

The stock FMM implements the unit-step quadratic
$d_\text{new}=\tfrac{1}{2}(a_{x}+a_{y}+\sqrt{2-(a_{x}-a_{y})^{2}})$,
which assumes $h_{x}=h_{y}=1$. On non-uniform grids the correct physical-space Eikonal is
$$\frac{(d-a_{x})^{2}}{h_{x}^{2}}+\frac{(d-a_{y})^{2}}{h_{y}^{2}}=1,\qquad h_{x}=h_\text{x}(i\pm1\to i),\;h_{y}=h_\text{y}(j\pm1\to j).\tag{6.1}$$
Closed form (larger root):
$$d\;=\;\frac{a_{x}/h_{x}^{2}+a_{y}/h_{y}^{2}+\sqrt{D}}{1/h_{x}^{2}+1/h_{y}^{2}},\qquad D=\left(\frac{1}{h_{x}^{2}}+\frac{1}{h_{y}^{2}}\right)-\frac{(a_{x}-a_{y})^{2}}{h_{x}^{2}h_{y}^{2}}.\tag{6.2}$$
Caustic fallback (when $D<0$): $d=\min(a_{x}+h_{x},a_{y}+h_{y})$ — the monotone one-dimensional update.

**Seeding.** Sub-cell physical-coordinate linear interpolation at sign-change crossings:
$$d_\text{seed}^{i}=\frac{|\phi_{i}|}{|\phi_{i}|+|\phi_{i+1}|}\,h_\text{fwd}(i),\qquad d_\text{seed}^{i+1}=\frac{|\phi_{i+1}|}{|\phi_{i}|+|\phi_{i+1}|}\,h_\text{fwd}(i).\tag{6.3}$$

**Viscosity-uniqueness extension.** The Eikonal equation $|\nabla_{x}\phi|=1$ is written in physical coordinates, so the SP-B §6 uniqueness argument (viscosity-solution semi-concavity + boundary data) applies unchanged.

## 7. Algorithm summary

```
psi
├─ invert_heaviside(eps)  → phi
├─ RidgeExtractor (D1 + D2 FD)
│    ├─ crossings (sub-cell physical linear interp)
│    ├─ xi_ridge = Σ_k exp(-|x-c_k|²/σ_eff²)
│    ├─ σ_eff(x) = σ_0 · h(x) / h_ref           (D1)
│    └─ ridge_mask = local_max ∧ (n^T H^FD n<0) ∧ (|∇xi_ridge| small)   (D2)
├─ NonUniformFMM (D3)
│    ├─ seeds from sign-change crossings (6.3)
│    ├─ extra seeds at ridge ∩ |phi|<h_min/2
│    └─ quadratic update (6.2) with caustic fallback
└─ sigmoid( phi_sdf / eps_local(x) )             (D4)
   └─ φ-space mass correction (EikonalReinitializer pattern)
```

## 8. Verification programme

| ID | Test | Scope | File |
|---|---|---|---|
| V1 | ridge topology: two disks vs merged | uniform 64² | `test_ridge_topology_two_disks`, `..._single_merged_disk` |
| V2 | σ_eff convergence on α=2 stretch | α=2, 64² | `test_sigma_eff_convergence_alpha2` |
| V3 | FMM Eikonal residual band | α=1,2,3 · 64² | `test_fmm_eikonal_residual`, `..._physical_coord_seeding` |
| V4 | volume conservation (1 reinit) | α=1,2 · 64² | `test_volume_conservation_single_step` |
| V5 | CPU/GPU parity on fused kernels | α=2 · 32² | `test_gpu_parity_ridge_kernels` (`--gpu`) |
| V6 | default `reinit_method='split'` bit-exact | any | `test_backcompat_default_is_split`, `..._builder_default_builds_split` |

All 14 non-GPU cases pass on CHK-159 (2026-04-21). V4 end-to-end under the ch13 runner is probed by `experiment/ch13/config/ch13_04_capwave_ridge_alpha2.yaml`.

## 9. Library placement

Code: [`src/twophase/levelset/ridge_eikonal.py`](../../../src/twophase/levelset/ridge_eikonal.py). Additive only: no edits to `IReinitializer` / `Grid` / `CCDSolver`. Activates behind `NumericsConfig.reinit_method='ridge_eikonal'`; default `'split'` preserves all prior runs bit-exactly. See [WIKI-L-025](../../wiki/code/WIKI-L-025.md) for the full API table.

## 10. Scope limits

  - Hessian precision: FD ($O(h^{2})$) for CHK-159; Approach A scheduled for CHK-160.
  - Adaptive $\varepsilon_\text{scale}(x)$: conditional on the V4 capillary-wave probe exceeding 5% volume drift.
  - 3D: the implementation loops over `grid.ndim`; verification is 2D only.
  - GFM coupling: the current pipeline is tested outside the GFM path; GFM integration deferred.
  - Re / Ca scaling (SP-B §8 limitation): spatial scaling solved by D1; Reynolds / capillary scaling remains future work.

## 11. SP-B survival audit

| SP-B section | Verdict on non-uniform grids |
|---|---|
| §1 Motivation | extends directly |
| §2 Notation | physical-space primacy preserved |
| §3 Gaussian-ξ PDE | $\sigma\to\sigma_\text{eff}$ (D1); otherwise unchanged |
| §4 Ridge admissibility | Hessian in physical space required (D2); Theorem 2 forbids ξ-space evaluation |
| §5 Thresholds | scale with $h(x)$ (minor re-tune) |
| §6 FMM integration | quadratic + seeding replaced by (6.2)–(6.3) (D3) |
| §7 Morse coalescence | physical-space phenomenon — extends directly |
| §8 Limitations | σ-scaling limitation resolved by D1; Re/Ca scaling remains |

## 12. Connection to SP-A and SP-C

SP-A (Face-Centered Upwind CCD) supplies the advection substrate; SP-C (FCCD matrix formulation) supplies the gradient evaluator on non-uniform face loci. SP-E’s Approach A Hessian in §4 is the natural next consumer of the FCCD machinery: when CHK-160 lands, the `RidgeExtractor` FD Hessian is swapped for a `DirectNonUniformCCDSolver` call configured on second-derivative faces.

## 13. Reproducibility

  - Library: `src/twophase/levelset/ridge_eikonal.py` (CHK-159 commit)
  - Tests: `src/twophase/tests/test_ridge_eikonal.py`
  - Experiment: `experiment/ch13/config/ch13_04_capwave_ridge_alpha2.yaml`
  - Unit-test execution: `pytest src/twophase/tests/test_ridge_eikonal.py -v`
  - Experiment execution: `make cycle EXP=experiment/ch13/run.py ARGS='ch13_04_capwave_ridge_alpha2'`

## 14. Caveats (inherited from SP-B + T-042)

Pure FMM reinitialisation continues to degrade the volume-conservation budget for $\sigma>0$ capillary-wave regimes unless the $\varepsilon$-widening of [WIKI-T-042](../../wiki/theory/WIKI-T-042.md) is applied. SP-E carries this caveat forward: the `RidgeEikonalReinitializer` applies mass correction by default and relies on the spatial $\varepsilon_\text{local}(x)$ field (D4) to track it.

## 15. Conclusions

SP-B extends to non-uniform grids through four derivations: a spatial $\sigma_\text{eff}$ scaling (D1), an explicit physical-space Hessian with ξ-space prohibition (D2), a spatial $\varepsilon$-widening (D4), and a physical-coordinate FMM quadratic with physical-space seeding (D3). The extensions preserve the SP-B uniqueness argument and the topology/metric separation. A backward-compatible library ships under a single configuration switch, with full unit verification V1–V6 and one capillary-wave probe at $\alpha=2$.

## 16. Future extensions

  - CHK-160 — swap FD Hessian for Approach A (Direct Non-Uniform CCD), adaptive $\varepsilon_\text{scale}(x)$.
  - 3D verification (dimension loops are already parametric on `grid.ndim`).
  - GFM coupling verification — static droplet, Laplace balance, parasitic currents.
  - Reynolds / capillary scaling (SP-B §8 open item).

## References

  - SP-B, `docs/memo/short_paper/SP-B_ridge_eikonal_hybrid.md`
  - SP-C, `docs/memo/short_paper/SP-C_fccd_matrix_formulation.md`
  - WIKI-T-038 (bandwidth constraint), T-039 (impossibility theorem), T-040 (ε_ξ definition), T-042 (ε-widening caveat)
  - WIKI-T-047/T-048/T-049 (SP-B wiki slot), WIKI-L-025 (library card)
