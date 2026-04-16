# 設計メモ：reproject_velocity 整合実装仕様 v0

日付: 2026-04-16  
関連理論: `docs/memo/理論_reproject_velocity_再構成直後投影の整合設計.md`

## 0. 目的
`_rebuild_grid` 直後の再投影を，

- 非一様格子の幾何演算子
- 二相密度重み
- 界面条件整合

に一致させ，`exp12_21` の `nu_default` 暴走モードを抑止する。

## 1. 現行コード基準
対象: `src/twophase/simulation/ns_pipeline.py`

- `_rebuild_grid`: 補間後に `_reproject_velocity(psi, u, v)` を呼ぶ
- `_reproject_velocity`: `rho = ones` で `phi_corr = _solve_ppe(div, rho)`
- `_solve_ppe`: `PPEBuilder.build(rho)` を利用（可変密度行列自体は既に実装済み）

観察: 再投影だけが「単相Laplace投影」となっており，主ステップ補正と不整合。

## 2. 導入方針（段階導入）

### Phase A: 変密度重み付き再投影（最優先）
再投影で `rho = rho_g + (rho_l-rho_g) * psi` を使用する。

式:

`D_h((1/rho) G_h phi) = D_h u^r`

`u <- u^r - (1/rho) G_h phi`

実装方針:
1. `_reproject_velocity` に `rho_l, rho_g` を受ける（またはsolver保持値を使う）
2. `rho` を `psi` から構成して `_solve_ppe(div, rho)` を呼ぶ
3. 補正時も `u -= dp_dx/rho`, `v -= dp_dy/rho`

### Phase B: 射影残差の監視とガード
目的は silent divergence の早期検知。

指標（毎再投影）:
- `div_before = ||D_h u^r||_inf`
- `div_after = ||D_h u||_inf`
- `gain = div_after / max(div_before, eps)`

ガード:
- `gain > 1.2` かつ `div_after > div_tol` のとき，
  - warningを出し
  - 一時的に rebuild cadence を緩和（次周期skip）または再投影をreject

### Phase C: 界面ジャンプ整合（IIM/GFM）
再投影PPEは「幾何補正専用」なので基準ジャンプは

- `[phi]_Gamma = 0`
- `[(1/rho) partial_n phi]_Gamma = 0`

を満たすよう，界面横断行に jump-aware 補正を入れる。

注: 表面張力ジャンプ（`[p]=sigma kappa`）は主PPEで扱う。再投影は追加ジャンプを注入しない。

## 3. API案（破壊的変更を避ける）

### 3.1 Solver state
`TwoPhaseNSSolver.__init__` に次を追加:
- `reproject_mode: str = "variable_density"`  (`legacy|variable_density|jump_aware`)
- `reproject_div_tol: float = 1e-6`
- `reproject_gain_tol: float = 1.2`

### 3.2 呼び出しシグネチャ
現行:

`_reproject_velocity(self, psi, u, v)`

提案:

`_reproject_velocity(self, psi, u, v, rho_l: float | None = None, rho_g: float | None = None)`

- `rho_l/rho_g` が `None` のときは `self` に保持した値を利用
- 互換性維持のため既存呼び出しは壊さない

### 3.3 実装分岐
- `legacy`: 現行の `rho=ones`
- `variable_density`: Phase A + B
- `jump_aware`: Phase A + B + C

## 4. 離散整合チェック（SOLID/PR-5観点）

1. Algorithm Fidelity (PR-5)
- 主ステップ補正と同一形式 `u <- u - dt/rho * grad p` に再投影も合わせる

2. A3 traceability
- Eq: `D_h M_rho^{-1} G_h phi = D_h u^r`
- Discrete: PPEBuilderの`rho`依存行列
- Code: `_reproject_velocity` / `_solve_ppe`

3. SOLID
- `_reproject_velocity` に monitor 計算を直書きせず，小関数化
  - `_compute_divergence(u,v)`
  - `_project_with_density(psi, u, v, rho)`
  - `_projection_diagnostics(...)`

## 5. 実験計画（この仕様に直結）

### 5.1 最小A/B
対象: `experiment/ch12/exp12_21_nonuniform_translate_rootcause.py`

比較:
1. `legacy`（現行）
2. `variable_density`
3. `variable_density + monitor_guard`

評価:
- `u_peak`, `div_peak`, `mass_final`
- 再投影前後 `div_before/div_after`

受け入れ基準（暫定）:
- `variable_density` が `legacy` 比で `div_peak` を 1桁以上低減
- ガード有効時に blow-up を再現不能（少なくとも当該ケース）

### 5.2 拡張
- `exp12_20_nonuniform_dynamic_gate.py` の4ケースへ横展開
- `translate_nonuniform` fail -> pass を第一目標

## 6. リスク
- `PPEBuilder` はFVM系で，CCD厳密整合ではない。Phase Aで改善しても根治しない可能性。
- jump-aware を入れると行列組立コストが増えるが，本タスクは計算コスト優先なので許容。

## 7. 次アクション
1. Phase A実装（最小差分）
2. `exp12_21` を remote GPU で再実行
3. 収束すれば Phase B ガードを追加
4. 最後に jump-aware（Phase C）を導入

