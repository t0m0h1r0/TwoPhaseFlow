# §1–§3 Peer Review Retry (2026-04-25)

対象: `paper/main.tex` の §1–§3  
視点: reject-oriented external reviewer  
対象ファイル: `01_introduction.tex`, `01b_classification_roadmap.tex`, `02_governing.tex`, `02b_surface_tension.tex`, `02c_nondim_curvature.tex`, `03_levelset.tex`, `03b_cls_transport.tex`, `03c_levelset_mapping.tex`, `03d_ridge_eikonal.tex`

## Verdict

**Major revision required.**

§1–§3 の大半は前回レビューより明確に改善されている。特に §1 の引用欠落、§2c の曲率不変定理の適用域明示、§3c のロジット逆変換の整理は前進している。一方で、**§3.4 Ridge--Eikonal 節だけは依然として査読停止要因**が残る。現状の主な問題は、(i) 章順序を破る forward dependency、(ii) 後段で未回収の検証約束、(iii) downstream algorithm の説明不整合である。

## Findings

### Major 1 — §3.4 が「第1部の基礎章」として自立していない

- **File**: `paper/sections/03d_ridge_eikonal.tex:25`
- **Quote**: `以下の章を既習前提として forward-reference する`
- **Problem**:
  §3.4 自身が、読解に `§4`, `§6`, `§7`, `§12` を既習前提として要求している。これは `paper/main.tex:21` で §1–§3 が「定式化：支配方程式と界面表現」として先行配置されている章構成と噛み合わない。注意書きで dependency を宣言している点は誠実だが、査読者には「この節は今ここに置くべきではない」と読まれる。
- **Why it matters**:
  第1部だけを通読した読者が §3.4 で足止めされる。基礎章の narrative contract を壊しており、章順序そのものへの疑義に繋がる。
- **Recommendation**:
  §3.4 を後段（少なくとも §6–§7 以降）へ移すか、本章では概念紹介の 1–2 ページに圧縮し、D1–D4 や実装校正値は後段へ送るべき。

### Major 2 — §3.4 の「後段で検証済み」主張が本文中で回収されていない

- **Files**: `paper/sections/03d_ridge_eikonal.tex:33`, `paper/sections/03d_ridge_eikonal.tex:40`, `paper/sections/03d_ridge_eikonal.tex:172`, `paper/sections/03d_ridge_eikonal.tex:186`, `paper/sections/03d_ridge_eikonal.tex:258`
- **Quotes**:
  - `§~\ref{sec:verification}（検証ベンチマーク）——Morse 遷移・再構成誤差の数値的検証`
  - `Morse 遷移時間スケール \tau_M——§~\ref{sec:verification} 検証ベンチマークで測定`
  - `推奨値 \sigma\in[2,4]（§~\ref{sec:verification} 校正）`
- **Problem**:
  後段の検証章を確認した限り、`tau_M`、`Morse 遷移`、`\sigma\in[2,4]` を回収する subsection が見当たらない。少なくとも `paper/sections/11_component_verification.tex:1`、`paper/sections/12_verification.tex:1`、`paper/sections/13_benchmarks.tex:1` には対応する記述がない。
- **Why it matters**:
  査読者には「将来あるはずの実証を先に仮置きした」と見える。特に `\tau_M` は離散時間刻み条件に直結するため、未検証のまま設計値として本文に置くのは危険。
- **Recommendation**:
  実証が未掲載なら「heuristic」「working hypothesis」に格下げする。もし実証済みなら、対応する検証 subsection を後段に実在させ、本文から明示的にリンクすべき。

### Major 3 — Ridge--Eikonal 後の handoff 記述が実際のアルゴリズム説明と矛盾する

- **Files**: `paper/sections/03d_ridge_eikonal.tex:218`, `paper/sections/07_advection.tex:12`, `paper/sections/10_full_algorithm.tex:97`
- **Quotes**:
  - `再構成後は既存の FCCD 面中心移流（§~\ref{sec:advection}）で鋭利な界面追跡を再開する`
  - `本章では CLS 移流・再初期化...FCCD による BF 整合移流 Option B/C は §~\ref{sec:fccd_advection}`
  - `Step 1 & CLS \psi 移流 & TVD-RK3 + DCCD`
- **Problem**:
  §3.4 は「界面追跡の既定 handoff」が FCCD であるかのように書くが、後段の本体フローでは **CLS `\psi` 移流の既定は DCCD** であり、FCCD Option B/C は別の拡張経路として導入されている。現状の文面だと、Ridge--Eikonal がどの transport loop に戻るのかが誤読される。
- **Why it matters**:
  査読者は「結局、界面は `\psi` を DCCD で運ぶのか、`\phi` を FCCD で運ぶのか」を判別できない。方法論の核である state variable / transport operator chain が曖昧になる。
- **Recommendation**:
  `Ridge--Eikonal -> \phi reconstruction -> \psi rebuild -> Step 1 (TVD-RK3 + DCCD)` のように、実際の main pipeline に合わせて書き直すべき。

### Minor 1 — HFE 参照先が導入節を指しており、定式化節を指していない

- **File**: `paper/sections/02b_surface_tension.tex:23`
- **Quote**: `GFM は HFE〔Hermite 場延長法；§~\ref{sec:intro}〕と併用で §~\ref{sec:field_extension} に現れる`
- **Problem**:
  HFE の正式な定式化は `§~\ref{sec:field_extension}` で与えられるのに、ここでは `sec:intro` を参照している。導入節で語彙として触れたことと、手法の定義を与えたことは別である。
- **Recommendation**:
  HFE の参照は `sec:field_extension` に一本化した方がよい。

### Minor 2 — 退化臨界点への「gauss ホワイトノイズ」安全策は再現性の説明が不足

- **File**: `paper/sections/03d_ridge_eikonal.tex:163`
- **Quote**: `微小な gauss ホワイトノイズを付与して退化を解消する`
- **Problem**:
  トポロジー判定の分岐点に乱数摂動を入れる設計なのに、seed 固定、感度解析、run-to-run invariance の説明がない。決定論的 CFD 法としては査読で必ず「再現可能なのか」を問われる。
- **Recommendation**:
  乱数摂動を残すなら seed と sensitivity envelope を明記する。理想的には deterministic tie-breaker に置き換えるべき。

### Minor 3 — 本文に著者メモ調の to-do 文体が残っている

- **File**: `paper/sections/03b_cls_transport.tex:43`
- **Quote**: `...で実際の保存性を定量確認すること`
- **Problem**:
  叙述論文の本文としては不自然で、執筆メモが残っているように読める。読者に向けた記述なら「...で確認した」または「...で確認する」に揃えるべき。
- **Recommendation**:
  imperative を declarative に統一する。

## Overall Assessment

§1–§3 のうち、**§1–§3.3 は accept-with-minor にかなり近い**。今回の reject risk はほぼ §3.4 に集中している。したがって修正優先度は明確で、次の順に対処すればよい。

1. §3.4 の章配置または分量を見直す  
2. §3.4 の later-proof / later-benchmark 約束を回収する  
3. Ridge--Eikonal から main pipeline への handoff を downstream chapters と一致させる  
4. cross-ref / reproducibility / 文体の残差を掃除する

この 4 点が片付けば、§1–§3 単体レビューとしては **Major revision -> Minor revision** まで進められる。
