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

## Round 3: ユーザー指摘後の非語彙レビュー

判定: MAJOR なし。ただし MINOR 複数。

確認:
- 第4章の主張は「3点コンパクト性を基盤に、節点中心散逸系統（CCD/DCCD/UCCD6）と面中心系統（FCCD/面ジェット）を分け、後続章が使う評価位置を固定する」という線で通っている。
- DCCD は標準 CLS 移流・圧力面閉包の主演算子ではなく、節点中心 CCD の補助後置フィルタとして説明されている。
- UCCD6 は運動量の領域内部対流に使う節点中心散逸演算子、FCCD/面ジェットは面評価位置を後続章へ渡す形式として整理されている。

指摘:
- MINOR: `インターフェイス` が多く残り、再びソフトウェア仕様書的に見えた。面ジェットは数理的な受け渡し形式として説明すべき。
- MINOR: `アドホック`, `Corrector`, `for 2D`, `既存 CCD ソルバ再利用` など、英語・内部実装寄りの表現が残っていた。

対応:
- `インターフェイス` を「入出力形式」「受け渡し形式」「面入出力形式」に置換し、面ジェットを公開契約ではなく後続章の入力前提として読めるようにした。
- `アドホックな数値粘性` を「場当たり的な数値粘性」、`Corrector 発散` を「補正段発散」、`for 2D` を「2次元で」、`既存 CCD ソルバ再利用` を「CCD 求解器の再利用」に修正した。
- `bidiagonal node-to-face` を「二重対角の節点から面への差分」とし、FCCD の DFT 解析で英語主語彙が浮かないようにした。

## Round 4: 再レビュー

判定: MAJOR なし。

確認:
- 重点語彙スキャンで `契約`, `input contract`, `public contract`, `primitive`, `ロカス`, `post-filter`, `API`, `family`, `bulk`, `clamp`, `Stage`, `stencil residual`, `face-centered`, `formal 精度`, `Corrector`, `interface`, `インターフェイス`, `アドホック`, `for 2D` は検出されない。
- `git diff --check` は通過した。

残留リスク:
- `CCD`, `DCCD`, `FCCD`, `UCCD6`, `Fourier`, `Nyquist`, `Thomas`, `DFT`, `block-circulant`, `Face-centered CCD` は手法名・解析名として残る。日本語の役割説明と併記されているため、MAJOR ではない。
