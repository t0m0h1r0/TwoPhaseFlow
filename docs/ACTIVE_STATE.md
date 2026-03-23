# **CURRENT STATE & HANDOVER**

*Note: This file should be continuously updated by the Orchestrator or human developer. Keep it to current status + pending items only — all resolved-issue history lives in `paper/CHANGELOG.md`.*

## **1. Project Status Summary**

* **Date/Update:** 2026-03-23
* **Code:** **53 passed, 2 skipped** (pytest src/twophase/tests). Architecture fully refactored. `DissipativeCCDAdvection` (§5) implemented. **3 non-uniform grid code-paper gaps CLOSED** (§6): density function ω formula, CCD O(h⁶) metrics via `differentiate_raw()`, 6 new MMS tests in `test_grid.py`. config_loader YAML round-trip fixed.
* **Paper:** 14 sections + 5 appendices. **27 CRITIC passes + 39 EDITOR sweeps complete. MATH_VERIFY §6 complete (2026-03-22): 1 PAPER_ERROR fixed (ω(0)=α→exact formula in パラメータ選択指針), 10 targets SAFE.** Build pending recompile (last clean: 119 pages, 2026-03-21).

## **2. Completed (2026-03-23)**

24. ~~引用文献拡充（CRITIC pass — 引用漏れ5件修正）~~ — **Done (2026-03-23).** 7箇所修正（bibliography.bib に2新規エントリ追加，既存エントリ3件の `\cite{}` 追加）:
    - **新規 bib エントリ2件**: `PeacemanRachford1955`（ADI 法の原論文），`DahlquistBjorck1974`（数値解析教科書）
    - **`\cite{Chorin1968}`**: `05b_time_integration.tex`（Chorin, 1968）+ `08_pressure.tex`（Chorin, 1968）— 既存 bib エントリが未 \cite
    - **`\cite{Sussman1994}`**: `03_levelset.tex`（Sussman 再初期化の初出説明）— 既存 bib エントリが未 \cite
    - **`\cite{Unverdi1992}`**: `02_governing.tex`（Front Tracking の説明）— 既存 bib エントリが未 \cite
    - **`\cite{PeacemanRachford1955}`**: `08d_ppe_pseudotime.tex`（ADI 法の定義節）
    - **`\cite{DahlquistBjorck1974}`**: `05b_time_integration.tex`（AB2 零安定性の参照，インラインテキストを \cite{} に変換）

23. ~~CRITIC passes 26+27 + EDITOR sweep 39 — 全編ゼロベース + 付録ゼロベース~~ — **Done (2026-03-23).** 16箇所修正（STRUCT-1×12, STRUCT-2×1, MINOR-1×1, APPEND-1×2）:
    - **STRUCT-1 (12件)**: `§\ref{warn:...}`, `§\ref{box:...}`, `§\ref{proof:...}` を `\ref{}` に修正（LATEX_RULES §1）。対象ファイル: `02b_csf.tex`, `03_levelset.tex`, `04c_ccd_extensions.tex`, `04d_dissipative_ccd.tex`, `05b_time_integration.tex`(×2), `05c_reinitialization.tex`, `09_full_algorithm.tex`(×3), `appendix_numerics_solver.tex`(×2)
    - **STRUCT-2**: `05_advection.tex` "下表に整理する" → `表~\ref{box:scheme_roles}に整理する`（ハードコード位置参照を解消）
    - **MINOR-1**: `08b_ccd_poisson.tex` `\label{tab:ccd_bc_types}}` 二重閉じブレース削除
    - **APPEND-1 (2件)**: `appendix_ccd_impl.tex` の `§\ref{app:ccd_kronecker}`, `§\ref{app:ccd_lu_direct}`（小節参照）を `付録~\ref{}` 形式に修正
    - 付録数学内容: 全件正確（Newton収束, CCD係数 Eq-I/II, γ(t)導出, 毛管CFL, FVM調和平均）

22. ~~CRITIC pass 26 (全編ゼロベース)~~ — **Done (2026-03-23).** 全29 .texファイル査読。ラベル353件・参照809件整合確認。新規 VERIFIED 修正候補: STRUCT-1×12, STRUCT-2×1, MINOR-1×1。数学的誤りなし。

