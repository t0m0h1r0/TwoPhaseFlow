# CHK-RA-PAPER-1-11-STRICT-001 / Chapter 1 Review

対象:
- `paper/sections/01_introduction.tex`
- `paper/sections/01b_classification_roadmap.tex`

## Round 1: 厳正レビュー

判定: MAJOR あり。

指摘:
- MAJOR: 冒頭が `pressure-jump`, `affine jump`, `Hodge`, `V6/V7/V9`, `slope` などを一度に提示しており、読者が「何を解く論文か」を理解する前に実装語彙へ押し込まれる。技術内容は必要だが、導入では問題、設計原理、検証済み範囲の順に再構成すべき。
- MAJOR: `projection-native`, `face closure`, `pressure-jump face data`, `moving-interface`, `sub-system`, `primitive`, `結合 stack` などの英語由来語が残り、日本語論文としての入口を弱くしている。専門語を残す場合も、日本語を主にして意味が読める形へ統一すべき。
- MAJOR: ロードマップで「7 ステップ統合実装は Part 2 各章に分散」と書いており、第11章で統合アルゴリズムを提示する構成と矛盾する。第11章を統合の入口として明示する必要がある。
- MAJOR: 検証済み範囲と今後の検証対象の線引きはあるが、`検証ゲート` や版管理的な言い方が導入章に残り、研究の試行錯誤を論文本文へ持ち込んでいる印象を与える。
- MINOR: `sharp phase volume`, `observed slope`, `Predictor--PPE--Corrector` など、読者に不要な英語表現が図注・失敗例説明に残る。

対応:
- 冒頭の技術中核段落を、(1) 面上の共通離散構造、(2) CSF/BF 縮約経路、(3) 分相圧力ジャンプ PPE、(4) 検証済み範囲、の順に再構成した。
- `pressure-jump`, `affine jump`, `moving-interface`, `sub-system`, `primitive`, `stack`, `face closure`, `pressure-jump face data`, `slope`, `sharp phase volume` を日本語主語彙へ置換した。
- 第11章 `sec:algorithm` を統合アルゴリズムの入口として参照し、Part 2 は各演算子の詳細章として説明する構成へ修正した。
- 未検証範囲は「今後の検証対象」とし、版管理・試行錯誤を連想させる表現を削った。

## Round 2: 再レビュー

判定: MAJOR なし。

確認:
- 第1章内の重点語彙スキャンで `pressure-jump`, `affine jump`, `face closure`, `pressure-jump face data`, `moving-interface`, `sub-system`, `primitive`, `projection-native`, `face-space contract`, `結合 stack`, `検証ゲート`, `slope`, `sharp phase volume`, `sec:solver_integration` は検出されない。
- 第11章への参照は既存ラベル `sec:algorithm` を使用しており、未定義ラベルを増やしていない。
- ナラティブは「問題設定 → 用語固定 → 設計原理 → 検証済み範囲 → 失敗例 → ロードマップ」の順に整理された。

残留リスク:
- `face cochain` は初出の括弧書きとして残した。本文では日本語の「面共鎖」を主語彙として使っており、現時点では MAJOR ではない。
