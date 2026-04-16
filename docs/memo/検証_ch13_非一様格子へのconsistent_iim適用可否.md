# 検証メモ：13章問題への consistent_iim 適用可否

日付: 2026-04-16  
対象: `experiment/ch13/run.py` の capillary-wave probe 系

## 0. 実施内容
以下3ケースを remote で実行。

1. `exp13_01_capillary_wave_probe`（既存, legacy）
2. `exp13_01_capillary_wave_probe_iim`（新規, `reproject_mode=consistent_iim`）
3. `exp13_01_capillary_wave_probe_iim_tuned`（新規, CFL低減 + reinit_every=2 + rebuild_freq=100）

## 1. 実測サマリ
`data.npz` からの主要値:

1. legacy
- `n_steps=49`, `t_end=1.938e-03`
- `KE_end=1.262e+06`
- BLOWUP あり

2. consistent_iim
- `n_steps=50`, `t_end=1.963e-03`
- `KE_end=1.401e+06`
- BLOWUP あり（ステップはほぼ同等、時間はわずかに延伸）

3. consistent_iim tuned
- `n_steps=121`, `t_end=4.711e-03`
- `KE_end=1.394e+06`
- BLOWUP あり（ただし生存時間は約2.4倍）

## 2. 判定
結論: **13章 capillary-wave（alpha=2）へ「問題なく適用」は現時点で不可。**

- `consistent_iim` 単体で破綻回避は未達
- tuned で延命はできるが，目標時刻までの安定到達は未達

## 3. 解釈
1. `consistent_iim` は再投影起因の悪化を抑える方向には働く。
2. ただし13章 capillary-wave では，破綻主因が再投影だけでなく
   高曲率/毛管駆動の他要素（PPE結合・時間刻み・界面再構成）にもある。
3. 実問題適用前に，capillary-wave 系の専用安定化（特に高σ条件）を別途詰める必要がある。

## 4. 次ステップ
1. `exp13_01` 向けに `cfl`/`rebuild_freq`/`reinit_every` の系統スイープを追加
2. `consistent_iim` の受理閾値と backtracking スケールを capillary条件で適応化
3. `consistent_gfm` 実体化後に再比較

