---
ref_id: WIKI-E-029
title: "exp13_17/16: 物理的水-空気系毛細管波（GFM, ρ=833:1）"
domain: experiment
status: VERIFIED
superseded_by: null
sources:
  - path: experiment/ch13/config/exp13_17_capwave_waterair_gfm.yaml
    git_hash: 054aefb
    description: main config (omega0/beta corrected to 2D Lamb)
  - path: experiment/ch13/config/exp13_16_capwave_gfm_rho1000.yaml
    description: stability pre-check config (rho=1000:1, T=1)
  - path: experiment/ch13/results/exp13_17_waterair_gfm/data.npz
    description: simulation output (9700 steps, T=8)
depends_on:
  - "[[WIKI-T-043]]: 2D Lamb formula and D(t) metric"
  - "[[WIKI-X-016]]: reinit dispatch policy (eikonal_xi)"
  - "[[WIKI-T-004]]: Balanced-Force / parasitic currents at high density ratio"
  - "[[WIKI-T-036]]: phi_primary_transport theory"
compiled_by: Claude Sonnet 4.6
verified_by: data.npz D(t)/KE analysis
compiled_at: "2026-04-19"
---

# exp13_17/16: 物理的水-空気系毛細管波（GFM, ρ=833:1）

## 背景・動機

論文 §3.1（毛細管波ベンチマーク）を物理的に意味のあるパラメータで実施する．
標準 Prosperetti ベンチマーク（ρ_l=10）は計算コスト上の慣例であり，
現実の水-空気系（ρ_l/ρ_g≈833）での GFM 動作検証が目的．

### 無次元化の根拠

| 物理量 | 実値 | 無次元値 | 根拠 |
|--------|------|----------|------|
| ρ_l (水) | 998 kg/m³ | **833** | ρ_water/ρ_air = 998/1.2 |
| ρ_g (空気) | 1.2 kg/m³ | **1** | 基準密度 |
| σ | 0.072 N/m | **1** | 基準表面張力 |
| μ | 1×10⁻³ Pa·s | **0.05** | Oh=0.05/√(833×1×0.25)≈3.5×10⁻³ (~1mm水滴) |
| g | 0 | **0** | 毛細管波は重力なし |

L_ref ≈ 4.6mm（液滴半径 R=0.25 → 実スケール 1.15mm，物理的に妥当）

---

## exp13_16: 安定性事前確認 (ρ_l=1000, T=1)

**Config**: `exp13_16_capwave_gfm_rho1000.yaml`
- ρ_l=1000, ρ_g=1 (1000:1 密度比), σ=1, μ=0.05
- Grid: 64×64, α=1.5, use_local_eps=true
- Method: eikonal_xi + phi_primary_transport + consistent_gfm
- T_final=1.0, snap_interval=0.25

**結果**: T=1 まで安定完走（ブローアップなし）→ ρ=833:1 でも安定と判断

---

## exp13_17: 水-空気系毛細管波

### 設定

| パラメータ | 値 |
|-----------|-----|
| Grid | 64×64, α=1.5, use_local_eps=true, grid_rebuild_freq=0 |
| ρ_l/ρ_g | 833/1 |
| σ, μ, g | 1.0, 0.05, 0 |
| 初期条件 | perturbed_circle, R=0.25, ε=0.05, mode=2 |
| 再初期化 | eikonal_xi, reinit_every=2, reinit_eps_scale=1.4 |
| 移流 | phi_primary_transport=true |
| PPE | reproject_mode=consistent_gfm |
| T_final | 8.0 (~0.86×T₀=9.26) |
| CFL | 0.10 |

### 解析パラメータ (2D Lamb, WIKI-T-043)

| 量 | 値 |
|----|-----|
| ω₀ | 0.679 rad/τ |
| T₀ | 9.26 τ |
| β | 0.00288 τ⁻¹ |
| D₀ | 0.05 |

### 結果

| 指標 | 値 | 目標/備考 | 判定 |
|------|-----|-----------|------|
| VolCons max | **7.55×10⁻¹⁵** | <1×10⁻⁶ | **PASS** (機械精度) |
| D(t=0) 初期値 | 0.041 | 0.05 (理論) | -18% (格子離散化誤差) |
| D 第1零点 | t≈2.47 | T₀/4=2.32 | **OK** (6% 差) |
| T₀_sim 推定 | ≈11.0 | 9.26 (2D Lamb) | **19% 過大** |
| KE(T=8) | 0.098 | 単調減少を期待 | **FAIL** (寄生渦流) |
| ステップ数 | 9,700 | — | — |

### D(t) 時系列（主要点）

| t | D | KE |
|---|---|-----|
| 0.001 | 0.041 | 5×10⁻⁶ |
| 2.475 | 0.000 | 0.031 (第1零点) |
| 4.125 | 0.042 | 0.046 |
| 5.205 | **0.052** | 0.059 (第2ピーク・最大値) |
| 8.000 | 0.003 | **0.098** (終端) |

D の第2ピーク (0.052) が初期値 (0.041) を上回る → 物理的には不正（振幅増大）→ 寄生渦流によるエネルギー注入を示唆．

---

## 問題分析: 寄生渦流

**観測**: KE が 5×10⁻⁶ から 0.098 まで単調増加（約 20,000 倍）

**根本原因**:
- ρ=833:1 の高密度比で曲率推定誤差 δκ が寄生速度 u_para ∝ σ·δκ/ρ_g を生成
- ρ_g=1（分母が小さい）→ 寄生速度が液体側より気体側で支配的
- HFE (InterfaceLimitedFilter, C=0.05) + GFM を使用しても 64×64 + α=1.5 では抑制不十分
- 参考: 静止液滴では CCD balanced-force が O(h⁶) 消去 (WIKI-T-004); 動的界面では残差が蓄積

**受け入れ判断**:
- D(t) の振動挙動は確認 → ω₀ ≈ 0.6 rad/τ, 第1零点 t≈2.47
- KE 増加は論文の制限事項として明記（"高密度比における寄生渦流"）
- VolCons は機械精度 → phi_primary_transport + eikonal_xi の組合せは有効

---

## Open Questions

1. **T₀_sim ≈ 11 vs 理論 9.26 (19% 差)**: 壁面 BC・有限ドメイン・粘性補正・非線形効果のどれが支配的か未調査
2. **寄生渦流の密度比依存性**: ρ=10 ではどこまで抑制されるか（exp13_1x との比較未実施）
3. **α=1.5 の効果**: 同条件で α=1.0 に変更した場合の KE 増加率比較未実施
