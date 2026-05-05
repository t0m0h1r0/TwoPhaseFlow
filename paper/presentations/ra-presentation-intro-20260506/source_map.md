# Slide Source Map

| Slide | Lead claim | Source |
|---:|---|---|
| 1 | 高次コンパクト差分に基づく気液二相流数値法 | paper/sections/00_abstract.tex; 01_introduction.tex |
| 2 | 二相流の難しさは、界面が方程式の全項を同時に壊すことにある | paper/sections/01_introduction.tex |
| 3 | 本研究の主張は、寄生流れを「調整」ではなく離散契約で抑えること | paper/sections/01_introduction.tex; 08_collocate.tex; 11_full_algorithm.tex |
| 4 | One-Fluid 表現は入口であり、圧力ジャンプの扱いが出口を決める | paper/sections/02_governing.tex; 02b_surface_tension.tex; 03_levelset.tex; 09b_split_ppe.tex |
| 5 | CCDファミリは、節点中心の高次性を面中心の保存形へ広げる | paper/sections/04_ccd.tex; 04c_dccd_derivation.tex; 04d_uccd6.tex; 04e_fccd.tex |
| 6 | 界面追跡は、保存形輸送と距離関数修復を分けて設計する | paper/sections/03b_cls_transport.tex; 03d_ridge_eikonal.tex; 05b_cls_stages.tex; 12_component_verification.tex |
| 7 | 高密度比では、一括PPEではなく分相PPEとして圧力を閉じる | paper/sections/09b_split_ppe.tex; 09c_hfe.tex; 09d_defect_correction.tex; 12u6_split_ppe_dc_hfe.tex |
| 8 | Balanced-Force の条件は、同じface footprintを共有することに落ちる | paper/sections/08_collocate.tex; 11_full_algorithm.tex; 14_benchmarks.tex |
| 9 | 1タイムステップは、界面面幾何を先に閉じてからNS更新へ渡す | paper/sections/11_full_algorithm.tex |
| 10 | 単体検証は、各primitiveが単独で設計どおり働くことを確認した | paper/sections/12_component_verification.tex; 12h_summary.tex |
| 11 | 統合検証は、合格領域と条件付き領域を分けて読む | paper/sections/13_verification.tex; 13f_error_budget.tex |
| 12 | 寄生流れは、FD基準より小さい絶対スケールへ抑制 | paper/sections/13b_twophase_static.tex; 13d_density_ratio.tex; 13f_error_budget.tex |
| 13 | 限界は隠さず、どの誤差源が支配するかを分離する | paper/sections/13f_error_budget.tex; 15_conclusion.tex |
| 14 | 物理ベンチマークは、毛管波の符号検証から次のゲートへ進む | paper/sections/14_benchmarks.tex; 15_conclusion.tex |
| 15 | 結論：高次化の本体は、演算子次数ではなく界面面契約の整合である | paper/sections/15_conclusion.tex |
