# §13 ResearchArchitect 再査読 — 2026-04-29

担当: ResearchArchitect (CHK-RA-CH13-001 / id_prefix=RA-CH13)
初回査読: `artifacts/A/review_ch13_researcharchitect_20260429.md`
ブランチ: `worktree-ra-ch13-review-20260429`
**最終判定: PASS (open severity = 0)**

## サマリ

初回査読で指摘した 10 件 (FATAL 5 / MAJOR 3 / MINOR 1 / Nit 1) はすべて
P6 修正で closed． 13f master table の `tab:v_accuracy_summary` は
sub-file 実測値と完全整合し，誤差源スタック・合格判定・設計指針の各段落も
新しい値に同期された．V5/V8 の非単調挙動には CCD 短波長 spurious mode 仮説
を明示的に追加し，V4 二重否定を直截化．V3 指標を peak/end 整合させた．

| Severity | 当初件数 | closed | open |
|---|---:|---:|---:|
| FATAL | 5 | 5 | 0 |
| MAJOR | 3 | 3 | 0 |
| MINOR | 1 | 1 | 0 |
| Nit   | 1 | 1 | 0 |
| **計**  | **10** | **10** | **0** |

## 修正内訳

### FATAL (5/5 closed)

#### RA-CH13-001 — V1-b 時間 slope (closed in 3a64916)
- 修正前: `13f:32` → `slope = 2.00 ✓ O(Δt²) 達成`
- 修正後: `13f:32` → `slope = 1.00 (△ fractional-step 結合) / O(Δt²) 設計`
- 検証: V1 再実行 (P3) で時間 sweep (dt=3.85e-3/2.0e-3/1.0e-3) 連続比から
  finest local slope ≈ 1.00 を確認．13a Tab.V1_temporal の `1.00` と一致．
- 追加修正: 「合格判定」L67 で V1-b を ✓ から △ に再分類．「誤差源スタック」L52
  を「fractional-step 結合で V1-b 時間 slope は 1.00 に縮退する」へ更新．

#### RA-CH13-002 — V2-a 空間 slope (closed in 3a64916)
- 修正前: `13f:33` → `slope = 6.00 ✓ O(h⁶) 達成`
- 修正後: `13f:33` → `slope = 3.95 (△ 圧力境界・界面外周低次寄与) / O(h⁶) 設計`
- 検証: 13a Tab.V2_spatial asymptotic slope = 3.95 と直接一致．
- 追加修正: L50「CCD 6 次（V2 で確証）」→「CCD 6 次設計に対し，V2 Kovasznay slope
  は実効 3.95」へ更新．「合格判定」で V2-a を ✓ から △ に再分類．

#### RA-CH13-003 — V7 IMEX-BDF2 slope (closed in 3a64916)
- 修正前: `13f:38` → `slope = 0.56 × 設計未達`
- 修正後: `13f:38` → `slope = 1.58 (△ coupled-stack 実効次数) / O(Δt²) 設計`
- 検証: V7 再実行 (P3) で n=8/16/32 → Linf err = 6.20e-4/5.75e-4/1.92e-4，
  finest local slope = log2(5.75e-4/1.92e-4) ≈ 1.58．13d Tab.V7 の `1.58` と一致．
- 追加修正: 「合格判定」で V7 を × から △ に移動．× カテゴリは「該当なし」に．
  「誤差源スタック」L52 を coupled-stack O(Δt^1.58) に更新．

#### RA-CH13-004 — V10-a/V10-b α swap (closed in 3a64916)
- 修正前: `13f:41-42` → V10-a (α=1) drift = `0.107%`, V10-b (α=2) = `1.519%`
- 修正後: `13f:41-42` → V10-a (α=1) drift = `1.535%` (△ slot 解像度限界),
  V10-b (α=2) = `0.030%` (△ centroid 弱収束)
- 検証: V10 再実行 (P3) で α=1 N=128 volume_drift = 0.0153 (1.535%),
  α=2 N=128 volume_drift = 2.97e-4 (0.030%)．13e Tab.V10_zalesak と完全一致．
- 追加修正: 合格判定で V10-b を ✓ に，V10-a を △ に再分類．
  「誤差源スタック」L58–60 を「α=2 で 0.030%」「α=1 では 1.535%, slot 解像度律速」
  へ更新．

