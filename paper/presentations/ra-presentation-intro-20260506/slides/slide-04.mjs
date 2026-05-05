import { makeSlide } from "./common.mjs";

const data = {
  "no": 4,
  "title": "One-Fluid 表現は入口であり、圧力ジャンプの扱いが出口を決める",
  "lead": "CLS は界面を保存形に追跡し、Young--Laplace ジャンプは CSF 体積力ではなく pressure-jump として PPE に渡す。",
  "source": "paper/sections/02_governing.tex; 02b_surface_tension.tex; 03_levelset.tex; 09b_split_ppe.tex",
  "visual": "equationFlow",
  "flow": [
    [
      "psi = H_e(-phi)",
      "保存形界面変数"
    ],
    [
      "kappa_lg",
      "HFE / direct-psi 曲率"
    ],
    [
      "j_gl = p_g - p_l",
      "-sigma kappa_lg"
    ],
    [
      "G(p) - B(j)",
      "affine jump corrector"
    ]
  ]
};

export async function slide04(presentation, ctx) {
  return makeSlide(presentation, ctx, data);
}
