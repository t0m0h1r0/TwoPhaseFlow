# §13 ResearchArchitect 厳正査読 — 2026-04-29

担当: ResearchArchitect (CHK-RA-CH13-001 / id_prefix=RA-CH13)
査読対象: `paper/sections/13_verification.tex` + `13a..13f` 全 6 sub-file
ブランチ: `worktree-ra-ch13-review-20260429`
初回判定: **MAJOR REVISION REQUIRED** (FATAL 5件 / MAJOR 3件 / MINOR 1件 / Nit 1件)

## エグゼクティブサマリ

§13f の master table `tab:v_accuracy_summary` (line 21–46) が，§13a–§13e の
sub-file 実測値と **5箇所で不一致**．V1/V2/V6/V7/V9 各実験スクリプトが
§14 stack に書き換えられた (`90f5273`/`c4d450e`/`8531c5d`/`40ee1f8`) 以降，
13f master table が更新されないまま残留した可能性が極めて高い．
「合格 ✓ / 条件付き △ / 未達 ×」の振り分けが実測と乖離し，論文の総合判定基盤を
損なっている．本査読は **FATAL 5件をすべて 13f 修正で閉じる** ことを推奨する．

加えて V5 (CCD N=64→128 の寄生流増加) および V8 (α=1, N=96 で u∞ が 4× ジャンプ)
で説明なしの非単調が残り，**条件付き合格**の判定根拠が弱い．これらは
本文での原因仮説の追記で対応する．

| Severity | 件数 | 備考 |
|---|---:|---|
| FATAL  | 5 | 13f master table 数値乖離 (V1-b, V2-a, V7, V10-a/b 入替, V10-c) |
| MAJOR  | 3 | V6 指標名・数値乖離 / V8 α=1 非単調未説明 / V5 CCD N=128 反転未説明 |
| MINOR  | 1 | V4 判定文の二重否定 |
| Nit    | 1 | V3/V5 で `u∞^end` 指標が peak/end 混在 (Tab.V_summary) |

## Findings

### FATAL

#### RA-CH13-001 (FATAL) — V1-b 時間 slope の master table 値が誤り
- **位置**: [13f_error_budget.tex:32](paper/sections/13f_error_budget.tex#L32) vs [13a_single_phase_ns.tex:55](paper/sections/13a_single_phase_ns.tex#L55)
- **問題**: 13f master table は V1-b: slope = `2.00 ✓ O(Δt²) 達成` と記載するが，
  Tab.V1_temporal の finest local slope は `1.00`，本文 (13a:74) は
  「AB2 単体の 2 次設計は，PPE 射影との fractional-step 結合では維持されない」と
  明示的に否定している．
- **根拠**: V1 再実行による独立確認 (本査読 P3, 2026-04-29) — 時間 sweep
  dt=3.85e-3/2.0e-3/1.0e-3 → E_rel=5.87e-7/3.13e-7/1.58e-7，連続比から
  実測 slope ≈ **1.00** で 13a と一致．
- **修正方向**: 13f L32 の V1-b 行を `1.00` および `× O(Δt²) 未達`（あるいは
  `△ fractional-step 1次に縮退 (設計通りの制約)`) に置換．
  「合格判定」リストからの除外が必要．

