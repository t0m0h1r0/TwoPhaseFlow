# Slide Source Map

| Slide | Lead claim | Audience source label | Manuscript source files |
|---:|---|---|---|
| 1 | CCD/FCCD/UCCD6を核にした二相流数値法 | Abstract; Introduction | paper/sections/00_abstract.tex; paper/sections/01_introduction.tex |
| 2 | 二相流の難しさは、界面が方程式の全項を同時に壊すことにある | Introduction | paper/sections/01_introduction.tex |
| 3 | 計算コアはCCDファミリ：微分・面フラックス・運動量対流 | Introduction; collocated face geometry; full algorithm | paper/sections/01_introduction.tex; paper/sections/08_collocate.tex; paper/sections/11_full_algorithm.tex |
| 4 | One-Fluid 表現は入口であり、圧力ジャンプの扱いが出口を決める | Governing equations; surface tension jump; CLS; split PPE | paper/sections/02_governing.tex; paper/sections/02b_surface_tension.tex; paper/sections/03_levelset.tex; paper/sections/09b_split_ppe.tex |
| 5 | CCD -> FCCD/UCCD6 が、この数値法の演算子コア | CCD, DCCD, UCCD6, and FCCD operator derivations | paper/sections/04_ccd.tex; paper/sections/04c_dccd_derivation.tex; paper/sections/04d_uccd6.tex; paper/sections/04e_fccd.tex |
| 6 | 界面追跡は、保存形輸送と距離関数修復を分けて設計する | CLS transport; Ridge-Eikonal; CLS stages; component verification | paper/sections/03b_cls_transport.tex; paper/sections/03d_ridge_eikonal.tex; paper/sections/05b_cls_stages.tex; paper/sections/12_component_verification.tex |
| 7 | 高密度比では、一括PPEではなく分相PPEとして圧力を閉じる | Split PPE; HFE; defect correction; component verification | paper/sections/09b_split_ppe.tex; paper/sections/09c_hfe.tex; paper/sections/09d_defect_correction.tex; paper/sections/12u6_split_ppe_dc_hfe.tex |
| 8 | Balanced-Force の条件は、同じface footprintを共有することに落ちる | Collocated face geometry; full algorithm; benchmark conditions | paper/sections/08_collocate.tex; paper/sections/11_full_algorithm.tex; paper/sections/14_benchmarks.tex |
| 9 | 1タイムステップは、界面面幾何を先に閉じてからNS更新へ渡す | Full algorithm | paper/sections/11_full_algorithm.tex |
| 10 | 単体検証は、CCDファミリと圧力閉包が単独で働くことを確認 | Component verification summary | paper/sections/12_component_verification.tex; paper/sections/12h_summary.tex |
| 11 | 統合検証は、合格領域・構造修正・設計限界を分けて読む | Integrated verification; error budget | paper/sections/13_verification.tex; paper/sections/13f_error_budget.tex |
| 12 | 寄生流れは、FD基準より小さい絶対スケールへ抑制 | Static droplet; density-ratio sweep; error budget | paper/sections/13b_twophase_static.tex; paper/sections/13d_density_ratio.tex; paper/sections/13f_error_budget.tex |
| 13 | 設計限界は、テストIDではなく物理的な誤差源として読む | Error budget; conclusion | paper/sections/13f_error_budget.tex; paper/sections/15_conclusion.tex |
| 14 | 物理ベンチマークは、毛管波の符号検証から次のゲートへ進む | Benchmark gates; conclusion | paper/sections/14_benchmarks.tex; paper/sections/15_conclusion.tex |
| 15 | 結論：高次化の本体は、演算子次数ではなく界面面契約の整合である | Conclusion | paper/sections/15_conclusion.tex |
