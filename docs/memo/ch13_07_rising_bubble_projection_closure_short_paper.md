# Short Paper: ch13 α=2 上昇気泡の早期ブローアップ診断

Date: 2026-04-24  
Branch: `worktree-researcharchitect-src-refactor-plan`  
Compiled by: ResearchArchitect

## Abstract

本メモは、`experiment/ch13/config/ch13_rising_bubble_water_air_alpha2_n128x256.yaml`
で発生した早期ブローアップについて、前提条件、NS 計算スキーム、症状、
仮説立案、検証結果、最有力原因、今後の設計含意を短い論文形式で整理した
ものである。主結論は、今回の不安定化は**浮力によって励起される
variable-density projection の離散閉包不整合**であり、表面張力、`α=2`
非一様格子、高密度比はその増幅因子である、というものである。

## 1. Problem Setting

対象は 2D 水-空気上昇気泡で、条件は次の通りである。

- 領域: `LX × LY = 1.0 × 2.0`
- 格子: `128 × 256`
- 境界条件: wall
- 格子分布: interface-fitted `alpha=2.0`, static rebuild
- 物性: `ρ_l=1000`, `ρ_g=1.2`, `μ_l=1e-3`, `μ_g=1.8e-5`, `σ=0.072`
- 重力: `g=0.001`
- 初期条件: 半径 `0.25` の gas bubble at `(0.5, 0.5)`

設定の実体は
`experiment/ch13/config/ch13_rising_bubble_water_air_alpha2_n128x256.yaml`
にある。

## 2. NS Scheme Under Test

本件の NS/CLS スキームは、GPU 優先の ch13 実行スタックであり、要点は次の
通りである。

- interface transport: psi-direct + FCCD + TVD-RK3
- reinitialization: ridge-eikonal every 4 steps
- convection: UCCD6 + AB2
- viscosity: CCD bulk + Crank-Nicolson predictor
- surface tension: `pressure_jump`
- pressure projection: FCCD matrix-free PPE + defect correction
- PPE coefficient: `phase_separated`
- interface coupling: `jump_decomposition`
- boundary: wall

重要なのは、FCCD 経路では `face_flux_projection` が実質的に自動で有効化
される点である。したがって、初期 diagnosis 時点から「face projection が
全く無い」状況ではなかった。

## 3. Observed Failure

debug 実行
`experiment/ch13/config/ch13_rising_bubble_water_air_alpha2_n128x256_debug.yaml`
では、`step=6`, `t=0.0148` で BLOWUP した。

症状は以下である。

- `volume_conservation ≈ 7e-08` と小さい
- `ppe_rhs_max: 1.33e+01 → 9.06e+09`
- `bf_residual_max: 2.36e+00 → 1.98e+11`
- `div_u_max: 2.48e-03 → 6.54e+05`
- `kinetic_energy` は最終的に `O(10^6)` まで急上昇

したがって、壊れている主対象は CLS 質量保存ではなく、
**projection / balanced-force / divergence closure** 側である。

## 4. Hypothesis Campaign

本件では、少なくとも次の 8 仮説を立てて検証した。

| ID | Hypothesis | Verdict | Evidence |
|---|---|---|---|
| H1 | 表面張力が主因 | 棄却 | `sigma=0` でも BLOWUP |
| H2 | 浮力が必要励起源 | 強く支持 | `g=0` は `T=0.05` まで安定 |
| H3 | reinit が主因 | 棄却 | `reinit_every=0` はむしろ悪化 |
| H4 | `α=2` 非一様格子だけが原因 | 棄却 | `alpha=1` でも後に BLOWUP |
| H5 | face projection が無効 | 棄却 | FCCD path では既に on、forced off で悪化 |
| H6 | post-corrector wall zeroing が主犯 | 弱化 | face-preserve PoC でも改善せず |
| H7 | buoyancy 注入位置だけが原因 | 棄却 | projection-consistent buoyancy PoC は悪化 |
| H8 | nodal/face source-of-truth 不整合 | 最有力 | 全検証と最も整合 |

