import { makeSlide } from "./common.mjs";

const data = {
  "no": 13,
  "title": "設計限界は、テストIDではなく物理的な誤差源として読む",
  "lead": "時間精度は毛管圧力ジャンプとprojectionの界面帯に律速され、強変形CLSは固定格子の位相・細線解像限界に当たる。",
  "source": "Error budget; conclusion",
  "visual": "limitMap",
  "limits": [
    [
      "二相時間精度",
      "slope 1.48",
      "毛管pressure-jump/projection界面帯が支配"
    ],
    [
      "Zalesak形状",
      "centroid 4.911e-3",
      "slot under-resolution"
    ],
    [
      "単一渦形状",
      "L1 2.248e-2",
      "folded filament の固定格子限界"
    ]
  ]
};

export async function slide13(presentation, ctx) {
  return makeSlide(presentation, ctx, data);
}
