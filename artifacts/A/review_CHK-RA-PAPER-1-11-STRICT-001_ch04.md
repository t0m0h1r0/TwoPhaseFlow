# CHK-RA-PAPER-1-11-STRICT-001 / Chapter 4 Review

対象:
- `paper/sections/04_ccd.tex`
- `paper/sections/04b_ccd_bc.tex`
- `paper/sections/04c_dccd_derivation.tex`
- `paper/sections/04d_uccd6.tex`
- `paper/sections/04e_fccd.tex`
- `paper/sections/04f_face_jet.tex`

## Round 1: 厳正レビュー

判定: MAJOR あり。

指摘:
- MAJOR: `入力契約`, `public contract`, `API`, `primitive`, `family`, `ロカス` が演算子章の本文に残っており、数学的な入出力条件と内部実装語が混ざって見える。第1章の用語方針に合わせ、評価位置・入力前提・公開インターフェイス・基盤量・系統へ統一すべき。
- MAJOR: DCCD の説明が `post-filter`, `spectral post-filter`, `clamp`, `Stage B/F` のまま残り、標準経路に入れない補助フィルタであるというナラティブが読みにくい。
- MAJOR: UCCD6/FCCD/面ジェットの比較で `bulk`, `family`, `formal`, `hyperviscosity`, `dispersion preservation` など英語主語彙が多く、節点中心系統と面中心系統の違いが日本語として掴みにくい。
- MAJOR: `MAC` 章ではないが、面ジェットを「公開契約」として説明しており、ユーザーが指摘した `contract` 系語彙と同じ問題を再発している。
- MINOR: `cancellation`, `bidiagonal`, `stencil residual`, `face-centered` は初学者向けロードマップから浮いているため、日本語主語彙へ寄せるべき。

対応:
- `契約/API/primitive/family/ロカス` を「入力前提」「公開インターフェイス」「基盤量」「系統」「評価位置」に置換した。
- DCCD の `post-filter` 系語彙を「後置フィルタ」「スペクトル後置フィルタ」に統一し、`clamp` と `Stage` は「値域制限」「段階」に直した。
- `bulk` は「領域内部」，`formal 精度` は「形式精度」，`dispersion preservation` は「分散精度の保持」に置換した。
- FCCD/面ジェットの説明では `cancellation`, `bidiagonal`, `face-centered`, `stencil residual` を「打ち消し」「二重対角」「面中心」「ステンシル残差」に置換した。
- 面ジェットは「公開契約」ではなく「公開インターフェイス」として説明し、後続章が仮定する入出力だけを明示した。

## Round 2: 再レビュー

判定: MAJOR なし。

確認:
- 第4章本文の重点語彙スキャンで `契約`, `input contract`, `public contract`, `primitive`, `プリミティブ`, `ロカス`, `post-filter`, `API`, `family`, `bulk`, `clamp`, `Stage`, `stencil residual`, `face-centered`, `formal 精度` は表示本文として検出されない。
- 残検出は既存ラベル `sec:uccd6_hyperviscosity` のみで、読者に表示される語ではない。
- 章の読み筋は「3 点コンパクト性 → 基底 CCD → 境界閉包 → DCCD 後置フィルタ → UCCD6 内部散逸 → FCCD 面中心化 → 面ジェット公開インターフェイス」に整理された。

残留リスク:
- `CCD`, `DCCD`, `FCCD`, `UCCD6`, `Fourier`, `Nyquist`, `Thomas` は手法名・解析名として残した。章内で役割が定義されており、MAJOR ではない。
