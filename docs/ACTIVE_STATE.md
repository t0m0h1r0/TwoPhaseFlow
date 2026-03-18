# **CURRENT STATE & HANDOVER**

*Note: This file should be continuously updated by the Orchestrator or human developer.*

## **1\. Project Status Summary**

* **Date/Update:** 2026-03-19
* **Code:** 28 tests passing (pytest src/twophase/tests). Architecture fully refactored to use SimulationBuilder and component injection.
* **Paper:** 12 sections + appendix\_proofs. **9 CRITIC passes + 5 EDITOR sweeps + LATEX ENGINE pass complete (2026-03-19).** 8 issues from 9th-pass CRITIC review resolved in EDITOR 5th sweep. Requires re-compile to confirm clean build.

## **2\. Recent Resolutions**

### Paper (2026-03-19 — CRITIC 9th pass + EDITOR 5th sweep)

* **D-1 FIXED**: `00_abstract.tex` defbox — 精度律速行追加（NS 対流項 O(Δt)，CSF O(ε²)；§sec:accuracy_summary 参照）
* **D-2 FIXED**: `07_pressure.tex` tab:ppe_methods — 「精度」列ヘッダー → 「空間離散化次数」；スウィープ型は O(h⁶) が Krylov 実装のみ実現することを明記
* **D-3 FIXED**: `07_pressure.tex` resultbox — balanced-force O(h⁴) 主張を「曲率離散化誤差成分のみ」に限定；CSF O(ε²) 残留を明記
* **D-4 FIXED**: `07_pressure.tex` Predictor Step 1 — ρ^{n+1} の出所と operator splitting 順序を mybox で説明
* **G-1 FIXED**: `08_time_integration.tex` — 負側 β_k^- の3式（eq:weno5_beta_minus）を明示；インデックス反転則を記述
* **G-2 FIXED**: `07_pressure.tex` RC 補正 — (1/ρ)^harm の評価時刻（時刻 n，陽的）を明示
* **G-3 CONFIRMED**: `03_levelset.tex` L.440-448 — N_reinit=28 の指数収束推定式（既存）を確認；変更不要
* **L-1 FIXED**: `07_pressure.tex` warn:boundary_cv — fbox でスキップ案内を追加（CCD 実装者向け）
* **I-2 FIXED**: `07_pressure.tex` Δτ defbox — C_τ=2 推奨値，典型収束回数 10〜30 回の実測値例を追記

---

### Paper (2026-03-18 — LATEX ENGINE pass, 12\_LATEX\_ENGINE.md)

* 13 relative-reference violations eliminated across 5 files (次節/前節/前章/上式 → \\ref/\\eqref).
* 3 new \\label{} added: `sec:ccd_def` (04\_ccd §4.2), `sec:ccd_te_I` (04\_ccd §4.3), `sec:nondim_items` (02\_governing §2.5.4).
* `\\[...\\]` at 02\_governing L898 upgraded to `\\begin{equation}` so `\\label{eq:dny_dy}` is referenceable.
* **106-page PDF: XeLaTeX clean compile, zero undefined references.**

---

### Code (2026-03-15)

* SimulationConfig is now pure sub-config composition (GridConfig, FluidConfig, NumericsConfig, SolverConfig, use\_gpu). All backward-compat shims removed.
* TwoPhaseSimulation.\_\_init\_\_ deleted; SimulationBuilder(cfg).build() is the sole construction path.

---

### Paper (2026-03-18 — EDITOR 4th sweep, post-8th-pass CRITIC)

* **D-1 FIXED**: `05_grid.tex` Python pseudocode — `np.gradient(xi, x)` (O(h²) central diff) replaced with CCD-based Jx evaluation; algbox Step 5 expanded with 3-step CCD application explanation.
* **D-2 FIXED**: `09_full_algorithm.tex` fig:ns_solvers S5 node — "半陰的" → "陽的"; caption updated to state CSF surface tension is explicit (time-n body force).
* **B-1 FIXED**: `10_verification_metrics.tex` warnbox — curvature error claim O(h⁴) corrected to O(h^6) (numerical discretization) vs. O(ε²)≈O(h²) (CSF model error, the bottleneck).
* **B-2 FIXED**: `11_conclusion.tex` §pressure chapter description — "FVM で離散化した" → CCD-PPE(O(h^6)) + 仮想時間陰解法 as primary; FVM relegated to comparison.
* **G-1 FIXED**: `10_verification_metrics.tex` L.131 — `第\ref{sec:governing}章参照` → `§\ref{sec:balanced_force}参照`.
* **L-1 FIXED**: `05_grid.tex` algbox Step 5 — 3-step CCD procedure for Jx made explicit (apply CCD to x(ξ_i) to get dx/dξ and d²x/dξ² simultaneously).
* **L-2 CONFIRMED**: `appendix_proofs.tex` `\ref{sec:two_to_one}` — label exists in `02_governing.tex:79`. No action required.