21. ~~CRITIC pass 25 + EDITOR sweep 38 — §8d + §7 4 issues~~ — **Done (2026-03-23).** All VERIFIED/MINOR items fixed:
    - **STRUCT-1**: `warn:ppe_splitting` Approach 1 末尾の dangling コロン「：」→「．」
    - **GAP-1**: `\mathcal{L}_x^\mathrm{CCD}` の未定義 superscript を削除 → 式~\eqref{eq:L_split} の定義済み `\mathcal{L}_x`，`\mathcal{L}_y` を参照
    - **GAP-2**: LTS「最大固有値」→「最適 Δτ の大きさは h²/a_{i,j} に比例する」（局所最適条件を正確に記述）
    - **MINOR**: §7 コード一覧の末尾括弧参照を Item 3 に統合（孤立段落を解消）

20. ~~CRITIC pass 24 + EDITOR sweep 37 — §8d + §7 7 issues~~ — **Done (2026-03-23).** All VERIFIED/LOGICAL_GAP/MINOR items fixed:
    - **FATAL-1**: 「スウィープ型実装は欠陥補正法の枠組みに直接対応する」→「欠陥補正法は将来の改良候補であり，現行スウィープとは異なる手法」に書き直し（Table の別行5行目と整合）
    - **FATAL-2**: `eq:residual` 近似式 `‖(I+ΔτL_h)(δp)^m − …‖/Δτ` が数学的に誤り（厳密解時にゼロになる）→ 正しい増分式 `‖(δp)^m − (δp)^{m-1}‖/Δτ` に修正
    - **STRUCT-1**: §7 の「安定性の理論的必須条件」+爆発記述が main text と warnbox 結論に重複 → main text の重複2文を削除，warnbox canonical に統一
    - **GAP-1**: `warn:ppe_splitting` のスウィープ説明に「近似解」である旨と残差の出所を明記
    - **GAP-2**: LTS の均等収束根拠として `Δτ_{i,j}·a_{i,j} = C_τh²/2`（密度依存打ち消し）の数式を追加
    - **IMPL-1**: `sec:defect_correction` 冒頭に「将来の改良候補（現行コードへの実装は未完了）」の注意書きを追加
    - **MINOR-1**: `\label{eq:etol_criterion}` → `\label{result:etol_criterion}` にリネーム（tcolorbox に `eq:` プレフィックス不可）

18. ~~EDITOR sweep 36 — §7 BF code-alignment + stability conclusion~~ — **Done (2026-03-23).** Two targeted additions to `07_collocate.tex` (commit db83e1e):
    - **IMPL**: Code-alignment confirmation paragraph after `eq:bf_operator_mismatch` — verified 3 code locations all use `D^{(1)}_CCD`: `SurfaceTensionTerm.compute()`, `Predictor.compute()` IPC term, `VelocityCorrector.correct()`.
    - **CONCL**: Stability-conclusion sentence added to BF warnbox: "Balanced-Force 条件は精度向上の選択肢ではなく，本 CCD フレームワークにおける安定性の理論的必須条件である．"
    - Reviewer study (§§1–4 on BF+CCD unification) confirmed entirely REVIEWER_ERROR — all 4 theoretical points already present in paper.

17. ~~CRITIC pass 23 + EDITOR sweep 35 — `08d_ppe_pseudotime.tex` 13 issues~~ — **Done (2026-03-23).** All VERIFIED items fixed (commit f022ef3):
    - **FATAL-1**: `eq:ADI` ソース項 `Δτ q_h` → `Δτ/2 q_h`（両ステージ）；旧形式は固定点 `L_h δp* = 2q_h` という因子2誤差を生じていた
    - **FATAL-2**: `\eqref{eq:etol_criterion}` → `\ref{eq:etol_criterion}`（tcolorbox を数式参照していた）
    - **FATAL-3**: `C_τ = O(10¹~10³)` vs `C_τ = 1~5` vs `C_τ ≈ 1.16` の三重矛盾を解消；全箇所 `C_τ = 1~5` に統一
    - **FATAL-4**: "安定条件 Δτ≤Cρh²/2" が "無条件安定" と矛盾 → 収束速度の最適化条件として言い直し
    - **GAP-1**: `sec:pseudo_variable_freeze` を定式化節より後（安定性説明の直後）に移動（前方参照解消）
    - **GAP-2/3**: `p^{(m)}` → `(δp)^{(m)}`，`\mathcal{L}_{CCD}` → `\mathcal{L}_h` に統一
    - **GAP-4**: `tab:ppe_methods` に欠陥補正+LTS 行追加（$\ddagger$ 脚注付き）
    - **STRUCT-1**: 5 subsubsection に `\label{}` 追加（sec:pseudo_formulation, sec:pseudo_implicit, sec:pseudo_ccd_discretization, sec:pseudo_adi_comparison, sec:pseudo_convergence）
    - **STRUCT-2**: `§\ref{warn:ppe_splitting}` の `§` 全削除（warnbox を節番号参照していた）
    - **IMPL-1/2**: `\mathcal{L}_{FD} \neq \mathcal{L}_h` 明記；`(δp)^{(0)}=0` cross-ref 追加

