# Speaker Notes

## 1. 高次コンパクト差分に基づく気液二相流数値法

保存形界面追跡・Balanced-Force・pressure-jump 分相PPEを、同じ面幾何で閉じる。

Source: paper/sections/00_abstract.tex; 01_introduction.tex

## 2. 二相流の難しさは、界面が方程式の全項を同時に壊すことにある

密度・粘性・曲率・圧力ジャンプが同じ場所で不連続になるため、単相流の高次化だけでは寄生流れを止められない。

Source: paper/sections/01_introduction.tex

## 3. 本研究の主張は、寄生流れを「調整」ではなく離散契約で抑えること

曲率・圧力・速度補正・界面輸送を face-space contract に集約し、Balanced-Force 条件を演算子レベルで保つ。

Source: paper/sections/01_introduction.tex; 08_collocate.tex; 11_full_algorithm.tex

## 4. One-Fluid 表現は入口であり、圧力ジャンプの扱いが出口を決める

CLS は界面を保存形に追跡し、Young--Laplace ジャンプは CSF 体積力ではなく pressure-jump として PPE に渡す。

Source: paper/sections/02_governing.tex; 02b_surface_tension.tex; 03_levelset.tex; 09b_split_ppe.tex

## 5. CCDファミリは、節点中心の高次性を面中心の保存形へ広げる

内点6次のCCDを起点に、DCCDで高波数を制御し、UCCD6とFCCDで運動量・界面フラックスを分担する。

Source: paper/sections/04_ccd.tex; 04c_dccd_derivation.tex; 04d_uccd6.tex; 04e_fccd.tex

## 6. 界面追跡は、保存形輸送と距離関数修復を分けて設計する

FCCD flux-form で質量を運び、Ridge--Eikonal 再初期化で距離関数品質を戻す。

Source: paper/sections/03b_cls_transport.tex; 03d_ridge_eikonal.tex; 05b_cls_stages.tex; 12_component_verification.tex

## 7. 高密度比では、一括PPEではなく分相PPEとして圧力を閉じる

相内Poisson、HFE場延長、欠陥補正DCを組み合わせ、ジャンプ条件をPPEとcorrectorが共有する。

Source: paper/sections/09b_split_ppe.tex; 09c_hfe.tex; 09d_defect_correction.tex; 12u6_split_ppe_dc_hfe.tex

## 8. Balanced-Force の条件は、同じface footprintを共有することに落ちる

圧力勾配、表面張力、HFE上流点、GFMジャンプを別々に作ると、同じ式を使っても釣合いは崩れる。

Source: paper/sections/08_collocate.tex; 11_full_algorithm.tex; 14_benchmarks.tex

## 9. 1タイムステップは、界面面幾何を先に閉じてからNS更新へ渡す

7段更新は部品表ではなく、psi・phi・rho・mu・kappa・face-state の受け渡し契約である。

Source: paper/sections/11_full_algorithm.tex

## 10. 単体検証は、各primitiveが単独で設計どおり働くことを確認した

U1--U9は、基礎演算から否定検証までをトポロジカルに並べ、式・離散化・観測指標を一対一に結んだ。

Source: paper/sections/12_component_verification.tex; 12h_summary.tex

## 11. 統合検証は、合格領域と条件付き領域を分けて読む

V1--V10は x ゼロだが、V7とV10の形状軸はType-Dとして設計限界を明示した。

Source: paper/sections/13_verification.tex; 13f_error_budget.tex

## 12. 寄生流れは、FD基準より小さい絶対スケールへ抑制

静止液滴と密度比sweepでは、CCD/BF構成とpressure-jump stackの安定性を別々の指標で確認した。

Source: paper/sections/13b_twophase_static.tex; 13d_density_ratio.tex; 13f_error_budget.tex

## 13. 限界は隠さず、どの誤差源が支配するかを分離する

二相時間精度はcapillary pressure-jump/projection界面帯に律速され、CLS形状復元は固定格子の位相・filament限界に当たる。

Source: paper/sections/13f_error_budget.tex; 15_conclusion.tex

## 14. 物理ベンチマークは、毛管波の符号検証から次のゲートへ進む

向き付き affine jump は短時間の復元力符号を通したが、気泡上昇とRayleigh--Taylorは未完了検証として分離する。

Source: paper/sections/14_benchmarks.tex; 15_conclusion.tex

## 15. 結論：高次化の本体は、演算子次数ではなく界面面契約の整合である

本研究は、CCD高次群・分相PPE+HFE+DC・Balanced-Force face subsystemを統合し、二相流で何が合格し何が未解決かを検証軸として固定した。

Source: paper/sections/15_conclusion.tex

