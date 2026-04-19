---
ref_id: WIKI-L-019
title: "config_io.py パースバグ: snap_interval / reinit_eps_scale 欠落"
domain: code
status: CLOSED
superseded_by: null
sources:
  - path: src/twophase/simulation/config_io.py
    git_hash: 251e631
    description: bug fix commit — 2 fields added to _parse_run()
consumers:
  - domain: experiment
    usage: all ch13 experiments re-run after fix (exp13_10..13_17)
depends_on:
  - "[[WIKI-X-016]]: reinit dispatch policy (reinit_eps_scale=1.4)"
compiled_by: Claude Sonnet 4.6
verified_by: re-run of exp13_10..13_15 with correct parameters
compiled_at: "2026-04-19"
---

# config_io.py パースバグ: snap_interval / reinit_eps_scale 欠落

## バグ概要

`src/twophase/simulation/config_io.py` の `_parse_run()` に 2 つのフィールドが未実装で，
YAML に記述した値が **silently 無視** されていた．

### 欠落していたフィールド

| フィールド | YAML 設定値 | バグ時の実効値 | 影響 |
|-----------|------------|--------------|------|
| `snap_interval` | 1.4（etc.） | **0.1**（ハードコード） | 過剰スナップショット生成（メモリ・計算時間の無駄） |
| `reinit_eps_scale` | 1.4 | **1.0**（デフォルト） | ξ-SDF 界面幅が設計値より 28% 狭く，VolCons 誤差が増大 |

`reinit_eps_scale=1.0` で動作した場合，CHK-139 で特定した「eps_scale=1.4 が安定化に必要」
という知見が実験で反映されていなかった．

---

## 修正

**commit 251e631** — `_parse_run()` に 2 行追加:

```python
# config_io.py _parse_run() 内
snap_interval=_opt_float(d.get("snap_interval", 0.1)),
reinit_eps_scale=float(d.get("reinit_eps_scale", 1.0)),
```

デフォルト値（0.1 / 1.0）はバグ時の実効値と同じなので，既存 YAML に `snap_interval:` /
`reinit_eps_scale:` を書いていなかった実験への後方互換性は維持される．

---

## 影響範囲と対処

### 影響を受けた実験

| 実験 | 設定 snap_interval | 設定 eps_scale | 対処 |
|------|------------------|---------------|------|
| exp13_10..13_15 (CHK-141 関連) | 各種 | 1.4 | **全再実行済み** |
| exp13_16 (ρ=1000 安定確認) | 0.25 | 1.4 | 再実行済み |
| exp13_17 (水-空気 GFM) | 2.0 | 1.4 | fix 後に実行 |

### CHK-141 への影響

eps_scale が 1.0 → 1.4 に変更されたことで:
- `reinit_every=4` だけでなく `reinit_every=20` でも T=1 完走 (VolCons 改善)
- `reinit_every=100` と `disabled` は依然としてブローアップ

---

## 教訓

`RunCfg` に新フィールドを追加するときは，同一コミット内で `_parse_run()` への
`d.get(...)` 行を追加すること．型アノテーション付きの dataclass フィールドだけ
追加してパーサを更新しないと，デフォルト値で動作し設定値が無効になる（本バグと同じパターン）．

推奨チェック: `RunCfg` のフィールドと `_parse_run()` の `d.get()` キー一覧を
機械的に突き合わせるテストを追加する（将来課題）．