#### RA-CH13-002 (FATAL) — V2-a 空間 slope の master table 値が誤り
- **位置**: [13f_error_budget.tex:33](paper/sections/13f_error_budget.tex#L33) vs [13a_single_phase_ns.tex:117](paper/sections/13a_single_phase_ns.tex#L117)
- **問題**: 13f master table V2-a: `slope = 6.00 ✓ O(h⁶) 達成`．
  Tab.V2_spatial の asymptotic slope は `3.95`，caption (13a:103) 自身が
  「実効 4 次に留まる」と明記．13f line 50 にも「CCD 6 次（V2 で確証）」と
  ある記述も乖離．
- **根拠**: 13a Tab.V2_spatial 線形回帰列を直接読出．数値同定は [13a:117](paper/sections/13a_single_phase_ns.tex#L117) のみ．
- **修正方向**: 13f L33 の V2-a 行を `3.95` および
  `△ 設計 6 次に対し実効 4 次（圧力境界・界面外周の低次寄与）` に置換．
  L50 の「CCD 6 次（V2 で確証）」も「V2 で実効 4 次を確認」へ修正．

#### RA-CH13-003 (FATAL) — V7 IMEX-BDF2 slope が旧 reduced proxy 値のまま
- **位置**: [13f_error_budget.tex:38](paper/sections/13f_error_budget.tex#L38) vs [13d_density_ratio.tex:118](paper/sections/13d_density_ratio.tex#L118)
- **問題**: 13f master table V7: `slope = 0.56 ×`．Tab.V7 の finest local slope は
  `1.58`．[13d:135](paper/sections/13d_density_ratio.tex#L135) 本文に「旧 reduced proxy の slope $0.56$ より §14 stack では改善する」と
  明記され，0.56 は廃棄済み proxy 値であることが論文中で公言されている．
- **根拠**: V7 再実行 (本査読 P3, 2026-04-29) — Linf err: n=8/16/32 →
  6.20e-4 / 5.75e-4 / 1.92e-4，連続比 1.08 / 2.99，finest local slope ≈ **1.58**
  で 13d Tab.V7 と一致．
- **修正方向**: 13f L38 の V7 行を `1.58` および
  `△ coupled-stack 実効次数（reinit cadence・PPE 結合誤差）` に置換．

#### RA-CH13-004 (FATAL) — V10-a/V10-b の drift が α=1/α=2 で逆転している
- **位置**: [13f_error_budget.tex:41-42](paper/sections/13f_error_budget.tex#L41-L42) vs
  [13e_nonuniform_ns.tex:170-173](paper/sections/13e_nonuniform_ns.tex#L170-L173)
- **問題**: 13f master table:
  - V10-a (α=1, Zalesak): drift = `0.107%`
  - V10-b (α=2, Zalesak): drift = `1.519%`
  Tab.V10_zalesak (N=128):
  - α=1, N=128: mass drift = `1.535%`
  - α=2, N=128: mass drift = `0.030%`
  → α が逆になっており，「α=2 で改善」という Tab.V10 の物理的傾向と矛盾．
- **根拠**: V10 再実行 (本査読 P3) ※V10 完了時に値を本書に追記．
- **修正方向**: 13f L41 の V10-a 行を `α=1: drift=1.535%` に，
  L42 の V10-b 行を `α=2: drift=0.030%` に交換．
  合格判定 (L64–74) も α=2 を ✓，α=1 を △ に再分類．

#### RA-CH13-005 (FATAL) — V10-c 単一渦 drift = 0.000% は実測と矛盾
- **位置**: [13f_error_budget.tex:43](paper/sections/13f_error_budget.tex#L43) vs
  [13e_nonuniform_ns.tex:187](paper/sections/13e_nonuniform_ns.tex#L187)
- **問題**: 13f master table V10-c: `volume drift = 0.000%`．
  Tab.V10_single_vortex の N=96, α=2 セルは mass drift = `0.979%`
  ($V_T/V_0 = 0.9902$)．完全保存はトポロジー変化のある単一渦輸送では
  物理的にあり得ず，明らかな誤記または旧 truncation 残留．
- **根拠**: V10 再実行 (本査読 P3) で再確認．
- **修正方向**: 13f L43 を `volume drift = 0.979%` および
  `△ 単一渦変形での界面再初期化バランス（≤1%）` に置換．

### MAJOR

#### RA-CH13-006 (MAJOR) — V6 で master table の指標名・数値が表内に存在しない
- **位置**: [13f_error_budget.tex:37](paper/sections/13f_error_budget.tex#L37) vs
  [13d_density_ratio.tex:42-58](paper/sections/13d_density_ratio.tex#L42-L58)
- **問題**: 13f が `|Δp_rel|^max = 1.77% (ρ_r=833, N=32)` と記載するが，
  Tab.V6 の表ヘッダは `u∞^end / |ΔV_ψ|/V_ψ,0 / |Δp_corr|/(σ/r)` のみで
  `|Δp_rel|` の列は存在しない．`|Δp_corr|/(σ/r)` の ρ_r=833, N=32 セルは
  `1.067×10⁻¹` (≈10.7%, pressure-jump 補正圧スケール) であり 1.77% に対応せず．
- **根拠**: 13d Tab.V6 を直接読出．論文中で `|Δp_rel|` の定義は提示されていない．
- **修正方向**: 13f L37 を Tab.V6 の指標と数値に同期．
  推奨: `|Δp_corr|/(σ/r) = 0.107 (ρ_r=833, N=32; pressure-jump 補正圧スケール)`
  もしくは `|ΔV_ψ|/V_ψ,0 = 3.95×10⁻¹¹`（CLS 体積保存指標）．
  「Laplace 絶対圧誤差ではない」旨を明記する 13d:38–40 のロジックに合わせる．

#### RA-CH13-007 (MAJOR) — V8 α=1 で N=48→64→96 が非単調 (1.42→1.35→5.64×10⁻⁴) ＋ 説明なし
- **位置**: [13e_nonuniform_ns.tex:35-40](paper/sections/13e_nonuniform_ns.tex#L35-L40)
  「判定と制約条件」段落 (line 53–60)
- **問題**: Tab.V8 で α=1 (一様) の u∞^end が N=64→96 で **4倍** ジャンプ．
  caption は α=2 の界面細密化に言及するが，α=1 の非単調については沈黙．
  「設計通りの安定動作」と判定しつつ，N=96 での悪化メカニズムが提示されない．
  査読観点では未説明非単調は判定根拠として弱い．
- **修正方向**: 判定段落に，N=96 で(a) HFE 曲率推定が界面 stencil 半径に対して
  ε=1.5h を再離散したときの δ-mass 配分の数値ジオメトリ，
  (b) 200 step での寄生流の長時間累積，
  (c) Δt = h/4 が固定されており CFL multiplier の効果に対する Δt 単独の影響，
  のいずれかを原因仮説として追加．これは V5 N=128 反転と関連する
  共通の高頻度励起 (短波長 spurious mode) が候補．

#### RA-CH13-008 (MAJOR) — V5 で CCD が ρ_r 全条件で N=64→128 反転 ＋ 説明なし
- **位置**: [13b_twophase_static.tex:106-108](paper/sections/13b_twophase_static.tex#L106-L108)
  「判定と制約条件」段落 (line 117–129)
- **問題**: Tab.V5 で CCD 列が ρ_r∈{1,10,100} すべての条件で N=64→128 で増加:
  - ρ_r=1: 4.50e-4 → 6.27e-4 (+39%)
  - ρ_r=10: 1.68e-4 → 6.27e-4 (+273%)
  - ρ_r=100: 1.68e-4 → 6.26e-4 (+273%)
  ρ_r=1 (低密度比) でも増加するため「高密度比由来の高周波励起」では説明できない．
  本文は CCD/FD 比の縮小傾向のみ言及し，N=128 反転は無視されている．
- **修正方向**: 判定段落に「CCD 高次微分作用素は N=128 で短波長 spurious mode を
  励起しうる; これは Δt = h/4 の固定に対し N 増加で Δt が短くなり，
  短波長スプリアス成分の蓄積時間が変化することと整合．本効果は
  CCD/FD 比の優位性を損なわない (FD は同様に増加する)．」を追加．
  あるいは N=128 を独立に「filter 検証の必要性」として carve-out．

### MINOR

#### RA-CH13-009 (MINOR) — V4 判定文の二重否定が誤読リスク
- **位置**: [13c_galilean_offset.tex:51](paper/sections/13c_galilean_offset.tex#L51) 周辺
- **問題**: 「ソルバが不変性を破ることを排除するものではない」は二重否定で，
  読者によっては「不変性を破る可能性がある」と誤読し得る．
- **修正方向**: 「O(‖U‖) 残差は固定壁・参照点ゲージ下での設計制約であり，
  ソルバ自体は Galilean 不変条件を満たす」のように直截に書き換える．

### Nit

#### RA-CH13-010 (Nit) — Tab.V_summary で V3/V5 の `u∞^end` 指標が peak/end 混在
- **位置**: [13_verification.tex:65](paper/sections/13_verification.tex#L65) 周辺
- **問題**: Tab.V_summary で V3 と V5 ともに `u∞^end` 表記．
  V3 は 13b で peak (max-over-time) を，V5 は final-step 値を採用しており，
  指標名の意味が異なる．
- **修正方向**: V3 行の指標名を `u∞^max` に変更 (1 文字置換)．

## 再現性 (P3 再実行)

- V1 (`make cycle EXP=experiment/ch13/exp_V1_tgv_energy_decay.py`) — 完了．
  時間 sweep slope ≈ **1.00** (dt=3.85e-3/2.0e-3/1.0e-3, E_rel=5.87e-7/3.13e-7/1.58e-7)
  → 13a Tab.V1_temporal の `1.00` と一致．13f master table の `2.00` は誤り．
- V7 (`make cycle EXP=experiment/ch13/exp_V7_imex_bdf2_twophase_time.py`) — 完了．
  Linf err: n=8/16/32 → 6.20e-4 / 5.75e-4 / 1.92e-4，連続比から
  finest local slope = log2(5.75e-4 / 1.92e-4) ≈ **1.58** で 13d Tab.V7 と一致．
  13f master table の `0.56` は廃棄済み reduced proxy の値であることを確認．
- V10 (`make cycle EXP=experiment/ch13/exp_V10_cls_advection_nonuniform.py`) — 後続
  → 完了時に α=1/2 drift および single-vortex drift を本書に追記．

## スクリプト忠実性 (P4)

- `experiment/ch13/exp_V1_tgv_energy_decay.py`:
  ν=0.01, T=0.05, SPATIAL_N=(32,48,64), TIME_DT_TARGETS=(4e-3,2e-3,1e-3) — 13a 設定段落と一致．
- `experiment/ch13/exp_V7_imex_bdf2_twophase_time.py`:
  σ=1, ρ_l=10, ρ_g=1, N=24, T=0.02, N_STEPS_LIST=(8,16,32,64) — 13d 設定段落と一致 (ref=64 を最大として slope 計算)．
- `experiment/ch13/exp_V10_cls_advection_nonuniform.py`:
  Zalesak: N∈{64,128}, α∈{1,2}; single-vortex: N=96, α=2, T=1.0 — 13e 設定段落と一致．
- `experiment/ch13/ch14_stack_common.py` (337 行) は §14 stack assertion を提供．

## 引用 (bib key 実在確認)

`paper/bibliography.bib` 中で全 14 key を確認済:
Brachet1983, Kovasznay1948, Hysing2009, AlandVoigt2019, Roy2003, Zalesak1979,
Brackbill1992, Popinet2009, DennerVanWachem2015, HarvieDavidsonRudman2006,
SussmanSmereka1997, Tryggvason2011, AscherRuuthSpiteri1997, HairerWanner1996.

## 修正方針

1. **P6**: 13f master table の 5 行 (V1-b, V2-a, V7, V10-a, V10-b, V10-c) を
   sub-file 実測値に同期 (FATAL 5 件解消)．「合格判定」リスト (L64–74) を再分類．
   V6 指標名・数値を Tab.V6 と整合 (MAJOR 1 件)．
2. **P6**: 13e 「V8 判定段落」と 13b 「V5 判定段落」に非単調原因仮説を追記
   (MAJOR 2 件)．
3. **P6**: 13c V4 判定文の書き直し (MINOR 1 件)．
4. **P6**: 13_verification.tex Tab.V_summary V3 指標名を `u∞^max` に (Nit 1 件)．
5. **P7**: 修正後 11 所見すべて closed/resolved の再査読アーティファクトを発行．
6. **P8**: `latexmk -g -xelatex -interaction=nonstopmode main.tex` clean，
   pp count 確認．

## 総合判定

**MAJOR REVISION REQUIRED**: §14 stack 化リワーク後の master table 同期が
取れていない．全 FATAL/MAJOR を P6 で 13f 中心に閉じれば合格水準に到達する見込み．
