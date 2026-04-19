---
ref_id: WIKI-T-043
title: "2D Lamb 毛細管波分散式と D(t) 変形量計測"
domain: theory
status: VERIFIED
superseded_by: null
sources:
  - path: experiment/ch13/config/exp13_17_capwave_waterair_gfm.yaml
    git_hash: 054aefb
    description: water/air GFM capwave — corrected omega0/beta to 2D Lamb formula
  - path: src/twophase/tools/diagnostics/collector.py
    description: _deformation() — second-moment D=(L-B)/(L+B) implementation
consumers:
  - domain: experiment
    description: exp13_17 analytical overlay parameter derivation
  - domain: paper
    description: §13 capillary wave benchmark formula correction
depends_on:
  - "[[WIKI-T-014]]: Capillary CFL Constraint & ALE Grid Motion Effects"
  - "[[WIKI-P-009]]: Prosperetti (1981) benchmark parameters"
  - "[[WIKI-T-004]]: Balanced-Force Condition (parasitic currents)"
tags: [capillary_wave, Lamb, Prosperetti, deformation_metric, 2D_vs_3D, analytical]
compiled_by: Claude Sonnet 4.6
compiled_at: "2026-04-19"
---

# 2D Lamb 毛細管波分散式と D(t) 変形量計測

## Motivation

論文 §13 の毛細管波ベンチマーク (exp13_17) で，YAML の `omega0` に 3D Prosperetti 公式
（分子 8）が誤適用されていた．2D シミュレーションには 2D Lamb の円柱公式（分子 6）が正しく，
ω₀ を 15% 過大評価していた．また `_deformation()` が常に非負の D を返すため，
D(t) が符号付き解析解と異なる挙動を示す点も整理が必要だった．

---

## 2D Lamb 公式（円柱液滴）

2D の円形液滴（無限円柱断面）の mode-n 毛細管振動の非粘性固有振動数（Lamb 1932）:

$$
\omega_0^2 = \frac{n(n^2-1)\,\sigma}{(\rho_l + \rho_g)\,R^3}
$$

| mode n | 分子 n(n²-1) |
|--------|------------|
| 2 | 6 |
| 3 | 24 |
| 4 | 60 |

粘性減衰係数（2D，ρ_l >> ρ_g 近似）:

$$
\beta = \frac{(n^2-1)\,\mu}{(\rho_l + \rho_g)\,R^2}
$$

### 3D Prosperetti 公式との対比

Prosperetti (1981) の球形液滴公式（mode l）:

$$
\omega_0^2 = \frac{l(l-1)(l+2)\,\sigma}{(\rho_l + \rho_g)\,R^3}
$$

l=2 では分子 = 2×1×4 = **8**（2D の 6 より 33% 大）.

| 次元 | 公式の分子 | n/l=2 での ω₀ (ρ=833, R=0.25) |
|------|----------|-------------------------------|
| 2D Lamb | n(n²-1) = **6** | **0.679** rad/τ (T₀=9.26) |
| 3D Prosperetti | l(l-1)(l+2) = **8** | **0.784** rad/τ (T₀=8.01) |

→ 2D シミュレーションに 3D 公式を使うと ω₀ を **15.5% 過大評価**，T₀ を 13.5% 過小評価．

### 水-空気系 (ρ_l=833, ρ_g=1, σ=1, R=0.25) の数値例

| パラメータ | 値 |
|-----------|-----|
| ω₀ (2D Lamb) | 0.6786 rad/τ |
| T₀ | 9.26 τ |
| β (2D) | 0.00288 τ⁻¹ |
| exp(-β×9.26) | 0.974（1周期後振幅保持率） |

---

## D(t) 変形量計測の注意事項

`_deformation()` (collector.py) の実装:

```python
# mask = psi > 0.5  (液相領域のピクセル)
# 2次モーメントの固有値 eig1 >= eig2
L = sqrt(eig1);  B = sqrt(eig2)
D = (L - B) / (L + B)   # 常に >= 0
```

**D は常に非負**であるため，解析解 D₀·e^{-βt}·cos(ω₀t) の符号変化を捉えられない:

| 解析解の符号 | 物理的意味 | 測定 D |
|------------|----------|-------|
| > 0 | x 方向 prolate | D > 0 |
| = 0 | 真円 | D ≈ 0 |
| < 0 | y 方向 prolate（x 方向 oblate） | D > 0（符号逆転せず） |

したがって **測定 D(t) は |解析解|** に相当し，振動数 ω₀ の 2 倍に見える「折り返し」が生じる:

$$
D_\text{measured}(t) \approx D_0 \cdot e^{-\beta t} \cdot |\cos(\omega_0 t)|
$$

### snap_interval の選択に関する注意

`snap_interval = T₀/4` に設定すると各スナップが零点付近で撮られ，
D ≈ 0 のみが記録されて「振動なし」に見える．
推奨: `snap_interval = T₀/4` の奇数倍を避ける（例: T₀/2 または T₀/3）．

---

## CHK-141 補足: omega0 誤り検出フロー

1. exp13_17 を T=8（≈T₀と誤認）で実行 → D(0)=0.041, D(8)=0.003
2. D(8) が D₀ に戻っていない（理論では cos(2π)≈1 のはず）→ 矛盾
3. 解析: 第1零点 t≈2.47 → ω₀=π/(2×2.47)=0.635 ≈ 2D Lamb 予測 0.679（整合）
4. 原因判明: YAML の分子 8 は 3D 公式 → 2D Lamb 分子 6 に修正
5. 修正後: omega0=0.679, beta=0.00288, T₀=9.26 (commit 054aefb)

---

## Assumptions

- 2D 境界条件（壁面）は Lamb 公式の仮定（無限空間）から外れるため，数値 ω₀ は理論値より小さくなる可能性がある
- 高密度比（ρ=833:1）では寄生渦流が振動を乱す（WIKI-T-004 参照）
- β の 2D 公式は μ_l=μ_g=μ（一様粘性）の仮定に基づく
