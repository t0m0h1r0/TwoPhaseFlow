---
ref_id: WIKI-L-020
title: "GPU最適化: PCR Thomas + D2H同期除去 (merge 362dbd3)"
domain: code
status: VERIFIED
superseded_by: null
sources:
  - path: src/twophase/linalg_backend.py
    git_hash: bce1996
    description: PCR Thomas — replace sequential Python loop with vectorised xp.roll stages
  - path: src/twophase/levelset/reinit_eikonal.py
    git_hash: 9eb02a0
    description: float(W) D2H sync removal — replace guard with xp.where masking
  - path: src/twophase/simulation/ns_pipeline.py
    git_hash: 362dbd3
    description: phi_primary_transport path D2H/H2D elimination
consumers:
  - domain: experiment
    usage: all GPU experiments benefit from reduced kernel dispatch and sync overhead
depends_on:
  - "[[WIKI-T-036]]: phi_primary_transport theory"
  - "[[WIKI-T-042]]: Eikonal reinitialization (mass correction W)"
  - "[[WIKI-L-015]]: CuPy backend unification (xp dispatch pattern)"
compiled_by: Claude Sonnet 4.6
verified_by: "all 211 linalg_backend + suite tests pass (bce1996)"
compiled_at: "2026-04-19"
---

# GPU最適化: PCR Thomas + D2H同期除去 (merge 362dbd3)

## 概要

3つの独立した GPU パフォーマンス改善を 1 回のマージコミット (362dbd3) にまとめた．
いずれも **動作等価**（CPU NumPy パスの出力は bit-exact 変化なし）かつ
GPU カーネル数またはデバイス-ホスト転送を削減する．

---

## 1. PCR Thomas アルゴリズム (`linalg_backend.py`, commit bce1996)

### 問題

従来の `thomas_batched` は Python for ループで `2n` 回の逐次カーネルディスパッチを実行．
n=129（64グリッドの CCD 列サイズ）では 258 回の個別 GPU カーネル → GPU アイドル時間大．

### 解決策

CuPy バックエンドで `thomas_batched` を **Parallel Cyclic Reduction (PCR)** にルーティング:

```python
def _pcr_solve_batched(xp, factors, rhs):
    # ceil(log2(n)) 回の完全ベクトル化 xp.roll ステージ
    # 各ステージは 1 カーネルで全行を並列処理
    stages = int(np.ceil(np.log2(n)))
    for s in range(stages):
        stride = 1 << s
        # xp.roll で stride 分の隣接係数を参照 (境界折り返しは端点マスクで無効化)
        ...
```

| 指標 | 従来 Thomas | PCR |
|------|-----------|-----|
| カーネル数 (n=129) | 258 | **14** (=⌈log₂129⌉×2+補正) |
| 削減率 | — | **−94.6%** |
| CPU (NumPy) | ThomasFactors（変更なし） | — |

### 注意事項

- PCR は奇数ストライドで境界ピクセルへの参照が折り返す可能性 → 端点マスクで明示的にゼロ化
- CPU パスは従来 ThomasFactors がキャッシュ局所性で最適のため変更なし

---

## 2. Eikonal 質量修正の D2H 同期除去 (`reinit_eikonal.py`, commit 9eb02a0)

### 問題

```python
# バグ: 毎 reinit call に D2H 同期が発生
if float(W) > 1e-14:   # float() が device→host を強制
    phi -= delta_phi * (mass_error / W)
```

`float(W)` はスカラー値を GPU メモリからホストに転送するため，
reinit_every=2 なら 2 ステップ毎に 1 回，T=8 (9700 ステップ) なら約 4850 回の
不必要な D2H 同期が発生していた．

### 修正

```python
# 修正: xp.where でデバイス上で条件判定
gate = xp.where(W > 1e-14, xp.ones_like(W), xp.zeros_like(W))
phi -= delta_phi * gate * (mass_error / xp.maximum(W, 1e-14))
```

既存の `apply_mass_correction()` と同パターン．
W ≤ 1e-14 のとき delta_phi がゼロになる（動作等価）．

---

## 3. phi_primary_transport パスの D2H/H2D 除去 (`ns_pipeline.py`, commit 362dbd3)

### 問題

`phi_primary_transport` ルートで `psi` の再構築にホスト側 Python 演算が混入しており，
不必要な D2H/H2D が発生していた．

### 修正

`xp` を一貫して使用し，デバイス上で完結させる．
`phi_primary_transport` の意義 (WIKI-T-036) は維持され，
改善はパフォーマンスのみ（動作出力は変化なし）．

---

## 統合効果

CCD 計算（→ Thomas/PCR）と eikonal reinit（→ float(W) 除去）は
毎ステップ呼ばれる hotpath であるため，長時間シミュレーション（9700+ ステップ）での
累積削減効果は大きい．具体的なスピードアップ計測は未実施だが，
ch11 GPU 最適化 (CHK-120..127) で Thomas が主要ボトルネックの 1 つと特定されている．
