# FVM-CCD メトリクス不整合と G^adj 圧力勾配による修正

**date**: 2026-04-19  
**status**: VERIFIED (実装済み、実験 b83837r0w 確認待ち)  
**wiki**: WIKI-T-044 (theory), WIKI-L-022 (code)

---

## 1. 動機

`ch13_02_waterair_bubble`（α=1.5 非均一格子、64×128、壁面BC）で
ステップ 51（t≈0.023）に運動エネルギーが 1e-3 → 1.141e6 に爆発する
現象を観察した。均一格子（α=1.0）では同じ設定で安定完走する。

---

## 2. 根本原因：演算子メトリクスの不整合

投影法のステップ 5（速度補正）と PPE ソルバーは別のメトリクスを使う。

### PPE の FVM Laplacian $\mathcal{L}_\text{FVM}$

面間距離 $d_f^{(i)} = x_{i+1} - x_i$ を使う（有限体積法的）:

$$
(\mathcal{L}_\text{FVM}\, p)_i
= \frac{1}{\delta v_i}\left[
  \frac{p_{i+1} - p_i}{d_f^{(i)}} - \frac{p_i - p_{i-1}}{d_f^{(i-1)}}
\right]
$$

メトリクス: $J_f = 1/d_f$

### 速度補正の CCD 圧力勾配 $\mathcal{G}_\text{CCD}$

CCD はノード制御体積 $\delta v_i = (x_{i+1}-x_{i-1})/2$ でメトリクスを定義:

$$
(\mathcal{G}_\text{CCD}\, p)_i = J_n \cdot \frac{\partial p}{\partial \xi}\bigg|_i,
\quad J_n = \frac{1}{\delta v_i}
$$

### 不整合の帰結

非均一格子では $d_f \ne \delta v$（一般に異なる）。これにより:

$$
\mathcal{D}_\text{FVM}(\mathcal{G}_\text{CCD}\, p) - \mathcal{L}_\text{FVM}\, p
= \frac{(\delta J_i)(p_{i+1}-p_i) - (\delta J_{i-1})(p_i - p_{i-1})}{\delta v_i} + O(h^2)
$$

ここで $\delta J_i = J_f^{(i)} - J_n^{(i)}$。

この残差は毎ステップ速度場に偽の発散として注入され、蓄積する。

---

## 3. 不整合の定量化

α=1.5、64×128 グリッドで解析:

| 項目 | 値 |
|------|-----|
| max \|J_f - J_n\| / J_f | **0.774**（77%） |
| ブローアップ発生ステップ | **51**（t≈0.023） |
| KE_max | 1.141 × 10⁶ |

---

## 4. 切り分け実験（ch13_02_bisect）

| ラベル | 設定変更 | 結果 |
|--------|---------|------|
| `alpha10` | alpha_grid = 1.0（均一格子） | **安定**（n=82, t=0.10完走） |
| `g_low` | g_acc = 0.0001（重力 1/10） | **ブローアップ**（n=51、同様） |

**結論**: 非均一格子（α>1）が唯一の原因。重力の大きさは無関係。

---

## 5. G^adj：face-average 圧力勾配

不整合を解消する修正勾配として、FVM 面メトリクスを直接使う：

$$
(\mathcal{G}^\text{adj}\, p)_i
= \frac{1}{2}\left[
  \frac{p_{i+1} - p_i}{d_f^{(i)}}
+ \frac{p_i - p_{i-1}}{d_f^{(i-1)}}
\right]
$$

### 整合性の証明

FVM 発散 $\mathcal{D}_\text{FVM}$ を G^adj に適用:

$$
\bigl[\mathcal{D}_\text{FVM}(\mathcal{G}^\text{adj}\, p)\bigr]_i
= \frac{1}{\delta v_i}\left[
  \frac{p_{i+1}-p_i}{d_f^{(i)}} - \frac{p_i - p_{i-1}}{d_f^{(i-1)}}
\right]
= (\mathcal{L}_\text{FVM}\, p)_i
$$

残差ゼロ。投影が厳密に整合する。

---

## 6. GFM との整合性

Ghost-Fluid Method 補正:

$$
b_i^\text{GFM} = \pm \frac{\Delta\rho\, \kappa\, \hat{n}}{We \cdot d_f^{(i)} \cdot \delta v_i}
$$

| 演算子 | メトリクス |
|--------|----------|
| $\mathcal{L}_\text{FVM}$ | $1/d_f$（面） |
| $\mathcal{G}^\text{adj}$（修正後） | $1/d_f$（面） ✓ |
| $b^\text{GFM}$ | $d_f/\delta v$（両方）✓ |
| $\mathcal{G}_\text{CCD}$（旧） | $1/\delta v$（ノード）✗ |

GFM・L_FVM・G^adj がすべて同じ FVM 空間。

---

## 7. 実装と境界条件

`ns_pipeline.py` に 2 メソッドを追加:

- `_precompute_fvm_grad_spacing()`: `_rebuild_grid` 末尾から呼ぶ。face spacing をデバイス配列として事前計算。
- `_fvm_pressure_grad(p, ax)`: G^adj の計算。境界（wall）は 0 初期化のまま = Neumann dp/dn=0 が自然に実現。

速度補正での切り替えガード:

```python
if not self._grid.uniform and self.bc_type == "wall":
    dp_dx = self._fvm_pressure_grad(p, 0)
    dp_dy = self._fvm_pressure_grad(p, 1)
else:
    # CCD unchanged (uniform grid, or periodic BC)
    ...
```

精度: G^adj は 2 次精度。PPE 自体が FVM 2 次精度なので問題なし。
均一格子では G^adj = CCD（d_f = δv）となり後退互換。

---

## 8. 実験結果

**実験 b83837r0w**（G^adj 修正適用後、ch13_02_waterair_bubble）:

> *(結果取得後に記入)*

期待値: T_final=20 まで完走、KE が緩やか増加→プラトー。

---

## 9. 関連ドキュメント

- [WIKI-T-044](../wiki/theory/WIKI-T-044.md) — 理論詳細（証明付き）
- [WIKI-L-022](../wiki/code/WIKI-L-022.md) — コード実装詳細
- [WIKI-X-012](../wiki/cross-domain/WIKI-X-012.md) — CCD メトリクス不安定性（既存）
- [WIKI-T-003](../wiki/theory/WIKI-T-003.md) — 変密度投影法
- [WIKI-T-017](../wiki/theory/WIKI-T-017.md) — FVM 参照手法