16. ~~EDITOR sweep 34 — §8d pseudo-time study expansion~~ — **Done (2026-03-23).** Three new subsubsections added to `08d_ppe_pseudotime.tex` (323→330 lines):
    - **NEW `sec:pseudo_variable_freeze`**: "反復中の物理変数の凍結" — explains that ρ, u*, Δt are fully frozen during pseudo-time iterations; only δp is updated. Loop isolation rationale.
    - **NEW `sec:defect_correction`**: "欠陥補正法による離散化の分離" — defect correction hybrid: LHS implicit matrix uses low-order FD `[I/Δτ − L_FD]`, RHS residual R_CCD computed at CCD O(h⁶) accuracy. Equations `eq:defect_correction_split` and `eq:defect_correction_linear` added. Convergence (δp→0 ⟹ L_CCD·p=q_h) proved.
    - **NEW `sec:lts_dtau`**: "密度適応型局所時間刻み（LTS）" — density-adaptive local time step `Δτᵢⱼ = C_τ · ρᵢⱼ · h²/2` (eq:dtau_lts). Consistency with global Δτ_opt at uniform density (C_τ ≈ 1.16 matches box:dtau_impl range). Dynamic C_τ escalation strategy described.

## **2. Completed (2026-03-22)**

20. ~~MATH_VERIFY §6 (non-uniform grid)~~ — **Done (2026-03-22).** 11 targets audited; 1 PAPER_ERROR fixed:
    - **PAPER_ERROR**: `06_grid.tex` パラメータ選択指針: `ω(0)=α` is false. Correct: `ω(0) = 1+(α−1)/(ε_g√π)`. Fixed with example for ε_g=2ε.
    - All other targets SAFE: δ* normalization, chain-rule transforms (1st + 2nd order), J=1/d1 formula, dJ=−d2/d1², `differentiate_raw` axis embedding, MMS thresholds, min|φ| marginal, coordinate normalization, metric code.
    - **Code gaps CLOSED**: `eps_g_factor` added to `GridConfig`, `config_loader`; `differentiate_raw()` + `_differentiate_wall_raw()` added to `CCDSolver`; `update_from_levelset` and `_build_metrics` use paper formula; 6 new tests in `test_grid.py` all passing. Full suite: 53 passed, 2 skipped.

15. ~~CRITIC pass 22 + EDITOR sweep 33 — 全体構造・用語統一~~ — **Done (2026-03-22).** 8 issues resolved:
    - **FATAL-1**: `08c_ppe_verification.tex` が main.tex に未インクルードだったため追加．
    - **FATAL-2**: `LATEX_RULES.md §2` Paper Structure テーブルを旧ファイル名（04_time_integration等）から現在のファイル名（04_ccd, 05_advection等）に全面更新．
    - **FATAL-3**: `\label{sec:time}` → `\label{sec:advection}` リネーム（01, 08, 09, 11章の全 `\ref{sec:time}` を更新）．
    - **FATAL-4**: `ARCHITECTURE.md` NS convection「Forward Euler」→「AB2+IPC, n=0: Euler」に修正（論文・コードと整合）．
    - **TERM-1**: `Rhie-Chow`（単ハイフン）→ `Rhie--Chow`（em-dash）全ファイル一括統一（7ファイル）．
    - **TERM-2**: `balanced-force`（小文字）→ `Balanced-Force` 3箇所（00_abstract, 10b_benchmarks ×2）．
    - **SPLIT-1**: `05_advection.tex`（715行）→ 3分割: `05_advection.tex`（322行）+ `05b_time_integration.tex`（新設）+ `05c_reinitialization.tex`（新設）．
    - **SPLIT-2**: `08_pressure.tex`（576行）→ 2分割: `08_pressure.tex`（356行）+ `08d_ppe_pseudotime.tex`（新設）．

