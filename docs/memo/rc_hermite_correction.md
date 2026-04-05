# Rhie-Chow 高次補正：CCD p'' による追加コストゼロの O(h⁴) 化

## 1. 動機

前稿 (`rc_ccd_high_order_correction.md`) の Richardson 補正は CCD で p''' を追加計算する必要があった（2回/2D）。
CCD は `differentiate()` 1回で d1=p' と d2=p'' を同時に返すため、
p'' を活用すれば**追加コストゼロ**で同等以上の精度改善が可能である。

本稿では 3 つのアプローチを検討し、最終的に **d2fd 方式**を推奨する。

## 2. アプローチ A: Hermite 補間（理論的に最良、実用上不安定）

### 2.1 フェイス勾配（p の Hermite 補間微分）

p(x) の Hermite 補間を (p_P, p'_P) と (p_E, p'_E) の 4 条件で構築し、
x_f = (x_P + x_E)/2 で微分を評価する:

$$
(\nabla p)_f^{\rm H} = \frac{3(p_E - p_P)}{2h} - \frac{p'_P + p'_E}{4}
$$

**導出:** 3次 Hermite 基底 $h_{00}, h_{10}, h_{01}, h_{11}$ の微分を $t=1/2$ で評価すると
$h'_{00} = -3/2,\; h'_{10} = -1/4,\; h'_{01} = 3/2,\; h'_{11} = -1/4$。

**Taylor 展開:**

$$
(\nabla p)_f^{\rm H} = p'(x_f) - \frac{h^4}{1920}p^{(5)}(x_f) + O(h^6)
$$

### 2.2 セル中心平均（p' の Hermite 補間）

p'(x) の Hermite 補間を (p'_P, p''_P) と (p'_E, p''_E) の 4 条件で構築し、
x_f で値を評価する:

$$
\overline{(\nabla p)}_f^{\rm H} = \frac{p'_P + p'_E}{2} + \frac{h}{8}(p''_P - p''_E)
$$

**Taylor 展開:**

$$
\overline{(\nabla p)}_f^{\rm H} = p'(x_f) - \frac{h^4}{384}p^{(5)}(x_f) + O(h^6)
$$

### 2.3 Hermite ブラケット

$$
(\nabla p)_f^{\rm H} - \overline{(\nabla p)}_f^{\rm H}
= \frac{h^4}{480} p^{(5)}(x_f) + O(h^6)
$$

### 2.4 不安定性の原���

Hermite フェイス勾配 $3(p_E-p_P)/(2h)$ は標準の $(p_E-p_P)/h$ の **1.5 倍**。
これがRCの減衰特性を根本的に変えてしまい、時間発展で発散する（N=32: step 289, N=64: step 343 で BLOWUP）。
壁境界での CCD d2 精度低下 (O(h^{2.5})) も一因。

**結論:** 理論的に最小の O(h⁴) 係数 (1/480) を持つが、実用上は不安定。

## 3. アプローチ B（推奨）: d2fd — CCD d2 の FD による p''' 推定

### 3.1 着想

標準 RC ブラケットの構造��一切変えず、CCD d2 (= p'') の**隣接差分**で p''' をフェイスで��定:

$$
p'''_f \approx \frac{p''_R - p''_L}{h}
$$

### 3.2 補正式

標準ブラケットに加算するだけ:

$$
\text{bracket}_{\rm d2fd} = \underbrace{(\nabla p)_f - \overline{(\nabla p)}_f}_{\text{standard}} + \frac{h}{12}(p''_R - p''_L)
$$

### 3.3 Taylor 展開

$$
\frac{h}{12}(p''_R - p''_L) = \frac{h}{12}\left[h\,p''' + \frac{h^3}{24}p^{(5)} + \cdots\right]
= \frac{h^2}{12}p''' + \frac{h^4}{288}p^{(5)} + O(h^6)
$$

標準ブラケット $= -h^2/12\,p''' - h^4/480\,p^{(5)} + O(h^6)$ と合わせて:

$$
\text{bracket}_{\rm d2fd} = h^4\left(-\frac{1}{480} + \frac{1}{288}\right)p^{(5)} + O(h^6)
= \frac{h^4}{720}\,p^{(5)} + O(h^6)
$$

### 3.4 安定性

- **標準フェイス勾配 $(p_E-p_P)/h$ を変えない** → チェッカーボード減��がそのまま保持
- **標準平均 $\frac{1}{2}(p'_P+p'_E)$ を変えない** → RC の安定構造が不変
- 加算する補正 $h/12 \cdot (p''_R - p''_L)$ は滑らかな場で $O(h^2)$、チェッカーボード場でも標準ブラケットの $O(1)$ に比べて小さい

## 4. 全方式の比較

| 方式 | ブラケット精度 | O(h⁴) 係数 | 追加 CCD | 安定性 | 推奨 |
|------|--------------|-----------|---------|--------|------|
| 標準（算術平均） | $O(h^2)$ | — | 0 | OK | baseline |
| Richardson (p''') | $O(h^4)$ | $1/120$ | 2回/2D | OK | |
| Hermite (p'') | $O(h^4)$ | $1/480$ | **0** | **BLOWUP** | NG |
| **d2fd (p'' FD)** | **$O(h^4)$** | **$1/720$** | **0** | **OK** | **推奨** |

d2fd は:
- O(h⁴) 係数が全方式中**最小** (1/720)
- 追加 CCD コスト**ゼロ**
- 実際の PPE ループで**安定**
- Richardson より寄生流れ低減が大きい (N=64: 4.24e-4 vs 4.29e-4)

## 5. 数値結果

### 5.1 ブラケット収束（周期 BC、$p = \cos 2\pi x \cos 2\pi y$）

| N | Standard | Richardson | Hermite | d2fd |
|---|----------|-----------|---------|------|
| 16 | 7.89e-2 | 1.22e-3 | 3.08e-4 | **2.05e-4** |
| 32 | 2.01e-2 | 7.74e-5 | 1.94e-5 | **1.29e-5** |
| 64 | 5.04e-3 | 4.86e-6 | 1.22e-6 | **8.10e-7** |
| 128 | 1.26e-3 | 3.04e-7 | 7.60e-8 | **5.07e-8** |

全 O(h⁴) 方式で slope = 4.00。d2fd が全 N で最小ノルム。

### 5.2 静止液滴（400 ステップ）

| N | Mode | ‖u‖∞ | Δp err | 安定 |
|---|------|------|--------|------|
| 32 | std | 2.51e-2 | 0.58% | OK |
| 32 | rich | 2.55e-2 | 2.44% | OK |
| 32 | herm | BLOWUP | — | NG |
| 32 | **d2fd** | **2.49e-2** | **0.42%** | OK |
| 64 | std | 5.49e-4 | 1.23% | OK |
| 64 | rich | 4.29e-4 | 1.23% | OK |
| 64 | herm | BLOWUP | — | NG |
| 64 | **d2fd** | **4.24e-4** | 1.23% | OK |

## 6. 実装

```python
# In RC face velocity loop (per axis):
dp_cell, d2p_cell = ccd.differentiate(p, axis)  # already computed
# ... standard bracket computation ...
# Add d2fd correction:
bracket += (h / 12.0) * (d2p_R - d2p_L)
```

1 行の加算のみ。壁境界では CCD d2 が O(h^{2.5}) に落ちるが、
標準 RC の壁処理 (one-sided FD for dp_cell) と独立であり、
実験では安定に動作している。
