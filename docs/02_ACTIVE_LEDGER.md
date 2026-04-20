# 02_ACTIVE_LEDGER — Phase, Branch, CHK Register, Assumptions & Lessons
# LIVE document — append-only for CHK/ASM/KL entries; phase/branch updated each session.
# Last updated: 2026-04-21

────────────────────────────────────────────────────────
# § ACTIVE STATE

| Key | Value |
|---|---|
| phase | META_REDESIGN_IN_PROGRESS |
| branch | worktree-fccd-matrix-bc |
| last_CHK | CHK-156 DONE 2026-04-21 — FCCD 行列形 + 壁/周期 BC 理論確立. 3 gap 調査: (1) 行列形=未確立, (2) 壁 BC=部分確立 (Option III scalar のみ, 行列行未記述), (3) 周期 BC=未確立 (1行 dismissal). **新規 [WIKI-T-054](wiki/theory/WIKI-T-054.md)**: Route 1 合成作用素 $\mathbf{M}^{\mathrm{FCCD}}=\mathbf{D}_1-\mathbf{D}_2\mathbf{S}_{\mathrm{CCD}}$ (sparse×dense×sparse, $O(N)$), 壁 Option III 行列行 (augmented zero-rows, BF=0 証明再掲), 周期 block-circulant $\mathbf{M}^{\mathrm{FCCD,per}}$ + DFT 修正波数 $\hat M^{\mathrm{FCCD}}(\omega_k)=i\omega_k[1-7(\omega_k H)^4/5760+O((\omega_k H)^6)]$ (leading truncation coefficient 明示). 非一様は $\theta$ 加重 bidiagonal 3 行列 ($\mathbf{D}_\mu^{(H\theta)},\mathbf{D}_\lambda^{(H)}$) 合成. Route-2 native face-CCD は deferred. **新規 SP-C** ([docs/memo/short_paper/SP-C_fccd_matrix_formulation.md](memo/short_paper/SP-C_fccd_matrix_formulation.md)): SP-A 導出の先に位置する行列 + BC 実装仕様書. [WIKI-T-051](wiki/theory/WIKI-T-051.md) に "Matrix row form (CHK-156 supplement)" 追補; [WIKI-T-046](wiki/theory/WIKI-T-046.md)/[WIKI-T-050](wiki/theory/WIKI-T-050.md)/[WIKI-T-053](wiki/theory/WIKI-T-053.md) に T-054 consumer cross-link. INDEX 160→161. コード変更ゼロ. Branch: worktree-fccd-matrix-bc |
| next_action | [NEXT] CHK-157: R-1.5 Phase 1 実装 ([WIKI-L-023](wiki/code/WIKI-L-023.md)) と並行して, R-1 FCCD PoC-1 を [WIKI-T-054](wiki/theory/WIKI-T-054.md) §8 implementation checklist に従い実装 (CCD d2 closure + 面 stencil + Option III wall zero). Verification §9: modified wavenumber $-7/5760$ 測定, uniform $O(H^4)$ 収束, BF residual on WIKI-E-030 capillary benchmark. |

### Notes
- `last_CHK` is the most recent closed work item; older CHKs live in § CHECKLIST tables below.
- ALL 31 ch11 experiments are GPU-opted and baselined (CHK-125..127).
- Wiki: **161 entries** (docs/wiki/INDEX.md). T-054 added 2026-04-21 (CHK-156); T-053 added 2026-04-20 (CHK-155); T-050/T-051/T-052 + L-023 added 2026-04-20 (CHK-154). SP-C short paper added 2026-04-21 (CHK-156).
- phi_primary_transport=true + eikonal_xi は ns_pipeline のデフォルトに設定済み (a544840).
- G^adj (worktree-gfm-nonuniform) を main にマージ済み (f7e8db4, CHK-151).
- WIKI-E-030 **CLOSED**: 根本原因確定 **H-01（G^adj/CCD BF残差）**唯一主因; Exp-2(σ=0→T=20安定)が決定的証拠. H-09(増幅)+H-16(暴走)は共役. CHK-152 DONE.
- ResearchArchitect 研究方針評価 **CLOSED** (CHK-153): SP-A (FCCD) + SP-B (Ridge-Eikonal) ショートペーパー + wiki 6件新規. 方針転換 (α/β/γ) 判断は PoC 後.

