import { makeSlide } from "./common.mjs";

const data = {
  "no": 13,
  "title": "限界は隠さず、どの誤差源が支配するかを分離する",
  "lead": "二相時間精度はcapillary pressure-jump/projection界面帯に律速され、CLS形状復元は固定格子の位相・filament限界に当たる。",
  "source": "paper/sections/13f_error_budget.tex; 15_conclusion.tex",
  "visual": "limitMap",
  "limits": [
    [
      "V7",
      "slope 1.48",
      "BDF2単体ではなくcoupled-stack実効次数"
    ],
    [
      "V10-a",
      "centroid 4.911e-3",
      "Zalesak slot under-resolution"
    ],
    [
      "V10-b",
      "L1 2.248e-2",
      "folded filament の固定格子限界"
    ]
  ]
};

export async function slide13(presentation, ctx) {
  return makeSlide(presentation, ctx, data);
}