### 4.1 Key Probe Results

- `sigma=0`: `step=5`, `t=0.0383` で BLOWUP  
  → 表面張力は必要条件ではない
- `g=0`: `T=0.05` まで安定、`ppe_rhs=bf_res=div_u=0`  
  → 浮力が必要励起源
- `reinit_every=0`: baseline より悪化  
  → reinit は culprit ではなく stabilizer
- `alpha=1`: より遅れて BLOWUP  
  → 非一様格子は増幅因子であって単独犯ではない
- `face_flux_projection forced off`: 大幅悪化  
  → 既存 face projection は不十分だが有益

## 5. Most Plausible Cause

理想的な variable-density projection は、同じ離散空間で

$$
D\left(u^\* + \Delta t \frac{f}{\rho} - \Delta t M^{-1}Gp\right)=0
$$

を満たさねばならない。

しかし現状の ch13 path では、

1. PPE は normal face flux の空間で解かれる
2. corrector は face で安定化される
3. その後の canonical solver state は nodal velocity に戻される
4. 次 step の predictor / convection / BC は nodal state を source of
   truth として使う

という構造を持つ。

このため、PPE が閉じた face flux を解いても、その情報が「次の canonical
state」として保存されない。浮力は毎 step 新たな predictor flux を作るため、
この閉包誤差が繰り返し励起され、`ppe_rhs`, `bf_residual`, `div_u` が急増する。

### 5.1 Why Nearby Hypotheses Fail

- **surface tension culprit 説**は、`sigma=0` で壊れるため一次原因ではない
- **wall BC culprit 説**は、face-preserve PoC で改善しないため弱い
- **buoyancy placement だけの問題**なら、force channel に揃えた PoC で改善すべきだが、実際は悪化した

## 6. Knowledge Gained

この一連の仮説立案・検証・分析で得られた知見は次の通りである。

### 6.1 Physical / Numerical Knowledge

- `volume_conservation` が小さくても projection closure failure は起こり得る
- buoyancy は「存在するかどうか」だけでなく、「どの離散空間で閉じるか」が支配的
- `α=2` 非一様格子は root cause ではなく amplifier として振る舞う
- reinitialization は少なくとも今回の static psi-direct path では stabilizing
  に働く

### 6.2 Diagnostic Knowledge

- `ppe_rhs_max`, `bf_residual_max`, `div_u_max` の 3 連時系列は、
  rising-bubble blowup diagnosis に非常に有効
- `kinetic_energy` 単独では発散の「結果」は見えるが、原因特定には不十分
- opt-in PoC を小さく入れる方法は、近傍仮説の反証に有効である

### 6.3 Design Knowledge

- FCCD face projection を「持っている」ことと、face state を
  **canonical state** として維持することは別問題である
- 次の viable design は、pressure corrector 後の source of truth を
  真に face/staggered state へ寄せることである

## 7. Design Implication

今後の本命修正は、次の設計を満たす必要がある。

1. pressure corrector 後の canonical velocity state を face/staggered に置く
2. divergence gate は face divergence を用いる
3. nodal velocity は advection / diagnostics / visualization 用の派生量に下げる
4. buoyancy と pressure correction を同一 face closure の中で扱う

face-preserve PoC と projection-consistent-buoyancy PoC は、いずれも
「最小変更では足りない」ことを示した負例として価値がある。

## 8. Artifact Map

- baseline debug result:
  `experiment/ch13/results/ch13_rising_bubble_water_air_alpha2_n128x256_debug`
- face-projection comparison:
  `experiment/ch13/results/ch13_rising_bubble_water_air_alpha2_n128x256_faceproj_debug`
- face-preserve PoC:
  `experiment/ch13/results/ch13_rising_bubble_water_air_alpha2_n128x256_facepreserve_debug`
- buoyancy-projection PoC:
  `experiment/ch13/results/ch13_rising_bubble_water_air_alpha2_n128x256_buoyancyproj_debug`
- PoC follow-up memo:
  `docs/memo/ch13_06_projection_closure_poc_followups.md`