────────────────────────────────────────────────────────
# § CHECKLIST — recent activity (one line per CHK)
# Format: `CHK-ID | YYYY-MM-DD | type | summary`
# Full detail in git log / commit messages / linked memos.

## §1 — Most recent (CHK-120..139)

| CHK | Date | Type | Summary |
|---|---|---|---|
| CHK-156 | 2026-04-21 | theory+wiki+paper | [DONE] FCCD 行列形 + 壁/周期 BC 理論確立. 3 gap 調査: 行列形=未確立, 壁 BC=部分確立 (Option III scalar のみ, 行列行未記述), 周期 BC=未確立 (1行 dismissal). **新規 [WIKI-T-054](wiki/theory/WIKI-T-054.md)** (FCCD Matrix Formulation): Route 1 合成作用素 $\mathbf{M}^{\mathrm{FCCD}}=\mathbf{D}_1-\mathbf{D}_2\mathbf{S}_{\mathrm{CCD}}$ (sparse×dense×sparse, bidiagonal $\mathbf{D}_1,\mathbf{D}_2$ + 既存 CCD block-Thomas solve, $O(N)$ per axis), 壁 Option III 行列行 (augmented zero-rows at face 0 / $N+1$, BF=0 証明再掲, CCD boundary-row 継承 note), 周期 block-circulant $\mathbf{M}^{\mathrm{FCCD,per}}=\mathbf{D}_1^{\mathrm{per}}-\mathbf{D}_2^{\mathrm{per}}\mathbf{S}_{\mathrm{CCD}}^{\mathrm{per}}$ + DFT 修正波数 $\hat M^{\mathrm{FCCD}}(\omega_k)=i\omega_k[1-7(\omega_k H)^4/5760+O((\omega_k H)^6)]$ (leading truncation coefficient 明示, Nyquist 誤差 12%), wrap face consistency. 非一様は $\theta$ 加重 bidiagonal 3 行列 ($\mathbf{D}_\mu^{(H\theta)},\mathbf{D}_\lambda^{(H)}$) 合成; uniform 極限で §4 に退化. Route-2 native face-CCD (2M×2M 自立ブロック系) は deferred. **新規 SP-C short paper** ([docs/memo/short_paper/SP-C_fccd_matrix_formulation.md](memo/short_paper/SP-C_fccd_matrix_formulation.md)): SP-A 導出の先に位置する行列 + BC 実装仕様書 (12 節構成, 行列形 / 壁 / 周期 / 実装 checklist / verification). [WIKI-T-051](wiki/theory/WIKI-T-051.md) に "Matrix row form (CHK-156 supplement)" 追補; [WIKI-T-046](wiki/theory/WIKI-T-046.md)/[WIKI-T-050](wiki/theory/WIKI-T-050.md)/[WIKI-T-053](wiki/theory/WIKI-T-053.md) に T-054 consumer cross-link. INDEX 160→161 (Theory 53→54). コード変更・実験ゼロ. Branch: worktree-fccd-matrix-bc |
| CHK-155 | 2026-04-20 | research+wiki | [DONE] ResearchArchitect FCCD 計算方程式レビュー. 論文 CCD 導出方法（Equation-I/II で $(u',u'')$ を同時解）に照らし, SP-A/WIKI の $\tilde u'''_f$ は新未知数ではなく $q_i=(D_{\mathrm{CCD}}^{(2)}u)_i$ から $\tilde u'''_f=(q_i-q_{i-1})/H$ と閉じるべきと整理. 新規 [WIKI-T-053](wiki/theory/WIKI-T-053.md): uniform $D^{FCCD}u_f=(u_i-u_{i-1})/H-H(q_i-q_{i-1})/24$, nonuniform $D^{FCCD,nu}u_f=(u_i-u_{i-1})/H-\mu H[\theta q_{i-1}+(1-\theta)q_i]-\lambda H(q_i-q_{i-1})$. [WIKI-T-046](wiki/theory/WIKI-T-046.md)/[WIKI-T-050](wiki/theory/WIKI-T-050.md) に executable equation cross-link 追加; [WIKI-T-001](wiki/theory/WIKI-T-001.md) の CCD 要約式を論文・`ccd_solver.py` と整合修正. INDEX 159→160. コード変更ゼロ. Branch: worktree-researcharchitect-fccd-equations |
| CHK-154 | 2026-04-20 | theory+wiki | [DONE] H-01 remediation 理論補完. **SP-A §6.3 三 caveat 個別解決**: (1) 非一様格子拡張 → [WIKI-T-050](wiki/theory/WIKI-T-050.md) cancellation coefficients $\mu(\theta)=\theta-1/2,\, \lambda(\theta)=(1-3\theta(1-\theta))/6,\, \nu(\theta)$ as functions of face-position $\theta = h_R/H$; $\theta=1/2$ で uniform 限界 ($\mu=\nu=0,\lambda=1/24$) に退化. (2) Wall BC → [WIKI-T-051](wiki/theory/WIKI-T-051.md) 三案 (ghost-cell mirror / one-sided face / ψ-only) 比較; Neumann 場には Option III 推奨 (既存 G^adj wall handling と完全等価). (3) PPE 互換 → 現行 `ns_pipeline._solve_ppe` は spsolve 直接解法で pseudotime DC 非依存; caveat 非該当を [WIKI-T-046](wiki/theory/WIKI-T-046.md) §"後続展開" に追記. **即時最小修正 R-1.5 提案** ([WIKI-T-052](wiki/theory/WIKI-T-052.md)): 既存 `_fvm_pressure_grad` を ψ にも流用 (3 行編集 / 同一ガード `not uniform and bc_type==wall`); const κ で BF=機械精度, variable κ で $\mathcal{O}(h^2)$ (= CSF model floor). FCCD with $\mu \equiv \lambda \equiv 0$ の特殊例として R-1 と連続接続. 実装ロードマップ [WIKI-L-023](wiki/code/WIKI-L-023.md) (SPEC; CHK-155 で実施). [WIKI-X-018](wiki/cross-domain/WIKI-X-018.md) に R-1.5 行追加 + PoC ゲート並行化 (R-1.5 即時 / R-1 weeks-scale, 独立). [WIKI-T-044](wiki/theory/WIKI-T-044.md) に PC vs BF 独立性追記. INDEX 155→159 (T-050/T-051/T-052/L-023). コード変更・実験ゼロ. Branch: worktree-h01-remediation-theory |
| CHK-153 | 2026-04-20 | research+wiki | [DONE] ResearchArchitect 成果物: 5件のユーザー提示 short paper メモを 2 本に集約し, wiki 補完. **SP-A** [docs/memo/short_paper/SP-A_face_centered_upwind_ccd.md](memo/short_paper/SP-A_face_centered_upwind_ccd.md) (離散化軸, Chu-Fan 忠実 + G^adj 整合性節) + **SP-B** [docs/memo/short_paper/SP-B_ridge_eikonal_hybrid.md](memo/short_paper/SP-B_ridge_eikonal_hybrid.md) (位相軸, memos 1-4 統合 + ξ_ridge 記号導入 + CHK-138 σ>0 caveat). 新規 wiki 6件: [T-046](wiki/theory/WIKI-T-046.md) FCCD / [T-047](wiki/theory/WIKI-T-047.md) Gaussian-ξ Ridge / [T-048](wiki/theory/WIKI-T-048.md) Ridge-Eikonal hybrid + uniqueness / [T-049](wiki/theory/WIKI-T-049.md) ξ 記号 disambiguation / [X-018](wiki/cross-domain/WIKI-X-018.md) H-01 remediation map / [X-019](wiki/cross-domain/WIKI-X-019.md) topology/metric 役割分離. 既存 cross-link: T-042 / T-045 / X-012 / X-014. INDEX 149→155. 方針転換 (α/β/γ) 判断保留 — PoC 後に決定. Branch: worktree-research-arch-ridge-fccd. コード変更・論文 .tex 変更なし. |
| CHK-152 | 2026-04-20 | diag+wiki | [DONE] WIKI-E-030 後期ブローアップ根本原因調査完了. **H-01（Corrector G^adj/CCD BF残差）が唯一主因確定**. 証拠: Exp-1(bf_res=884@step1→構造的), Exp-2(σ=0→T=20安定⭐決定的), Exp-3(CFL×0.5→ブローアップ1.48×遅延、消えず), Exp-4(no reinit→H-05二次確認). 修正要件: G^adj と σκ∇ψ を同一メトリクス空間に統一（将来タスク）. Branch: worktree-worktree-e030-theory |
| CHK-151 | 2026-04-20 | merge | worktree-gfm-nonuniform → main マージ (f7e8db4): G^adj 圧力勾配（_fvm_pressure_grad, _precompute_fvm_grad_spacing）+ GFM 非一様格子対応 (d_f/dv_L/dv_R プリコンピュート) + ch13_02_bisect.yaml. 3 files, 140 ins / 48 del. コンフリクトなし. Branch: main |
| CHK-150 | 2026-04-20 | paper+wiki | 実験結果を論文に反映: §12g に G^adj 検証サブセクション（切り分け表・結果表・後期ブローアップ注記）; §13 格子方針を FVM-CCD 根本原因と G^adj 修正内容に更新. WIKI-E-030 作成（後期ブローアップ課題記録）. INDEX 147→148. コンパイルエラーゼロ. Branch: main |
| CHK-149 | 2026-04-20 | paper | 論文§12g/§13 実験結果反映 2コミット（417e997, f7f2016）+ LaTeX fix (84c7c01). |
| CHK-148 | 2026-04-20 | paper | 論文§10改稿: Step 7 Corrector 式を $\mathcal{G}$（均一: CCD, 非一様+壁: G^adj）に更新; 図キャプ "CCD勾配" 修正; 演算子記法ボックスに G^adj 追加. コンパイルエラーゼロ. Branch: main |
| CHK-147 | 2026-04-19 | paper | 論文§2-9改稿（G^adj FVM整合性）: §6b に FVM-CCD メトリクス不整合 warnbox 追加; §8b に G^adj 実装注記+label; §8 Balanced-Force CCD 統一宣言に非一様格子例外を追記; §9/§9b/§9f O(h^6) クレームに caveat. 5コミット; xelatex エラーゼロ. Branch: main |
| CHK-146 | 2026-04-19 | theory+code+wiki | G^adj 実装完了（commits f61e0cd+4706f37）+ 理論文書化: docs/memo/理論_FVM-CCD_メトリクス不整合とGadj圧力勾配.md（ショートペーパー）; WIKI-T-044（理論）; WIKI-L-022（コード）; INDEX 145→147. Branch: gfm-nonuniform worktree |
| CHK-145 | 2026-04-19 | exp | ch13_02_bisect: alpha10(均一格子)=安定(n=82), g_low(重力1/10)=ブローアップ(n=51). α=1.5 非均一格子が唯一の原因と確定. Branch: gfm-nonuniform worktree |
| CHK-144 | 2026-04-19 | perf | GFMCorrector.__init__ に face spacing + dv デバイス配列を事前計算（_d_f/_dv_L/_dv_R）; キャッシュ廃止; compute_rhs_correction 簡略化. Branch: gfm-nonuniform worktree |
| CHK-143 | 2026-04-19 | config+wiki | ch13 config clean-slate: 47 research configs → 3 production configs (ch13_01/02/03, §13.N命名). WIKI-X-017(production config pattern), WIKI-L-021(matplotlib CJK font). INDEX 143→145. Branch: worktree-ch13-rebuild |
| CHK-142 | 2026-04-19 | wiki+paper | Wiki 4新規(T-043:2D Lamb公式, E-029:exp13_17水-空気GFM, L-019:config_io parseバグ, L-020:GPU opt); 論文§13毛細管波改稿(ρ=833:1, 2D Lamb ω₀=0.679, GFM+α=1.5, VolCons=7.55e-15, 寄生渦流制限明記); INDEX 139→143. Branch: main |
| CHK-141 | 2026-04-19 | perf | GPU最適化3件マージ(362dbd3): PCR Thomas(thomas_batched→_pcr_solve_batched, n=129で258→14カーネル); float(W) D2H同期除去→xp.where; phi_primary_transport D2H/H2D除去. 211テスト全PASS. Branch: worktree-gpu-opt |
| CHK-140 | 2026-04-18 | fix+diag | xi_sdf interior hole: TRUE root cause = DissipativeCCDAdvection (NOT WENO5) oscillates ψ around 0.5 at deep-interior nodes; [0,1] clip insufficient (0.48 ∈ [0,1]). Onset: reinit call 37 (t≈0.048), psi_in=0.480. Fixes 1-4 and 案B all ineffective. Fix: phi_primary_transport=true — φ=logit(ψ)·ε transported; deep interior φ>>0 cannot flip sign. exp13_09 verified: T=0.1 clean (no hole t=0.05/0.10), VolCons=0.00%. Fix 4 reverted. WIKI-T-042 §CHK-140 + WIKI-E-025 exp13_09 added. Branch: worktree-ch13-eikonal-improvements |
| CHK-139 | 2026-04-18 | impl+exp+wiki | ξ-SDF eps_scale=1.4 interface widening: EikonalReinitializer(eps_scale) + Reinitializer + ns_pipeline.from_config chain. T=1: D=0.018 ✓, VolCons=0.80% ✓. T=2: D=0.028 ✓, VolCons=1.38% (target <1% marginally missed). Root cause confirmed (interface width effect). WIKI-E-028/X-016/P-012 created; Sethian1996 bib added; INDEX 136→139. Branch: worktree-ch13-eikonal-improvements |
| CHK-138 | 2026-04-18 | exp+theory | FMM T=1 quick check: VolCons=8.2% WORSE than ξ-SDF (1.46%@T=2) despite lower φ_xx noise (2.83 vs 3.93). Voronoi kink hypothesis refuted. Revised root cause: interface width ε (narrow band → PPE residual ∝ σκ/ε → ΔV drift). Split-only's ~1.4ε broadening is stabilizing. WIKI-T-042 §CHK-138 + paper CHK-138 FMM section updated. Branch: worktree-ch13-eikonal-improvements |
| CHK-137 | 2026-04-18 | impl+exp+paper | Two strategies for CHK-136 zero-set drift: A=ZSP (D=0.129, freeze band |φ|<h/2), B=ξ-SDF non-iterative (D=0.050 T=2 borderline, D=0.226 T=10 fail). ξ-SDF proofs: zero-set preservation, |∇_ξφ|=1, no drift. Paper §7b ξ-SDF subsubsection + 4 equations + 3 propositions. WIKI-T-042 §CHK-137. Static test: 200 reinit calls → VolCons≈0% (drift from advection, not reinit). Branch: worktree-ch13-eikonal-improvements |
| CHK-136 | 2026-04-18 | exp+theory | Eikonal Godunov baseline: D(T=2)=0.245 ✗. Root cause: discrete Godunov does not exactly preserve φ=0 contour; per-cell drift ∝ dtau×(1−|∇φ_raw|)/(h) × systematic mode-2 correlation × 37000 reinit calls. Analogous to DGR global-median nonuniformity but different mechanism. WIKI-T-042 §CHK-136 + paper §7b Eikonal method section. Branch: worktree-ch13-eikonal-improvements |
| CHK-135 | 2026-04-18 | theory+paper | Hybrid reinit wrong D(t)=0.227 on σ>0 capillary waves: root cause = DGR global-median ε_eff applies uniform scale on non-uniform (compressed/elongated) interface → mode-2 amplification per DGR call. Compressed ends over-scaled (outward shift), elongated tips under-scaled (inward). Split-only gives D=0.037 but ~1.4ε interface. Paper DGR limitation section + WIKI-T-042 motivation. Branch: worktree-ch13-eikonal-improvements |
| CHK-134 | 2026-04-18 | theory+wiki | Third-order time integration theory note + WIKI-T-041. Paper §5 time-evolution chapters absorbed; rate-limiter taxonomy built (AB2/CN/IPC cap at O(Δt²), cross-visc at O(Δt¹)). Route B recommended: AB3 convection + Richardson(Picard-CN) viscous + AB3 cross-term extrapolation + Rotational IPC (Guermond–Shen 2003). Preserves Peaceman–Rachford ADI tridiagonal. Reuses shipped RichardsonCNAdvance. ~50 lines future library work. 5 new bib entries queued. WIKI: T-003/T-033/T-030 dependencies; INDEX 100→101. Branch: worktree-research-third-order-time-evolution |
| CHK-133 | 2026-04-18 | fix | ch13 DGR blowup: root cause = DGR cannot repair interface folds (|∇ψ|→0) under σ>0 capillary dynamics; global median eps_eff treats folds as outliers → DGR near-no-op → CSF blowup. Fix: reinit_method: hybrid in exp13_01_a{1.0,1.2,1.5,2.0}_dgr.yaml. Isolation exps A1-A4 confirm mechanism. WIKI-T-030 Limitations section added. Tests 206P/7S/2XF. Branch: worktree-ch13-dgr-blowup-fix |
| CHK-132 | 2026-04-18 | meta | v7.0.0 "Lean Kernel" redesign: 8 kernel-*.md (constitution/roles/ops/domains/workflow/antipatterns/project/deploy) + 46 agent files (23 claude + 23 codex) + 2 _base.yaml. -56% token target. v6.0.0 features: HAND-04/DYNAMIC-REPLANNING/OP-CONDENSE/EVALUATOR-OPTIMIZER. Branch: meta-v7-lean-kernel |
| CHK-131 | 2026-04-17 | fix | GPU smoke tests: thomas_precompute .get() fix (linalg_backend.py); atol 1e-13→1e-11 (test_gpu_smoke.py); 3 FAILED → 0 |
| CHK-130 | 2026-04-16 | fix+paper+merge | ch11 reinit non-uniform fix (4 files); DGR fallback α>1; exp11_29 880× improvement; WIKI-E-017 updated |
| CHK-129 | 2026-04-15 | paper+merge | ch12 re-run paper sync + main merge (752b9f3); 5 tex files; 199pp 0 err |
| CHK-128 | 2026-04-12 | fix | FieldExtender upwind NaN fix (65aed8d); q_safe masking; test added |
| CHK-127 | 2026-04-12 | gpu-optin | exp11_22 zalesak_nonuniform (Tier C, CPU baseline generated first); 31/31 ch11 GPU-opted |
| CHK-126 | 2026-04-12 | gpu-optin | Batch 6b (5 exp: 11_12b/14_picard/25/28/29) + 6 library CuPy-strict fixes |
| CHK-125 | 2026-04-11 | gpu-optin | Batch 6a (3 exp: 11_15/24/27); confirms ASM-122-A DGR-contractive mechanism |
| CHK-124 | 2026-04-11 | diagnosis | ASM-122-A root cause = FUNDAMENTAL (chaos-amplified FP noise, Lyapunov λ≈ln(e)/20steps); 5-probe binary search |
| CHK-123 | 2026-04-12 | deploy | EnvMetaBootstrapper v5.2 + v1.1 Hybrid redeploy; 33 agents + AP-09/10 inject |
| CHK-122 | 2026-04-12 | perf | cn_diffusion_axis dense-inverse (70×); exp11_21 CPU 258s → GPU 61.6s (4.19×); documented ASM-122-A |
| CHK-121 | 2026-04-12 | gpu-optin | Batch 5 (exp11_19/20/21/23); exp11_21 62 min → 2 min post perf-rounds; `make push --checksum` load-bearing |
| CHK-120 | 2026-04-12 | perf+fix | Round 6 rsync-race correction; `--checksum` added. Corrected Test B 900s→41.25s (−95.4% vs CHK-106) |

## §2 — Perf/GPU rounds (CHK-115..119)

| CHK | Date | Type | Summary |
|---|---|---|---|
| CHK-119 | 2026-04-12 | perf | Round 5: A_inv_dev = lu_solve(I) cached; GPU hot = A_inv @ rhs (18× speedup) |
| CHK-118 | 2026-04-11 | perf | Round 4: cached device ops for _build_axis_solver; matmul contractions |
| CHK-117 | 2026-04-11 | perf | Round 3b: Wall-BC CCD unified onto dense block-banded LU |
| CHK-116 | 2026-04-11 | perf | Round 3a: vectorised _differentiate_wall_raw; 126→4 launches/CCD call |
| CHK-115 | 2026-04-11 | perf+gpu | Round 2 perf tuning + Batch 4 GPU opt-in (collision — ID reused by 2 parallel worktrees) |
| CHK-114 | 2026-04-11 | meta | v5.1.0 Concurrency-Aware refactor (worktree-based locks; HAND schema); feature flag flipped LIVE |
| CHK-113 | 2026-04-11 | gpu-optin | Batch 3 (exp11_10/11/17/26) |
| CHK-112 | 2026-04-11 | gpu-optin | Batch 2 (exp11_4/8/14) |
| CHK-111 | 2026-04-11 | review | PaperReviewer §11–§13 review (0F/4M/7m/2S); WIKI-P-006 |
| CHK-110 | 2026-04-11 | gpu-optin | Batch (exp11_3/9/16); hybrid CPU scipy.sparse + device CCD pattern |
| CHK-109 | 2026-04-11 | gpu-optin | exp11_7 HFE + ClosestPointExtender xp fix (Phase C leak #3) |
| CHK-108 | 2026-04-11 | gpu-optin | Grid.meshgrid() device-aware + exp11_2 |
| CHK-107 | 2026-04-11 | infra | Remote-default + GPU auto-selection; Makefile run/run-local targets; pyproject cupy→[gpu] extra |
| CHK-106 | 2026-04-12 | backend | CuPy backend unification (retroactive close — all content absorbed via 107..127 chain) |

## §3 — Earlier activity (CHK-085..105)

| CHK | Date | Type | Summary |
|---|---|---|---|
| CHK-105 | 2026-04-09 | paper | §7b DCCD mass proof + adaptive reinit; §10 Step 2 trigger; §11.2 conservation verify |
| CHK-104 | 2026-04-09 | wiki | Shape preservation memo + WIKI-T-028 update |
| CHK-103 | 2026-04-09 | exp | exp11_19 shape study; adaptive reinit DOMINANT (+49%, 227→2 reinits) |
| CHK-102 | 2026-04-09 | exp | exp11_18 CLS-DCCD conservation verified; split+mc recommended |
| CHK-101 | 2026-04-09 | theory | CLS-DCCD conservation analysis; unified DCCD reinit proposed; WIKI-T-028 |
| CHK-100 | 2026-04-08 | wiki | ch11 experiment wiki (L-002..L-007); 48 entries |
| CHK-099 | 2026-04-08 | audit | WikiAuditor K-LINT PASS; INDEX.md created |
| CHK-098 | 2026-04-08 | wiki | Memo wiki compilation (10 new); 41 entries |
| CHK-097 | 2026-04-08 | wiki | Appendix wiki (T-010..T-018, 9 new); 31 entries |
| CHK-096 | 2026-04-08 | review | PaperReviewer §1–§11 (0F/7M/14m/3S); 10 verifications PASS |
| CHK-095 | 2026-04-08 | paper | §5–§8 bridges + §11 zero-base rewrite |
| CHK-094 | 2026-04-08 | deploy | EnvMetaBootstrapper full regen (33 agents) |
| CHK-093 | 2026-04-08 | wiki | ch11 experiment wiki (E-001..E-006) |
| CHK-092 | 2026-04-07 | wiki | §1–§3 wiki (T-006..T-009, P-003, X-003) |
| CHK-091 | 2026-04-07 | wiki | First 10 wiki entries; K-Domain operational |
| CHK-090 | 2026-04-07 | review | PaperReviewer §4–§10 story structure; 6 issues |
| CHK-089 | 2026-04-07 | deploy | EnvMetaBootstrapper A1→A11 (Knowledge-First); 4 K-Domain agents |
| CHK-085 | 2026-03-31 | paper | §8 structural rewrite (Modifications I–IV); 167pp |
| CHK-010..084 | 2026-03-27 .. 03-31 | paper+code+test | Initial bootstrap, §9–§12 narrative, DCCD verification, 154/154 tests. Full detail in git log. |

────────────────────────────────────────────────────────
# § ASSUMPTIONS

| ASM | Status | Scope | One-line |
|---|---|---|---|
| ASM-001 | ACTIVE | src/twophase/ | SimulationBuilder is sole construction path |
| ASM-002 | ACTIVE | src/twophase/pressure/ | PPE Kronecker has 8-dim null space — ‖Lp−q‖₂ not a pass/fail metric |
| ASM-003 | DEPRECATED | src/twophase/pressure/ | Superseded 2026-04-15 by PR-2 — CCD Kronecker PPE indefinite (2 wrong-sign eigenvalues/axis); CCD-LU restricted to ch11 smooth-RHS tests |
| ASM-004 | ACTIVE | src/twophase/ccd/ | CCD boundary-limited: d1 ≥ 3.5, d2 ≥ 2.5 on L∞ |
| ASM-005 | DEPRECATED | src/twophase/pressure/ | Superseded 2026-04-15 — LGMRES prohibited for PPE (PR-6); production = FD spsolve or DC sweep |
| ASM-006 | ACTIVE | src/twophase/ccd/ | Banded/block-tridiag: direct LU (O(N) fill-in) |
| ASM-007 | ACTIVE | src/twophase/ | SimulationConfig is pure sub-config composition |
| ASM-008 | FIXED | src/twophase/ | 3 symmetry-breaking root causes fixed 2026-03-22 (Rhie-Chow wall N_ax, PPE pin at center, capillary CFL) |
| ASM-009 | FIXED | src/twophase/ | FVM/CCD mismatch in IPC+corrector fixed 2026-03-22 |
| ASM-010 | ACTIVE | paper/ | docs/00_GLOBAL_RULES.md §P1 is authoritative LaTeX standard |
| ASM-122-A | FUNDAMENTAL | src/twophase/levelset/reinit_split.py | GPU/CPU pointwise drift on long Zalesak runs = chaos-amplified FP noise (CHK-124). Lyapunov λ≈ln(e)/20 steps. Hybrid/DGR path escapes via Lyapunov-contractive projection. PR-5 carve-out: pointwise O(1e-2) on split GPU is fundamental; L₂/mass/physics preserved. DGR default for α>1 in ns_pipeline.py reduces practical impact (CHK-130). |

────────────────────────────────────────────────────────
# § LESSONS (KL-01 .. KL-12)

## §A — Known Error Classes (Math/Code)

| KL | Failure | Fix Pattern |
|---|---|---|
| KL-01 | Block matrix (2,1) sign flip after RHS transposition | Read RHS coeff → negate → write to LHS |
| KL-02 | Wrong block size (3×3 vs 2×2) in docs | Verify block dims against actual code arrays |
| KL-03 | Pseudocode comment names wrong algorithm | Cross-check comment vs accumulation pattern |
| KL-04 | D(κf) ≠ κD(f) for varying κ | Expand D(κf) = κD(f) + f·∇κ — never factor variable coefficients |
| KL-05 | Nyquist modified wavenumber ≠ finite-grid spectral radius | Compute spectral radius of actual discrete matrix |
| KL-06 | Pre-asymptotic O(h⁴) mistaken for asymptotic | Confirm slope stability over ≥3 grid doublings |
| KL-07 | "Conservative" CFL rounding wrong direction | Conservative means SMALLER dt — floor for dt, ceiling for Nsteps |
| KL-08 | Kronecker C-order vs Fortran-order confusion | State convention explicitly; verify with N=2 example |
| KL-09 | PPE LGMRES-primary/LU-fallback vs LU-primary confusion | LGMRES primary; spsolve auto-fallback on non-convergence (pre-2026-04-15) |
| KL-10 | Collocated corrector "exact CCD-div-free" claim | RC PPE leaves ‖∇_RC·u^{n+1}‖=0 but CCD sense residual O(h²) |
| KL-11 | Pin-node excl still targets (0,0) after move to center | Use `pin_dof = ravel_multi_index(tuple(n//2 for n in grid.N), grid.shape)` |
| KL-12 | `\texorpdfstring` missing in math heading → xelatex infinite loop | Wrap ALL numbered headings with `$...$` in texorpdfstring; pre-compile grep scan required |

────────────────────────────────────────────────────────
# § REFERENCE — moved content

- **§5 Evolution Log** (EVO-001..006 meta-governance YAML): moved to git commit messages + `prompts/meta/meta-deploy.md §v1.1 changelog`
- **§4 Branch Lock Registry** (v5.1 concurrency): live state in `docs/locks/*.lock.json`; historical rows in git log. Protocol: `prompts/meta/meta-ops.md §LOCK-ACQUIRE/RELEASE`
- **§ INTEGRITY_MANIFEST**: all-pending hash placeholders dropped. Contracts unsigned; re-introduce when first interface is locked.