### Paper (2026-03-18 — EDITOR 3rd sweep, post-7th-pass)

* **04\_ccd.tex** L393-398 warnbox `{境界スキームの役割と精度}` — split blanket "O(h^5)" claim into:
  Equation-I (f'₀): O(h^5); Equation-II (f''₀): O(h^2) with L² impact note (consistent with mybox at L.587-596).

### Paper (2026-03-18 — CRITIC 7th pass, all resolved via 10\_PAPER\_EDITOR)

* **D-1 FIXED**: `07_pressure.tex` resultbox — stale "第§1・§9 で BiCGSTAB と記した箇所" claim removed; §1 and §9 already use 仮想時間陰解法.
* **D-2 FIXED**: `07_pressure.tex` eq:NS\_full — added mybox clarifying derivation uses simplified Backward Euler while implementation uses Crank--Nicolson (O(Δt²)) per §4; CN viscous → implicit linear system for u*.
* **D-3 FIXED**: `01_introduction.tex` L.344 + `09_full_algorithm.tex` fig:ns\_solvers — NS 対流項 explicitly uses Forward Euler (O(Δt)), not TVD-RK3; CLS advection uses TVD-RK3; figure S1 node corrected from "WENO5/TVD-RK3" to "CCD D^(1)/前進Euler".
* **L-5 FIXED**: `01_introduction.tex` tab:chapter\_overview Ch4 — 前提 "3" → "2, 3"; content revised to distinguish CLS(WENO5+TVD-RK3) from NS(前進Euler+CN); Ch5 CCD description scoped to §5 only with PPE application reference to §8.
* **algbox enhancement**: Step 5 scheme names added (前進Euler/CN); Step 6 Rhie-Chow corrected divergence ∇\_h^RC·u\* explicitly referenced.
* **B-1 FIXED**: `07_pressure.tex` warnbox boundary\_cv — titled "(FVM 実装専用)"; note added that CCD-Poisson boundary handling is in §8.5 and does NOT need this correction.
* **B-2 FIXED**: `07_pressure.tex` L.316 — dangling "前処理については下記参照" replaced with reference to §8.5 and tab:ppe\_methods.
* **B-3 FIXED**: `07_pressure.tex` eq:balanced\_force\_condition — asymmetric operator notation corrected; supplementary mybox explains "≈" in terms of CSF O(ε²) accuracy limit.
* **G-3 FIXED**: `07_pressure.tex` eq:rc\_divergence — p^n (前時刻) explicitly noted in Rhie-Chow face velocity formula.

### Paper (2026-03-18 — CRITIC passes 3rd–6th, all resolved via 10\_PAPER\_EDITOR)

**3rd pass:**
* **D-1**: `10_verification_metrics.tex` L93 cross-ref corrected.
* **D-2**: `03_levelset.tex` §3.3 warnbox — CFL wave speed corrected (flux Jacobian `|1-2ψ|≤1`); `Δτ_hyp ≤ Δs`.
* **D-3**: `00_abstract.tex` L21 — `FVM-PPE` → `CCD-PPE（$O(h^6)$）`.

**4th pass:**
* `03_levelset.tex` §3.2 — stability: `Δτ=0.5Δs` → `Δτ=0.25Δs` (within parabolic limit); N\_reinit: 14→28 steps.
* `01_introduction.tex` L445 — relative ref `下図の 7ステップフロー` → `図\ref{fig:algo_flow}の 7ステップフロー`.
* `09_full_algorithm.tex` L67 — `$\mathcal{C}_\text{WENO}$` → `$\mathcal{C}_\text{CCD}$`.
* `03_levelset.tex` §3.4 — false claim "解析的に行えない" → logit inverse + appendix proof; new file `sections/appendix_proofs.tex`.

**5th pass:**
* `08_time_integration.tex` — CLS advection: non-conservative `u·∇ψ` → conservative `∇·(ψu)`.
* `07_pressure.tex` tab:accuracy\_summary — CSF O(ε²)≈O(h²) row added; spatial bottleneck updated.
* `10_verification_metrics.tex` tab:error\_budget — NS predictor: WENO5 O(h⁵) → CCD O(h⁶).
* `11_conclusion.tex` — `ADI分解による求解` → `逐次Thomas法による求解`.
* `01_introduction.tex` + `02_governing.tex` — stale "ニュートン法が必要" → logit analytic inverse.
* `03_levelset.tex` §3.4 warnbox — retitled "ロジット逆変換 vs. Sussman 再初期化".
* `05_grid.tex` algbox step 5 — O(h²) formula replaced with CCD approach.
* `02_governing.tex` L572 — `∫s²δ_ε ds = π²ε²/3` self-contained proof added (Dirichlet η(2)).
* `02_governing.tex` §2.2.3 — 1D One-Fluid proof moved to `appendix_proofs.tex` §\ref{app:onefluid\_1d}.

**6th pass:**
* `09_full_algorithm.tex` L106+L120-123 — ρ(ψ)・μ(ψ) interpolation sign corrected (liquid/gas were swapped).
* `09_full_algorithm.tex` L119 — `(Newton法)` → logit function + Newton fallback note.
* `04_ccd.tex` L21 — 4th-order central diff typo: `+f_{i+2}` → `+f_{i-2}`.
* `05_grid.tex` warnbox — dangling "上記の中心差分" fixed; redundant CCD formulas removed.
* `06_collocate.tex` L35-115 — Helmholtz/Projection scalar φ → Φ (10 instances; local-scope note added).

### Paper (2026-03-18 — CRITIC passes 1st–2nd, all resolved via 10\_PAPER\_EDITOR)

**1st pass:**
* **D-1**: `10_verification_metrics.tex` L93 — `第\ref{sec:governing}章参照` → `§\ref{sec:balanced_force}参照`.
* **D-2**: `03_levelset.tex` §3.3 warnbox — CFL wave speed corrected from function value `|ψ(1-ψ)|≤1/4` to flux Jacobian `|F'(ψ)|=|1-2ψ|` max=1; `Δτ_hyp ≤ 4Δs` → `Δτ_hyp ≤ Δs`; min formula updated.
* **D-3**: `00_abstract.tex` L21 — `FVM-PPE` → `CCD-PPE（$O(h^6)$）`.
* **B-1**: `02_governing.tex` L418-419 — Heaviside figure φ-axis labels swapped: 液相 (φ<0) and 気相 (φ>0), consistent with §2.1 sign convention.
* **B-2**: `11_conclusion.tex` §7.2 description list — reordered to sec:time (Ch4) → sec:CCD (Ch5) → sec:grid (Ch6), matching actual chapter order.
* **B-3**: `11_conclusion.tex` L115-116 — Spatial bottleneck corrected from WENO5 O(h⁵) to CSF O(ε²)≈O(Δx²).
* **M-1**: `04_ccd.tex` L1 comment `05_ccd.tex` → `04_ccd.tex`; `05_grid.tex` L1 comment `04_grid.tex` → `05_grid.tex`.

**2nd pass:**
* **D-1**: `09_full_algorithm.tex` L39 solver box S2 — `FVM-PPE` → `CCD-PPE（$O(h^6)$）`; L53 caption — `FVM ベース PPE` → `CCD-PPE（$O(h^6)$）`.
* **D-2**: `08_time_integration.tex` §sec:godunov defbox — `α = max|ψ(1-ψ)| ≤ 1/4` → `α = max|1-2ψ| ≤ 1`（正しい LF フラックスヤコビアン上界）.
* **B-1**: `10_verification_metrics.tex` tab:error\_budget 最終行 — 空間律速を WENO5 O(h⁵) → CSF O(ε²)≈O(Δx²) に修正; mybox "精度設計のまとめ" の律速記述も同様に修正.

### Paper (2026-03-17 review cycle — all resolved)

* **D-1**: Removed stale FVM-PPE O(h²) bottleneck row from tab:error\_budget; warnbox deleted.
* **D-1b**: Removed CCD-Poisson "future work" framing from 11\_conclusion.tex.
* **D-2**: Fixed ψ convention in 02\_governing.tex defbox (液相でψ≈0，気相でψ≈1).
* **B-1**: M\_ref = M(0) defined in 03\_levelset.tex adaptive reinitialization criterion.
* **B-2**: Quantitative boundary accuracy analysis added to 04\_ccd.tex (O(h²) boundary → O(h³) global).
* **B-3**: Rhie-Chow pressure gradient mixed-precision clarified in 06\_collocate.tex.
* **B-4**: Newton convergence quadratic-convergence proof added to 03\_levelset.tex §3.4.
* **C-1**: tab:chapter\_overview Ch.5 row updated with pseudo-time elliptic interpretation.
* **M-5**: E\_shape norm corrected to L2 formula in 10\_verification\_metrics.tex.

---

## **3\. Pending Action Items**

### **Code / Implementation**

1. Run benchmarks at higher resolution (N=128) and compare to reference values.
2. Verify GPU backend compatibility (CuPy).
3. Implement and test 3D cases.
4. Implement VTK output writer in io/.

### **Paper / Documentation**

1. Final compile and cross-reference check using 12\_LATEX\_ENGINE.md.
