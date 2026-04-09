# CLS 再初期化 + 移流の質量保存補正

Date: 2026-04-09
Status: IMPLEMENTED
Related: reinitialize.py, advection.py, builder.py, exp11_6

---

## 1. 問題

CLS 再初期化方程式（§5c, eq:cls_reinit_split）:

$$
\frac{\partial\psi}{\partial\tau} + \nabla\cdot[\psi(1-\psi)\hat{n}] = \nabla\cdot(\varepsilon\nabla\psi)
$$

**連続形では保存形**（両辺が発散形）。壁面/周期 BC で $\int\psi\,dV = \text{const}$ が成立する。

しかし現在の `Reinitializer.reinitialize()` では質量が失われる。原因は3つ:

1. **離散化誤差** — CCD の離散発散が発散定理を厳密に満たさない
2. **`clip(q, 0, 1)`** — 各擬似時間ステップ後の切り落としが質量を破壊
3. **BC 境界フラックス** — 壁面でのフラックス零条件が近似的にしか成立しない

## 2. 実験データ

Single vortex テスト (N=64, DCCD ε_d=0.05, T=8.0):

| reinit 頻度 | L₂ | L∞ | 質量誤差 |
|:-----------:|:-------:|:-------:|:--------:|
| 10 step 毎 | 1.90e-1 | 8.46e-1 | 1.78e-3 |
| 5 step 毎  | 2.00e-1 | 8.71e-1 | 4.54e-3 |
| 2 step 毎  | 2.20e-1 | 9.38e-1 | 2.00e-2 |
| 毎 step    | 2.29e-1 | 9.27e-1 | 3.85e-2 |

**再初期化頻度を上げると質量誤差が 22 倍悪化** (1.78e-3 → 3.85e-2)。
形状誤差 (L₂, L∞) も単調に悪化。

## 3. 既存手法: グローバルスケーリング (exp11_8)

CLS 保存型再マッピング（格子リフレッシュ時）で使用:

```python
psi = psi * (M_old / M_new)
```

**問題点:** ψ≈0, ψ≈1 のバルク領域も一律スケーリングされるため、
界面が太る（interface smearing）。再初期化は界面を「鋭くする」操作なので、
スケーリングで「にじませる」のは目的と矛盾する。

## 4. 提案手法: 界面重み付き質量補正

```python
def reinitialize(self, psi):
    xp = self.xp
    q = xp.copy(psi)
    M_old = float(xp.sum(q))

    for _ in range(self.n_steps):
        # Stage 1: compression (既存)
        # Stage 2: diffusion   (既存)

    # ── 質量保存補正 ──
    M_new = float(xp.sum(q))
    w = 4.0 * q * (1.0 - q)       # 重み: ψ=0.5で最大(=1), ψ=0,1で零
    W = float(xp.sum(w))
    if W > 1e-12:
        q = q + ((M_old - M_new) / W) * w
    q = xp.clip(q, 0.0, 1.0)

    return q
```

## 5. グローバルスケーリング vs 界面重み付き補正

| 項目 | グローバル `ψ *= M_old/M_new` | 界面重み `ψ += δM/W · w(ψ)` |
|------|:---:|:---:|
| 補正の空間分布 | 一様（全領域） | 界面近傍に集中 |
| バルク ψ≈0,1 への影響 | あり（界面太り） | なし（w=0） |
| 再初期化の目的との整合 | 矛盾（にじみ） | 整合（界面のみ修正） |
| 実装の複雑さ | 1行 | 4行 |
| clip 後の再誤差 | 小（スケーリング比が1に近い場合） | 極小（補正量が微小） |

## 6. 理論的根拠

Olsson & Kreiss (2005), Olsson, Kreiss & Zahedi (2007) の CLS 法では、
再初期化方程式に Lagrange 乗数項 λ(τ)·f(ψ) を追加:

$$
\frac{\partial\psi}{\partial\tau} + \nabla\cdot[\psi(1-\psi)\hat{n}] = \nabla\cdot(\varepsilon\nabla\psi) + \lambda(\tau) f(\psi)
$$

ここで f(ψ) は界面に集中する重み関数。λ(τ) は ∫ψ dV = const を満たすよう決定。

提案手法は、この Lagrange 乗数法の **事後的（post-hoc）近似**:
- f(ψ) = 4ψ(1-ψ) と同じ基底を使用
- 各擬似時間ステップではなく全 n_steps 後にまとめて補正
- 厳密な PDE レベルの保存ではなく、積分値の帳尻合わせ

PDE レベルで λ を各ステップに組み込む方法がより厳密だが、
事後補正でも実用上十分な精度が得られるか、実験で検証する必要がある。

## 7. 実装箇所

- **ファイル:** `src/twophase/levelset/reinitialize.py`
- **メソッド:** `Reinitializer.reinitialize()` (L88-109)
- **変更量:** 6行追加
- **既存ステップへの影響:** なし（for ループ内は変更なし）

## 8. 実装結果 (2026-04-09)

### 最終設計: 移流 + 再初期化の両方に質量補正

reinit のみに補正を入れると、修正前は reinit が偶然 +21.57 の質量を追加して
adv の -38.48 の損失を相殺していたことが判明（N=128 Zalesak）。
reinit 補正で相殺が消え、Zalesak の mass_err が悪化。

**根本原因:** DCCD フィルタの 2 階差分と TVD-RK3 各ステージの clip(0,1) が
保存形の発散定理を破壊。移流にも同一補正を適用して解決。

### 実装

- `reinitialize.py`: n_steps 後に w=4ψ(1-ψ) 重み付き補正（全ケース適用）
- `advection.py`: `mass_correction=True` フラグで有効化（デフォルト False）
- `builder.py`: CLS 移流構築時に `mass_correction=True` を指定

### 実験結果

| テスト | N | L₂ (前) | L₂ (後) | mass (前) | mass (後) |
|-------|---:|:-------:|:-------:|:---------:|:---------:|
| Zalesak | 64 | 9.67e-2 | 9.96e-2 | 5.55e-3 | **O(1e-15)** |
| Zalesak | 128 | 9.28e-2 | 9.34e-2 | 1.08e-3 | **O(1e-15)** |
| Zalesak | 256 | 7.62e-2 | 7.62e-2 | 6.01e-5 | **O(1e-15)** |
| Vortex | 64 | 1.90e-1 | 1.91e-1 | 1.78e-3 | **O(1e-15)** |
| Vortex | 128 | 1.73e-1 | 1.73e-1 | 1.63e-3 | **O(1e-15)** |
| Vortex | 256 | 1.43e-1 | 1.43e-1 | 7.10e-5 | **O(1e-15)** |

質量誤差: 10⁻³〜10⁻⁵ → **機械精度 10⁻¹⁵**。形状誤差 L₂ はほぼ不変。
141/141 テスト PASS（pre-existing failure 1件は変更と無関係）。