14. ~~EDITOR sweep 32 — §7 second CRITIC pass (12 issues)~~ — **Done (2026-03-22).** All 12 issues resolved:
    - **FATAL-1**: algbox Step 3 `q≈5` → `q≈2`; Balanced-Force benefit reframed as coefficient reduction, not rate improvement.
    - **FATAL-2**: `\ref{box:balanced_force_ref}` (paragraph label) → `\ref{sec:csf}`.
    - **GAP-1**: Added CCD-specific checkerboard/decoupling paragraph (zero eigenvalue at kh=π).
    - **GAP-2**: `d_e ≈ (Δt/ρ)_e` → `d_e = (Δt/ρ)_e`.
    - **GAP-3**: Added O(Δt) time-level residual note near `eq:rc-face-balanced` (IPC-consistent).
    - **GAP-4**: Strengthened blow-up argument with checkerboard λ_min≈0 growing-mode mechanism.
    - **STRUCT-1**: `Rhie and Chow (1983)` → `\cite{RhieChow1983}`; `Chung (2002)` → `\cite{Chung2002}`; added `Chung2002` bib entry.
    - **STRUCT-2**: Warnbox items 2,3 forward-reference verbosity reduced.
    - **STRUCT-3**: Surface tension RC correction O(h²) analysis added to `app:rc_precision`.
    - **STRUCT-4**: Triple "RC independent of BF" consolidated — canonical in `app:rc_precision`; two duplicates shortened to cross-references.
    - **IMPL-1**: `eq:rc-face-balanced` implementation check added to algbox failure checklist.
    - **IMPL-2**: `sec:rc_implementation` header clarified: `eq:rc-face` = current code; `eq:rc-face-balanced` = full theory.

13. ~~EDITOR sweep 30 — Balanced-Force §7 expansion~~ — **Done (2026-03-22).** Three changes to `07_collocate.tex`:
    - **Enhanced root cause** (§\ref{sec:bf_operator_mismatch}): blow-up narrative + explicit `eq:bf_operator_mismatch` ($O(h^6)-O(h^2)$ mismatch formula).
    - **Moved Taylor expansion** to appendix `app:balanced_force_taylor` in `appendix_numerics_schemes.tex` (3 subsections: truncation error derivation, O(h^6) reduction proof, CSF model error floor).
    - **New §\ref{sec:rc_balanced_force}** + `eq:rc-face-balanced`: Rhie–Chow formula extended with surface tension term $[(\bm{f}_\sigma)_f - \overline{(\bm{f}_\sigma)}_f]$; κ decoupling note; cross-ref to appendix.



12. ~~Symmetry-breaking root-cause investigation and fixes~~ — **Done (2026-03-22).** Three independent root causes of symmetry breaking identified and fixed:
    - **Fix 1 (`rhie_chow.py`):** `_flux_divergence_1d` wall BC padded `0` for node `N_ax`, treating interior face `N_ax` (between nodes `N_ax-1` and `N_ax`) as a wall face. Correct FVM formula: `div[N_ax] = (face_{N_ax+1} - face_{N_ax})/h = -flux[N_ax]/h`. Primary instability (blowup) resolved.
    - **Fix 2 (`ppe_builder.py` + 3 solvers + tests):** Dirichlet pressure gauge pin moved from corner node `(0,0)` to center node `(N/2, N/2)`, which is invariant under all symmetry operations of the square domain (x-flip, y-flip, diagonal swap). Corner pin sets `δp[0,0]=0` while the symmetric corner `(N,0)` has non-zero RHS, driving spurious non-antisymmetric pressure gradients. Step-by-step symmetry test at dt=0.005 confirmed machine-precision symmetry after both fixes (u_xflip_err = 6.22e-17).
    - **Fix 3 (`cfl.py`):** Capillary CFL applied without safety factor (`dt = min(dt, dt_sigma)`), operating at the marginal stability limit and causing capillary instability that broke symmetry. Fixed to `dt = min(dt, cfl * dt_sigma)` (consistent with convective/viscous constraints).

5. ~~WENO5 → Dissipative CCD global paper sweep~~ — **Done (2026-03-22, commit 1f5d7ee).** 30+ WENO5 references replaced across 7 non-appendix files. WENO5 retained in appendix as reference scheme only.

