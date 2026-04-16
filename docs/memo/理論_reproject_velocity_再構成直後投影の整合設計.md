# 理論ショートペーパー：reproject_velocity 再構成直後投影の整合設計

日付: 2026-04-16  
対象: `src/twophase/simulation/ns_pipeline.py` の `_rebuild_grid` -> `_reproject_velocity`

## 0. 要旨
非一様格子で界面追従再構成を行うと，補間後速度 `u^r` は一般に離散非圧縮制約を満たさない。  
本稿は，`reproject_velocity` を「補間ノイズ除去」ではなく「再構成後幾何に対する重み付きHodge射影」として再定式化する。

中核主張は次の3点である。

1. 破綻の第一原因は `D_h^{n+1} R_h != R_h D_h^n`（再構成写像 `R_h` と離散発散 `D_h` の非可換）であり，毎step再構成で発散モードが蓄積する。  
2. 現行の `rho=1` 射影は，二相の運動量内積に対する最小修正になっておらず，高密度相で過補正を誘発する。  
3. 本質対策は「(i) 幾何整合演算子ペア + (ii) 変密度重み付き射影 + (iii) 界面条件整合」を同時に満たすこと。

---

## 1. 問題設定
再構成前格子を `G^n`，再構成後格子を `G^{n+1}` とする。補間演算子を `R_h^{n->n+1}` とすると

`u^r = R_h u^n`

だが，`D_h^{n+1} u^r = 0` は一般に成り立たない。連続系では `div u = 0` が保存されても，離散では

`D_h^{n+1} R_h u^n - R_h D_h^n u^n = [D_h^{n+1}, R_h] u^n`

の交換子誤差が残る。

`exp12_21` の観測（`nu_default` 暴走，`nu_no_rebuild` 安定）と整合的に，この誤差は毎step再構成で指数的に増幅され得る。

---

## 2. 現行 `_reproject_velocity` の理論的不整合
現行実装（要約）:

- `div = D_h u^r`
- `rho = 1`
- `L_h phi = div` を解く
- `u <- u^r - G_h phi`

ここで主な不整合は3つ。

1. 密度重み不整合  
二相NS補正は本来 `u <- u* - dt*(1/rho) grad p`。しかし再投影だけ `rho=1` とすると，`L2` 最小化にはなっても運動量（`rho` 重み）最小化にならない。

2. 演算子対の随伴不整合  
`D_h` と `G_h` が同一離散内積で随伴（mimetic/SBP）でないと，射影が正射影にならず，エネルギーを増やし得る。

3. 界面条件の省略  
再投影ポテンシャル `phi` にも界面での流束連続条件が必要。これを落とすと界面近傍で補正勾配が不連続化し，`u_peak` を押し上げる。

---

## 3. 提案理論：重み付き整合Hodge射影

### 3.1 変分定式化（本質）
再投影を次の制約最適化として定義する。

`min_u 1/2 (u-u^r)^T M_rho (u-u^r)`  
subject to `D_h u = 0`.

`M_rho` は密度重み付き質量行列（離散内積）。ラグランジュ乗数 `phi` を導入すると

`u = u^r - M_rho^{-1} G_h phi`

`D_h M_rho^{-1} G_h phi = D_h u^r`

を得る。これが再構成後格子 `G^{n+1}` 上での一貫した再投影PPEである。

### 3.2 二相・界面条件
界面 `Gamma` をまたぐ補正ポテンシャル `phi` は，少なくとも

- `[phi]_Gamma = 0`
- `[(1/rho) partial_n phi]_Gamma = 0`

を満たす（再投影は幾何補正であり，表面張力ジャンプを新規注入しない）。

これにより補正後法線流束の連続性が維持される。

### 3.3 非一様格子での演算子整合条件
`L_h = D_h M_rho^{-1} G_h` を構成する際，以下を要求する。

- 同一メトリクス/Jacobianで `D_h` と `G_h` を定義
- 離散積分部品 `D_h = -H^{-1} G_h^T H + B`（境界項 `B`）を満たす
- 壁境界では `n·(M_rho^{-1}G_h phi)=0` をSAT/ghostで一貫実装

これで `L_h` の半正定性と，射影後の離散運動エネルギー非増大

`||u^{n+1}||_{M_rho} <= ||u^r||_{M_rho}`

が得られる。

---

## 4. 分相PPEとの接続（1+3+4 方針）
高密度比で条件数悪化を抑えるには，3.1をそのまま一括で解く代わりに

- 相内 `Omega_l`, `Omega_g` で `L_h^(a) phi^(a) = b^(a)` を解き
- 界面条件で連成

する分相化が有効。これは既存の「整合離散 x 界面条件明示 x 分相PPE」理論と同型で，`reproject_velocity` をその特別ケース（強制項なし）として埋め込める。

---

## 5. A3トレーサビリティ（Equation -> Discretization -> Code）

1. Equation  
`D_h M_rho^{-1} G_h phi = D_h u^r`, `u = u^r - M_rho^{-1} G_h phi`

2. Discretization  
`D_h,G_h` は再構成後 `J, metric` と整合，`M_rho` は `rho(psi)` で構築。界面横断では jump-aware（IIM/GFM）補正を適用。

3. Code（現行対応箇所）
- `src/twophase/simulation/ns_pipeline.py::_rebuild_grid`
- `src/twophase/simulation/ns_pipeline.py::_reproject_velocity`
- `src/twophase/simulation/ns_pipeline.py::_solve_ppe`

現行差分（理論基準比）:
- `_reproject_velocity` が `rho=ones` を使用
- 再投影で界面条件の明示注入なし
- `D_h/G_h` の射影用随伴性保証をコード上で明示していない

---

## 6. 検証可能な予測
本理論に基づく実装へ移行すると，`exp12_21` 系で次が観測されるはず。

1. `nu_default` の `div_peak` が桁単位で低下（毎step再構成でも残差が抑制）
2. `u_peak` の暴走が止まり，`nu_rebuild10` との差が縮小
3. PPE残差と運動エネルギー増分の相関が弱化（射影がエネルギー安定化として機能）

---

## 7. 限界と注意
- DCCDやフィルタ単独は高周波抑制には効くが，交換子誤差・密度重み不整合・界面条件不整合を同時には解けない。  
- よって本件の本質対策は「再投影の定義変更」であり，単なる後段平滑化ではない。

