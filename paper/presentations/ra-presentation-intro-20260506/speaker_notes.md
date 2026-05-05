# Speaker Notes

## 1. CCD/FCCD/UCCD6を核にした二相流数値法

保存形界面追跡・Balanced-Force・pressure-jump分相PPEを、CCDファミリの面幾何で閉じる。

Source: Abstract; Introduction

## 2. 二相流の難しさは、界面が方程式の全項を同時に壊すことにある

密度・粘性・曲率・圧力ジャンプが同じ場所で不連続になるため、単相流の高次化だけでは寄生流れを止められない。

Source: Introduction

## 3. 計算コアはCCDファミリ：微分・面フラックス・運動量対流

CCDが節点微分、FCCDが面値/面勾配、UCCD6が運動量対流を担い、その上に圧力閉包と界面追跡を載せる。

Source: Introduction; collocated face geometry; full algorithm

## 4. One-Fluid 表現は入口であり、圧力ジャンプの扱いが出口を決める

CLS は界面を保存形に追跡し、Young--Laplace ジャンプは CSF 体積力ではなく pressure-jump として PPE に渡す。

Source: Governing equations; surface tension jump; CLS; split PPE

## 5. CCD -> FCCD/UCCD6 が、この数値法の演算子コア

CCDの高次微分を、FCCDの保存形face fluxとUCCD6の運動量対流へ展開する。DCCDは補助的な高波数制御に限定する。

Source: CCD, DCCD, UCCD6, and FCCD operator derivations

## 6. 界面追跡は、保存形輸送と距離関数修復を分けて設計する

FCCD flux-form で質量を運び、Ridge--Eikonal 再初期化で距離関数品質を戻す。

Source: CLS transport; Ridge-Eikonal; CLS stages; component verification

## 7. 高密度比では、一括PPEではなく分相PPEとして圧力を閉じる

相内Poisson、HFE場延長、欠陥補正DCを組み合わせ、ジャンプ条件をPPEとcorrectorが共有する。

Source: Split PPE; HFE; defect correction; component verification

## 8. Balanced-Force の条件は、同じface footprintを共有することに落ちる

圧力勾配、表面張力、HFE上流点、GFMジャンプを別々に作ると、同じ式を使っても釣合いは崩れる。

Source: Collocated face geometry; full algorithm; benchmark conditions

## 9. 1タイムステップは、界面面幾何を先に閉じてからNS更新へ渡す

7段更新は部品表ではなく、psi・phi・rho・mu・kappa・face-state の受け渡し契約である。

Source: Full algorithm

## 10. 単体検証は、CCDファミリと圧力閉包が単独で働くことを確認

基礎演算・非一様格子・静止液滴・圧力DCCD禁止を、式と観測指標の対応で確認した。

Source: Component verification summary

## 11. 統合検証は、合格領域・構造修正・設計限界を分けて読む

単に「全ケース合格」と言わず、通常合格、質量補正での合格、理論的限界に分解した。

Source: Integrated verification; error budget

## 12. 寄生流れは、FD基準より小さい絶対スケールへ抑制

静止液滴と密度比sweepでは、CCD/BF構成とpressure-jump stackの安定性を別々の指標で確認した。

Source: Static droplet; density-ratio sweep; error budget

## 13. 設計限界は、テストIDではなく物理的な誤差源として読む

時間精度は毛管圧力ジャンプとprojectionの界面帯に律速され、強変形CLSは固定格子の位相・細線解像限界に当たる。

Source: Error budget; conclusion

## 14. 物理ベンチマークは、毛管波の符号検証から次のゲートへ進む

向き付き affine jump は短時間の復元力符号を通したが、気泡上昇とRayleigh--Taylorは未完了検証として分離する。

Source: Benchmark gates; conclusion

## 15. 結論：高次化の本体は、演算子次数ではなく界面面契約の整合である

本研究は、CCD/FCCD/UCCD6を核に分相PPE+HFE+DC・Balanced-Force face subsystemを統合し、合格範囲と未解決範囲を検証軸として固定した。

Source: Conclusion

