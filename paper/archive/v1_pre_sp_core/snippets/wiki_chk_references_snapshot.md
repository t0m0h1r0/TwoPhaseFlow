# WIKI-T/E/L/X / CHK-xxx 本文露出スナップショット（CHK-194 Phase A 除去前）

**生成日**: 2026-04-24
**対象**: CHK-194 Phase A で本文から除去する WIKI/CHK 番号参照の全件
**復元手段**: git 履歴 + 本 snapshot（二重化）

## 除去方針（要約）

- algbox タイトル末尾の `（WIKI-T-XXX）` → 削除
- `WIKI-E-030` → `H-01 診断 (§\ref{sec:fccd_motivation_h01})` に置換
- `CHK-xxx (SP-J §N)` → `SP-J §N \cite{SPJ}` に置換
- `CHK-xxx で確立/測定/検証` → 時制表現（「本稿で確立した」等）に無害化
- parenthetical `（WIKI-T-091, CHK-152）` 形式 → 完全削除
- コメント行内 `CHK-086 / CHK-088` 等の履歴注記 → 保持可（Phase B で一部修正）

## Grep 出力（除去前全件）

```
paper/sections/appendix_numerics_solver_s4.tex:9:%% ※ 旧 08g_fvm_note.tex の内容を統合（CHK-088）
paper/sections/appendix_numerics_solver_s4.tex:42:%% 旧所在: §8.4（08f_ppe_bc.tex）→ 付録 E.4 へ移動（CHK-086）
paper/sections/02_governing.tex:41:FMM/FSM/Godunov Hamilton--Jacobi の各再初期化（WIKI-T-042 参照）は，
paper/sections/04c_dccd_derivation.tex:52:散逸がない（WIKI-T-001/002 参照）．
paper/sections/04c_dccd_derivation.tex:84:に置き換える（WIKI-T-002）．
paper/sections/04c_dccd_derivation.tex:90:WIKI-T-002 の波数選択的設計はこの極限を精緻化したものである．
paper/sections/04c_dccd_derivation.tex:131:      §\ref{sec:ccd_bc} の Option III/IV で壁近傍の行を置換（WIKI-T-051/056）．
paper/sections/04c_dccd_derivation.tex:137:      WENO5 相互検証（WIKI-T-013）で経験的裏付け．
paper/sections/04c_dccd_derivation.tex:140:      $\varepsilon_d\le 0.05$ の製品設定で非拘束（WIKI-T-002）．
paper/sections/04c_dccd_derivation.tex:173:WIKI-T-002（DCCD スペクトル設計）・WIKI-T-013（DCCD vs WENO5 比較）を参照．
paper/sections/07c_fccd_advection.tex:20:退化する（CHK-172 測定）．
paper/sections/07c_fccd_advection.tex:175:Option B でのみ H-01 が完全解消する（WIKI-E-030 実測で SP-C 単独の
paper/sections/07c_fccd_advection.tex:229:演算量は純 CCD 移流の 1.3--1.5$\times$（WIKI-L-019）．
paper/sections/07c_fccd_advection.tex:241:製品コンフィグは Stage 3（WIKI-X-018），
paper/sections/04e_fccd.tex:24:WIKI-T-044 が FVM 面平均勾配 $\mathcal{G}^{\text{adj}}$ と
paper/sections/04e_fccd.tex:26:WIKI-E-030 Exp-1 の毛管ベンチマーク（$\rho_\text{liq}/\rho_\text{gas}=833$）で
paper/sections/04e_fccd.tex:30:メトリック空間不一致が長時間破綻の主因」）が確定した（CHK-152）．
paper/sections/04e_fccd.tex:158:（WIKI-T-050）．合成演算子は
paper/sections/04e_fccd.tex:185:これにより CHK-152 の未解決アクション
paper/sections/07d_cls_stages.tex:153:（CHK-160 回帰テスト）．
paper/sections/06d_ridge_eikonal_nonuniform.tex:82:（WIKI-L-017 参照）ではこの fallback を一時許容する（CHK-160 検証済）．
paper/sections/06d_ridge_eikonal_nonuniform.tex:116:一軸あたり 1.0--1.2$\times$（$h_x[i]$ 参照の分，WIKI-L-017）．
paper/sections/06d_ridge_eikonal_nonuniform.tex:138:（CHK-138/139 で閾値同定）．
paper/sections/06d_ridge_eikonal_nonuniform.tex:160:        （CHK-160 実測値）．
paper/sections/06d_ridge_eikonal_nonuniform.tex:185:一軸あたり実行時間は一様版の 1.1--1.3$\times$（WIKI-L-017）．
paper/sections/appendix_ppe_pseudotime.tex:10:%% 旧所在: §8.1（08_pressure.tex）→ 付録 E.5 へ移動（CHK-086）
paper/sections/appendix_ccd_impl_s3.tex:272:%% 旧所在: §8.2.2（08c_ccd_poisson.tex）→ 付録 C.3 へ移動（CHK-086）
paper/sections/appendix_ccd_impl_s3.tex:315:%% 旧所在: §8.2.3 algbox（08c_ccd_poisson.tex）→ 付録 C.3 へ移動（CHK-086）
paper/sections/appendix_ccd_impl_s3.tex:334:%% 旧所在: §8.4（08f_ppe_bc.tex）→ 付録 C.3 へ移動（CHK-086）
paper/sections/07_0_scheme_per_variable.tex:39:        CN 半陰的処理でも不安定化する（CHK-137 検証）．
paper/sections/08b_pressure.tex:109:% 旧 inline warnbox は CHK-193 Phase D-3 で §8c 完全版と重複のため退避:
paper/sections/10_full_algorithm.tex:516:粘性 CN 時間中心 & $(n + n^*)/2$ & WIKI-T-033 \\
paper/sections/09e_ppe_bc.tex:17:%% 付録~\ref{sec:ccd_neumann_unit_test} に移動（CHK-086）．
paper/sections/09e_ppe_bc.tex:19:%% 付録~\ref{sec:fvm_periodic} に移動（CHK-086）．
paper/sections/06c_fccd_nonuniform.tex:16:ここでは WIKI-T-050 の非一様 \textbf{打ち消し係数} $(\mu_i,\lambda_i)$ を
paper/sections/06c_fccd_nonuniform.tex:33:WIKI-T-050 の \textbf{打ち消し係数}：
paper/sections/06c_fccd_nonuniform.tex:67:WIKI-T-053 が与える非一様 FCCD の面式
paper/sections/06c_fccd_nonuniform.tex:106:SP-C §5 の Taylor 解析（WIKI-T-050 の $\mu,\lambda$ 導出と整合）により，
paper/sections/06c_fccd_nonuniform.tex:137:（重み配列ロードの分；WIKI-L-015）．
paper/sections/06c_fccd_nonuniform.tex:152:境界行の wall BC 拡張は付録 B.2 および WIKI-T-050/053 参照．
paper/sections/08_0_bf_failure.tex:52:必ず踏む．CHK-172 の rising bubble PoC では F-2 と F-4 が同時発生し，
paper/sections/13_benchmarks.tex:27:短時間（$t < 0.13$）でブローアップした（詳細は WIKI-E-022）．
paper/sections/02b_surface_tension.tex:55:本稿の H-01 診断（WIKI-E-030）はモード F-1/F-3/F-5 が主因と結論しており，
paper/sections/08_1_bf_seven_principles.tex:58:\noindent\textbf{CHK-172 rising bubble への含意}：
paper/sections/04g_face_jet.tex:135:        不連続を Gibbs 振動として輸送する（WIKI-L-030 の警告）．
paper/sections/07b_reinitialization.tex:224:（§~\ref{sec:val_capillary}，CHK-135 参照）．
paper/sections/07b_reinitialization.tex:248:CSF 力 $\sigma\kappa\delta_\varepsilon\bnabla\psi$ が指数的に増大して発散する（CHK-133）．
paper/sections/07b_reinitialization.tex:254:    しかし $D(t)$ が誤った値に飽和（CHK-135）．
paper/sections/07b_reinitialization.tex:265:\subsubsection{統一再初期化：Eikonal 法（WIKI-T-042）}
paper/sections/07b_reinitialization.tex:279:\begin{tcolorbox}[algbox, title={Eikonal 再初期化アルゴリズム（CHK-136）}]
paper/sections/07b_reinitialization.tex:300:\noindent\textbf{理論的保証（WIKI-T-031）：}
paper/sections/07b_reinitialization.tex:321:    \textbf{Eikonal}（本法）& $\checkmark$（連続形） & $\checkmark$ & $\times$ $D(t)$ 誤差（CHK-136）\\
paper/sections/07b_reinitialization.tex:324:  \caption{再初期化手法の比較．WIKI-T-042 参照．}
paper/sections/07b_reinitialization.tex:327:\noindent\textbf{CHK-136 検証結果（$T=2$，Prosperetti ベンチマーク）：}
paper/sections/07b_reinitialization.tex:340:離散ゼロセットドリフトを原理的に排除できる（CHK-137 で ZSP として実装・検証済み；次節参照）．
paper/sections/07b_reinitialization.tex:344:\subsubsection{\texorpdfstring{$\xi$}{ξ}空間符号距離関数法（CHK-137）}
paper/sections/07b_reinitialization.tex:348:CHK-136 の失敗原因（Godunov 差分の離散ゼロセットドリフト累積）を根本的に排除するため，
paper/sections/07b_reinitialization.tex:353:\begin{tcolorbox}[algbox, title={ξ-SDF 再初期化アルゴリズム（CHK-137 Strategy B）}]
paper/sections/07b_reinitialization.tex:420:Godunov 差分の $O(\Delta\tau\cdot n_{\mathrm{iter}})$ 累積ドリフト（CHK-136 根本原因）を生じない．
paper/sections/07b_reinitialization.tex:423:\noindent\textbf{CHK-137 検証結果（Prosperetti ベンチマーク，$\alpha=1.0$，$64\times64$）：}
paper/sections/07b_reinitialization.tex:430:Eikonal（CHK-136，ZSP なし） & 0.245 & — & $\times$ \\
paper/sections/07b_reinitialization.tex:433:分裂法のみ（参照，CHK-135）   & 0.037 & 0.0036 & $\checkmark$ \\
paper/sections/07b_reinitialization.tex:441:\noindent\textbf{CHK-138（Fast Marching Method による検証）：}
paper/sections/07b_reinitialization.tex:442:CHK-137 の失敗原因として当初 Voronoi kink 仮説（ξ-SDF の $C^0$ 不連続が
paper/sections/07b_reinitialization.tex:452:\noindent\textbf{修正仮説（CHK-138）—界面幅効果：}
paper/sections/07b_reinitialization.tex:481:    Eikonal（CHK-136）& $\checkmark$ & $\checkmark$ & $\times$ & 0.245 & 低 & あり \\
paper/sections/07b_reinitialization.tex:482:    Eikonal+ZSP（CHK-137A）& $\checkmark$ & $\checkmark$ & $\times$ & 0.129 & 低 & あり \\
paper/sections/07b_reinitialization.tex:483:    ξ-SDF（CHK-137B）& $\checkmark$ & $\checkmark$ & $\times$ & 0.050 & $3.5\%$ @$T{=}10$ & なし \\
paper/sections/07b_reinitialization.tex:484:    \textbf{FMM（CHK-138）}& $\checkmark$ & $\checkmark$ & $\times$ & — & $\mathbf{8.2\%}$ @$T{=}1$ & なし \\
paper/sections/07b_reinitialization.tex:485:    \textbf{ξ-SDF（$f{=}1.4$，CHK-139）}& $\checkmark$ & $\checkmark$ & $\checkmark$ & \textbf{0.028} & $1.38\%$ @$T{=}2$ & なし \\
paper/sections/07b_reinitialization.tex:488:  \caption{再初期化手法の比較（CHK-139 更新）．WIKI-T-042 参照．ε幅拡大（$f{=}1.4$）が最良の $D(T{=}2)$を実現．}
paper/sections/07b_reinitialization.tex:492:\noindent\textbf{CHK-139（ε幅拡大による修正）：}
paper/sections/07b_reinitialization.tex:493:CHK-138 の界面幅仮説に基づき，ξ-SDF 再構成のパラメータに $f{=}1.4$ を設定して
paper/sections/07b_reinitialization.tex:506:\textbf{CHK-139 検証結果：}
paper/sections/07b_reinitialization.tex:512:  ξ-SDF（$f{=}1.0$，CHK-137） & — & 0.050 & $3.5\%$ @$T{=}10$ \\
paper/sections/07b_reinitialization.tex:513:  \textbf{ξ-SDF（$f{=}1.4$，CHK-139）} & \textbf{0.018 $\checkmark$} & \textbf{0.028 $\checkmark$} & \textbf{1.38\% @$T{=}2$} \\
paper/sections/appendix_gpu_fvm.tex:4:%       （SP-F 全取り込み。旧 §9.7 を 2026-04-24 CHK-193 で付録化）
paper/sections/08_2_fccd_bf.tex:12:（WIKI-E-030，CHK-152），$\BF_\text{res} = \Ord{\Delta x^2}\cdot|d\log J/dx|$
paper/sections/08_2_fccd_bf.tex:19:% H-01 診断の一次定義は §\ref{sec:fccd_motivation_h01}（§4.5, WIKI-E-030, CHK-152）にある．
paper/sections/08_2_fccd_bf.tex:22:% paper/archive/v1_pre_sp_core/snippets/h01_recap_08_2.tex に退避（CHK-193 Phase D-1）．
paper/sections/03d_ridge_eikonal.tex:14:\textbf{関連 wiki：} WIKI-T-042（再初期化カタログ），
paper/sections/03d_ridge_eikonal.tex:15:WIKI-T-049（$\xi$ 記号の曖昧性解消），
paper/sections/03d_ridge_eikonal.tex:16:WIKI-T-057/058/059（D1/D2/D3 非一様拡張），
paper/sections/03d_ridge_eikonal.tex:17:WIKI-L-025（ライブラリ）．
paper/sections/03d_ridge_eikonal.tex:141:WIKI-T-039 の不可能性定理に抵触，
paper/sections/03d_ridge_eikonal.tex:164:WIKI-T-039 の不可能性結果より，界面遷移幅が $\le 4$ セルのとき
paper/sections/03d_ridge_eikonal.tex:174:        で $\bnabla_x^2\xiridge$ を直接評価（SP-E 本命, CHK-160）．
paper/sections/03d_ridge_eikonal.tex:213:CHK-138/139 の一様格子較正値 $\varepsilon_\text{scale}=1.4$ を維持し，
paper/sections/03d_ridge_eikonal.tex:219:\subsubsection{$\sigma>0$ 制約（CHK-138 / CHK-139）}
paper/sections/03d_ridge_eikonal.tex:223:（WIKI-T-042 CHK-138：毛管波 $T=1$ で $|\Delta V/V|=8.2\%$）．
paper/sections/03d_ridge_eikonal.tex:244:（WIKI-T-036）の厳密な一般化となる．
paper/main.tex:80:\input{sections/09f_pressure_summary}  %% §9のまとめ（GPU-native FVM 詳細は付録H へ移動 CHK-193）
paper/main.tex:82:%% ※ appendix_fvm_note（FVM 調和平均・RC 発散定義）→ 付録 E.4 に統合（CHK-088）
paper/main.tex:141:%% 付録H: GPU-native FVM 投影（SP-F, §9 から移動 CHK-193）
paper/sections/09_ccd_poisson.tex:207:%% 08h_pressure_summary.tex に移動（CHK-087: R5 — 読者が全節を読んでから結論に到達できるよう）．
paper/sections/09b_split_ppe.tex:268:\noindent\textbf{YAML セマンティクス}（CHK-181 確定）：
```