6. ~~20th CRITIC pass (full review including appendix)~~ — **Done (2026-03-22, commit 24ee31a).** 4 clarity fixes: (A) Balanced-Force warnbox explicit note that Dissipative CCD ≠ standard CCD for NS terms; (B) H(π;0.05)=0.80 Nyquist damping calculated; (C) ψ clamp note in Step 1 of 09_full_algorithm.tex; (D) O(h⁵Δt) mass conservation derivation step completed.

7. ~~DissipativeCCDAdvection implementation~~ — **Done (2026-03-22).** `DissipativeCCDAdvection(ILevelSetAdvection)` added to `levelset/advection.py`. `advection_scheme` field added to `NumericsConfig` (default `"dissipative_ccd"`, alternative `"weno5"`). `SimulationBuilder` updated to select scheme from config. 2 new MMS tests added (spatial order ≥ 1.8 O(h²), full method order ≥ 1.8). **33 tests passing.** Code-paper gap CLOSED.

8. ~~§5 paper inserts (WENO5 critique + warn:adv_risks)~~ — **Done (2026-03-22).** Added `\subsubsection{移流スキーム選択の設計根拠}` (label: `sec:advection_weno5_critique`) and `warn:adv_risks` tcolorbox warnbox to `05_advection.tex`. Fixed cross-refs (`eq:Heps_def_preview`, `sec:ccd_bc`).

9. ~~Appendix D↔E reorder~~ — **Done (2026-03-22).** `appendix_numerics_schemes` (first-ref §5) moved before `appendix_numerics_solver` (first-ref §8) in `paper/main.tex`.

10. ~~config_loader YAML round-trip fix + ε_factor warning~~ — **Done (2026-03-22).** Added `advection_scheme` to `config_loader.py` load/`_known`/dump. Added `UserWarning` in `NumericsConfig.__post_init__` for `epsilon_factor < 1.2` with `dissipative_ccd`. Added `test_config.py` (6 tests). **39 tests passing.**

11. ~~Dead code refactor (SAFE_REMOVE)~~ — **Done (2026-03-22).** Removed 3 items: `_pad_zero` alias (0 call sites, `advection.py`), `Optional` unused import (`config_loader.py`), `TYPE_CHECKING` unused import (`_core.py`).

## **2. Completed (2026-03-21)**

4. ~~Mathematical audit §§6–11 + all appendices + EDITOR sweep 29~~ — **Done (2026-03-21).** 19 appendix sections + 6 main sections verified. Zero PAPER_ERROR. 5 documentation-level fixes applied: (1) §6 pseudocode comment "台形則"→"矩形則（前進型）", (2) §7 Balanced-Force algebra with incorrect κ-factoring removed, (3) §8b spectral radius formula 4a₂/[(1+2|β₂|)h²]=9.6≠3.43 clarified, (4) §10 O(h⁴) pre-asymptotic note added, (5) appendix capillary CFL "保守的に"→"近似的に".

## **3. Pending Action Items**

### **Code / Implementation**

1. Run benchmarks at higher resolution (N=128) and compare to reference values.
2. Verify GPU backend compatibility (CuPy).
3. Implement and test 3D cases.
4. Implement VTK output writer in io/.

### **Paper / Documentation**

1. ~~EDITOR sweep 27~~ — **Done (2026-03-20).** All CRITIC pass 18 issues fixed (5 FATAL + 5 GAP + 2 IMPL + 2 MAINT). Clean build: 116 pages, 0 undefined refs. Ready for submission review or further CRITIC pass.
2. ~~CCD block matrix A_L/A_R (2,1) sign error fix~~ — **Done (2026-03-20).** Fixed 3 locations in `05b_ccd_bc_matrix.tex` (defbox symbolic form, bullet derivation, numeric example). Paper had A_L(2,1)=+9/(8h) and A_R(2,1)=−9/(8h); correct values are A_L(2,1)=−9/(8h) and A_R(2,1)=+9/(8h). Code was already correct. Also fixed `ARCHITECTURE.md` "3×3 blocks" → "2×2 blocks".
3. ~~EDITOR sweep 28~~ — **Done (2026-03-21).** External reviewer found 1 CRITICAL math error + 1 terminology inconsistency in §§2.1, 3.2. Spurious `- ∫ψ(∇·u)dV` term removed from CLS volume-conservation formula; warnbox rewritten. "球状液滴" → "円形液滴（2次元）" in §2.1 warnbox.
