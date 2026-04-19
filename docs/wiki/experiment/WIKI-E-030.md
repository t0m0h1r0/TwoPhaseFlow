---
ref_id: WIKI-E-030
title: "G^adj 後期ブローアップ: α=1.5 壁面BC 気泡上昇 t≈12.6 の未解明不安定性"
domain: experiment
status: OPEN
superseded_by: null
sources:
  - path: experiment/ch13/results/ch13_02_waterair_bubble/data.npz
    git_hash: fe17e6b
    description: b83837r0w — G^adj 修正後の ch13_02_waterair_bubble 実行結果
depends_on:
  - "[[WIKI-T-044]]: FVM-CCD Metric Inconsistency (G^adj の理論)"
  - "[[WIKI-E-030 前提]]: ch13_02_waterair_bubble G^adj 修正 (b83837r0w)"
tags: [non_uniform_grid, bubble_rising, blowup, open_issue, late_instability, alpha_1.5, wall_bc]
compiled_by: Claude Sonnet 4.6
compiled_at: "2026-04-20"
---

# G^adj 後期ブローアップ: α=1.5 壁面BC 気泡上昇 t≈12.6 の未解明不安定性

## 現象の観察

G^adj 修正（WIKI-T-044）の検証実験（b83837r0w）で、元のブローアップ（step 51, t≈0.023）は解消されたが、**ステップ 28,122（t≈12.6）に別のブローアップが観察された**。

### 観測データ

| 指標 | 値 |
|------|-----|
| ブローアップ発生 | step 28,122, t ≈ 12.5977 |
| KE_max | 1.0375 × 10⁶ |
| KE @ t=12.50 | 5.93 × 10⁻¹（急上昇の開始） |
| KE @ t=12.59 | 2.59 × 10¹ |
| 気泡重心 y_c @ t=12.59 | 0.5438（初期 0.50，ほぼ静止） |
| 気泡速度 v_c @ t=12.59 | 0.0116（非常に小さい） |
| 体積保存 @ t=12.59 | 4.69 × 10⁻¹⁵（機械精度，正常） |

### 時系列

```
t=10.00  KE=1.29e-01  yc=0.5284  vc=0.0048
t=12.00  KE=1.92e-01  yc=0.5384  vc=0.0068
t=12.50  KE=5.93e-01  yc=0.5425  vc=0.0104  ← KE急上昇開始
t=12.55  KE=...        yc=0.5434  vc=0.0120
t=12.59  KE=2.59e+01  yc=0.5438  vc=0.0116
t=12.60  KE=1.04e+06  → ブローアップ
```

---

## G^adj ブローアップとの違い

| 特性 | G^adj 修正前（step 51） | 後期ブローアップ（step 28122） |
|------|----------------------|------------------------------|
| 発生時刻 | t ≈ 0.023（即時） | t ≈ 12.60（遅延） |
| KE 急増の開始 | 初期から | t ≈ 12.50 から |
| 気泡の移動量 | ほぼゼロ | y_c = 0.04（わずか） |
| 体積保存 | 記録なし | 正常（機械精度） |
| 根本原因 | FVM-CCD メトリクス不整合（解明済み） | **未特定** |

---

## 仮説

### 仮説 A: GFM 界面ジャンプ条件の数値不安定
- GFM は圧力ジャンプ条件 Δp = σκ を界面をまたぐ面に課す
- 界面の変形が進むにつれて曲率 κ の誤差が蓄積
- α=1.5 非均一格子では界面近傍のステンシルが非対称になり誤差増幅

### 仮説 B: 非均一格子 + GFM の Balanced-Force 条件破れ
- G^adj は速度補正の勾配を修正したが、Predictor の ∇p^n は CCD のまま
- 非均一格子では ∇p^n（CCD）と b^GFM（FVM空間）の間にも不整合があるかもしれない
- これが毎ステップ小さな誤差を注入し長時間で蓄積

### 仮説 C: CLS 再初期化の非均一格子誤差の蓄積
- 再初期化器（eikonal_xi）が非均一格子上で毎ステップ小さな形状誤差を蓄積
- t≈12 以降で界面変形が閾値を超えてカスケード
- ただし体積保存は正常なため、再初期化誤差は小さい可能性

### 仮説 D: CFL 条件の違反
- 気泡の加速により局所的な CFL が上昇し数値不安定化
- ただし v_c = 0.012 は非常に小さく、CFL 違反は考えにくい

---

## 調査に必要な情報

1. **alpha=1.0 との比較**: 同じ設定で α=1.0（均一格子）で走らせた場合に同じ時刻にブローアップするか
   - 同じ → 物理的/アルゴリズム的問題（非一様格子と無関係）
   - しない → 非一様格子固有の問題

2. **診断量の追加**: t=12.0〜12.6 の間に以下を記録
   - 最大曲率 κ_max
   - GFM 補正の最大値 b^GFM_max
   - PPE 残差
   - CFL 数の時系列

3. **Predictor の ∇p^n の置換試験**: 仮説 B を検証するため、
   Predictor でも G^adj を使用するバリアントで実験

4. **GFM なし（CSF）での同条件実験**: GFM 特有の問題かどうかを分離

---

## 設定

```yaml
# ch13_02_waterair_bubble の主要パラメータ
grid:
  NX: 64, NY: 128, LX: 1.0, LY: 2.0
  bc_type: wall
  alpha_grid: 1.5
physics:
  rho_l: 833, rho_g: 1, sigma: 1, mu: 0.05, g_acc: 0.001
run:
  T_final: 20.0
  cfl: 0.10
  reinit_method: eikonal_xi
  phi_primary_transport: true
  reproject_mode: consistent_gfm
```

---

## ステータス

- [x] 現象の観察・記録
- [x] G^adj ブローアップとの区別
- [ ] alpha=1.0 との比較実験
- [ ] 診断量の追加記録
- [ ] 根本原因の同定
- [ ] 修正の実装・検証

**次セッションで調査予定。**