## 置換マッピング（カテゴリ別サマリ）

### WIKI-T-XXX → 学術表現
- `WIKI-T-001/002` (DCCD スペクトル設計) → 「DCCD スペクトル設計」「本節の設計」
- `WIKI-T-013` (DCCD vs WENO5 比較) → 「WENO5 相互検証」
- `WIKI-T-031` (CLS 理論保証) → 「CLS 理論的保証」
- `WIKI-T-033` (粘性 CN 時間中心) → 表キャプション列を削除
- `WIKI-T-036` → 「先行研究」
- `WIKI-T-039` (ε 幅不可能性定理) → 「界面幅不可能性定理」
- `WIKI-T-042` (再初期化カタログ) → 「Eikonal 再初期化」
- `WIKI-T-044` (FVM 面平均勾配) → 「FVM 面平均勾配 $\mathcal{G}^{\text{adj}}$」
- `WIKI-T-049/050/051/053/056/057/058/059` → 「非一様 FCCD 打ち消し係数」「境界拡張」
- `WIKI-T-091` → 「H-01 診断」

### WIKI-E-XXX → H-01 診断
- `WIKI-E-022` (ブローアップ実験) → 「予備実験」
- `WIKI-E-030` (毛管ベンチマーク) → 「H-01 診断 (§\ref{sec:fccd_motivation_h01})」または「毛管ベンチマーク」

