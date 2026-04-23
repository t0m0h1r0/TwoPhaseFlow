# paper/archive/v1_pre_sp_core — SP-core 化以前の論文素材

## 目的

本ディレクトリは、2026-04-23..24 の §2-§10 SP-core 再構築（CHK-182..190）と post-merge 再レビュー（CHK-191..193）で
本編から退避されたが **将来再利用の可能性があるコンテンツ** を git 履歴とともに保存する。

退避の二原則:

1. 機能的 single-source-of-truth を本編で保つ（重複記述は本編から除去）
2. 退避物は `%!TEX root = ../../main.tex` ヘッダを維持し、再 `\input` のみで復活可能

## ディレクトリ構成

```
v1_pre_sp_core/
├── README.md                       # 本ファイル
├── 04d_dissipative_ccd.tex         # 旧 §4.4 DCCD 解説（SP-G 以前）
├── 13_legacy_benchmarks.tex        # 旧 §13 の benchmarks stub
├── appendix_grid_impl.tex          # 旧 付録 E grid_impl（app:grid_impl ラベル）
└── snippets/                       # 削除された本文断片
    ├── h01_recap_08_2.tex          # §8.4.1 H-01 診断再掲（§4.5 と完全重複）
    ├── fccd_matrix_redef_07c.tex   # §7c の FCCD 行列再定義（§4e と重複）
    ├── pressure_filter_warnbox_08b.tex  # §8b inline warnbox（§8c 完全版と重複）
    └── level3_activation_note.tex  # §5 の「CHK にキュー化」内部露出文
```

## 退避ファイルの詳細

### 04d_dissipative_ccd.tex（314 LOC, CHK-185 で吸収）

- **退避理由**: CHK-185（Phase 1c, 2026-04-23）で `04c_dccd_derivation.tex` に SP-G §1-§5 として完全吸収された。
- **吸収先**: `paper/sections/04c_dccd_derivation.tex` の §4.4 Dissipative CCD 派生
- **保持 labels**: `04c` 側で phantomsection として温存（`sec:dissipative_ccd`, `sec:dccd_motivation`, `sec:dccd_bc`, `sec:dccd_conservation`, `sec:dccd_filter_theory`, `eq:dccd_filter`, `eq:dccd_transfer`）— §7, §8, §10b, §11, §12d 等から活発に参照中
- **再活性化条件**: DCCD の派生過程を **SP-G とは別の独立議論** として再掲する必要が生じた場合

### 13_legacy_benchmarks.tex（7 LOC stub）

- **退避理由**: 内容は `paper/sections/12h_error_budget.tex` に移動済、main.tex で `\input` なし
- **再活性化条件**: 旧 §13 の独立章として benchmark 章を復活する場合

### appendix_grid_impl.tex

- **退避理由**: active `\input` なし、`app:grid_impl` ラベルへの参照ゼロ（`app:grid_ale` とは別ラベル、混同の可能性あり）
- **代替**: grid ALE 実装は `appendix_numerics_solver_s1.tex:52` `\label{app:grid_ale}` 側で記述
- **再活性化条件**: grid_impl 系の独立付録を復活する場合

## snippets/ の断片退避

### h01_recap_08_2.tex

- **元の位置**: `paper/sections/08_2_fccd_bf.tex` §8.4.1 "H-01 診断の再掲と FCCD 救済" subsection
- **退避理由**: §4.5 `04e_fccd.tex` の H-01 一次定義と完全重複（E-030 Exp-1 の 884 数値まで再掲）
- **本編の代替**: §8.4 冒頭に 3 行の橋渡し段落 + `§\ref{sec:fccd_motivation_h01}` cross-ref

### fccd_matrix_redef_07c.tex

- **元の位置**: `paper/sections/07c_fccd_advection.tex` L13 付近 + L152 付近
- **退避理由**: §4e の `eq:fccd_composite_matrix` 一次定義と同式を箱定義で再掲
- **本編の代替**: `\eqref{eq:fccd_composite_matrix}` 参照

### pressure_filter_warnbox_08b.tex

- **元の位置**: `paper/sections/08b_pressure.tex` L108-130 "圧力場へのフィルタ適用禁止" warnbox + 2 bullet
- **退避理由**: §8c `08c_pressure_filter.tex` の SP-J §4 完全版と内容重複
- **本編の代替**: 1 行の `§\ref{sec:dccd_pressure_filter_prohibition}` cross-ref

### level3_activation_note.tex

- **元の位置**: `paper/sections/05_time_integration.tex` L452-453
- **退避理由**: 本文中に「別 CHK にキュー化」という内部チケット参照が露出していた
- **本編の代替**: 削除（CHK トラッキングは ledger 側で管理）

## 再活性化手順

1. 目的のファイルを `paper/sections/` へ `git mv` で戻す
2. 本編で重複していた定義・段落を当該箇所から削除、退避ファイル側の `\label{}` を活性化
3. `paper/main.tex` の `\input` 配列に追加
4. `latexmk -xelatex main.tex` で整合性確認
5. phantomsection が対応先にある場合は除去（単一定義に統合）

## 追跡リンク

- [CHK-191](../../../docs/02_ACTIVE_LEDGER.md) — post-merge R-1..R-8 機械的修正
- [CHK-193](../../../docs/02_ACTIVE_LEDGER.md) — 本退避作業（narrative grade B → A）
- [WIKI-P-013](../../../docs/wiki/paper/WIKI-P-013.md) §6 Update log
