# 検討メモ：reproject_velocity の「演算子整合 + 界面条件整合」同時導入方針

日付: 2026-04-16  
対象: 非一様格子再構成後の `reproject_velocity`

## 0. 結論（先出し）
`reproject_velocity` の本質対策は，以下の同時導入が必要。

1. 演算子整合: 再投影PPEと速度補正で同一の離散作用素対（`D_h`, `G_h`, `L_h`）を使う
2. 界面条件整合: 再投影PPEに界面ジャンプ条件（少なくとも法線流束連続）を明示注入する

実験事実として，変密度化単独（`reproject_variable_density=True`）は `exp12_21` で悪化（`u_peak~1e27`）し，単独導入は不採用。

---

## 1. 現状ギャップ（コード観測）

### 1.1 `ns_pipeline` 側
- `src/twophase/simulation/ns_pipeline.py`
- `_reproject_velocity` は再構成後に補間誤差を除去する目的でPPEを解く。
- ただし再投影は `PPEBuilder` の最小経路に依存し，界面補正は未注入。

### 1.2 利用可能な既存資産
同リポジトリ内に，界面整合を持つPPE経路が既に存在する。

1. `src/twophase/ppe/iim_solver.py`（`PPESolverIIM`）
- `IIMStencilCorrector` を使い，`delta_q` をRHSへ注入する構造が実装済み。
- `decomp/lu/dc` の3 backend があり，特に `decomp` は jump decomposition を実装。

2. `src/twophase/ppe/iim/stencil_corrector.py`
- crossing face検出と jump 補正（nearest/hermite）を実装済み。
- `L_sparse` と `phi,kappa,rho,rhs` から `delta_q` を計算可能。

3. `src/twophase/coupling/gfm.py`, `src/twophase/coupling/ppe_rhs_gfm.py`
- GFM correction を PPE RHS へ加えるパスが確立済み。

=> 新規実装より「再投影に既存IIM/GFM経路を移植」する方がリスクが低い。

---

## 2. 同時導入の実装原則

### 原則P1: 射影の定義を最適化問題で固定

`min_u 1/2 ||u-u^r||_{M_rho}^2` s.t. `D_h u = 0`

ここから

`u = u^r - M_rho^{-1} G_h phi`,
`L_h phi = D_h u^r`, `L_h = D_h M_rho^{-1} G_h`

を採用し，この式をコード設計の「唯一の正」とする。

### 原則P2: 補正項はRHS注入で統一
界面条件は行列改造よりまずRHS補正 (`rhs += delta_q`) で導入し，
既存 `IIMStencilCorrector` 資産を再利用する。

### 原則P3: 再投影専用ジャンプを明示
再投影は幾何補正であり，主PPEの物理圧力ジャンプと役割を分離する。

- 基本: `[phi]_Gamma = 0`
- 必須: `[(1/rho)∂_n phi]_Gamma = 0`

表面張力由来 `[p]=σκ` の注入は主PPE側責務として分離。

---

## 3. 実装アーキテクチャ案

## 3.1 `ns_pipeline` に mode を追加
`TwoPhaseNSSolver` に

- `reproject_mode = "legacy" | "consistent_iim" | "consistent_gfm"`

を追加し，既定は `legacy` 維持（既存実験互換）。

## 3.2 `consistent_iim` の処理フロー
1. 再構成後 `u^r` から `rhs = D_h u^r` を構築
2. `PPESolverIIM.solve(rhs, rho, dt=1.0, phi=phi, kappa=0, sigma=0)` を呼ぶ
3. `phi_corr` を使い `u <- u^r - (1/rho)G_h phi_corr`

注: `sigma=0` でも `IIMStencilCorrector` を法線流束連続専用に拡張できる。
現状の `IIMStencilCorrector` は `[p]=σκ` 寄りなので，再投影専用jump演算子を追加する。

## 3.3 演算子整合チェック
再投影前後で

- `||D_h u||_2`（必須）
- `ΔE_rho = ||u||_{M_rho}^2 - ||u^r||_{M_rho}^2`（非増大期待）

を記録。`ΔE_rho > 0` が連続発生したら mode を自動降格する。

---

## 4. 必要な追加実装（最小集合）

1. 新規クラス `ReprojectionJumpCorrector`（推奨）
- 役割: 再投影専用のjump補正 `delta_q_reproj` を返す
- 入力: `L_sparse, phi, rho, rhs`
- 出力: `delta_q`

2. `ns_pipeline._reproject_velocity` の分岐
- `legacy`: 既存そのまま
- `consistent_*`: `rhs + delta_q` を解いて速度補正

3. 計測フック追加
- `div_before`, `div_after`, `energy_delta_rho`, `ppe_residual`

---

## 5. 実験計画（同時導入検証）

### Stage-1: 再現性固定
- `exp12_21` に `reproject_mode` 軸を追加
- 比較: `legacy`, `variable_density_only`, `consistent_iim`

### Stage-2: 動的界面ゲート
- `exp12_20` の4ケースへ横展開
- 合格条件: `translate_nonuniform` の FAIL 解消

### Stage-3: 収束性
- 解像度スイープで `div_peak`, `u_peak`, `mass_err` の次数確認

---

## 6. リスク評価

1. IIM補正を再投影へ持ち込む際，`sigma` 前提ロジックを無効化しないと過補正になる。  
2. `PPEBuilder`（FVM系）とCCD系演算子の混在は依然ギャップを残す。  
3. よって最終的には `PPESolverIIM` ベースへ寄せて，`ns_pipeline` の再投影も同一PPE実装へ統一するのが望ましい。

---

## 7. 推奨実行順

1. `consistent_iim` モードのスケルトン追加（既定`legacy`維持）
2. `ReprojectionJumpCorrector` を `nearest` 相当で先行実装
3. `exp12_21` で `u_peak/div_peak` が `legacy` 以下を満たすか確認
4. 成功後に `hermite` へ拡張