#### RA-CH13-005 — V10-c 単一渦 drift (closed in 3a64916)
- 修正前: `13f:43` → `volume drift = 0.000% ✓`
- 修正後: `13f:43` → `mass drift = 0.979% ✓` (L¹ reversal $2.42\times 10^{-3}$)
- 検証: V10 再実行 (P3) で single_vortex N=96, α=2 → volume_drift = 9.79e-3 (0.979%)．
  13e Tab.V10_single_vortex と一致．`area_drift = 0.0` (面積) と
  `volume_drift = 0.979%` (psi 体積) は別指標であり，13e の「mass drift」は後者．
  指標名も `volume drift` → `mass drift` に統一．

### MAJOR (3/3 closed)

#### RA-CH13-006 — V6 指標名・数値 (closed in 3a64916)
- 修正前: `13f:37` → `|Δp_rel|^max = 1.77% (ρ_r=833, N=32) ✓`
- 修正後: `13f:37` → `|Δp_corr|/(σ/r) = 1.07×10⁻¹ (ρ_r=833, N=32; pressure-jump 補正圧) ✓`
- 検証: 13d Tab.V6 のヘッダ `|Δp_corr|/(σ/r)`, ρ_r=833, N=32 セル = 1.067e-1 と一致．
  「Laplace 絶対圧誤差ではない」(13d:38–40) との整合．

#### RA-CH13-007 — V8 α=1 N=96 ジャンプ説明 (closed in a50395d)
- 修正前: 13e:53–60 「判定と制約条件」段落で α=1 N=96 の 4× ジャンプに沈黙．
- 修正後: 13e に短波長 spurious mode 励起仮説を追記．Δp_final = 0.395 一定なので
  BF 平衡は維持されることを明示．長時間 spurious 抑制には HFE/pressure-jump
  経路 (V6/V7) が必要との制約を追加．

#### RA-CH13-008 — V5 N=128 反転説明 (closed in a50395d)
- 修正前: 13b:117–129 「判定と制約条件」段落で CCD N=64→128 反転に沈黙．
- 修正後: 13b に CCD 高次微分作用素 + Δt=h/4 固定下で短波長成分が累積する仮説を追記．
  ρ_r=1 でも増加することと CCD/FD 比優位性が維持されることを明示．

### MINOR / Nit (2/2 closed)

#### RA-CH13-009 (MINOR) — V4 二重否定 (closed in a50395d)
- 修正前: 13c:51 「ソルバが Galilean 不変性を破ることを排除するものではなく…」
- 修正後: 13c で「O(‖U‖) 残差はソルバの不変性違反ではなく，参照点ゲージ固定 PPE と
  固定 Eulerian の合成境界制約に由来する．完全な不変性検証には ALE 化が必要」へ
  直截化．

#### RA-CH13-010 (Nit) — V3 indicator (closed in a50395d)
- 修正前: 13_verification.tex:63 V3 主要指標 = `u∞^end`
- 修正後: 13_verification.tex:63 V3 主要指標 = `u∞^max`
- 13b 本文 (line 51) で V3 が peak (max-over-time) を採用しているのと整合．

## ビルド検証

`paper/` で `latexmk -g -xelatex -interaction=nonstopmode main.tex` を実行 (P8)，
exit 0．

- **228 pages** (基準 227 pp に対し +1 pp; 項目追加分の自然増)
- 0 undefined references / citations
- 0 multiply-defined labels
- 0 `^!` errors
- main.log 末尾: `Output written on main.xdv (228 pages, 5324472 bytes).`

## 設計指針への反映

13f「設計指針 (PR-5 Algorithm Fidelity)」L77 を以下のように更新済:
- 「単相 NS：CCD 6 次空間 + AB2/IMEX-BDF2 2 次時間が paper-exact 設計通り」
  → 「Kovasznay 実効 slope 3.95，TGV は時間誤差床下，PPE 射影との
  fractional-step 結合では時間 slope は 1.00 に縮退する．設計 2 次性能は
  予測子単体に限定」

これにより本論文の精度主張 (PR-5 Algorithm Fidelity) と V1-b/V2-a 実測値が
論文内で整合する．

## 結論

§13 「多相流ソルバの統合検証実験」章は，§14 stack 化リワーク以降の master
table 同期不足を解消し，sub-file 実測値・合格判定・誤差源スタック・設計指針
の全層で整合．**PASS**.

Out-of-scope:
- 残る非単調仮説 (V5/V8 CCD 短波長 mode) の実験的確認は今 CHK の範囲外．
  必要なら別 CHK で V5 N=256/CFL sweep の追加検証．
- main へのマージはユーザ指示まで保留 (`git merge --no-ff worktree-ra-ch13-review-20260429`)．
