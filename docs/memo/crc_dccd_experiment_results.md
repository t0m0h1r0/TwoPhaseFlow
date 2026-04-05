# C/RC & C/RC-DCCD 静止液滴実験結果

## 1. 実験設定

- 静止液滴 R=0.25, ρ_l/ρ_g=2, We=10, σ=1
- 周期境界条件 (CCD wall BC null space 回避)
- 100 ステップ, dt=0.25h
- PPE: CCD Kronecker LU (N×N DOF, 周期 BC 対応済み)
- RHS: DCCD フィルタ済み CCD 発散 (ε_d=1/4, §7.5)
- Corrector: CCD ∇p (balanced-force)

## 2. C/RC (CCD-enhanced Rhie-Chow, §7.4.3)

### 概要
RC ブラケットの p''' 係数不整合 (1/24 vs 1/8) を CCD d2 (=p'') で相殺:
```
avg* = 0.5*(p'_P + p'_E) + h/12*(p''_P - p''_E)
```
p''' 係数: 1/8 - 1/12 = 1/24 → フェイス差分と一致 → ブラケット O(h²) → O(h⁴)

### 適用範囲
- **RC パスのみ**に適用可能 (RC ブラケットが存在する場合)
- DCCD パスでは RC ブラケットが不在のため直接的には無効
- f_σ ブラケットには適用不可 (界面近傍で d2(f_σ) が発散 → 不安定)

### 検証結果 (exp12_rc_high_order.py, FD spsolve + RC)

| N | Standard ‖bracket‖∞ (slope) | C/RC ‖bracket‖∞ (slope) |
|---|---|---|
| 16 | 7.89e-2 | 2.05e-4 |
| 32 | 2.01e-2 (2.0) | 1.29e-5 (4.0) |
| 64 | 5.04e-3 (2.0) | 8.10e-7 (4.0) |
| 128 | 1.26e-3 (2.0) | 5.07e-8 (4.0) |

## 3. C/RC-DCCD (CCD-enhanced DCCD)

### 概要
DCCD フィルタの散逸誤差 O(ε_d h²) を、CCD differentiate が同時に返す d2 で補正:
```
div_corrected = D¹_CCD(ũ*) - ε_d h² * FD(D²_CCD(ũ*))
```
d2 はフィルタ済み ũ* から計算 → チェッカーボード成分ゼロ → 再導入なし。

### Taylor 展開
- DCCD フィルタ誤差: ε_d h² u*''' (→ div に O(ε_d h²) 散逸)
- 補正: ε_d h² * (d2_{i+1}-d2_{i-1})/(2h) ≈ ε_d h² u*''' + O(ε_d h⁴)
- 補正後: O(ε_d h⁴) — 散逸誤差が 2 次改善

### 結果 (exp12_crc_static_droplet.py, DCCD + CCD-LU, periodic)

| N | Mode | ‖u‖∞ | Δp err |
|---|------|------|--------|
| 32 | DCCD standard | 3.767e-1 | 0.010% |
| 32 | **C/RC-DCCD** | **3.748e-1** | **0.002%** |
| 64 | DCCD standard | 3.449e-3 | 1.234% |
| 64 | C/RC-DCCD | 3.445e-3 | 1.234% |

N=32: C/RC-DCCD で Δp 5 倍改善 (DCCD フィルタ誤差が律速)
N=64: 効果なし (CSF O(h²) が律速、フィルタ誤差は非支配的)

## 4. CCD-PPE ソルバ状況

| ソルバ | 変密度 | 周期 BC | 壁 BC | 速度 |
|--------|--------|---------|-------|------|
| CCD Kronecker LU | OK | **OK** (N×N DOF fix) | NG (12D null space) | 遅い |
| DC (FD前処理+CCD残差) | **NG** (iter 4 で発散) | OK (定密度のみ) | 未テスト | 速い |
| ADI defect correction | **NG** (L_CCD 負定値) | NG | NG | �� |

### DC 発散の原因
変密度 PPE: L_FD と L_CCD の演算子差が密度比に比例して増大。
DC 収縮率 ‖I - L_FD⁻¹ L_CCD‖ > 1 (ρ_l/ρ_g=2 で iter 4 以降で発散)。
定密度 (ρ=1) では完璧に収束 (5 iter で残差 1e-7)。

### 壁 BC の null space 問題
CCD D² Kronecker 行列 + wall Neumann BC: 12D null space (N=16)。
単一ピンでは 1 DOF しか除去できず、11 near-null mode が残存。
周期 BC ではこの問題は発生しない (N×N DOF fix 後)。

## 5. 今後の課題

1. **壁 BC CCD-PPE**: null space の完��除去 (12 ピン? SVD 射影?)
2. **変密度 DC 収束**: ILU 前処理, CCD ベースの前処理
3. **C/RC-DCCD の高解像度効果**: N=128+ で DCCD フィルタ��差が再び律速する領域を確認
4. **IPC (Incremental Pressure Correction)**: 時間精度 O(Δt²) の確保