### WIKI-L-XXX → 実装言及を削除
- `WIKI-L-015/017/019/025/030` (ライブラリ参照) → 削除

### WIKI-X-XXX → 製品コンフィグ記述簡略化
- `WIKI-X-018` → 「Stage 3 製品コンフィグ」

### CHK-xxx → 時制/削除
- `CHK-133/135/136/137/138/139/152/160/172/181/185` → 検証済み事実として無害化 or 完全削除
- `CHK-086/087/088` (編集履歴) → コメント行では保持可（Phase B で位置修正含む）
- `CHK-193` (本 CHK の直前) → archive README で言及 + コメントからは削除

## 復元手順

将来（例：SP-I/SP-J 投稿時）に WIKI/CHK 追跡を復活させる場合：

1. 本 snapshot から対象 occurrence の行番号・文脈を特定
2. `git log --follow paper/sections/<file>` で除去 commit（CHK-194 Phase A）を取得
3. `git show <commit>:paper/sections/<file>` で除去前の文脈を復元
4. `docs/wiki/paper/WIKI-P-013.md` の CHK-xxx → commit hash mapping で追跡情報を取得

## 参考

- CHK-193 Phase F の snippet 4 本（h01_recap_08_2, fccd_matrix_redef_07c, pressure_filter_warnbox_08b, level3_activation_note）と同じ哲学
- 外部公開用（arXiv/SP-J）には本 snapshot を含めない（`paper/archive/` ディレクトリは `.latexignore` 相当）
