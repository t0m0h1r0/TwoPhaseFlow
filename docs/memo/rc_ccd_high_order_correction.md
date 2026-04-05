# Rhie-Chow 補正の CCD 高次精度化：O(h²) → O(h⁴)

## 1. 現状の精度制限

付録 M.4 eq:rc_detection_taylor より、RC 検出項（ブラケット）は:

$$
(\nabla p)_f - \overline{(\nabla p)}_f = -\frac{h^2}{12} p'''(x_f) + \mathcal{O}(h^4)
$$

| 項 | 定義 | テイラー展開 |
|----|------|-------------|
| $(\nabla p)_f$ | $(p_E - p_P)/h$ （フェイス直接差分） | $p'(x_f) + \frac{h^2}{24}p''' + \mathcal{O}(h^4)$ |
| $\overline{(\nabla p)}_f$ | $\frac{1}{2}[D^{(1)}_{\rm CCD}(p)_P + D^{(1)}_{\rm CCD}(p)_E]$ | $p'(x_f) + \frac{h^2}{8}p''' + \mathcal{O}(h^4)$ |

$p'(x_f)$ は相殺し、残差の主項は $-h^2/12 \cdot p'''(x_f)$。

**問題:** CCD セル中心微分は $\mathcal{O}(h^6)$ だが、算術平均でフェイス中点に補間すると $\mathcal{O}(h^2)$ に落ちる。RC 補正全体が $\mathcal{O}(\Delta t \cdot h^2)$ となり、CCD の高次精度を活かせない。

## 2. 提案：CCD p''' による Richardson 型補正

CCD は $d_1 = p'$, $d_2 = p''$ を同時に返す。$d_2$ を再度 CCD で微分すれば $p'''$ が $\mathcal{O}(h^6)$ で得られる。

フェイス中点値を算術平均で近似:

$$
\bar{p}'''_f = \frac{1}{2}(p'''_P + p'''_E) = p'''(x_f) + \mathcal{O}(h^2)
$$

### 補正後ブラケット

$$
\underbrace{(\nabla p)_f - \overline{(\nabla p)}_f}_{= -\frac{h^2}{12}p''' + \mathcal{O}(h^4)}
+ \frac{h^2}{12}\bar{p}'''_f
= \mathcal{O}(h^4)
$$

$h^2/12 \cdot \bar{p}'''_f$ の補正項自体が $\mathcal{O}(h^2)$ であり、主項 $-h^2/12 \cdot p'''$ を正確に打ち消す。

### 補正後 RC フェイス速度

$$
u_f = \bar{u}_f - d_f \left[
  (\nabla p)_f - \overline{(\nabla p)}_f + \frac{h^2}{12}\bar{p}'''_f
\right]
$$

RC 補正量: $\mathcal{O}(\Delta t \cdot h^2) \to \mathcal{O}(\Delta t \cdot h^4)$

## 3. CCD による計算コスト

| ステップ | CCD 呼び出し | 出力 |
|---------|-------------|------|
| 1. $p' = D^{(1)}_{\rm CCD}(p)$ | 既存（速度補正で使用済み） | $p'_i$ |
| 2. $p'' = D^{(2)}_{\rm CCD}(p)$ | 既存（ステップ 1 と同時取得） | $p''_i$ |
| 3. $p''' = D^{(1)}_{\rm CCD}(p'')$ | **追加 1 回/軸** | $p'''_i$ |
| 4. $\bar{p}'''_f = (p'''_P + p'''_E)/2$ | 算術平均（コスト無視可能） | フェイス値 |

追加コスト: 軸あたり CCD 1 回（$p''$ の微分）。2D で 2 回。

## 4. 陰的 RC 補正（PPE 左辺への組み込み）

現状の RC は前時刻圧力 $p^n$ を陽的に評価:

$$
u_f^{\rm RC} = \bar{u}_f^* - d_f [(\nabla p^n)_f - \overline{(\nabla p^n)}_f]
$$

**陰的定式化:** $p^n \to p^{n+1}$ として RC 補正を PPE 左辺に移す。

RC 補正済みフェイス速度の発散を PPE 右辺に代入すると、$p^{n+1}$ 依存項が生じる:

$$
\nabla_h^{\rm RC} \cdot \mathbf{u}^* = \nabla_h \cdot \bar{\mathbf{u}}^*
- \nabla_h \cdot \left( d_f \left[ (\nabla p^{n+1})_f - \overline{(\nabla p^{n+1})}_f \right] \right)
$$

PPE: $\nabla \cdot (1/\rho \nabla p^{n+1}) = (1/\Delta t) \nabla_h \cdot \bar{\mathbf{u}}^*$ の左辺に RC 項を移動:

$$
\underbrace{\nabla \cdot \frac{1}{\rho}\nabla p^{n+1}}_{\rm CCD\ Laplacian}
+ \underbrace{\frac{1}{\Delta t}\nabla_h \cdot \left(d_f [(\nabla p^{n+1})_f - \overline{(\nabla p^{n+1})}_f]\right)}_{\rm RC\ implicit\ correction}
= \frac{1}{\Delta t}\nabla_h \cdot \bar{\mathbf{u}}^*
$$

### CCD-PPE での実現可能性

CCD-PPE は Kronecker 積で大域行列 $L_{\rm CCD}$ を組み立てる。RC 陰的補正項は:

- $(\nabla p)_f$: 隣接ノード差分 → 帯行列（FD 的、既知構造）
- $\overline{(\nabla p)}_f$: CCD $D^{(1)}$ の算術平均 → CCD 行列の行平均

両者は既知の行列として $L_{\rm CCD}$ に加算可能。**追加の非零要素は発生しない**（CCD の帯幅内に収まる）。

## 5. 精度改善まとめ

| 定式化 | RC ブラケット精度 | 時間精度 | 実装難度 |
|--------|-----------------|---------|---------|
| 現行（陽的 FD フェイス差分） | $\mathcal{O}(h^2)$ | $\mathcal{O}(\Delta t)$（$p^n$ 使用） | 既存 |
| 提案 A: p''' Richardson 補正 | $\mathcal{O}(h^4)$ | $\mathcal{O}(\Delta t)$ | CCD 1 回/軸 追加 |
| 提案 B: 陰的 RC + p''' 補正 | $\mathcal{O}(h^4)$ | $\mathcal{O}(\Delta t^2)$（IPC 内） | PPE 行列修正 |

## 6. 表面張力 Balanced-Force 項への適用

同じ論理が eq:rc-face-balanced の $(\mathbf{f}_\sigma)_f - \overline{(\mathbf{f}_\sigma)}_f$ にも適用可能:

$$
(\mathbf{f}_\sigma)_f - \overline{(\mathbf{f}_\sigma)}_f
= -\frac{h^2}{12}(\kappa/We)^{(3)}\psi'''(x_f) + \mathcal{O}(h^4)
$$

CCD で $\psi'''$ を計算し同様の Richardson 補正を加えれば、BF 補正項も $\mathcal{O}(h^4)$ に改善。
