# Ch14 capillary origin-reset next-session prompt

```text
Execute ResearchArchitect
---
[作業方針]
* この作業は新規ワークツリーで行うこと
* キリのいい単位でコミットしつつ進めること
* 指示があるまで main へのマージは行わないこと
* main マージしても、完了後はワークツリー同じで作業を続けること
* main へのマージは no ff で行うこと
* 失敗した実装の続きを惰性で進めず、必ず原点から理論を再構成すること

[最初に読むもの]
* docs/wiki/theory/WIKI-T-174.md
* docs/wiki/cross-domain/WIKI-X-056.md
* docs/wiki/cross-domain/WIKI-X-055.md
* artifacts/A/ch14_origin_reset_handoff_CHK-RA-CH14-ORIGIN-RESET-001.md

[目的]
Ch14 の毛管波・振動液滴 T/8 を、同じ計算思想で扱える理論から再構築する。
screened q/phi projection の失敗は事実として保持するが、それを既定路線として
修理し続けない。まず物理学・数学の原点に戻り、界面を所有する離散状態が
何であるべきかを決める。

[必須の理論検討]
* 連続問題の主役を、物質界面 Gamma(t)、表面エネルギー E[Gamma]、体積保存、
  非圧縮制約、圧力反力として書き直すこと
* phi は幾何を表すゲージ、q は有限体積セル上の測度であり、どちらを主変数に
  するかを先に決めること
* 次の二案を対等に比較すること
  1. interface-configuration primary: Gamma_h を所有し、q=Q_h(Gamma_h) を従属量にする
  2. cell-volume primary: q を所有し、表面エネルギー E_h[q] を q 空間で定義する
* 毛管波は graph chart、閉液滴は closed-curve chart として扱い、分岐条件ではなく
  同一変分原理の chart 違いとして整理すること
* 「閉曲面のときだけ」「screened Riesz が立っているときだけ」のような
  特殊条件を理論の本体にしないこと

[仮説創出]
少なくとも次を仮説表に入れること。
* transported q が滑らかな phi/graph chart で表現できない自由度を含んでいる
* graph rebuild の compat_linf=0 は、pre-rebuild q を保存したのではなく q を再定義している
* exact q projection が界面をガタガタにするのは、q を絶対視しすぎているため
* 表面エネルギーの変分と transport の主変数が一致していない
* moving-grid rebuild が、物質界面ではなくゲージ再構築を追っている
* 毛管波と閉液滴を別理論として扱っている
* 圧力・速度・face cochain・境界条件の空間が一致していない

[検証方針]
* いきなり長い T/8 実験に入らないこと
* まず最小の毛管波 oracle を作ること
  - eta(x) -> Q_h(eta)
  - E[eta]
  - delta E/delta eta
  - force sign, mode/phase, symmetry, energy trend
* oracle は可視化を必須にすること
* 毛管波 oracle が通ったら、同じ変分原理で閉液滴 chart を設計すること
* その後に Ch14 runtime へ接続し、T/8 振動を試すこと

[禁止]
* tolerance weakening
* smoothing / damping / curvature cap
* CFL retuning as the primary fix
* rebuild skipping
* FD/WENO/PPE family fallback
* hidden CPU fallback
* 見た目だけの可視化成功を合格にすること

[成果物]
* 理論再構築メモまたは artifact
* 仮説表と falsification 結果
* 毛管波 oracle の実装・可視化・検証結果
* 必要なら wiki 更新
* 実装に進む場合は、Equation -> Discretization -> Code の対応を明記すること
```
