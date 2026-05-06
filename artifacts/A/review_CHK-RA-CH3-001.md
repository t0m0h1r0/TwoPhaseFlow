# CHK-RA-CH3-001 — Chapter 3 Strict Narrative Review

Scope: `paper/sections/03_levelset.tex`, `03b_cls_transport.tex`, `03c_levelset_mapping.tex`, `03d_ridge_eikonal.tex`; adjacent checks against §2, §5, §10, §11, §13 only where needed.

## Round 1 Verdict: FAIL

Severity count: FATAL 1 / MAJOR 5 / MINOR 2.

### FATAL-1 — Coarea measure factor was written backwards
- Location: `paper/sections/03_levelset.tex:146`
- Original quote: `$\delta_\varepsilon(\phi)|\bnabla\phi|^{-1} = \delta_s$`
- Problem: the surface measure identity is `\delta(\phi)|\nabla\phi| = \delta_s`. With the Eikonal assumption the numerical value collapses to the same factor, but the written measure contract is mathematically wrong and would mislead later CSF/HFE arguments.
- Fix: corrected the coarea statement to `\delta_\varepsilon(\phi)|\bnabla\phi| = \delta_s`.

### MAJOR-1 — Chapter 3 still described the old DCCD/point-derivative transport path
- Location: `paper/sections/03b_cls_transport.tex:56-60`
- Original quote: `本稿の主実装では CLS 移流に Dissipative CCD ... 1ステップあたりの体積保存誤差は \Ord{h^5\Delta t}`
- Problem: latest §5/§11 standard path uses TVD-RK3 + FCCD shared face flux with projection-native face velocity, not DCCD point derivative transport. The old `O(h^5)` story also hid clamp/reinitialization/mass-closure residuals inside a single order claim.
- Fix: rewrote the transport narrative around FCCD shared face fluxes, projection-native `\bu_f^n`, and explicit residual separation into boundary, clamp, grid transfer, reinitialization, and Stage B/F mass closure.

### MAJOR-2 — Direct-ψ curvature and Eikonal quality were conflated
- Location: `paper/sections/03_levelset.tex:24-27`, `paper/sections/03c_levelset_mapping.tex:185-190`
- Original quote: `曲率精度の第一保証が再初期化品質（Eikonal 条件）にある`
- Problem: §2 theorem and §11 standard path make direct-ψ curvature independent of `|\nabla\phi|=1` as long as the interface-band ψ profile remains a monotone transform. Eikonal quality is the guarantee for the φ/HFE path, not the primary direct-ψ curvature guarantee.
- Fix: separated ψ-profile quality monitoring from φ/HFE Eikonal quality and clarified the role of `\varepsilon_{\mathrm{eff}}`.

### MAJOR-3 — Ridge--Eikonal was framed as a saturation fallback instead of the current geometry-repair stage
- Location: `paper/sections/03b_cls_transport.tex:115-120`, `paper/sections/03d_ridge_eikonal.tex:13-28`
- Original quote: `Ridge--Eikonal 補助場経路 ... にフォールバックする`
- Problem: this reads as an alternate low-order fallback, contradicting §5/§11 where Ridge--Eikonal/ξ-SDF/FMM distance reconstruction is the standard geometry repair when quality triggers require it.
- Fix: replaced fallback wording with standard geometry-repair language and tied reconstruction to quality triggers, topology changes, and Stage D/F closure.

### MAJOR-4 — Gaussian auxiliary width reused surface-tension notation
- Location: `paper/sections/03d_ridge_eikonal.tex:52-54`, `03d_ridge_eikonal.tex:239-247`
- Original quote: `ここで \sigma は相互作用スケール` and later `$\sigma\kappa/\varepsilon$`
- Problem: `\sigma` is already the surface-tension coefficient throughout the paper. Reusing it for the Gaussian width made the surface-tension discussion ambiguous.
- Fix: renamed the auxiliary Gaussian scale to `\sigma_\xi` and stated that §10's `\sigma_\text{eff}` is its nonuniform-grid version.

### MAJOR-5 — Ridge sets were treated as ordinary Morse critical points
- Location: `paper/sections/03d_ridge_eikonal.tex:96-143`
- Original quote: `\bnabla\xiridge=0`, `Morse 函数`, `Morse 指数`
- Problem: a smooth interface ridge is generally a Morse--Bott-type ridge manifold: normal Hessian negative, tangential directions degenerate. Treating it as isolated Morse critical points overclaims the topology theory and conflicts with the ridge surface geometry.
- Fix: rewrote the ridge definition, proposition, proof sketch, and degeneracy safeguard using regular ridge/Morse--Bott language and deterministic degenerate-ridge detection.

### MINOR-1 — Chapter opening understated that §3 must feed the latest standard algorithm
- Fix: rewrote the opening roadmap so §3 explicitly leads into §5/§11 standard stages.

### MINOR-2 — Research-log phrasing leaked into paper prose
- Fix: removed `7-step Step` wording and replaced it with stable section/stage references.

## Round 2 Verdict: PASS

Severity count: FATAL 0 / MAJOR 0 / MINOR 0.

Targeted rescans found no remaining MAJOR+ instances of old DCCD transport framing, fallback language, direct-ψ/Eikonal conflation, Gaussian-width/surface-tension collision, or ordinary-Morse overclaim in Chapter 3.

Validation: `git diff --check` passed; `make -C paper` passed (`paper/main.pdf`, 245 pages); fatal/error/undefined-control/overfull log scan passed.
